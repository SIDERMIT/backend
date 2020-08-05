import logging

from rest_framework import serializers

from storage.models import City, Scene, Passenger, TransportMode, OptimizationResultPerMode, OptimizationResult, \
    Optimization, TransportNetwork, Route

logger = logging.getLogger(__name__)


class PassengerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Passenger
        fields = ('name', 'created_at', 'va', 'pv', 'pw', 'pa', 'pt', 'spv', 'spw', 'spa', 'spt')
        read_only_fields = ['created_at']


class TransportModeSerializer(serializers.ModelSerializer):
    scene_public_id = serializers.UUIDField(write_only=True)

    def validate_scene_public_id(self, value):
        try:
            scene_obj = Scene.objects.get(public_id=value)
        except Scene.DoesNotExist:
            raise serializers.ValidationError('Scene does not exist')

        return scene_obj

    def create(self, validated_data):
        scene_obj = validated_data.pop('scene_public_id')
        transport_mode_obj = TransportMode.objects.create(scene=scene_obj, **validated_data)

        return transport_mode_obj

    class Meta:
        model = TransportMode
        fields = (
            'name', 'created_at', 'public_id', 'b_a', 'co', 'c1', 'c2', 'v', 't', 'f_max', 'k_max', 'theta', 'tat', 'd',
            'scene_public_id')
        read_only_fields = ['created_at', 'public_id']


class RouteSerializer(serializers.ModelSerializer):
    transport_mode = TransportModeSerializer(many=False, read_only=True)
    transport_mode_public_id = serializers.UUIDField(write_only=True)
    transport_network_public_id = serializers.UUIDField(write_only=True)

    def validate_transport_mode_public_id(self, value):
        try:
            transport_mode_obj = TransportMode.objects.get(public_id=value)
        except TransportMode.DoesNotExist:
            raise serializers.ValidationError('Transport mode does not exist')

        return transport_mode_obj

    def validate_transport_network_public_id(self, value):
        try:
            transport_network_obj = TransportNetwork.objects.get(public_id=value)
        except TransportNetwork.DoesNotExist:
            raise serializers.ValidationError('Transport network does not exist')

        return transport_network_obj

    def create(self, validated_data):
        transport_mode_obj = validated_data.pop('transport_mode_public_id')
        transport_network_obj = validated_data.pop('transport_network_public_id')
        route_obj = Route.objects.create(transport_network=transport_network_obj, transport_mode=transport_mode_obj,
                                         **validated_data)

        return route_obj

    class Meta:
        model = Route
        fields = (
            'created_at', 'public_id', 'name', 'node_sequence_i', 'stop_sequence_i', 'node_sequence_r',
            'stop_sequence_r', 'transport_mode_public_id', 'transport_network_public_id', 'transport_mode')
        read_only_fields = ['created_at', 'public_id']


class TransportNetworkSerializer(serializers.ModelSerializer):
    route_set = RouteSerializer(many=True, read_only=True)
    scene_public_id = serializers.UUIDField(write_only=True)

    def validate_scene_public_id(self, value):
        try:
            scene_obj = Scene.objects.get(public_id=value)
        except Scene.DoesNotExist:
            raise serializers.ValidationError('Scene does not exist')

        return scene_obj

    def create(self, validated_data):
        scene_obj = validated_data.pop('scene_public_id')
        transport_network_obj = TransportNetwork.objects.create(scene=scene_obj, **validated_data)

        return transport_network_obj

    class Meta:
        model = TransportNetwork
        fields = ('name', 'created_at', 'route_set', 'scene_public_id')


class SceneSerializer(serializers.ModelSerializer):
    passenger = PassengerSerializer(read_only=True)
    transportmode_set = TransportModeSerializer(many=True, read_only=True)
    city_public_id = serializers.UUIDField(write_only=True)
    transportnetwork_set = TransportNetworkSerializer(many=True, read_only=True)

    class Meta:
        model = Scene
        fields = (
            'public_id', 'created_at', 'name', 'passenger', 'transportmode_set', 'city_public_id',
            'transportnetwork_set')
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


class CitySerializer(serializers.ModelSerializer):
    scene_set = SceneSerializer(many=True, read_only=True)

    class Meta:
        model = City
        fields = (
            'public_id', 'created_at', 'name', 'graph', 'demand_matrix', 'n', 'p', 'l', 'g', 'y', 'a', 'alpha', 'beta',
            'scene_set')
        read_only_fields = ['created_at', 'public_id', 'scene_set']


class OptimizationResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = OptimizationResult
        fields = ('vrc', 'co', 'ci', 'cu', 'tv', 'tw', 'ta', 't')


class OptimizationResultPerModeSerializer(serializers.ModelSerializer):
    transport_mode = serializers.SlugRelatedField(many=False, read_only=True, slug_field='name')

    class Meta:
        model = OptimizationResultPerMode
        fields = ('b', 'k', 'l', 'transport_mode')


class TransportNetworkOptimizationSerializer(serializers.ModelSerializer):
    transport_network = TransportNetworkSerializer(many=False)
    optimizationresult = OptimizationResultSerializer(many=False)
    optimizationresultpermode_set = OptimizationResultPerModeSerializer(many=True)

    class Meta:
        model = Optimization
        fields = ('status', 'created_at', 'transport_network', 'optimizationresult', 'optimizationresultpermode_set')


class RecentOptimizationSerializer(serializers.ModelSerializer):
    network_name = serializers.CharField(read_only=True, source='transport_network.name')
    network_public_id = serializers.CharField(read_only=True, source='transport_network.public_id')
    scene_name = serializers.CharField(read_only=True, source='transport_network.scene.name')
    scene_public_id = serializers.CharField(read_only=True, source='transport_network.scene.public_id')
    city_name = serializers.CharField(read_only=True, source='transport_network.scene.city.name')
    city_public_id = serializers.CharField(read_only=True, source='transport_network.scene.city.public_id')

    class Meta:
        model = Optimization
        fields = (
        'status', 'network_name', 'scene_name', 'city_name', 'network_public_id', 'scene_public_id', 'city_public_id')
