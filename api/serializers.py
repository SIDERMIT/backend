import logging

from rest_framework import serializers

from storage.models import City, Scene, Passenger, TransportMode

logger = logging.getLogger(__name__)


class CitySerializer(serializers.ModelSerializer):
    class Meta:
        model = City
        fields = (
            'public_id', 'created_at', 'name', 'graph', 'demand_matrix', 'n', 'p', 'l', 'g', 'y', 'a', 'alpha', 'beta')
        read_only_fields = ['created_at', 'public_id']


class PassengerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Passenger
        fields = ('name', 'va', 'pv', 'pw', 'pa', 'pt', 'spv', 'spw', 'spa', 'spt')


class TransportModeSerializer(serializers.ModelSerializer):
    class Meta:
        model = TransportMode
        fields = ('name', 'b_a', 'co', 'c1', 'c2', 'v', 't', 'f_max', 'k_max', 'theta', 'tat', 'd')
        read_only_fields = []


class SceneSerializer(serializers.ModelSerializer):
    passenger = PassengerSerializer(read_only=True)
    transportmode_set = TransportModeSerializer(many=True, read_only=True)
    city_public_id = serializers.UUIDField(write_only=True)

    class Meta:
        model = Scene
        fields = ('public_id', 'created_at', 'name', 'passenger', 'transportmode_set', 'city_public_id')
        read_only_fields = ['created_at', 'public_id']

    def validate_city_public_id(self, value):
        try:
            city_obj = City.objects.get(public_id=value)
        except City.DoesNotExist:
            raise serializers.ValidationError('City does not exist')

        return city_obj

    def create(self, validated_data):
        city_obj = validated_data.pop('city_public_id')
        scene_obj = Scene.objects.create(city=city_obj, **validated_data)

        return scene_obj
