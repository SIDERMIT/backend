import json

from django.test import TestCase
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIClient

from api.serializers import CitySerializer
from storage.models import City


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


class CityAPITest(BaseTestCase):

    def setUp(self):
        self.client = APIClient()
        self.name = 'city name'
        self.graph = 'Nodes 1\n1 node1 12\n2 node2 12'
        self.matrix = [[1, 2], [1, 2]]
        self.city_obj = City.objects.create(name=self.name, graph=self.graph, demand_matrix=self.matrix)

    def test_retrieve_city_list(self):
        with self.assertNumQueries(2):
            json_response = self.cities_list(self.client)

        self.assertEqual(len(json_response), 1)
        self.assertDictEqual(json_response[0], CitySerializer(self.city_obj).data)

    def test_retrieve_city_with_public_id(self):
        with self.assertNumQueries(2):
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
        with self.assertNumQueries(3):
            json_response = self.cities_update(self.client, self.city_obj.public_id, new_data)

        self.city_obj.refresh_from_db()
        self.assertDictEqual(json_response, CitySerializer(self.city_obj).data)
        self.assertEqual(self.city_obj.name, new_city_name)

    def test_partial_update_city(self):
        new_city_name = 'name2'
        new_data = dict(name=new_city_name)
        with self.assertNumQueries(3):
            json_response = self.cities_partial_update(self.client, self.city_obj.public_id, new_data)

        self.city_obj.refresh_from_db()
        self.assertDictEqual(json_response, CitySerializer(self.city_obj).data)
        self.assertEqual(self.city_obj.name, new_city_name)

    def test_delete_city(self):
        with self.assertNumQueries(4):
            self.cities_delete(self.client, self.city_obj.public_id)

        self.assertEqual(City.objects.count(), 0)
