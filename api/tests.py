import json
import uuid

from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIClient
from sidermit.city import Graph, GraphContentFormat, Demand

from api.serializers import CitySerializer, SceneSerializer, TransportModeSerializer, \
    TransportNetworkOptimizationSerializer, TransportNetworkSerializer, RouteSerializer, \
    OptimizationResultPerRouteSerializer
from storage.models import City, Scene, Passenger, TransportMode, TransportNetwork, OptimizationResult, \
    OptimizationResultPerMode, Route, OptimizationResultPerRoute, OptimizationResultPerRouteDetail


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
            n, l, g, p = 4, 2, 3, 4
            graph_obj = Graph.build_from_parameters(n, l, g, p)
            demand_obj = Demand.build_from_parameters(graph_obj, 15000, 0.8, 0.4, 0.5)
            demand_matrix = demand_obj.get_matrix()
            demand_matrix_data = []
            size = len(demand_matrix.keys())
            for i in range(size):
                row = []
                for j in range(size):
                    row.append(demand_matrix[i][j])
                demand_matrix_data.append(row)

            city_obj = City.objects.create(name=name, graph=graph_obj.export_graph(GraphContentFormat.PAJEK),
                                           n=n, l=l, g=g, p=p, demand_matrix=demand_matrix_data)

            for j in range(scene_number):
                scene_obj = Scene.objects.create(name='s{0}-{1}'.format(i, j), city=city_obj)
                if passenger:
                    Passenger.objects.create(va=1, pv=1, pw=1, pa=1, pt=1, spv=1, spw=1, spa=1, spt=1, scene=scene_obj)

                transport_mode_obj_list = []
                for k in range(transport_mode_number):
                    transport_mode_obj = TransportMode.objects.create(name='tm-{0}-{1}-{2}'.format(i, j, k), bya=1,
                                                                      co=1, c1=1, c2=1, v=1, t=1, fmax=150, kmax=100,
                                                                      theta=1, tat=1, d=4, fini=1, scene=scene_obj)
                    transport_mode_obj_list.append(transport_mode_obj)

                for p in range(transport_network_number):
                    transport_network_obj = TransportNetwork.objects.create(scene=scene_obj,
                                                                            name='tn-{0}-{1}-{2}'.format(i, j, p))

                    for q in range(route_number):
                        Route.objects.create(transport_network=transport_network_obj, name='route {0}'.format(q),
                                             transport_mode=transport_mode_obj_list[0], nodes_sequence_i='1,2',
                                             stops_sequence_i='1,2', nodes_sequence_r='2,1', stops_sequence_r='2,1',
                                             type=Route.CUSTOM)

            data.append(city_obj)

        return data

    # city helpers

    def cities_list(self, client, data, status_code=status.HTTP_200_OK):
        url = reverse('cities-list')

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

    def cities_build_graph_file_from_parameters_action(self, client, data, status_code=status.HTTP_200_OK):
        url = reverse('cities-build-graph-file-from-parameters')

        return self._make_request(client, self.GET_REQUEST, url, data, status_code, format='json')

    def cities_network_data_from_pajek_file_action(self, client, data, status_code=status.HTTP_200_OK):
        url = reverse('cities-network-data-from-pajek-file')

        return self._make_request(client, self.GET_REQUEST, url, data, status_code, format='json')

    def cities_build_matrix_file_action(self, client, public_id, data, status_code=status.HTTP_200_OK):
        url = reverse('cities-build-matrix-file', kwargs=dict(public_id=public_id))

        return self._make_request(client, self.GET_REQUEST, url, data, status_code, format='json')

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

    def transport_network_create_default_routes_action(self, client, scene_public_id, default_routes,
                                                       status_code=status.HTTP_200_OK):
        url = reverse('transport-networks-create-default-routes')
        data = dict(scene_public_id=scene_public_id, default_routes=default_routes)

        return self._make_request(client, self.POST_REQUEST, url, data, status_code, format='json')

    def transport_network_results(self, client, transport_network_public_id, status_code=status.HTTP_200_OK):
        url = reverse('transport-networks-results', kwargs=dict(public_id=transport_network_public_id))
        data = dict()

        return self._make_request(client, self.GET_REQUEST, url, data, status_code, format='json')

    # optimizations

    def run_optimization(self, client, transport_network_public_id, status_code=status.HTTP_201_CREATED):
        url = reverse('transport-networks-run-optimization', kwargs=dict(public_id=transport_network_public_id))
        data = dict()

        return self._make_request(client, self.POST_REQUEST, url, data, status_code, format='json')

    def cancel_optimization(self, client, transport_network_public_id, status_code=status.HTTP_200_OK):
        url = reverse('transport-networks-cancel-optimization', kwargs=dict(public_id=transport_network_public_id))
        data = dict()

        return self._make_request(client, self.POST_REQUEST, url, data, status_code, format='json')

    # recent optimizations

    def recent_optimizations_list(self, client, status_code=status.HTTP_200_OK):
        url = reverse('recent-optimizations')
        data = dict()

        return self._make_request(client, self.GET_REQUEST, url, data, status_code, format='json')


class CityAPITest(BaseTestCase):

    def setUp(self):
        self.client = APIClient()
        self.city_obj = self.create_data(city_number=1, scene_number=1)[0]

    def test_retrieve_city_list(self):
        with self.assertNumQueries(5):
            json_response = self.cities_list(self.client, dict())

        print(json_response[0])
        print(CitySerializer(self.city_obj).data)

        self.maxDiff = True
        self.assertEqual(len(json_response), 1)
        self.assertDictEqual(json_response[0], CitySerializer(self.city_obj).data)

    def test_retrieve_city_list_with_filter_param(self):
        with self.assertNumQueries(0):
            json_response = self.cities_list(self.client, dict(limit=0))

        self.assertEqual(len(json_response), 0)

    def test_retrieve_city_list_but_limit_param_is_not_int(self):
        with self.assertNumQueries(5):
            json_response = self.cities_list(self.client, dict(limit='fake_number'))

        self.assertEqual(len(json_response), 1)

    def test_retrieve_city_with_public_id(self):
        with self.assertNumQueries(5):
            json_response = self.cities_retrieve(self.client, self.city_obj.public_id)

        self.assertDictEqual(json_response, CitySerializer(self.city_obj).data)

    def test_create_city_graph(self):
        fields = dict(name='city name', graph='nodes 2', n=1, p=1, l=1, g=1, step=CitySerializer.STEP_1)
        with self.assertNumQueries(2):
            self.cities_create(self.client, fields)

        self.assertEqual(City.objects.count(), 2)

    def test_create_city_graph_with_parameters(self):
        fields = dict(name='city name', n=1, p=1, l=1, g=1, graph='pajek content', step=CitySerializer.STEP_1)
        with self.assertNumQueries(2):
            self.cities_create(self.client, fields)

        self.assertEqual(City.objects.count(), 2)

    def test_create_city_graph_from_file(self):
        graph_content = Graph.build_from_parameters(4, 1, 1, 1).export_graph(GraphContentFormat.PAJEK)
        fields = dict(name='city name', graph=graph_content, step=CitySerializer.STEP_1)
        with self.assertNumQueries(2):
            self.cities_create(self.client, fields)

        self.assertEqual(City.objects.count(), 2)

    def test_create_city_graph_from_file_but_file_has_wrong_format(self):
        fields = dict(name='city name', graph='wrong pajek format', step=CitySerializer.STEP_1)
        with self.assertNumQueries(0):
            json_response = self.cities_create(self.client, fields, status_code=status.HTTP_400_BAD_REQUEST)

        self.assertIn('number of lines', json_response['non_field_errors'][0])
        self.assertEqual(City.objects.count(), 1)

    def test_update_city_step_1(self):
        new_city_name = 'name2'
        new_data = dict(name=new_city_name, graph='nodes 2', n=1, p=1, l=1, g=1, step=CitySerializer.STEP_1)
        with self.assertNumQueries(10):
            json_response = self.cities_update(self.client, self.city_obj.public_id, new_data)

        self.city_obj.refresh_from_db()
        self.assertDictEqual(json_response, CitySerializer(self.city_obj).data)
        self.assertEqual(self.city_obj.name, new_city_name)

    def test_partial_update_city_step2(self):
        new_data = dict(demand_matrix=[[1, 1], [1, 1]], y=1, a=1, alpha=0.1, beta=0.2, step=CitySerializer.STEP_2)
        with self.assertNumQueries(11):
            json_response = self.cities_partial_update(self.client, self.city_obj.public_id, new_data)

        self.city_obj.refresh_from_db()
        self.assertDictEqual(json_response, CitySerializer(self.city_obj).data)

    def test_partial_update_city(self):
        new_city_name = 'name2'
        new_data = dict(name=new_city_name)
        with self.assertNumQueries(10):
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

    def test_build_graph_file_city(self):
        data = dict(n=1, l=1.0, p=1.0, g=1.0)
        with self.assertNumQueries(0):
            json_response = self.cities_build_graph_file_from_parameters_action(self.client, data)

        expected_content_file = '*vertices 3\n0 CBD 0 0 CBD 0 1.0\n1 P_1 2.0 0.0 P 1 1.0\n2 SC_1 1.0 0.0 SC 1 1.0\n'
        excepted_network_data = {
            'nodes': [{'name': 'CBD', 'id': 0, 'x': 0, 'y': 0, 'type': 'cbd'},
                      {'name': 'P_1', 'id': 1, 'x': 2.0, 'y': 0.0, 'type': 'periphery'},
                      {'name': 'SC_1', 'id': 2, 'x': 1.0, 'y': 0.0, 'type': 'subcenter'}],
            'edges': [{'id': 1, 'source': 1, 'target': 2}, {'id': 2, 'source': 2, 'target': 1},
                      {'id': 3, 'source': 2, 'target': 0}, {'id': 4, 'source': 0, 'target': 2}]}
        self.assertDictEqual(json_response, dict(pajek=expected_content_file, network=excepted_network_data))

    def test_build_graph_file_with_wrong_parameters_city(self):
        data = dict(n=1, l=1.0, p=1.0, g=1.0)
        for index, key in enumerate(['n', 'l', 'p', 'g']):
            new_data = data.copy()
            new_data[key] = 'asdasd'
            with self.assertNumQueries(0):
                json_response = self.cities_build_graph_file_from_parameters_action(
                    self.client, new_data, status_code=status.HTTP_400_BAD_REQUEST)
            if index == 0:
                self.assertIn('invalid literal', json_response['detail'])
            else:
                self.assertIn('could not convert string to float', json_response['detail'])

        data['n'] = -1
        json_response = self.cities_build_graph_file_from_parameters_action(self.client, data,
                                                                            status_code=status.HTTP_400_BAD_REQUEST)
        self.assertIn('n cannot be a negative number', json_response['detail'])

    def test_build_graph_file_without_parameters_city(self):
        with self.assertNumQueries(0):
            json_response = self.cities_build_graph_file_from_parameters_action(self.client, dict(),
                                                                                status_code=status.HTTP_400_BAD_REQUEST)
        self.assertIn('Parameter can not be empty', json_response['detail'])

    def test_get_network_data_from_pajek_file(self):
        data = dict(graph='*vertices 11\n'
                          '0 CBD 0 0 CBD 0 1.0\n'
                          '1 P_1 3.6 0.0 P 1 1.0\n'
                          '2 SC_1 3.0 0.0 SC 1 1.0\n'
                          '3 P_2 1.112461179749811 3.4238034586625528 P 2 1.0\n'
                          '4 SC_2 0.9270509831248424 2.8531695488854605 SC 2 1.0')
        with self.assertNumQueries(0):
            json_response = self.cities_network_data_from_pajek_file_action(self.client, data)
        expected_answer = {
            "network": {
                "nodes": [
                    {"name": "CBD", "id": 0, "x": 0.0, "y": 0.0, "type": "cbd"},
                    {"name": "P_1", "id": 1, "x": 3.6, "y": 0.0, "type": "periphery"},
                    {"name": "SC_1", "id": 2, "x": 3.0, "y": 0.0, "type": "subcenter"},
                    {"name": "P_2", "id": 3, "x": 1.112461179749811, "y": 3.4238034586625528, "type": "periphery"},
                    {"name": "SC_2", "id": 4, "x": 0.9270509831248424, "y": 2.8531695488854605, "type": "subcenter"}
                ],
                "edges": [
                    {"id": 1, "source": 1, "target": 2},
                    {"id": 2, "source": 2, "target": 1},
                    {"id": 3, "source": 2, "target": 0},
                    {"id": 4, "source": 0, "target": 2},
                    {"id": 5, "source": 2, "target": 4},
                    {"id": 6, "source": 4, "target": 2},
                    {"id": 7, "source": 3, "target": 4},
                    {"id": 8, "source": 4, "target": 3},
                    {"id": 9, "source": 4, "target": 0},
                    {"id": 10, "source": 0, "target": 4}
                ]}
        }
        self.assertDictEqual(expected_answer, json_response)

    def test_get_network_data_from_pajek_file_with_wrong_content(self):
        data = dict(graph='*vertices 11\n'
                          '0 CBD 0 0 CBD 0 1.0\n'
                          '1 P_1 3.6 0.0 P 1 1.0\n'
                          '2 SC_1 3.0 0.0 SC 1 1.0\n'
                          '3 P_2 1.112461179749811 3.4238034586625528 P 2 1.0\n'
                          '4 SC_2 0.9270509831248424 2.8531695488854605 SC 2 asd')
        with self.assertNumQueries(0):
            json_response = self.cities_network_data_from_pajek_file_action(self.client, data,
                                                                            status_code=status.HTTP_400_BAD_REQUEST)
        self.assertIn("could not convert string to float: 'asd'", json_response['detail'])

    def test_get_network_data_from_pajek_file_without_content(self):
        data = dict(graph='')
        with self.assertNumQueries(0):
            json_response = self.cities_network_data_from_pajek_file_action(self.client, data,
                                                                            status_code=status.HTTP_400_BAD_REQUEST)
        self.assertIn('The number of lines in the file must be 2n+1 or file is very big (until 5000 zones accepted)',
                      json_response['detail'])

    def test_build_matrix_file_city(self):
        data = dict(y=1, a=1.0, alpha=0.1, beta=0.8)
        with self.assertNumQueries(5):
            json_response = self.cities_build_matrix_file_action(self.client, self.city_obj.public_id, data)

        expected_demand_matrix_file = [
            [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0],
            [0.025, 0.0, 0.2, 0.0, 0.008333333333333331, 0.0, 0.008333333333333331, 0.0, 0.008333333333333331],
            [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            [0.025, 0.0, 0.008333333333333331, 0.0, 0.2, 0.0, 0.008333333333333331, 0.0, 0.008333333333333331],
            [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            [0.025, 0.0, 0.008333333333333331, 0.0, 0.008333333333333331, 0.0, 0.2, 0.0, 0.008333333333333331],
            [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            [0.025, 0.0, 0.008333333333333331, 0.0, 0.008333333333333331, 0.0, 0.008333333333333331, 0.0, 0.2],
            [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0]
        ]
        excepted_demand_matrix_header = ['CBD', 'P_1', 'SC_1', 'P_2', 'SC_2', 'P_3', 'SC_3', 'P_4', 'SC_4']
        self.maxDiff = None
        self.assertDictEqual(json_response, dict(demand_matrix=expected_demand_matrix_file,
                                                 demand_matrix_header=excepted_demand_matrix_header))

    def test_build_matrix_file_with_wrong_parameters_city(self):
        data = dict(y=1, a=1.0, alpha=0.4, beta=0.8)
        for index, key in enumerate(['y', 'a', 'alpha', 'beta']):
            new_data = data.copy()
            new_data[key] = 'asdasd'
            with self.assertNumQueries(0):
                json_response = self.cities_build_matrix_file_action(self.client, self.city_obj.public_id, new_data,
                                                                     status_code=status.HTTP_400_BAD_REQUEST)
            if index == 0:
                self.assertIn('invalid literal', json_response['detail'])
            else:
                self.assertIn('could not convert string to float', json_response['detail'])

        data['y'] = -1
        json_response = self.cities_build_matrix_file_action(self.client, self.city_obj.public_id, data,
                                                             status_code=status.HTTP_400_BAD_REQUEST)
        self.assertIn('y must be positive', json_response['detail'])

    def test_build_matrix_file_without_parameters_city(self):
        with self.assertNumQueries(0):
            json_response = self.cities_build_matrix_file_action(self.client, self.city_obj.public_id, dict(),
                                                                 status_code=status.HTTP_400_BAD_REQUEST)
        self.assertIn('Parameter can not be empty', json_response['detail'])


class SceneAPITest(BaseTestCase):

    def setUp(self):
        self.client = APIClient()
        self.city_obj = self.create_data(city_number=1, scene_number=1, passenger=True, transport_mode_number=2,
                                         transport_network_number=1)[0]
        self.scene_obj = self.city_obj.scene_set.all()[0]

    def test_retrieve_scene_with_public_id(self):
        with self.assertNumQueries(4):
            json_response = self.scenes_retrieve(self.client, self.scene_obj.public_id)

        self.assertIsNotNone(json_response['passenger'])
        self.assertEqual(len(json_response['transportmode_set']), 2)
        self.assertDictEqual(json_response, SceneSerializer(self.scene_obj).data)

    def test_create_scene(self):
        passenger_data = dict(va=2, pv=2, pw=2, pa=2, pt=2, spv=2, spw=2, spa=2, spt=2)
        transport_mode_data = dict(name='nam', bya=1, co=1, c1=1, c2=1, v=1, t=1, fmax=1, kmax=1, theta=1, tat=1, d=1,
                                   fini=1)
        fields = dict(name='scene name', city_public_id=self.city_obj.public_id, passenger=passenger_data,
                      transportmode_set=[transport_mode_data])
        with self.assertNumQueries(6):
            self.scenes_create(self.client, fields)

        self.assertEqual(Scene.objects.count(), 2)
        self.assertEqual(City.objects.count(), 1)
        self.assertEqual(TransportMode.objects.count(), 3)

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
        passenger_data = dict(va=0, pv=0, pw=0, pa=0, pt=0, spv=0, spw=0, spa=0, spt=0)
        # transport mode data is not needed on update because this has to be done in transport mode api directly
        transport_mode_data = dict(name='nam', bya=1, co=1, c1=1, c2=1, v=1, t=1, fmax=1, kmax=1, theta=1, tat=1, d=1,
                                   fini=1)
        new_data = dict(name=new_scene_name, city_public_id=self.city_obj.public_id, passenger=passenger_data,
                        transportmode_set=[transport_mode_data])
        with self.assertNumQueries(10):
            json_response = self.scenes_update(self.client, self.scene_obj.public_id, new_data)

        self.scene_obj.refresh_from_db()
        self.assertDictEqual(json_response, SceneSerializer(self.scene_obj).data)
        self.assertEqual(self.scene_obj.name, new_scene_name)

    def test_partial_update_scene(self):
        new_scene_name = 'name2'
        new_data = dict(name=new_scene_name, passenger=dict())
        with self.assertNumQueries(9):
            json_response = self.scenes_partial_update(self.client, self.scene_obj.public_id, new_data)

        self.scene_obj.refresh_from_db()
        self.assertDictEqual(json_response, SceneSerializer(self.scene_obj).data)
        self.assertEqual(self.scene_obj.name, new_scene_name)

    def test_delete_scene(self):
        with self.assertNumQueries(16):
            self.scenes_delete(self.client, self.scene_obj.public_id)

        self.assertEqual(Scene.objects.count(), 0)

    def test_duplicate_scene(self):
        with self.assertNumQueries(18):
            json_response = self.scenes_duplicate_action(self.client, self.scene_obj.public_id)

        self.assertEqual(Scene.objects.count(), 2)
        self.assertDictEqual(json_response, SceneSerializer(Scene.objects.order_by('-created_at').first()).data)

    def test_duplicate_scene_without_passenger(self):
        self.scene_obj.passenger.delete()

        with self.assertNumQueries(16):
            json_response = self.scenes_duplicate_action(self.client, self.scene_obj.public_id)

        self.assertEqual(Scene.objects.count(), 2)
        self.assertDictEqual(json_response, SceneSerializer(Scene.objects.order_by('-created_at').first()).data)

    def test_update_passenger(self):
        passenger_data = dict(va=3, pv=3, pw=2, pa=2, pt=2, spv=2, spw=2, spa=2, spt=2)
        scene_data = dict(passenger=passenger_data)
        with self.assertNumQueries(9):
            json_response = self.scenes_partial_update(self.client, self.scene_obj.public_id, scene_data,
                                                       status_code=status.HTTP_200_OK)

        self.assertEqual(json_response['passenger']['va'], passenger_data['va'])
        self.assertDictEqual(json_response, SceneSerializer(self.scene_obj).data)

    def test_partial_update_passenger(self):
        passenger_data = dict(va=3)
        scene_data = dict(passenger=passenger_data)

        with self.assertNumQueries(9):
            json_response = self.scenes_partial_update(self.client, self.scene_obj.public_id, scene_data,
                                                       status_code=status.HTTP_200_OK)
        self.assertEqual(json_response['passenger']['va'], passenger_data['va'])
        self.assertDictEqual(json_response, SceneSerializer(self.scene_obj).data)

    def test_get_global_result(self):
        transport_network_obj = TransportNetwork.objects.first()
        transport_network_obj.optimization_status = TransportNetwork.STATUS_FINISHED
        transport_network_obj.save()

        OptimizationResult.objects.create(transport_network=transport_network_obj, vrc=2, co=2, ci=2, cu=2, tv=2, tw=2,
                                          ta=2, t=2)
        for i, transport_mode_obj in enumerate(self.scene_obj.transportmode_set.all()):
            OptimizationResultPerMode.objects.create(transport_network=transport_network_obj,
                                                     transport_mode=transport_mode_obj,
                                                     b=i, k=i, l=i)

        with self.assertNumQueries(7):
            json_response = self.scenes_globalresults_action(self.client, self.scene_obj.public_id)

        self.assertListEqual(json_response['rows'],
                             [TransportNetworkOptimizationSerializer(transport_network_obj).data])
        self.assertIn('scene', json_response.keys())

    def test_get_global_result_without_optimization_data(self):
        with self.assertNumQueries(5):
            json_response = self.scenes_globalresults_action(self.client, self.scene_obj.public_id)

        self.assertListEqual(json_response['rows'], [])
        self.assertIn('scene', json_response.keys())

    def test_create_transport_mode(self):
        data = dict(name='new name', bya=1, co=2, c1=2, c2=2, v=2, t=2, fmax=2, kmax=2, theta=1, tat=2, d=2, fini=2)

        self.assertEqual(TransportMode.objects.count(), 2)
        with self.assertNumQueries(2):
            json_response = self.scenes_transportmode_create(self.client, self.scene_obj.public_id, data)

        self.assertEqual(TransportMode.objects.count(), 3)
        transport_mode_obj = TransportMode.objects.order_by('-created_at').first()
        self.assertDictEqual(json_response, TransportModeSerializer(transport_mode_obj).data)

    def test_retrieve_transport_mode(self):
        transport_mode_obj = self.scene_obj.transportmode_set.all()[0]

        with self.assertNumQueries(1):
            json_response = self.scenes_transportmode_retrieve(self.client, self.scene_obj.public_id,
                                                               transport_mode_obj.public_id)

        self.assertDictEqual(json_response, TransportModeSerializer(transport_mode_obj).data)

    def test_update_transport_mode(self):
        public_id = self.scene_obj.transportmode_set.all()[0].public_id
        data = dict(name='new name', public_id=str(public_id), bya=1, co=2, c1=2, c2=2, v=2, t=2, fmax=2, kmax=2,
                    theta=1, tat=2, d=2, fini=2)

        with self.assertNumQueries(2):
            json_response = self.scenes_transportmode_update(self.client, self.scene_obj.public_id, public_id, data)
        for key in data.keys():
            self.assertEqual(json_response[key], data[key])
        self.assertDictEqual(json_response,
                             TransportModeSerializer(TransportMode.objects.get(public_id=public_id)).data)

    def test_delete_transport_mode(self):
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
        route_data = dict(name='new name', nodes_sequence_i='1,2', stops_sequence_i='1,2', nodes_sequence_r='2,1',
                          stops_sequence_r='2,1', type=Route.CUSTOM,
                          transport_mode_public_id=TransportMode.objects.first().public_id)
        fields = dict(name='transport network name', scene_public_id=self.scene_obj.public_id, route_set=[route_data])
        with self.assertNumQueries(9):
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
        new_data = dict(name=new_scene_name, scene_public_id=self.scene_obj.public_id, route_set=[])
        with self.assertNumQueries(12):
            json_response = self.transport_network_update(self.client, self.transport_network_obj.public_id, new_data)

        self.transport_network_obj.refresh_from_db()
        self.assertDictEqual(json_response, TransportNetworkSerializer(self.transport_network_obj).data)
        self.assertEqual(self.transport_network_obj.name, new_scene_name)

    def test_partial_update_transport_network(self):
        new_scene_name = 'name2'
        new_data = dict(name=new_scene_name, route_set=[])
        with self.assertNumQueries(12):
            json_response = self.transport_network_partial_update(self.client, self.transport_network_obj.public_id,
                                                                  new_data)

        self.transport_network_obj.refresh_from_db()
        self.assertDictEqual(json_response, TransportNetworkSerializer(self.transport_network_obj).data)
        self.assertEqual(self.transport_network_obj.name, new_scene_name)

    def test_delete_transport_network(self):
        with self.assertNumQueries(10):
            self.transport_network_delete(self.client, self.transport_network_obj.public_id)

        self.assertEqual(TransportNetwork.objects.count(), 0)

    def test_duplicate_transport_network(self):
        with self.assertNumQueries(11):
            json_response = self.transport_network_duplicate_action(self.client, self.transport_network_obj.public_id)

        self.assertEqual(TransportNetwork.objects.count(), 2)
        self.assertDictEqual(json_response,
                             TransportNetworkSerializer(TransportNetwork.objects.order_by('-created_at').first()).data)

    def test_create_default_route(self):
        transport_mode_public_id = str(TransportMode.objects.filter(scene=self.scene_obj).first().public_id)
        route_type_list = ['Circular', 'Diametral', 'Feeder', 'Radial', 'Tangential']
        expected_results = [
            [{'name': 'CIR_I_tm-0-0-0', 'transport_mode_public_id': transport_mode_public_id,
              'nodes_sequence_i': '2,4,6,8,2', 'nodes_sequence_r': '', 'stops_sequence_i': '2,4,6,8,2',
              'stops_sequence_r': '', 'type': 3},
             {'name': 'CIR_R_tm-0-0-0', 'transport_mode_public_id': transport_mode_public_id,
              'nodes_sequence_i': '', 'nodes_sequence_r': '8,6,4,2,8', 'stops_sequence_i': '',
              'stops_sequence_r': '8,6,4,2,8', 'type': 3}],
            [{'name': 'DSE1_tm-0-0-0_1', 'transport_mode_public_id': transport_mode_public_id,
              'nodes_sequence_i': '2,0,4', 'nodes_sequence_r': '4,0,2', 'stops_sequence_i': '2,4',
              'stops_sequence_r': '4,2', 'type': 2},
             {'name': 'DSE1_tm-0-0-0_2', 'transport_mode_public_id': transport_mode_public_id,
              'nodes_sequence_i': '4,0,6', 'nodes_sequence_r': '6,0,4', 'stops_sequence_i': '4,6',
              'stops_sequence_r': '6,4', 'type': 2},
             {'name': 'DSE1_tm-0-0-0_3', 'transport_mode_public_id': transport_mode_public_id,
              'nodes_sequence_i': '6,0,8', 'nodes_sequence_r': '8,0,6', 'stops_sequence_i': '6,8',
              'stops_sequence_r': '8,6', 'type': 2},
             {'name': 'DSE1_tm-0-0-0_4', 'transport_mode_public_id': transport_mode_public_id,
              'nodes_sequence_i': '8,0,2', 'nodes_sequence_r': '2,0,8', 'stops_sequence_i': '8,2',
              'stops_sequence_r': '2,8', 'type': 2}],
            [{'name': 'F_tm-0-0-0_1', 'transport_mode_public_id': transport_mode_public_id,
              'nodes_sequence_i': '1,2', 'nodes_sequence_r': '2,1', 'stops_sequence_i': '1,2',
              'stops_sequence_r': '2,1', 'type': 2},
             {'name': 'F_tm-0-0-0_2', 'transport_mode_public_id': transport_mode_public_id,
              'nodes_sequence_i': '3,4', 'nodes_sequence_r': '4,3', 'stops_sequence_i': '3,4',
              'stops_sequence_r': '4,3', 'type': 2},
             {'name': 'F_tm-0-0-0_3', 'transport_mode_public_id': transport_mode_public_id,
              'nodes_sequence_i': '5,6', 'nodes_sequence_r': '6,5', 'stops_sequence_i': '5,6',
              'stops_sequence_r': '6,5', 'type': 2},
             {'name': 'F_tm-0-0-0_4', 'transport_mode_public_id': transport_mode_public_id,
              'nodes_sequence_i': '7,8', 'nodes_sequence_r': '8,7', 'stops_sequence_i': '7,8',
              'stops_sequence_r': '8,7', 'type': 2}],
            [{'name': 'RS_tm-0-0-0_1', 'transport_mode_public_id': transport_mode_public_id,
              'nodes_sequence_i': '2,0', 'nodes_sequence_r': '0,2', 'stops_sequence_i': '2,0',
              'stops_sequence_r': '0,2', 'type': 2},
             {'name': 'RS_tm-0-0-0_2', 'transport_mode_public_id': transport_mode_public_id,
              'nodes_sequence_i': '4,0', 'nodes_sequence_r': '0,4', 'stops_sequence_i': '4,0',
              'stops_sequence_r': '0,4', 'type': 2},
             {'name': 'RS_tm-0-0-0_3', 'transport_mode_public_id': transport_mode_public_id,
              'nodes_sequence_i': '6,0', 'nodes_sequence_r': '0,6', 'stops_sequence_i': '6,0',
              'stops_sequence_r': '0,6', 'type': 2},
             {'name': 'RS_tm-0-0-0_4', 'transport_mode_public_id': transport_mode_public_id,
              'nodes_sequence_i': '8,0', 'nodes_sequence_r': '0,8', 'stops_sequence_i': '8,0',
              'stops_sequence_r': '0,8', 'type': 2}],
            [{'name': 'TSE1_tm-0-0-0_1', 'transport_mode_public_id': transport_mode_public_id,
              'nodes_sequence_i': '2,4', 'nodes_sequence_r': '4,2', 'stops_sequence_i': '2,4',
              'stops_sequence_r': '4,2', 'type': 2},
             {'name': 'TSE1_tm-0-0-0_2', 'transport_mode_public_id': transport_mode_public_id,
              'nodes_sequence_i': '4,6', 'nodes_sequence_r': '6,4', 'stops_sequence_i': '4,6',
              'stops_sequence_r': '6,4', 'type': 2},
             {'name': 'TSE1_tm-0-0-0_3', 'transport_mode_public_id': transport_mode_public_id,
              'nodes_sequence_i': '6,8', 'nodes_sequence_r': '8,6', 'stops_sequence_i': '6,8',
              'stops_sequence_r': '8,6', 'type': 2},
             {'name': 'TSE1_tm-0-0-0_4', 'transport_mode_public_id': transport_mode_public_id,
              'nodes_sequence_i': '8,2', 'nodes_sequence_r': '2,8', 'stops_sequence_i': '8,2',
              'stops_sequence_r': '2,8', 'type': 2}]
        ]

        for route_type, expected_result in zip(route_type_list, expected_results):
            default_routes = [
                dict(transportMode=str(transport_mode_public_id), type=route_type, zoneJumps=1, extension=True,
                     odExclusive=True)
            ]

            with self.assertNumQueries(2):
                json_response = self.transport_network_create_default_routes_action(
                    self.client, str(self.scene_obj.public_id), default_routes)
            self.assertListEqual(json_response, expected_result)

    def test_create_route(self):
        route_data = dict(name='new name', nodes_sequence_i='1,2', stops_sequence_i='1,2', nodes_sequence_r='2,1',
                          stops_sequence_r='2,1', type=Route.CUSTOM,
                          transport_mode_public_id=TransportMode.objects.first().public_id)
        data = dict(name='transport network test', scene_public_id=self.scene_obj.public_id, route_set=[route_data])
        with self.assertNumQueries(9):
            json_response = self.transport_network_create(self.client, data)

        self.assertEqual(Route.objects.count(), 2)
        self.assertDictEqual(json_response['route_set'][0], RouteSerializer(Route.objects.order_by('-id').first()).data)

    def test_create_route_but_transport_mode_does_not_exist(self):
        route_data = dict(name='new name', nodes_sequence_i='1,2', stops_sequence_i='1,2', nodes_sequence_r='2,1',
                          stops_sequence_r='2,1', type=Route.CUSTOM, transport_mode_public_id=str(uuid.uuid4()))
        data = dict(name='transport network test', scene_public_id=self.scene_obj.public_id, route_set=[route_data])
        with self.assertNumQueries(2):
            json_response = self.transport_network_create(self.client, data,
                                                          status_code=status.HTTP_400_BAD_REQUEST)

        self.assertEqual(Route.objects.count(), 1)
        self.assertIn('Transport mode does not exist', json_response['non_field_errors'][0])

    def test_update_route(self):
        public_id = self.transport_network_obj.route_set.all()[0].public_id
        transport_mode_obj = TransportMode.objects.first()
        route_data = dict(name='new name', public_id=str(public_id), nodes_sequence_i='1,2', stops_sequence_i='1,2',
                          nodes_sequence_r='2,1', stops_sequence_r='2,1', type=Route.PREDEFINED,
                          transport_mode_public_id=str(transport_mode_obj.public_id))
        data = dict(name='new_name', scene_public_id=self.scene_obj.public_id, route_set=[route_data])

        with self.assertNumQueries(13):
            json_response = self.transport_network_update(self.client, self.transport_network_obj.public_id, data,
                                                          status_code=status.HTTP_200_OK)

        self.assertEqual(Route.objects.count(), 1)
        for key in route_data.keys():
            # this key is not present in answer
            if key not in ['transport_mode_public_id']:
                self.assertEqual(json_response['route_set'][0][key], route_data[key])
            else:
                self.assertEqual(json_response['route_set'][0]['transport_mode'],
                                 TransportModeSerializer(transport_mode_obj).data)
        self.assertDictEqual(json_response['route_set'][0],
                             RouteSerializer(Route.objects.get(public_id=public_id)).data)

    def test_update_transport_network_adding_new_route(self):
        route_set = []
        for route in self.transport_network_obj.route_set.all():
            route_set.append(
                dict(name=route.name, nodes_sequence_i=route.nodes_sequence_i, stops_sequence_i=route.stops_sequence_i,
                     nodes_sequence_r=route.nodes_sequence_r, stops_sequence_r=route.stops_sequence_r, type=route.type,
                     transport_mode_public_id=route.transport_mode.public_id, public_id=route.public_id))
        transport_mode_obj = TransportMode.objects.first()
        route_data = dict(name='new route', nodes_sequence_i='1,2', stops_sequence_i='1,2',
                          nodes_sequence_r='2,1', stops_sequence_r='2,1', type=Route.CUSTOM,
                          transport_mode_public_id=str(transport_mode_obj.public_id))
        route_set.append(route_data)
        data = dict(name='new_name', scene_public_id=self.scene_obj.public_id, route_set=route_set)

        with self.assertNumQueries(16):
            self.transport_network_update(self.client, self.transport_network_obj.public_id, data,
                                          status_code=status.HTTP_200_OK)

        self.assertEqual(Route.objects.count(), 2)

    def test_delete_route(self):
        data = dict(name='new name', scene_public_id=self.scene_obj.public_id, route_set=[])
        with self.assertNumQueries(12):
            self.transport_network_update(self.client, self.transport_network_obj.public_id, data)

        self.assertEqual(Route.objects.count(), 0)

    def test_transport_network_results(self):
        transport_network_obj = TransportNetwork.objects.first()
        transport_network_obj.optimization_status = TransportNetwork.STATUS_FINISHED
        transport_network_obj.optimization_ran_at = timezone.now()
        transport_network_obj.save()

        OptimizationResult.objects.create(transport_network=transport_network_obj, vrc=2, co=2, ci=2, cu=2, tv=2, tw=2,
                                          ta=2, t=2)
        for i, transport_mode_obj in enumerate(self.scene_obj.transportmode_set.all()):
            OptimizationResultPerMode.objects.create(transport_network=transport_network_obj,
                                                     transport_mode=transport_mode_obj,
                                                     b=i, k=i, l=i)

        route_obj = Route.objects.first()
        opt_result_per_route_obj = OptimizationResultPerRoute.objects.create(
            transport_network=transport_network_obj, route=route_obj, frequency=1, k=1, b=1, tc=1, co=1, lambda_min=1)
        OptimizationResultPerRouteDetail.objects.create(
            opt_route=opt_result_per_route_obj, direction=OptimizationResultPerRouteDetail.DIRECTION_I,
            origin_node=1, destination_node=2, lambda_value=1)
        OptimizationResultPerRouteDetail.objects.create(
            opt_route=opt_result_per_route_obj, direction=OptimizationResultPerRouteDetail.DIRECTION_I,
            origin_node=2, destination_node=3, lambda_value=1)

        with self.assertNumQueries(9):
            json_response = self.transport_network_results(self.client, transport_network_obj.public_id)

        self.assertDictEqual(json_response['opt_result'],
                             TransportNetworkOptimizationSerializer(transport_network_obj).data)
        self.assertListEqual(json_response['opt_result_per_route'],
                             [OptimizationResultPerRouteSerializer(opt_result_per_route_obj).data])

    def test_transport_network_results_without_data(self):
        with self.assertNumQueries(6):
            json_response = self.transport_network_results(self.client, self.transport_network_obj.public_id)

        self.assertDictEqual(json_response, dict(opt_result=[], opt_result_per_route=[]))


class RecentOptimizationsAPITest(BaseTestCase):

    def setUp(self):
        self.client = APIClient()
        self.create_data(city_number=1, scene_number=1, transport_network_number=5)

    def test_get_recent_optimizations(self):
        TransportNetwork.objects.update(optimization_ran_at=timezone.now())

        with self.assertNumQueries(1):
            json_response = self.recent_optimizations_list(self.client)

        self.assertEqual(4, len(json_response))
        # check fields
        fields = ['optimization_status', 'network_name', 'scene_name', 'city_name', 'network_public_id',
                  'scene_public_id', 'city_public_id']
        for opt in json_response:
            for field_name in fields:
                self.assertIn(field_name, opt)


class OptimizationActionTest(BaseTestCase):

    def setUp(self):
        self.client = APIClient()
        self.create_data(city_number=1, scene_number=1, passenger=True, transport_mode_number=2,
                         transport_network_number=1, route_number=0)
        self.transport_network_obj = TransportNetwork.objects.first()

    def test_run_optimization_with_wrong_data(self):
        with self.assertNumQueries(8):
            json_response = self.run_optimization(self.client, self.transport_network_obj.public_id)

        self.assertEqual(json_response['optimization_status'], TransportNetwork.STATUS_QUEUED)
        self.assertIsNone(json_response['optimization_ran_at'])

    def test_run_optimization_with_correct_data(self):
        # TODO: check with Felive Vera
        graph = self.transport_network_obj.scene.city.get_sidermit_graph()
        network_obj = self.transport_network_obj.get_sidermit_network(graph)
        # add feeder routes
        transport_mode_obj = TransportMode.objects.first()
        sidermit_transport_mode_obj = transport_mode_obj.get_sidermit_transport_mode()
        routes = network_obj.get_feeder_routes(sidermit_transport_mode_obj) + \
                 network_obj.get_radial_routes(sidermit_transport_mode_obj, short=False, express=False) + \
                 network_obj.get_diametral_routes(sidermit_transport_mode_obj, short=False, express=False, jump=1)
        #        network_obj.get_circular_routes(sidermit_transport_mode_obj)

        for route in routes:
            Route.objects.create(transport_network=self.transport_network_obj, transport_mode=transport_mode_obj,
                                 name=route.id, type=route._type.value,
                                 nodes_sequence_i=','.join([str(x) for x in route.nodes_sequence_i]),
                                 stops_sequence_i=','.join([str(x) for x in route.stops_sequence_i]),
                                 nodes_sequence_r=','.join([str(x) for x in route.nodes_sequence_r]),
                                 stops_sequence_r=','.join([str(x) for x in route.stops_sequence_r]))

        with self.assertNumQueries(169):
            json_response = self.run_optimization(self.client, self.transport_network_obj.public_id)

        self.assertEqual(json_response['optimization_status'], TransportNetwork.STATUS_QUEUED)
        self.assertIsNone(json_response['optimization_ran_at'])

        self.transport_network_obj.refresh_from_db()
        self.assertEqual(self.transport_network_obj.optimization_status, TransportNetwork.STATUS_FINISHED)
        self.assertIsNotNone(self.transport_network_obj.optimization_ran_at)

    def test_cancel_optimization(self):
        with self.assertNumQueries(3):
            json_response = self.cancel_optimization(self.client, self.transport_network_obj.public_id)

        self.assertIsNone(json_response['optimization_status'])
        self.assertIsNone(json_response['optimization_ran_at'])


class ValidationAPITest(BaseTestCase):

    def setUp(self):
        self.client = APIClient()
        # TODO: finish this

    def validate_route(self, client, data, status_code=status.HTTP_200_OK):
        url = reverse('validate-route')
        return self._make_request(client, self.GET_REQUEST, url, data, status_code, format='json')

    def validate_transport_mode(self, client, data, status_code=status.HTTP_200_OK):
        url = reverse('validate-transport-mode')
        return self._make_request(client, self.GET_REQUEST, url, data, status_code, format='json')

    def test_validate_route(self):
        json_response = self.validate_route(self.client, dict())
        print(json_response)

    def test_validate_transport_mode_without_data(self):
        json_response = self.validate_transport_mode(self.client, dict(), status_code=status.HTTP_400_BAD_REQUEST)
        for key in ['name', 'bya', 'co', 'c1', 'c2', 'v', 't', 'fmax', 'kmax', 'theta', 'tat', 'd', 'fini']:
            self.assertIn(json_response[key][0], 'This field is required.')

    def test_validate_transport_mode_with_wrong_data(self):
        data = dict(name='tm', bya=-10000, co=-1, c1=-1, c2=-1, v=-1, t=-1, fmax=1, kmax=1, theta=1, tat=1, d=1, fini=1)
        json_response = self.validate_transport_mode(self.client, data, status_code=status.HTTP_400_BAD_REQUEST)
        self.assertIn(json_response['non_field_errors'][0], 'You must give a valid value for bya')
