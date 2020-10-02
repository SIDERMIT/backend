import logging

from django.db import transaction
from rest_framework import serializers
from sidermit.city import Graph, GraphContentFormat, Demand
from sidermit.exceptions import SIDERMITException
from sidermit.publictransportsystem import TransportMode as SIDERMITTransportMode, RouteType as SidermitRouteType

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

    class Meta:
        model = Route
        fields = (
            'created_at', 'public_id', 'name', 'nodes_sequence_i', 'stops_sequence_i', 'nodes_sequence_r',
            'stops_sequence_r', 'transport_mode_public_id', 'transport_mode', 'type')
        read_only_fields = ['created_at']


class TransportNetworkSerializer(serializers.ModelSerializer):
    route_set = RouteSerializer(many=True)
    scene_public_id = serializers.UUIDField(write_only=True)
    optimization_status = serializers.CharField(source='optimization.status', read_only=True)

    def validate_scene_public_id(self, value):
        try:
            scene_obj = Scene.objects.select_related('city').prefetch_related('transportmode_set').get(public_id=value)
        except Scene.DoesNotExist:
            raise serializers.ValidationError('Scene does not exist')

        return scene_obj

    def validate(self, attrs):
        previous_data = attrs.copy()
        try:
            try:
                scene_obj = previous_data.pop('scene_public_id')
            except KeyError:
                # key does not exists so it is a validation for update
                scene_obj = TransportNetwork.objects.select_related('scene__city'). \
                    get(public_id=self.context['view'].kwargs['public_id']).scene

            route_set = previous_data.pop('route_set')

            transportmode_dict = {tm.public_id: (tm, tm.get_sidermit_transport_mode()) for tm in
                                  scene_obj.transportmode_set.all()}

            transport_network_obj = TransportNetwork(scene=scene_obj, **previous_data)
            sidermit_network_obj = transport_network_obj.get_sidermit_network(scene_obj.city.get_sidermit_graph())
            for route in route_set:
                try:
                    transport_mode_obj, sidermit_transport_mode = transportmode_dict[route['transport_mode_public_id']]
                except KeyError:
                    raise serializers.ValidationError('Transport mode does not exist')
                route_obj = Route(transport_network=transport_network_obj, transport_mode=transport_mode_obj,
                                  name=route['name'],
                                  nodes_sequence_i=route['nodes_sequence_i'],
                                  stops_sequence_i=route['stops_sequence_i'],
                                  nodes_sequence_r=route['nodes_sequence_r'],
                                  stops_sequence_r=route['stops_sequence_r'])
                sidermit_network_obj.add_route(
                    route_obj.get_sidermit_route(sidermit_transport_mode, SidermitRouteType(int(route['type']))))

        except SIDERMITException as e:
            raise serializers.ValidationError(e)

        return attrs

    def update(self, instance, validated_data):
        route_set = validated_data.pop('route_set')

        with transaction.atomic():
            # update attributes of transport network
            for key in validated_data:
                setattr(instance, key, validated_data.get(key))
            instance.save()

            route_public_id_list = []
            for route in route_set:
                transport_mode_public_id = route.pop('transport_mode_public_id')
                transport_mode_obj = TransportMode.objects.get(public_id=transport_mode_public_id)
                if 'public_id' in route:
                    public_id = route.pop('public_id')
                    route_public_id_list.append(public_id)
                    Route.objects.filter(public_id=public_id).update(transport_mode=transport_mode_obj, **route)
                else:
                    route_obj = Route.objects.create(transport_mode=transport_mode_obj, transport_network=instance,
                                                     **route)
                    route_public_id_list.append(route_obj.public_id)

            Route.objects.filter(transport_network=instance).exclude(public_id__in=route_public_id_list).delete()

        return instance

    def create(self, validated_data):
        # ignore public_id if exists
        try:
            validated_data.pop('public_id')
        except KeyError:
            pass
        route_set = validated_data.pop('route_set')
        scene_obj = validated_data.pop('scene_public_id')

        with transaction.atomic():
            transport_network_obj = TransportNetwork.objects.create(scene=scene_obj, **validated_data)
            route_list = []
            for route in route_set:
                transport_mode_obj = TransportMode.objects.get(public_id=route['transport_mode_public_id'])
                route_obj = Route(transport_network=transport_network_obj, transport_mode=transport_mode_obj,
                                  name=route['name'],
                                  nodes_sequence_i=route['nodes_sequence_i'],
                                  stops_sequence_i=route['stops_sequence_i'],
                                  nodes_sequence_r=route['nodes_sequence_r'],
                                  stops_sequence_r=route['stops_sequence_r'],
                                  type=int(route['type']))
                route_list.append(route_obj)
            Route.objects.bulk_create(route_list)

        return transport_network_obj

    class Meta:
        model = TransportNetwork
        fields = ('name', 'created_at', 'route_set', 'scene_public_id', 'public_id', 'optimization_status')
        read_only_fields = ['created_at', 'optimization_status']


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
