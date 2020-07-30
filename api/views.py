import logging
import uuid

from django.utils import timezone
from rest_framework import viewsets, status, mixins
from rest_framework.decorators import action
from rest_framework.response import Response

from api.serializers import CitySerializer, SceneSerializer, PassengerSerializer, TransportModeSerializer, \
    TransportNetworkOptimizationSerializer, TransportNetworkSerializer, RouteSerializer
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
                                             'scene_set__transportnetwork_set')

    @action(detail=True, methods=['POST'])
    def duplicate(self, request, public_id=None):
        new_city_obj = self.get_object()
        new_city_obj.id = None
        new_city_obj.created_at = timezone.now()
        new_city_obj.public_id = uuid.uuid4()
        new_city_obj.save()

        for scene_obj in new_city_obj.scene_set.all():
            scene_obj.id = None
            scene_obj.created_at = timezone.now()
            scene_obj.public_id = uuid.uuid4()
            scene_obj.city = new_city_obj
            scene_obj.save()

        return Response(CitySerializer(new_city_obj).data, status=status.HTTP_201_CREATED)


class SceneViewSet(mixins.RetrieveModelMixin, mixins.DestroyModelMixin, mixins.UpdateModelMixin,
                   mixins.CreateModelMixin, viewsets.GenericViewSet):
    """
    API endpoint to work with scenes
    """
    serializer_class = SceneSerializer
    lookup_field = 'public_id'
    queryset = Scene.objects.select_related('passenger').prefetch_related('transportmode_set')

    @action(detail=True, methods=['POST'])
    def duplicate(self, request, public_id=None):
        now = timezone.now()
        new_scene_obj = self.get_object()

        new_scene_obj.pk = None
        new_scene_obj.created_at = now
        new_scene_obj.public_id = uuid.uuid4()
        new_scene_obj.save()

        if new_scene_obj.passenger is not None:
            passenger_obj = new_scene_obj.passenger
            passenger_obj.pk = None
            passenger_obj.created_at = now
            passenger_obj.scene = new_scene_obj
            passenger_obj.save()

            new_scene_obj.passenger = passenger_obj
            new_scene_obj.save()

        for transport_mode_obj in self.get_object().transportmode_set.all():
            transport_mode_obj.pk = None
            transport_mode_obj.created_at = now
            transport_mode_obj.public_id = uuid.uuid4()
            transport_mode_obj.scene = new_scene_obj
            transport_mode_obj.save()

        # update reference to return correct transport mode instances
        new_scene_obj.refresh_from_db()

        return Response(SceneSerializer(new_scene_obj).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['POST'])
    def passenger(self, request, public_id=None):
        """ to manage passenger data """
        # create or update passenger parameters
        scene_obj = self.get_object()
        passenger_obj, created = Passenger.objects.get_or_create(scene=scene_obj, defaults=request.data)

        if created:
            status_code = status.HTTP_201_CREATED
        else:
            for attr in request.data:
                setattr(passenger_obj, attr, request.data[attr])
            passenger_obj.save()
            status_code = status.HTTP_200_OK

        return Response(PassengerSerializer(passenger_obj).data, status_code)

    @action(detail=True, methods=['POST'])
    def transport_mode(self, request, public_id=None):
        """ to manage transport modes """
        scene_obj = self.get_object()
        public_id = request.data.pop('public_id', None)
        if public_id is None:
            transport_mode_obj = TransportMode.objects.create(scene=scene_obj, **request.data)
            status_code = status.HTTP_201_CREATED
        else:
            transport_mode_obj = TransportMode.objects.get(public_id=public_id)
            for attr in request.data:
                setattr(transport_mode_obj, attr, request.data[attr])
            transport_mode_obj.save()
            status_code = status.HTTP_200_OK

        return Response(TransportModeSerializer(transport_mode_obj).data, status_code)

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


class RouteViewSet(mixins.RetrieveModelMixin, mixins.DestroyModelMixin, mixins.UpdateModelMixin,
                   mixins.CreateModelMixin, viewsets.GenericViewSet):
    """
    API endpoint to work with Route
    """
    serializer_class = RouteSerializer
    lookup_field = 'public_id'
    queryset = Route.objects.prefetch_related('transport_mode')

    def create(self, request, *args, **kwargs):
        parent_key = 'transport_network_public_id'
        request.data[parent_key] = kwargs[parent_key]
        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        parent_key = 'transport_network_public_id'
        request.data[parent_key] = kwargs[parent_key]
        return super().update(request, *args, **kwargs)
