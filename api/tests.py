import json
import uuid

from django.test import TestCase
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIClient

from api.serializers import CitySerializer, SceneSerializer, PassengerSerializer
from storage.models import City, Scene, Passenger, TransportMode


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

    def create_data(self, city_number, scene_number=0, passenger=False, transport_mode_number=0):
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
                for k in range(transport_mode_number):
                    TransportMode.objects.create(name='tm-{0}-{1}-{2}'.format(i, j, k), b_a=1,
                                                 co=1, c1=1, c2=1, v=1, t=1, f_max=1, k_max=1,
                                                 theta=1, tat=1, d=1, scene=scene_obj)

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
        self.city_obj = self.create_data(city_number=1, scene_number=1, passenger=True, transport_mode_number=2)[0]
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
        with self.assertNumQueries(9):
            self.scenes_delete(self.client, self.scene_obj.public_id)

        self.assertEqual(Scene.objects.count(), 0)

    def test_duplicate_scene(self):
        with self.assertNumQueries(9):
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
