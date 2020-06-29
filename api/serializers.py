import logging

from rest_framework import serializers

from storage.models import City

logger = logging.getLogger(__name__)


class CitySerializer(serializers.ModelSerializer):
    class Meta:
        model = City
        fields = (
            'public_id', 'created_at', 'name', 'graph', 'demand_matrix', 'n', 'p', 'l', 'g', 'y', 'a', 'alpha', 'beta')
        read_only_fields = ['created_at', 'public_id']
