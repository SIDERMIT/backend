import logging

from rest_framework import serializers
from sidermit.city import Graph, GraphContentFormat, Demand
from sidermit.exceptions import SIDERMITException
from sidermit.publictransportsystem import TransportMode as SIDERMITTransportMode

from api.utils import get_network_descriptor
from storage.models import City, Scene, Passenger, TransportMode, OptimizationResultPerMode, OptimizationResult, \
    Optimization, TransportNetwork, Route

logger = logging.getLogger(__name__)


class PassengerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Passenger
        fields = ('va', 'pv', 'pw', 'pa', 'pt', 'spv', 'spw', 'spa', 'spt')


class TransportModeSerializer(serializers.ModelSerializer):

    def validate(self, attrs):
        try:
            SIDERMITTransportMode(**attrs)
        except (SIDERMITException, TypeError) as e:
            raise serializers.ValidationError(e)

        return attrs

    def create(self, validated_data):
        try:
            scene_obj = Scene.objects.get(public_id=self.context['view'].kwargs['scene_public_id'])
        except Scene.DoesNotExist:
            raise serializers.ValidationError('Scene does not exist')

        transport_mode_obj = TransportMode.objects.create(scene=scene_obj, **validated_data)

        return transport_mode_obj

    class Meta:
        model = TransportMode
        fields = (
            'name', 'created_at', 'public_id', 'bya', 'co', 'c1', 'c2', 'v', 't', 'fmax', 'kmax', 'theta', 'tat', 'd',
            'fini')
        read_only_fields = ['created_at', 'public_id']


class RouteSerializer(serializers.ModelSerializer):
    transport_mode = TransportModeSerializer(many=False, read_only=True)
    transport_mode_public_id = serializers.UUIDField(write_only=True)

    def validate_transport_mode_public_id(self, value):
        try:
            transport_mode_obj = TransportMode.objects.get(public_id=value)
        except TransportMode.DoesNotExist:
            raise serializers.ValidationError('Transport mode does not exist')

        return transport_mode_obj

    def create(self, validated_data):
        try:
            transport_network_obj = TransportNetwork.objects. \
                get(public_id=self.context['view'].kwargs['transport_network_public_id'])
        except TransportNetwork.DoesNotExist:
            raise serializers.ValidationError('Transport network does not exist')

        transport_mode_obj = validated_data.pop('transport_mode_public_id')
        route_obj = Route.objects.create(transport_network=transport_network_obj, transport_mode=transport_mode_obj,
                                         **validated_data)

        return route_obj

    class Meta:
        model = Route
        fields = (
            'created_at', 'public_id', 'name', 'node_sequence_i', 'stop_sequence_i', 'node_sequence_r',
            'stop_sequence_r', 'transport_mode_public_id', 'transport_mode')
        read_only_fields = ['created_at', 'public_id']


class TransportNetworkSerializer(serializers.ModelSerializer):
    route_set = RouteSerializer(many=True, read_only=True)
    scene_public_id = serializers.UUIDField(write_only=True)
    public_id = serializers.UUIDField(read_only=True)

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
        fields = ('name', 'created_at', 'route_set', 'scene_public_id', 'public_id')


class BaseCitySerializer(serializers.ModelSerializer):
    network_descriptor = serializers.SerializerMethodField()
    demand_matrix_header = serializers.SerializerMethodField()

    def get_network_descriptor(self, obj):
        """
        :return: list of nodes and edges based on parameters or graph variable
        """
        content = dict(nodes=[], edges=[])
        try:
            graph_obj = Graph.build_from_parameters(obj.n, obj.l, obj.g, obj.p, )
        except (SIDERMITException, TypeError):
            graph_obj = Graph.build_from_content(obj.graph, GraphContentFormat.PAJEK)

        if graph_obj is not None:
            content = get_network_descriptor(graph_obj)

        return content

    def get_demand_matrix_header(self, obj):
        content = []
        try:
            graph_obj = Graph.build_from_parameters(obj.n, obj.l, obj.g, obj.p, )
        except (SIDERMITException, TypeError):
            graph_obj = Graph.build_from_content(obj.graph, GraphContentFormat.PAJEK)

        if graph_obj is not None:
            for node_obj in graph_obj.get_nodes():
                content.append(node_obj.name)

        return content


class ShortCitySerializer(BaseCitySerializer):
    class Meta:
        model = City
        fields = ('public_id', 'name', 'demand_matrix', 'n', 'y', 'a', 'alpha', 'beta', 'network_descriptor',
                  'demand_matrix_header')


class SceneSerializer(serializers.ModelSerializer):
    passenger = PassengerSerializer()
    transportmode_set = TransportModeSerializer(many=True)
    city_public_id = serializers.UUIDField(write_only=True)
    transportnetwork_set = TransportNetworkSerializer(many=True, read_only=True)
    city = ShortCitySerializer(read_only=True)

    class Meta:
        model = Scene
        fields = (
            'public_id', 'created_at', 'name', 'passenger', 'transportmode_set', 'city_public_id',
            'transportnetwork_set', 'city')
        read_only_fields = ['created_at', 'public_id']

    def validate_city_public_id(self, value):
        try:
            city_obj = City.objects.get(public_id=value)
        except City.DoesNotExist:
            raise serializers.ValidationError('City does not exist')

        return city_obj

    def validate_transportmode_set(self, value):
        if len(value) == 0:
            raise serializers.ValidationError('You have to add at least one transport mode')

        return value

    def create(self, validated_data):
        city_obj = validated_data.pop('city_public_id')
        transport_mode_set = validated_data.pop('transportmode_set')
        passenger_data = validated_data.pop('passenger')
        scene_obj = Scene.objects.create(city=city_obj, **validated_data)
        Passenger.objects.create(scene=scene_obj, **passenger_data)
        transport_mode_list = []
        for transport_mode_data in transport_mode_set:
            transport_mode_list.append(TransportMode(scene=scene_obj, **transport_mode_data))
        TransportMode.objects.bulk_create(transport_mode_list)

        return scene_obj

    def update(self, instance, validated_data):
        # we do not update passenger data
        passenger_data = validated_data.pop('passenger')
        # update are made directly on transportmode api, so this field is not needed
        try:
            validated_data.pop('transportmode_set')
        except KeyError:
            pass

        scene_obj = super().update(instance, validated_data)

        passenger_serializer = PassengerSerializer(scene_obj.passenger, data=passenger_data, partial=True)
        passenger_serializer.is_valid(raise_exception=True)
        passenger_serializer.save()

        return scene_obj


class CitySerializer(BaseCitySerializer):
    scene_set = SceneSerializer(many=True, read_only=True)
    STEP_1 = 'step1'
    STEP_2 = 'step2'
    step = serializers.ChoiceField(write_only=True, choices=[(STEP_1, 'Step 1'), (STEP_2, 'Step 2')])

    def validate(self, validated_data):

        if validated_data.get('step') == self.STEP_1:
            key_exists = []
            keys = ['n', 'l', 'g', 'p']
            for key in keys:
                key_exists.append(validated_data.get(key) is None)

            try:
                if all(key_exists):
                    # if all keys are none, there are not parameters but graph has to exist
                    Graph.build_from_content(validated_data['graph'], GraphContentFormat.PAJEK)
                else:
                    # all parameters has to exist and the graph result has to match with parameters
                    if validated_data['graph'] != Graph.build_from_parameters(validated_data.get('n'),
                                                                              validated_data.get('l'),
                                                                              validated_data.get('g'),
                                                                              validated_data.get('p')):
                        serializers.ValidationError('Graph description does not match with parameters')
            except SIDERMITException as e:
                raise serializers.ValidationError(e)

        elif validated_data.get('step') == self.STEP_2:
            key_exists = []
            keys = ['y', 'a', 'alpha', 'beta']
            for key in keys:
                key_exists.append(validated_data.get(key) is None)

            try:
                public_id = self.context['view'].kwargs['public_id']
                graph_obj = Graph.build_from_content(City.objects.only('graph').get(public_id=public_id).graph,
                                                     GraphContentFormat.PAJEK)
                if all(key_exists):
                    # if all keys are none, there are not parameters but graph has to exist
                    Demand.build_from_parameters(graph_obj, validated_data.get('y'), validated_data.get('a'),
                                                 validated_data.get('alpha'), validated_data.get('beta'))
                else:
                    # all parameters has to exist and the graph result has to match with parameters
                    if validated_data['demand_matrix'] != Demand.build_from_parameters(graph_obj,
                                                                                       validated_data.get('y'),
                                                                                       validated_data.get('a'),
                                                                                       validated_data.get('alpha'),
                                                                                       validated_data.get('beta')):
                        serializers.ValidationError('Graph description does not match with parameters')
            except SIDERMITException as e:
                raise serializers.ValidationError(e)

        return validated_data

    def create(self, validated_data):
        validated_data.pop('step')
        return super().create(validated_data)

    class Meta:
        model = City
        fields = (
            'public_id', 'created_at', 'name', 'graph', 'demand_matrix', 'n', 'p', 'l', 'g', 'y', 'a', 'alpha', 'beta',
            'scene_set', 'network_descriptor', 'demand_matrix_header', 'step')
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
            'status', 'network_name', 'scene_name', 'city_name', 'network_public_id', 'scene_public_id',
            'city_public_id')
