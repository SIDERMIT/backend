import logging

from django.db import transaction, IntegrityError
from rest_framework import serializers
from sidermit.city import Graph, GraphContentFormat, Demand
from sidermit.exceptions import SIDERMITException
from sidermit.publictransportsystem import TransportMode as SIDERMITTransportMode, Passenger as SIDERMITPassenger

from api.utils import get_network_descriptor
from storage.models import City, Scene, Passenger, TransportMode, OptimizationResultPerMode, OptimizationResult, \
    TransportNetwork, Route, OptimizationResultPerRoute, OptimizationResultPerRouteDetail

logger = logging.getLogger(__name__)


class PassengerSerializer(serializers.ModelSerializer):

    def validate(self, attrs):
        try:
            SIDERMITPassenger(**attrs)
        except (SIDERMITException, TypeError) as e:
            raise serializers.ValidationError(e)

        return attrs

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

        try:
            transport_mode_obj = TransportMode.objects.create(scene=scene_obj, **validated_data)
        except IntegrityError:
            raise serializers.ValidationError('Name "{0}" can not be duplicated'.format(validated_data.get('name')))

        return transport_mode_obj

    class Meta:
        model = TransportMode
        fields = (
            'name', 'created_at', 'public_id', 'bya', 'co', 'c1', 'c2', 'v', 't', 'fmax', 'kmax', 'theta', 'tat', 'd',
            'fini')
        read_only_fields = ['created_at', 'public_id']


class RouteSerializer(serializers.ModelSerializer):
    transport_mode = TransportModeSerializer(many=False, read_only=True)
    transport_mode_public_id = serializers.UUIDField(source='transport_mode.public_id')
    nodes_sequence_i = serializers.CharField(allow_blank=True)
    stops_sequence_i = serializers.CharField(allow_blank=True)
    nodes_sequence_r = serializers.CharField(allow_blank=True)
    stops_sequence_r = serializers.CharField(allow_blank=True)

    class Meta:
        model = Route
        fields = (
            'created_at', 'public_id', 'name', 'nodes_sequence_i', 'stops_sequence_i', 'nodes_sequence_r',
            'stops_sequence_r', 'transport_mode_public_id', 'transport_mode', 'type')
        read_only_fields = ['created_at']


class TransportNetworkSerializer(serializers.ModelSerializer):
    route_set = RouteSerializer(many=True)
    scene_public_id = serializers.UUIDField(write_only=True)

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
                    transport_mode_public_id = route['transport_mode']['public_id']
                    transport_mode_obj, sidermit_transport_mode = transportmode_dict[transport_mode_public_id]
                except KeyError:
                    raise serializers.ValidationError('Transport mode does not exist')
                route_obj = Route(transport_network=transport_network_obj, transport_mode=transport_mode_obj,
                                  name=route['name'], type=int(route['type']),
                                  nodes_sequence_i=route['nodes_sequence_i'],
                                  stops_sequence_i=route['stops_sequence_i'],
                                  nodes_sequence_r=route['nodes_sequence_r'],
                                  stops_sequence_r=route['stops_sequence_r'])
                sidermit_network_obj.add_route(route_obj.get_sidermit_route(sidermit_transport_mode))

        except SIDERMITException as e:
            raise serializers.ValidationError(e)

        return attrs

    def update(self, instance, validated_data):
        route_set = validated_data.pop('route_set')

        with transaction.atomic():
            # check if has results
            if instance.optimization_status in [TransportNetwork.STATUS_QUEUED, TransportNetwork.STATUS_PROCESSING,
                                                TransportNetwork.STATUS_FINISHED]:
                raise serializers.ValidationError(
                    'Transport network "{0}" can not be modified when is queued, processing or has results'.format(
                        instance.name))

            # update attributes of transport network
            for key in validated_data:
                setattr(instance, key, validated_data.get(key))

            if instance.optimization_status == TransportNetwork.STATUS_ERROR:
                instance.optimization_status = None
                instance.optimization_ran_at = None
                instance.optimization_error_message = None
                instance.duration = None
            instance.save()

            route_public_id_list = []
            for route in route_set:
                transport_mode_public_id = route.pop('transport_mode')['public_id']
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
                transport_mode_obj = TransportMode.objects.get(public_id=route['transport_mode']['public_id'])
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
        fields = (
            'name', 'created_at', 'route_set', 'scene_public_id', 'public_id', 'optimization_status',
            'optimization_ran_at', 'optimization_error_message')
        read_only_fields = ['created_at', 'optimization_status', 'optimization_ran_at', 'optimization_error_message']


class BaseCitySerializer(serializers.ModelSerializer):
    network_descriptor = serializers.SerializerMethodField()
    demand_matrix_header = serializers.SerializerMethodField()

    def get_network_descriptor(self, obj):
        """
        :return: list of nodes and edges based on parameters or graph variable
        """
        content = dict(nodes=[], edges=[])
        try:
            graph_obj = Graph.build_from_parameters(obj.n, obj.l, obj.g, obj.p, obj.etha, obj.etha_zone, obj.angles,
                                                    obj.gi, obj.hi)
        except (SIDERMITException, TypeError):
            graph_obj = Graph.build_from_content(obj.graph, GraphContentFormat.PAJEK)

        if graph_obj is not None:
            content = get_network_descriptor(graph_obj)

        return content

    def get_demand_matrix_header(self, obj):
        content = []
        try:
            graph_obj = Graph.build_from_parameters(obj.n, obj.l, obj.g, obj.p, obj.etha, obj.etha_zone, obj.angles,
                                                    obj.gi, obj.hi)
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

        PassengerSerializer(data=passenger_data).is_valid(raise_exception=True)

        scene_obj = Scene.objects.create(city=city_obj, **validated_data)
        Passenger.objects.create(scene=scene_obj, **passenger_data)
        transport_mode_list = []
        for transport_mode_data in transport_mode_set:
            transport_mode_list.append(TransportMode(scene=scene_obj, **transport_mode_data))
        TransportMode.objects.bulk_create(transport_mode_list)

        return scene_obj

    def update(self, instance, validated_data):
        # check if update can be done
        if instance.transportnetwork_set.filter(optimization_status=TransportNetwork.STATUS_FINISHED).exists():
            raise serializers.ValidationError(
                'Scene "{0}" can not be modified because have one or more networks with results'.format(instance.name))

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
    etha = serializers.FloatField(allow_null=True, required=False)
    etha_zone = serializers.IntegerField(allow_null=True, required=False)
    angles = serializers.CharField(allow_blank=True, allow_null=True, required=False)
    gi = serializers.CharField(allow_blank=True, allow_null=True, required=False)
    hi = serializers.CharField(allow_blank=True, allow_null=True, required=False)

    def validate_etha(self, value):
        if value == '':
            return None
        return value

    def validate_etha_zone(self, value):
        if value == '':
            return None
        return value

    def validate_angles(self, value):
        if value == '' or value is None:
            return None
        try:
            [float(v.strip()) for v in value.split(',')]
        except ValueError:
            raise serializers.ValidationError('angle value must a value between [0, 360]')

        return value

    def validate_gi(self, value):
        if value == '' or value is None:
            return None
        try:
            [float(v.strip()) for v in value.split(',')]
        except ValueError:
            raise serializers.ValidationError('gi value must a value number')

        return value

    def validate_hi(self, value):
        if value == '' or value is None:
            return None
        try:
            [float(v.strip()) for v in value.split(',')]
        except ValueError:
            raise serializers.ValidationError('hi value must be a list of number')

        return value

    def validate(self, validated_data):

        if validated_data.get('step') == self.STEP_1:
            key_exists = []
            keys = ['n', 'l', 'g', 'p']
            for key in keys:
                key_exists.append(validated_data.get(key) is None)

            etha = validated_data.get('etha')
            etha_zone = validated_data.get('etha_zone')
            angles = None
            gi = None
            hi = None

            if validated_data.get('angles') is not None:
                angles = [float(v.strip()) for v in validated_data.get('angles').split(',')]
            if validated_data.get('gi') is not None:
                gi = [float(v.strip()) for v in validated_data.get('gi').split(',')]
            if validated_data.get('hi') is not None:
                hi = [float(v.strip()) for v in validated_data.get('hi').split(',')]

            try:
                if not all(key_exists):
                    # if all keys are not none, there are not parameters but graph has to exist
                    Graph.build_from_parameters(validated_data.get('n'), validated_data.get('l'),
                                                validated_data.get('g'), validated_data.get('p'), etha, etha_zone,
                                                angles, gi, hi)

                Graph.build_from_content(validated_data['graph'], GraphContentFormat.PAJEK)
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
                if not all(key_exists):
                    # if all keys are not none, check values
                    Demand.build_from_parameters(graph_obj, validated_data.get('y'), validated_data.get('a'),
                                                 validated_data.get('alpha'), validated_data.get('beta'))

                if validated_data['demand_matrix'] is None:
                    raise serializers.ValidationError('You have to create a demand matrix before to continue')
                Demand.build_from_content(graph_obj, validated_data['demand_matrix'])
            except SIDERMITException as e:
                raise serializers.ValidationError(e)

        return validated_data

    def update(self, instance, validated_data):

        if instance.scene_set.count():
            raise serializers.ValidationError(
                'City "{0}" can not be modified because has scenes.'.format(instance.name))

        if validated_data.get('n', None) is not None and instance.n != validated_data.get('n'):
            validated_data['demand_matrix'] = None
            validated_data['y'] = None
            validated_data['a'] = None
            validated_data['alpha'] = None
            validated_data['beta'] = None

        return super().update(instance, validated_data)

    def create(self, validated_data):
        validated_data.pop('step')
        return super().create(validated_data)

    class Meta:
        model = City
        fields = (
            'public_id', 'created_at', 'name', 'graph', 'demand_matrix', 'n', 'p', 'l', 'g', 'etha', 'etha_zone',
            'angles', 'gi', 'hi', 'y', 'a', 'alpha', 'beta', 'scene_set', 'network_descriptor', 'demand_matrix_header',
            'step')
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
    optimizationresult = OptimizationResultSerializer(many=False)
    optimizationresultpermode_set = OptimizationResultPerModeSerializer(many=True)

    class Meta:
        model = TransportNetwork
        fields = ('optimization_status', 'optimization_ran_at', 'optimization_error_message', 'created_at',
                  'optimizationresult', 'optimizationresultpermode_set', 'name', 'public_id')


class OptimizationResultPerRouteDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = OptimizationResultPerRouteDetail
        fields = ('direction', 'origin_node', 'destination_node', 'lambda_value')


class OptimizationResultPerRouteSerializer(serializers.ModelSerializer):
    route = serializers.SlugRelatedField(many=False, read_only=True, slug_field='name')
    optimizationresultperroutedetail_set = OptimizationResultPerRouteDetailSerializer(many=True)

    class Meta:
        model = OptimizationResultPerRoute
        fields = ('route', 'frequency', 'frequency_per_line', 'k', 'b', 'tc', 'co', 'lambda_min',
                  'optimizationresultperroutedetail_set')


class RecentOptimizationSerializer(serializers.ModelSerializer):
    network_name = serializers.CharField(read_only=True, source='name')
    network_public_id = serializers.CharField(read_only=True, source='public_id')
    scene_name = serializers.CharField(read_only=True, source='scene.name')
    scene_public_id = serializers.CharField(read_only=True, source='scene.public_id')
    city_name = serializers.CharField(read_only=True, source='scene.city.name')
    city_public_id = serializers.CharField(read_only=True, source='scene.city.public_id')

    class Meta:
        model = TransportNetwork
        fields = (
            'optimization_status', 'network_name', 'scene_name', 'city_name', 'network_public_id', 'scene_public_id',
            'city_public_id')
