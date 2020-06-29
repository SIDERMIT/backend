from django.shortcuts import render

import itertools
import logging

import csv

from django.db import transaction
from django.db.models import Count, Q
from django.db.models.functions import Trunc
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone, dateparse
from django.utils.encoding import smart_str
from rest_framework import mixins
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from api.serializers import CitySerializer
from storage.models import City

logger = logging.getLogger(__name__)


class CityViewSet(viewsets.ModelViewSet):
    """
    API endpoint to work with cities
    """
    serializer_class = CitySerializer
    lookup_field = 'public_id'
    queryset = City.objects.prefetch_related('scene_set__transportmode_set')
