import logging
import uuid

from django.utils import timezone
from rest_framework import viewsets, status, mixins
from rest_framework.decorators import action
from rest_framework.response import Response

from api.serializers import CitySerializer, SceneSerializer
from storage.models import City, Scene

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
        new_scene_obj = self.get_object()
        new_scene_obj.pk = None
        new_scene_obj.created_at = timezone.now()
        new_scene_obj.public_id = uuid.uuid4()
        new_scene_obj.save()

        if new_scene_obj.passenger is not None:
            passenger_obj = new_scene_obj.passenger
            passenger_obj.pk = None
            passenger_obj.created_at = timezone.now()
            passenger_obj.scene = new_scene_obj
            passenger_obj.save()

            new_scene_obj.passenger = passenger_obj

        new_scene_obj.save()

        for transport_mode_obj in self.get_object().transportmode_set.all():
            transport_mode_obj.pk = None
            transport_mode_obj.created_at = timezone.now()
            transport_mode_obj.scene = new_scene_obj
            transport_mode_obj.save()

        return Response(SceneSerializer(new_scene_obj).data, status=status.HTTP_201_CREATED)
