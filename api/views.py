import logging
import uuid

from django.utils import timezone
from rest_framework import viewsets, status, mixins
from rest_framework.decorators import action, api_view
from rest_framework.exceptions import ParseError
from rest_framework.response import Response
from sidermit.city import Graph, GraphContentFormat, Demand
from sidermit.exceptions import SIDERMITException
from sidermit.publictransportsystem import TransportMode as SIDERMITTransportMode

from api.serializers import CitySerializer, SceneSerializer, TransportModeSerializer, \
    TransportNetworkOptimizationSerializer, TransportNetworkSerializer, RouteSerializer, RecentOptimizationSerializer
from api.utils import get_network_descriptor
from storage.models import City, Scene, Passenger, TransportMode, TransportNetwork, Route
from storage.models import Optimization

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
    def build_graph_file(self, request):
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
                    row.append(demand_matrix[str(i)][str(j)])
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
        rows = []
        for transport_network in TransportNetwork.objects.filter(scene=scene_obj). \
                prefetch_related('optimization__optimizationresultpermode_set__transport_mode'). \
                select_related('optimization__optimizationresult'):
            try:
                rows.append(TransportNetworkOptimizationSerializer(transport_network.optimization).data)
            except Optimization.DoesNotExist:
                pass

        return Response(rows, status.HTTP_200_OK)


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
    def create_default_routes(self, request, public_id=None):
        """ create defaults routes """
        transport_network_obj = self.get_object()

        # TODO: use sidermit library to create route in database and after that return list of objects
        # Route.objects.create()
        rows = []

        return Response(rows, status.HTTP_200_OK)


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
    optimizations = Optimization.objects.select_related('transport_network__scene__city').order_by('-created_at')[:4]
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
    try:
        name = request.query_params.get('name')
        b_a = int(request.query_params.get('b_a'))
        co = float(request.query_params.get('co'))
        c1 = float(request.query_params.get('c1'))
        c2 = float(request.query_params.get('c2'))
        v = float(request.query_params.get('v'))
        t = float(request.query_params.get('t'))
        f_max = float(request.query_params.get('f_max'))
        k_max = float(request.query_params.get('k_max'))
        theta = float(request.query_params.get('theta'))
        tat = float(request.query_params.get('tat'))
        d = int(request.query_params.get('d'))
        f_ini = float(request.query_params.get('f_ini'))

        SIDERMITTransportMode(name, b_a, co, c1, c2, v, t, f_max, k_max, theta, tat, d, f_ini)
    except (SIDERMITException, TypeError) as e:
        raise ParseError(e)

    return Response({})


@api_view()
def validate_passenger(request):
    return Response({})


@api_view()
def validate_route(request):
    return Response({})
