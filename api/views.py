import logging
import uuid

from django.utils import timezone
from rest_framework import viewsets, status, mixins
from rest_framework.decorators import action, api_view
from rest_framework.exceptions import ParseError, ValidationError
from rest_framework.response import Response
from sidermit.city import Graph, GraphContentFormat, Demand
from sidermit.exceptions import SIDERMITException
from sidermit.publictransportsystem import TransportNetwork as SidermitTransportNetwork

from api.serializers import CitySerializer, SceneSerializer, TransportModeSerializer, \
    TransportNetworkSerializer, RouteSerializer, RecentOptimizationSerializer, \
    TransportNetworkOptimizationSerializer, OptimizationResultPerRoute, OptimizationResultPerRouteSerializer
from api.utils import get_network_descriptor
from rqworkers.jobs import optimize_transport_network
from storage.models import City, Scene, Passenger, TransportMode, TransportNetwork, Route

logger = logging.getLogger(__name__)


class CityViewSet(viewsets.ModelViewSet):
    """
    API endpoint to work with cities
    """
    serializer_class = CitySerializer
    lookup_field = 'public_id'
    queryset = City.objects.prefetch_related('scene_set__transportmode_set',
                                             'scene_set__passenger',
                                             'scene_set__transportnetwork_set').order_by('-created_at')

    def get_queryset(self):
        queryset = super().get_queryset()
        limit = self.request.query_params.get('limit')
        if limit is not None:
            try:
                queryset = queryset[:int(limit)]
            except ValueError:
                pass

        return queryset

    @action(detail=True, methods=['POST'])
    def duplicate(self, request, public_id=None):
        new_city_obj = self.get_object()
        new_city_obj.id = None
        new_city_obj.created_at = timezone.now()
        new_city_obj.public_id = uuid.uuid4()
        new_city_obj.name = '{0} copy'.format(new_city_obj.name)
        new_city_obj.save()

        for scene_obj in new_city_obj.scene_set.all():
            scene_obj.id = None
            scene_obj.created_at = timezone.now()
            scene_obj.public_id = uuid.uuid4()
            scene_obj.city = new_city_obj
            scene_obj.save()

        return Response(CitySerializer(new_city_obj).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['GET'])
    def build_graph_file_from_parameters(self, request):
        try:
            n = int(request.query_params.get('n'))
            l = float(request.query_params.get('l'))
            p = float(request.query_params.get('p'))
            g = float(request.query_params.get('g'))

            graph_obj = Graph.build_from_parameters(n, l, g, p, None, None, None, None, None)
            content = graph_obj.export_graph(GraphContentFormat.PAJEK)
            network = get_network_descriptor(graph_obj)
        except (ValueError, SIDERMITException) as e:
            raise ParseError(e)
        except TypeError:
            raise ParseError('Parameter can not be empty')

        return Response({'pajek': content, 'network': network}, status.HTTP_200_OK)

    @action(detail=False, methods=['GET'])
    def network_data_from_pajek_file(self, request):
        try:
            graph_content = request.query_params.get('graph')

            graph_obj = Graph.build_from_content(graph_content, GraphContentFormat.PAJEK)
            network = get_network_descriptor(graph_obj)
            n, l, g, p, _, _, _, _, _ = graph_obj.get_parameters()
        except (ValueError, SIDERMITException) as e:
            raise ParseError(e)

        return Response({'network': network, 'n': n, 'l': l, 'p': p, 'g': g},
                        status.HTTP_200_OK)

    @action(detail=True, methods=['GET'])
    def build_matrix_file(self, request, public_id=None):
        try:
            y = int(request.query_params.get('y'))
            a = float(request.query_params.get('a'))
            alpha = float(request.query_params.get('alpha'))
            beta = float(request.query_params.get('beta'))

            city_obj = self.get_object()
            graph_obj = Graph.build_from_content(city_obj.graph, GraphContentFormat.PAJEK)

            demand_obj = Demand.build_from_parameters(graph_obj, y, a, alpha, beta)
            demand_matrix = demand_obj.get_matrix()
            # pass matrix dict to list of list
            demand_matrix_data = []
            size = len(demand_matrix.keys())
            for i in range(size):
                row = []
                for j in range(size):
                    row.append(demand_matrix[i][j])
                demand_matrix_data.append(row)

            demand_matrix_header = [node_obj.name for node_obj in graph_obj.get_nodes()]
        except (ValueError, SIDERMITException) as e:
            raise ParseError(e)
        except TypeError:
            raise ParseError('Parameter can not be empty')

        return Response({'demand_matrix': demand_matrix_data, 'demand_matrix_header': demand_matrix_header},
                        status.HTTP_200_OK)


class SceneViewSet(mixins.RetrieveModelMixin, mixins.DestroyModelMixin, mixins.UpdateModelMixin,
                   mixins.CreateModelMixin, viewsets.GenericViewSet):
    """
    API endpoint to work with scenes
    """
    serializer_class = SceneSerializer
    lookup_field = 'public_id'
    queryset = Scene.objects.select_related('passenger', 'city').prefetch_related('transportmode_set',
                                                                                  'transportnetwork_set__route_set')

    @action(detail=True, methods=['POST'])
    def duplicate(self, request, public_id=None):
        now = timezone.now()
        new_scene_obj = self.get_object()

        new_scene_obj.pk = None
        new_scene_obj.created_at = now
        new_scene_obj.public_id = uuid.uuid4()
        new_scene_obj.name = '{0} copy'.format(new_scene_obj.name)
        new_scene_obj.save()

        try:
            passenger_obj = new_scene_obj.passenger
            passenger_obj.pk = None
            passenger_obj.created_at = now
            passenger_obj.scene = new_scene_obj
            passenger_obj.save()

            new_scene_obj.passenger = passenger_obj
            new_scene_obj.save()
        except Passenger.DoesNotExist:
            pass

        for transport_mode_obj in self.get_object().transportmode_set.all():
            transport_mode_obj.pk = None
            transport_mode_obj.created_at = now
            transport_mode_obj.public_id = uuid.uuid4()
            transport_mode_obj.scene = new_scene_obj
            transport_mode_obj.save()

        # update reference to return correct transport mode instances
        new_scene_obj.refresh_from_db()

        return Response(SceneSerializer(new_scene_obj).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['GET'])
    def global_results(self, request, public_id=None):
        """ summarize results of optimizations in all transport networks """
        scene_obj = self.get_object()
        queryset = TransportNetwork.objects.select_related('optimizationresult').prefetch_related(
            'optimizationresultpermode_set__transport_mode').filter(scene=scene_obj, optimization_status__isnull=False)
        rows = TransportNetworkOptimizationSerializer(queryset, many=True).data
        response = dict(scene=SceneSerializer(scene_obj).data, rows=rows)

        return Response(response, status.HTTP_200_OK)


class TransportModeViewSet(mixins.RetrieveModelMixin, mixins.DestroyModelMixin, mixins.UpdateModelMixin,
                           mixins.CreateModelMixin, viewsets.GenericViewSet):
    """
    API endpoint to work with transport modes
    """
    serializer_class = TransportModeSerializer
    lookup_field = 'public_id'
    queryset = TransportMode.objects.all()


class TransportNetworkViewSet(mixins.RetrieveModelMixin, mixins.DestroyModelMixin, mixins.UpdateModelMixin,
                              mixins.CreateModelMixin, viewsets.GenericViewSet):
    """
    API endpoint to work with transport networks
    """
    serializer_class = TransportNetworkSerializer
    lookup_field = 'public_id'
    queryset = TransportNetwork.objects.prefetch_related('route_set__transport_mode')

    @action(detail=True, methods=['POST'])
    def duplicate(self, request, public_id=None):
        now = timezone.now()
        new_transport_network_obj = self.get_object()

        new_transport_network_obj.pk = None
        new_transport_network_obj.name = '{0} copy'.format(new_transport_network_obj.name)
        new_transport_network_obj.optimization_status = None
        new_transport_network_obj.optimization_ran_at = None
        new_transport_network_obj.created_at = now
        new_transport_network_obj.public_id = uuid.uuid4()
        new_transport_network_obj.save()

        for route_obj in self.get_object().route_set.all():
            route_obj.pk = None
            route_obj.transport_network = new_transport_network_obj
            route_obj.created_at = now
            route_obj.save()

        # update reference to return correct transport mode instances
        new_transport_network_obj.refresh_from_db()

        return Response(TransportNetworkSerializer(new_transport_network_obj).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['POST'])
    def create_default_routes(self, request):
        """ create defaults routes """
        default_routes = request.data.get('default_routes', [])
        scene_public_id = request.data.get('scene_public_id')

        scene_obj = Scene.objects.select_related('city').get(public_id=scene_public_id)

        graph_obj = scene_obj.city.get_sidermit_graph()
        network_obj = SidermitTransportNetwork(graph_obj)

        transport_mode_dict = dict()

        try:
            route_tuple = []
            all_routes = []
            for default_route in default_routes:
                transport_mode_public_id = default_route['transportMode']
                if transport_mode_public_id not in transport_mode_dict:
                    transport_mode_obj = TransportMode.objects.get(public_id=transport_mode_public_id)
                    transport_mode_dict[transport_mode_public_id] = transport_mode_obj.get_sidermit_transport_mode()

                if default_route['type'] == 'Feeder':
                    route_tuple.append((network_obj.get_feeder_routes(transport_mode_dict[transport_mode_public_id]),
                                        transport_mode_public_id))
                elif default_route['type'] == 'Circular':
                    route_tuple.append((network_obj.get_circular_routes(transport_mode_dict[transport_mode_public_id]),
                                        transport_mode_public_id))
                elif default_route['type'] == 'Radial':
                    route_tuple.append((network_obj.get_radial_routes(transport_mode_dict[transport_mode_public_id],
                                                                      short=default_route['extension'],
                                                                      express=default_route['odExclusive']),
                                        transport_mode_public_id))
                elif default_route['type'] == 'Diametral':
                    route_tuple.append((network_obj.get_diametral_routes(transport_mode_dict[transport_mode_public_id],
                                                                         jump=default_route['zoneJumps'],
                                                                         short=default_route['extension'],
                                                                         express=default_route['odExclusive']),
                                        transport_mode_public_id))
                elif default_route['type'] == 'Tangential':
                    route_tuple.append((network_obj.get_tangencial_routes(transport_mode_dict[transport_mode_public_id],
                                                                          jump=default_route['zoneJumps'],
                                                                          short=default_route['extension'],
                                                                          express=default_route['odExclusive']),
                                        transport_mode_public_id))
                else:
                    raise ParseError('type "{0}" is not valid.'.format(default_route['type']))

            for (routes, transport_mode_public_id) in route_tuple:
                for route in routes:
                    all_routes.append(
                        dict(name=route.id, transport_mode_public_id=transport_mode_public_id,
                             nodes_sequence_i=','.join(str(x) for x in route.nodes_sequence_i),
                             nodes_sequence_r=','.join(str(x) for x in route.nodes_sequence_r),
                             stops_sequence_i=','.join(str(x) for x in route.stops_sequence_i),
                             stops_sequence_r=','.join(str(x) for x in route.stops_sequence_r),
                             type=3 if route._type.value == 3 else 1))
        except SIDERMITException as e:
            raise ParseError(e)
        except TransportMode.DoesNotExist:
            raise ParseError('Transport mode does not exist')

        return Response(all_routes, status.HTTP_200_OK)

    @action(detail=True, methods=['POST'])
    def run_optimization(self, request, public_id=None):
        transport_network_obj = self.get_object()

        if transport_network_obj.optimization_status in [TransportNetwork.STATUS_QUEUED,
                                                         TransportNetwork.STATUS_PROCESSING]:
            raise ValidationError("Transport network is queued or processing at this moment")

        transport_network_obj.optimization_status = TransportNetwork.STATUS_QUEUED
        transport_network_obj.save()

        # async task
        optimize_transport_network.delay(transport_network_obj.public_id)

        return Response(TransportNetworkSerializer(transport_network_obj).data, status.HTTP_201_CREATED)

    @action(detail=True, methods=['POST'])
    def cancel_optimization(self, request, public_id=None):
        transport_network_obj = self.get_object()
        if transport_network_obj.optimization_status in [TransportNetwork.STATUS_ERROR,
                                                         TransportNetwork.STATUS_FINISHED]:
            raise ValidationError('Optimization is not running or queued')

        transport_network_obj.optimization_status = None
        transport_network_obj.optimization_ran_at = None
        transport_network_obj.optimization_error_message = None
        transport_network_obj.save()

        return Response(TransportNetworkSerializer(transport_network_obj).data, status.HTTP_200_OK)

    @action(detail=True, methods=['GET'])
    def results(self, request, public_id=None):
        transport_network_obj = self.get_object()

        opt_result = TransportNetworkOptimizationSerializer(transport_network_obj).data
        opt_result_per_route = OptimizationResultPerRouteSerializer(
            OptimizationResultPerRoute.objects.select_related('route').prefetch_related(
                'optimizationresultperroutedetail_set').filter(transport_network=transport_network_obj), many=True).data

        return Response(dict(opt_result=opt_result, opt_result_per_route=opt_result_per_route), status.HTTP_200_OK)


class RouteViewSet(mixins.RetrieveModelMixin, mixins.DestroyModelMixin, mixins.UpdateModelMixin,
                   mixins.CreateModelMixin, viewsets.GenericViewSet):
    """
    API endpoint to work with Route
    """
    serializer_class = RouteSerializer
    lookup_field = 'public_id'
    queryset = Route.objects.prefetch_related('transport_mode')


@api_view()
def recent_optimizations(request):
    optimizations = TransportNetwork.objects.select_related('scene__city'). \
                        exclude(optimization_ran_at__isnull=True).order_by('-optimization_ran_at')[:4]
    return Response(RecentOptimizationSerializer(optimizations, many=True).data)


@api_view()
def validate_graph_parameters(request):
    return Response({})


@api_view()
def validate_graph_file(request):
    return Response({})


@api_view()
def validate_matrix_parameters(request):
    return Response({})


@api_view()
def validate_matrix_parameters(request):
    return Response({})


@api_view()
def validate_transport_mode(request):
    transport_mode_serializer_obj = TransportModeSerializer(data=request.query_params)
    transport_mode_serializer_obj.is_valid(raise_exception=True)

    return Response({})


@api_view()
def validate_passenger(request):
    return Response({})


@api_view()
def validate_route(request):
    return Response({})
