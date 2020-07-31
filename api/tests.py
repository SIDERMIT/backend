import json
import uuid

from django.test import TestCase
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIClient

from api.serializers import CitySerializer, SceneSerializer, PassengerSerializer, TransportModeSerializer, \
    TransportNetworkOptimizationSerializer, TransportNetworkSerializer, RouteSerializer
from storage.models import City, Scene, Passenger, TransportMode, TransportNetwork, Optimization, OptimizationResult, \
    OptimizationResultPerMode, Route


class BaseTestCase(TestCase):
    GET_REQUEST = 'get'
    POST_REQUEST = 'post'
    PUT_REQUEST = 'put'  # update
    PATCH_REQUEST = 'patch'  # partial update
    DELETE_REQUEST = 'delete'

    def __init__(self, *args, **kwargs):
        super(BaseTestCase, self).__init__(*args, **kwargs)

    def _make_request(self, client, method, url, data, status_code, json_process=True, **additional_method_params):

        method_obj = None
        if method == self.GET_REQUEST:
            method_obj = client.get
        elif method == self.POST_REQUEST:
            method_obj = client.post
        elif method == self.PATCH_REQUEST:
            method_obj = client.patch
        elif method == self.PUT_REQUEST:
            method_obj = client.put
        elif method == self.DELETE_REQUEST:
            method_obj = client.delete

        response = method_obj(url, data, **additional_method_params)
        if response.status_code != status_code:
            print('error {0}: {1}'.format(response.status_code, response.content))
            assert response.status_code == status_code

        if json_process:
            return json.loads(response.content)
        return response

    def create_data(self, city_number, scene_number=0, passenger=False, transport_mode_number=0,
                    transport_network_number=0, route_number=0):
        data = []
        for i in range(city_number):
            name = 'city name {0}'.format(i)
            graph = 'Nodes 1\n1 node1 12\n2 node2 12'
            matrix = [[1, 2], [1, 2]]
            city_obj = City.objects.create(name=name, graph=graph, demand_matrix=matrix)

            for j in range(scene_number):
                scene_obj = Scene.objects.create(name='s{0}-{1}'.format(i, j), city=city_obj)
                if passenger:
                    Passenger.objects.create(name='p-{0}-{1}'.format(i, j), va=1, pv=1, pw=1, pa=1,
                                             pt=1, spv=1, spw=1, spa=1, spt=1, scene=scene_obj)

                transport_mode_obj_list = []
                for k in range(transport_mode_number):
                    transport_mode_obj = TransportMode.objects.create(name='tm-{0}-{1}-{2}'.format(i, j, k), b_a=1,
                                                                      co=1, c1=1, c2=1, v=1, t=1, f_max=1, k_max=1,
                                                                      theta=1, tat=1, d=1, scene=scene_obj)
                    transport_mode_obj_list.append(transport_mode_obj)

                for p in range(transport_network_number):
                    transport_network_obj = TransportNetwork.objects.create(scene=scene_obj,
                                                                            name='tn-{0}-{1}-{2}'.format(i, j, p))
                    for q in range(route_number):
                        Route.objects.create(transport_network=transport_network_obj, name='route {0}'.format(q),
                                             transport_mode=transport_mode_obj_list[0], node_sequence_i='1,2,3',
                                             stop_sequence_i='1,3', node_sequence_r='3,2,1', stop_sequence_r='3,1')

            data.append(city_obj)

        return data

    # city helpers

    def cities_list(self, client, status_code=status.HTTP_200_OK):
        url = reverse('cities-list')
        data = dict()

        return self._make_request(client, self.GET_REQUEST, url, data, status_code, format='json')

    def cities_create(self, client, data, status_code=status.HTTP_201_CREATED):
        url = reverse('cities-list')

        return self._make_request(client, self.POST_REQUEST, url, data, status_code, format='json')

    def cities_retrieve(self, client, public_id, status_code=status.HTTP_200_OK):
        url = reverse('cities-detail', kwargs=dict(public_id=public_id))
        data = dict()

        return self._make_request(client, self.GET_REQUEST, url, data, status_code, format='json')

    def cities_update(self, client, public_id, data, status_code=status.HTTP_200_OK):
        url = reverse('cities-detail', kwargs=dict(public_id=public_id))

        return self._make_request(client, self.PUT_REQUEST, url, data, status_code, format='json')

    def cities_partial_update(self, client, public_id, fields, status_code=status.HTTP_200_OK):
        url = reverse('cities-detail', kwargs=dict(public_id=public_id))
        data = fields

        return self._make_request(client, self.PATCH_REQUEST, url, data, status_code, format='json')

    def cities_delete(self, client, public_id, status_code=status.HTTP_204_NO_CONTENT):
        url = reverse('cities-detail', kwargs=dict(public_id=public_id))
        data = dict()

        return self._make_request(client, self.DELETE_REQUEST, url, data, status_code, format='json',
                                  json_process=False)

    def cities_duplicate_action(self, client, public_id, status_code=status.HTTP_201_CREATED):
        url = reverse('cities-duplicate', kwargs=dict(public_id=public_id))
        data = dict()

        return self._make_request(client, self.POST_REQUEST, url, data, status_code, format='json')

    # scene helper

    def scenes_create(self, client, data, status_code=status.HTTP_201_CREATED):
        url = reverse('scenes-list')

        return self._make_request(client, self.POST_REQUEST, url, data, status_code, format='json')

    def scenes_retrieve(self, client, public_id, status_code=status.HTTP_200_OK):
        url = reverse('scenes-detail', kwargs=dict(public_id=public_id))
        data = dict()

        return self._make_request(client, self.GET_REQUEST, url, data, status_code, format='json')

    def scenes_update(self, client, public_id, data, status_code=status.HTTP_200_OK):
        url = reverse('scenes-detail', kwargs=dict(public_id=public_id))

        return self._make_request(client, self.PUT_REQUEST, url, data, status_code, format='json')

    def scenes_partial_update(self, client, public_id, fields, status_code=status.HTTP_200_OK):
        url = reverse('scenes-detail', kwargs=dict(public_id=public_id))
        data = fields

        return self._make_request(client, self.PATCH_REQUEST, url, data, status_code, format='json')

    def scenes_delete(self, client, public_id, status_code=status.HTTP_204_NO_CONTENT):
        url = reverse('scenes-detail', kwargs=dict(public_id=public_id))
        data = dict()

        return self._make_request(client, self.DELETE_REQUEST, url, data, status_code, format='json',
                                  json_process=False)

    def scenes_duplicate_action(self, client, public_id, status_code=status.HTTP_201_CREATED):
        url = reverse('scenes-duplicate', kwargs=dict(public_id=public_id))
        data = dict()

        return self._make_request(client, self.POST_REQUEST, url, data, status_code, format='json')

    def scenes_passenger_action(self, client, public_id, data, status_code=status.HTTP_201_CREATED):
        url = reverse('scenes-passenger', kwargs=dict(public_id=public_id))

        return self._make_request(client, self.POST_REQUEST, url, data, status_code, format='json')

    def scenes_globalresults_action(self, client, public_id, status_code=status.HTTP_200_OK):
        url = reverse('scenes-global-results', kwargs=dict(public_id=public_id))
        data = dict()

        return self._make_request(client, self.GET_REQUEST, url, data, status_code, format='json')

    # transport mode helpers

    def scenes_transportmode_create(self, client, scene_public_id, data, status_code=status.HTTP_201_CREATED):
        url = reverse('transport-modes-list', kwargs=dict(scene_public_id=scene_public_id))

        return self._make_request(client, self.POST_REQUEST, url, data, status_code, format='json')

    def scenes_transportmode_retrieve(self, client, scene_public_id, public_id, status_code=status.HTTP_200_OK):
        url = reverse('transport-modes-detail', kwargs=dict(scene_public_id=scene_public_id, public_id=public_id))
        data = dict()

        return self._make_request(client, self.GET_REQUEST, url, data, status_code, format='json')

    def scenes_transportmode_update(self, client, scene_public_id, public_id, data, status_code=status.HTTP_200_OK):
        url = reverse('transport-modes-detail', kwargs=dict(scene_public_id=scene_public_id, public_id=public_id))

        return self._make_request(client, self.PUT_REQUEST, url, data, status_code, format='json')

    def scenes_transportmode_partial_update(self, client, scene_public_id, public_id, fields,
                                            status_code=status.HTTP_200_OK):
        url = reverse('transport-modes-detail', kwargs=dict(scene_public_id=scene_public_id, public_id=public_id))
        data = fields

        return self._make_request(client, self.PATCH_REQUEST, url, data, status_code, format='json')

    def scenes_transportmode_delete(self, client, scene_public_id, public_id, status_code=status.HTTP_204_NO_CONTENT):
        url = reverse('transport-modes-detail', kwargs=dict(scene_public_id=scene_public_id, public_id=public_id))
        data = dict()

        return self._make_request(client, self.DELETE_REQUEST, url, data, status_code, format='json',
                                  json_process=False)

    # transport network helpers

    def transport_network_create(self, client, data, status_code=status.HTTP_201_CREATED):
        url = reverse('transport-networks-list')

        return self._make_request(client, self.POST_REQUEST, url, data, status_code, format='json')

    def transport_network_retrieve(self, client, public_id, status_code=status.HTTP_200_OK):
        url = reverse('transport-networks-detail', kwargs=dict(public_id=public_id))
        data = dict()

        return self._make_request(client, self.GET_REQUEST, url, data, status_code, format='json')

    def transport_network_update(self, client, public_id, data, status_code=status.HTTP_200_OK):
        url = reverse('transport-networks-detail', kwargs=dict(public_id=public_id))

        return self._make_request(client, self.PUT_REQUEST, url, data, status_code, format='json')

    def transport_network_partial_update(self, client, public_id, fields, status_code=status.HTTP_200_OK):
        url = reverse('transport-networks-detail', kwargs=dict(public_id=public_id))
        data = fields

        return self._make_request(client, self.PATCH_REQUEST, url, data, status_code, format='json')

    def transport_network_delete(self, client, public_id, status_code=status.HTTP_204_NO_CONTENT):
        url = reverse('transport-networks-detail', kwargs=dict(public_id=public_id))
        data = dict()

        return self._make_request(client, self.DELETE_REQUEST, url, data, status_code, format='json',
                                  json_process=False)

    def transport_network_duplicate_action(self, client, public_id, status_code=status.HTTP_201_CREATED):
        url = reverse('transport-networks-duplicate', kwargs=dict(public_id=public_id))
        data = dict()

        return self._make_request(client, self.POST_REQUEST, url, data, status_code, format='json')

    # route helpers

    def transport_network_route_create(self, client, transport_network_public_id, data,
                                       status_code=status.HTTP_201_CREATED):
        url = reverse('routes-list', kwargs=dict(transport_network_public_id=transport_network_public_id))

        return self._make_request(client, self.POST_REQUEST, url, data, status_code, format='json')

    def transport_network_route_retrieve(self, client, transport_network_public_id, public_id,
                                         status_code=status.HTTP_200_OK):
        url = reverse('routes-detail',
                      kwargs=dict(transport_network_public_id=transport_network_public_id, public_id=public_id))
        data = dict()

        return self._make_request(client, self.GET_REQUEST, url, data, status_code, format='json')

    def transport_network_route_update(self, client, transport_network_public_id, public_id, data,
                                       status_code=status.HTTP_200_OK):
        url = reverse('routes-detail',
                      kwargs=dict(transport_network_public_id=transport_network_public_id, public_id=public_id))

        return self._make_request(client, self.PUT_REQUEST, url, data, status_code, format='json')

    def transport_network_route_partial_update(self, client, transport_network_public_id, public_id, fields,
                                               status_code=status.HTTP_200_OK):
        url = reverse('routes-detail',
                      kwargs=dict(transport_network_public_id=transport_network_public_id, public_id=public_id))
        data = fields

        return self._make_request(client, self.PATCH_REQUEST, url, data, status_code, format='json')

    def transport_network_route_delete(self, client, transport_network_public_id, public_id,
                                       status_code=status.HTTP_204_NO_CONTENT):
        url = reverse('routes-detail',
                      kwargs=dict(transport_network_public_id=transport_network_public_id, public_id=public_id))
        data = dict()

        return self._make_request(client, self.DELETE_REQUEST, url, data, status_code, format='json',
                                  json_process=False)


class CityAPITest(BaseTestCase):

    def setUp(self):
        self.client = APIClient()
        self.city_obj = self.create_data(city_number=1, scene_number=1)[0]

    def test_retrieve_city_list(self):
        with self.assertNumQueries(5):
            json_response = self.cities_list(self.client)

        self.assertEqual(len(json_response), 1)
        self.assertDictEqual(json_response[0], CitySerializer(self.city_obj).data)

    def test_retrieve_city_with_public_id(self):
        with self.assertNumQueries(5):
            json_response = self.cities_retrieve(self.client, self.city_obj.public_id)

        self.assertDictEqual(json_response, CitySerializer(self.city_obj).data)

    def test_create_city(self):
        fields = dict(name='city name', graph='nodes 2', demand_matrix=None, n=1, p=1, l=1, g=1, y=1, a=1, alpha=1,
                      beta=1)
        with self.assertNumQueries(1):
            self.cities_create(self.client, fields)

        self.assertEqual(City.objects.count(), 2)

    def test_update_city(self):
        new_city_name = 'name2'
        new_data = dict(name=new_city_name, graph='nodes 2', demand_matrix=None, n=1, p=1, l=1, g=1, y=1, a=1, alpha=1,
                        beta=1)
        with self.assertNumQueries(6):
            json_response = self.cities_update(self.client, self.city_obj.public_id, new_data)

        self.city_obj.refresh_from_db()
        self.assertDictEqual(json_response, CitySerializer(self.city_obj).data)
        self.assertEqual(self.city_obj.name, new_city_name)

    def test_partial_update_city(self):
        new_city_name = 'name2'
        new_data = dict(name=new_city_name)
        with self.assertNumQueries(6):
            json_response = self.cities_partial_update(self.client, self.city_obj.public_id, new_data)

        self.city_obj.refresh_from_db()
        self.assertDictEqual(json_response, CitySerializer(self.city_obj).data)
        self.assertEqual(self.city_obj.name, new_city_name)

    def test_delete_city(self):
        with self.assertNumQueries(11):
            self.cities_delete(self.client, self.city_obj.public_id)

        self.assertEqual(City.objects.count(), 0)

    def test_duplicate_city(self):
        with self.assertNumQueries(7):
            json_response = self.cities_duplicate_action(self.client, self.city_obj.public_id)

        self.assertEqual(City.objects.count(), 2)
        self.assertDictEqual(json_response, CitySerializer(City.objects.order_by('-created_at').first()).data)


class SceneAPITest(BaseTestCase):

    def setUp(self):
        self.client = APIClient()
        self.city_obj = self.create_data(city_number=1, scene_number=1, passenger=True, transport_mode_number=2,
                                         transport_network_number=1)[0]
        self.scene_obj = self.city_obj.scene_set.all()[0]

    def test_retrieve_scene_with_public_id(self):
        with self.assertNumQueries(2):
            json_response = self.scenes_retrieve(self.client, self.scene_obj.public_id)

        self.assertIsNotNone(json_response['passenger'])
        self.assertEqual(len(json_response['transportmode_set']), 2)
        self.assertDictEqual(json_response, SceneSerializer(self.scene_obj).data)

    def test_create_scene(self):
        fields = dict(name='scene name', city_public_id=self.city_obj.public_id)
        with self.assertNumQueries(4):
            self.scenes_create(self.client, fields)

        self.assertEqual(Scene.objects.count(), 2)
        self.assertEqual(City.objects.count(), 1)

    def test_create_scene_with_wrong_city_id(self):
        wrong_city_id_list = ['not_uuid_value', str(uuid.uuid4())]
        num_queries_expected_list = [0, 1]
        for wrong_city_id, num_queries_expected in zip(wrong_city_id_list, num_queries_expected_list):
            fields = dict(name='scene name', city_public_id=wrong_city_id)
            with self.assertNumQueries(num_queries_expected):
                self.scenes_create(self.client, fields, status_code=status.HTTP_400_BAD_REQUEST)

        self.assertEqual(Scene.objects.count(), 1)
        self.assertEqual(City.objects.count(), 1)

    def test_update_scene(self):
        new_scene_name = 'name2'
        new_data = dict(name=new_scene_name, city_public_id=self.city_obj.public_id)
        with self.assertNumQueries(5):
            json_response = self.scenes_update(self.client, self.scene_obj.public_id, new_data)

        self.scene_obj.refresh_from_db()
        self.assertDictEqual(json_response, SceneSerializer(self.scene_obj).data)
        self.assertEqual(self.scene_obj.name, new_scene_name)

    def test_partial_update_scene(self):
        new_scene_name = 'name2'
        new_data = dict(name=new_scene_name)
        with self.assertNumQueries(4):
            json_response = self.scenes_partial_update(self.client, self.scene_obj.public_id, new_data)

        self.scene_obj.refresh_from_db()
        self.assertDictEqual(json_response, SceneSerializer(self.scene_obj).data)
        self.assertEqual(self.scene_obj.name, new_scene_name)

    def test_delete_scene(self):
        with self.assertNumQueries(12):
            self.scenes_delete(self.client, self.scene_obj.public_id)

        self.assertEqual(Scene.objects.count(), 0)

    def test_duplicate_scene(self):
        with self.assertNumQueries(12):
            json_response = self.scenes_duplicate_action(self.client, self.scene_obj.public_id)

        self.assertEqual(Scene.objects.count(), 2)
        self.assertDictEqual(json_response, SceneSerializer(Scene.objects.order_by('-created_at').first()).data)

    def test_update_passenger(self):
        data = dict(name='new name', va=2, pv=2, pw=2, pa=2, pt=2, spv=2, spw=2, spa=2, spt=2)

        with self.assertNumQueries(4):
            json_response = self.scenes_passenger_action(self.client, self.scene_obj.public_id, data,
                                                         status_code=status.HTTP_200_OK)

        self.assertEqual(json_response['name'], data['name'])
        self.assertDictEqual(json_response, PassengerSerializer(Passenger.objects.first()).data)

    def test_partial_update_passenger(self):
        data = dict(name='new name')

        with self.assertNumQueries(4):
            json_response = self.scenes_passenger_action(self.client, self.scene_obj.public_id, data,
                                                         status_code=status.HTTP_200_OK)
        self.assertEqual(json_response['name'], data['name'])
        self.assertDictEqual(json_response, PassengerSerializer(Passenger.objects.first()).data)

    def test_create_passenger(self):
        self.scene_obj.passenger.delete()

        data = dict(name='new name', va=2, pv=2, pw=2, pa=2, pt=2, spv=2, spw=2, spa=2, spt=2)
        with self.assertNumQueries(6):
            json_response = self.scenes_passenger_action(self.client, self.scene_obj.public_id, data)

        self.assertDictEqual(json_response, PassengerSerializer(Passenger.objects.first()).data)

    def test_get_global_result(self):
        transport_network_obj = TransportNetwork.objects.first()

        optimization_obj = Optimization.objects.create(transport_network=transport_network_obj,
                                                       status=Optimization.STATUS_FINISHED)
        OptimizationResult.objects.create(optimization=optimization_obj, vrc=2, co=2, ci=2, cu=2, tv=2, tw=2, ta=2, t=2)
        for i, transport_mode_obj in enumerate(self.scene_obj.transportmode_set.all()):
            OptimizationResultPerMode.objects.create(optimization=optimization_obj, transport_mode=transport_mode_obj,
                                                     b=i, k=i, l=i)

        with self.assertNumQueries(6):
            json_response = self.scenes_globalresults_action(self.client, self.scene_obj.public_id)

        self.assertListEqual(json_response, [TransportNetworkOptimizationSerializer(optimization_obj).data])

    def test_get_global_result_without_optimization_data(self):
        with self.assertNumQueries(3):
            json_response = self.scenes_globalresults_action(self.client, self.scene_obj.public_id)

        self.assertListEqual(json_response, [])

    def test_create_transport_mode(self):
        self.scene_obj.transportmode_set.all().delete()

        data = dict(name='new name', b_a=2, co=2, c1=2, c2=2, v=2, t=2, f_max=2, k_max=2, theta=2, tat=2, d=2)
        with self.assertNumQueries(2):
            json_response = self.scenes_transportmode_create(self.client, self.scene_obj.public_id, data)

        self.assertDictEqual(json_response, TransportModeSerializer(TransportMode.objects.first()).data)

    def test_create_transport_mode_but_scene_does_not_exist(self):
        self.scene_obj.transportmode_set.all().delete()

        data = dict(name='new name', b_a=2, co=2, c1=2, c2=2, v=2, t=2, f_max=2, k_max=2, theta=2, tat=2, d=2)
        with self.assertNumQueries(1):
            json_response = self.scenes_transportmode_create(self.client, uuid.uuid4(), data,
                                                             status_code=status.HTTP_400_BAD_REQUEST)

        self.assertEqual(TransportMode.objects.count(), 0)
        self.assertIn('Scene does not exist', json_response['scene_public_id'][0])

    def test_retrieve_transport_mode(self):
        transport_mode_obj = self.scene_obj.transportmode_set.all()[0]

        with self.assertNumQueries(1):
            json_response = self.scenes_transportmode_retrieve(self.client, self.scene_obj.public_id,
                                                               transport_mode_obj.public_id)

        self.assertDictEqual(json_response, TransportModeSerializer(transport_mode_obj).data)

    def test_update_transport_mode(self):
        public_id = self.scene_obj.transportmode_set.all()[0].public_id
        data = dict(name='new name', public_id=str(public_id), b_a=2, co=2, c1=2, c2=2, v=2, t=2, f_max=2, k_max=2,
                    theta=2, tat=2, d=2)

        with self.assertNumQueries(3):
            json_response = self.scenes_transportmode_update(self.client, self.scene_obj.public_id, public_id, data)
        for key in data.keys():
            self.assertEqual(json_response[key], data[key])
        self.assertDictEqual(json_response,
                             TransportModeSerializer(TransportMode.objects.get(public_id=public_id)).data)

    def test_partial_update_transport_mode(self):
        public_id = self.scene_obj.transportmode_set.all()[0].public_id
        data = dict(name='new name', public_id=public_id)

        with self.assertNumQueries(3):
            json_response = self.scenes_transportmode_partial_update(self.client, self.scene_obj.public_id, public_id,
                                                                     data)
        self.assertEqual(json_response['name'], data['name'])
        self.assertDictEqual(json_response,
                             TransportModeSerializer(TransportMode.objects.get(public_id=public_id)).data)

    def test_partial_delete_transport_mode(self):
        public_id = self.scene_obj.transportmode_set.all()[0].public_id

        with self.assertNumQueries(4):
            self.scenes_transportmode_delete(self.client, self.scene_obj.public_id, public_id)

        self.assertEqual(TransportMode.objects.count(), 1)


class TransportNetworkAPITest(BaseTestCase):

    def setUp(self):
        self.client = APIClient()
        self.city_obj = self.create_data(city_number=1, scene_number=1, passenger=True, transport_mode_number=2,
                                         transport_network_number=1, route_number=1)[0]
        self.scene_obj = self.city_obj.scene_set.all()[0]
        self.transport_network_obj = TransportNetwork.objects.first()

    def test_retrieve_transport_network_with_public_id(self):
        with self.assertNumQueries(3):
            json_response = self.transport_network_retrieve(self.client, self.transport_network_obj.public_id)

        self.assertDictEqual(json_response, TransportNetworkSerializer(self.transport_network_obj).data)

    def test_create_transport_network(self):
        fields = dict(name='scene name', scene_public_id=self.scene_obj.public_id)
        with self.assertNumQueries(3):
            self.transport_network_create(self.client, fields)

        self.assertEqual(TransportNetwork.objects.count(), 2)
        self.assertEqual(Scene.objects.count(), 1)

    def test_create_transport_network_with_wrong_scene_id(self):
        wrong_scene_id_list = ['not_uuid_value', str(uuid.uuid4())]
        num_queries_expected_list = [0, 1]
        for wrong_city_id, num_queries_expected in zip(wrong_scene_id_list, num_queries_expected_list):
            fields = dict(name='scene name', scene_public_id=wrong_city_id)
            with self.assertNumQueries(num_queries_expected):
                self.transport_network_create(self.client, fields, status_code=status.HTTP_400_BAD_REQUEST)

        self.assertEqual(TransportNetwork.objects.count(), 1)
        self.assertEqual(Scene.objects.count(), 1)

    def test_update_transport_network(self):
        new_scene_name = 'name2'
        new_data = dict(name=new_scene_name, scene_public_id=self.scene_obj.public_id)
        with self.assertNumQueries(7):
            json_response = self.transport_network_update(self.client, self.transport_network_obj.public_id, new_data)

        self.transport_network_obj.refresh_from_db()
        self.assertDictEqual(json_response, TransportNetworkSerializer(self.transport_network_obj).data)
        self.assertEqual(self.transport_network_obj.name, new_scene_name)

    def test_partial_update_transport_network(self):
        new_scene_name = 'name2'
        new_data = dict(name=new_scene_name)
        with self.assertNumQueries(6):
            json_response = self.transport_network_partial_update(self.client, self.transport_network_obj.public_id,
                                                                  new_data)

        self.transport_network_obj.refresh_from_db()
        self.assertDictEqual(json_response, TransportNetworkSerializer(self.transport_network_obj).data)
        self.assertEqual(self.transport_network_obj.name, new_scene_name)

    def test_delete_transport_network(self):
        with self.assertNumQueries(8):
            self.transport_network_delete(self.client, self.transport_network_obj.public_id)

        self.assertEqual(TransportNetwork.objects.count(), 0)

    def test_duplicate_transport_network(self):
        with self.assertNumQueries(11):
            json_response = self.transport_network_duplicate_action(self.client, self.transport_network_obj.public_id)

        self.assertEqual(TransportNetwork.objects.count(), 2)
        self.assertDictEqual(json_response,
                             TransportNetworkSerializer(TransportNetwork.objects.order_by('-created_at').first()).data)

    def test_create_route(self):
        data = dict(name='new name', node_sequence_i='1,2,3', stop_sequence_i='3,2,1', node_sequence_r='4,5,6',
                    stop_sequence_r='6,5,4', transport_mode_public_id=TransportMode.objects.first().public_id)
        with self.assertNumQueries(3):
            json_response = self.transport_network_route_create(self.client, self.transport_network_obj.public_id, data)

        self.assertEqual(Route.objects.count(), 2)
        self.assertDictEqual(json_response, RouteSerializer(Route.objects.order_by('-id').first()).data)

    def test_create_route_but_transport_network_does_not_exist(self):
        data = dict(name='new name', node_sequence_i='1,2,3', stop_sequence_i='3,2,1', node_sequence_r='4,5,6',
                    stop_sequence_r='6,5,4', transport_mode_public_id=TransportMode.objects.first().public_id)
        with self.assertNumQueries(2):
            json_response = self.transport_network_route_create(self.client, uuid.uuid4(), data,
                                                                status_code=status.HTTP_400_BAD_REQUEST)

        self.assertEqual(Route.objects.count(), 1)
        self.assertIn('Transport network does not exist', json_response['transport_network_public_id'][0])

    def test_create_route_but_transport_mode_does_not_exist(self):
        data = dict(name='new name', node_sequence_i='1,2,3', stop_sequence_i='3,2,1', node_sequence_r='4,5,6',
                    stop_sequence_r='6,5,4', transport_mode_public_id=uuid.uuid4())
        with self.assertNumQueries(2):
            json_response = self.transport_network_route_create(self.client, self.transport_network_obj.public_id, data,
                                                                status_code=status.HTTP_400_BAD_REQUEST)

        self.assertEqual(Route.objects.count(), 1)
        self.assertIn('Transport mode does not exist', json_response['transport_mode_public_id'][0])

    def test_update_route(self):
        public_id = self.transport_network_obj.route_set.all()[0].public_id
        transport_mode_obj = TransportMode.objects.first()
        data = dict(name='new name', public_id=str(public_id), node_sequence_i='1,2,3', stop_sequence_i='1,3',
                    node_sequence_r='3,2,1', stop_sequence_r='e,1',
                    transport_mode_public_id=str(transport_mode_obj.public_id))

        with self.assertNumQueries(5):
            json_response = self.transport_network_route_update(self.client, self.transport_network_obj.public_id,
                                                                public_id, data, status_code=status.HTTP_200_OK)

        self.assertEqual(Route.objects.count(), 1)
        for key in data.keys():
            # this key is not present in answer
            if key not in ['transport_mode_public_id']:
                self.assertEqual(json_response[key], data[key])
            else:
                self.assertEqual(json_response['transport_mode'], TransportModeSerializer(transport_mode_obj).data)
        self.assertDictEqual(json_response, RouteSerializer(Route.objects.get(public_id=public_id)).data)

    def test_partial_update_route(self):
        public_id = self.transport_network_obj.route_set.all()[0].public_id
        data = dict(name='new name', public_id=public_id)

        with self.assertNumQueries(4):
            json_response = self.transport_network_route_partial_update(self.client,
                                                                        self.transport_network_obj.public_id,
                                                                        public_id, data, status_code=status.HTTP_200_OK)
        self.assertEqual(json_response['name'], data['name'])
        self.assertDictEqual(json_response, RouteSerializer(Route.objects.get(public_id=public_id)).data)

    def test_delete_route(self):
        public_id = Route.objects.first().public_id

        with self.assertNumQueries(4):
            self.transport_network_route_delete(self.client, self.transport_network_obj.public_id, public_id)

        self.assertEqual(Route.objects.count(), 0)

    def test_retrieve_route(self):
        route_obj = Route.objects.first()

        with self.assertNumQueries(2):
            json_response = self.transport_network_route_retrieve(self.client, self.transport_network_obj.public_id,
                                                                  route_obj.public_id)

        self.assertDictEqual(json_response, RouteSerializer(route_obj).data)


class ValidationAPITest(BaseTestCase):

    def setUp(self):
        self.client = APIClient()
        # TODO: finish this

    def validate_route(self, client, data, status_code=status.HTTP_200_OK):
        url = reverse('validate-route')
        return self._make_request(client, self.GET_REQUEST, url, data, status_code, format='json')

    def test_validate_route(self):
        json_response = self.validate_route(self.client, dict())
        print(json_response)
