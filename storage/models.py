import uuid

from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.utils import timezone


class City(models.Model):
    """ city == project """
    created_at = models.DateTimeField(default=timezone.now)
    public_id = models.UUIDField(default=uuid.uuid4)
    name = models.CharField(max_length=50)
    graph = models.TextField(null=False)
    demand_matrix = ArrayField(ArrayField(models.IntegerField()), null=True)
    # graph parameters
    n = models.FloatField(null=True)
    p = models.FloatField(null=True)
    l = models.FloatField(null=True)
    g = models.FloatField(null=True)
    # matrix parameters
    y = models.FloatField(null=True)
    a = models.FloatField(null=True)
    alpha = models.FloatField(null=True)
    beta = models.FloatField(null=True)


class Scene(models.Model):
    city = models.ForeignKey(City, on_delete=models.CASCADE)
    public_id = models.UUIDField(default=uuid.uuid4)
    created_at = models.DateTimeField(default=timezone.now)
    name = models.CharField(max_length=50)


class Passenger(models.Model):
    created_at = models.DateTimeField(default=timezone.now)
    name = models.CharField(max_length=50)
    scene = models.OneToOneField(Scene, on_delete=models.CASCADE)
    # passenger variables
    va = models.FloatField()
    pv = models.FloatField()
    pw = models.FloatField()
    pa = models.FloatField()
    pt = models.FloatField()
    spv = models.FloatField()
    spw = models.FloatField()
    spa = models.FloatField()
    spt = models.FloatField()


class TransportMode(models.Model):
    created_at = models.DateTimeField(default=timezone.now)
    name = models.CharField(max_length=50)
    scene = models.ForeignKey(Scene, on_delete=models.CASCADE)
    # transport mode variables
    b_a = models.IntegerField()  # b&a
    co = models.FloatField()
    c1 = models.FloatField()
    c2 = models.FloatField()
    v = models.FloatField()
    t = models.FloatField()
    f_max = models.FloatField()
    k_max = models.FloatField()
    theta = models.FloatField()
    tat = models.FloatField()
    d = models.FloatField()


class TransportNetwork(models.Model):
    scene = models.ForeignKey(Scene, on_delete=models.CASCADE)
    created_at = models.DateTimeField(default=timezone.now)
    name = models.CharField(max_length=50)


class Route(models.Model):
    transport_network = models.ForeignKey(TransportNetwork, on_delete=models.CASCADE)
    transport_mode = models.ForeignKey(TransportMode, on_delete=models.CASCADE)
    created_at = models.DateTimeField(default=timezone.now)
    name = models.CharField(max_length=50)
    node_sequence_i = models.CharField(max_length=50)
    stop_sequence_i = models.CharField(max_length=50)
    node_sequence_r = models.CharField(max_length=50, null=True)
    stop_sequence_r = models.CharField(max_length=50, null=True)


class Optimization(models.Model):
    transport_network = models.OneToOneField(TransportNetwork, on_delete=models.CASCADE)
    created_at = models.DateTimeField(default=timezone.now)
    STATUS_QUEUED = 'queued'
    STATUS_PROCESSING = 'processing'
    STATUS_FINISHED = 'finished'
    STATUS_ERROR = 'error'
    status_choices = (
        (STATUS_QUEUED, 'Queued'),
        (STATUS_PROCESSING, 'Processing'),
        (STATUS_FINISHED, 'Finished'),
        (STATUS_ERROR, 'Error'),
    )
    status = models.CharField(max_length=20, choices=status_choices, default=STATUS_QUEUED, null=False)


class OptimizationResult(models.Model):
    optimization = models.OneToOneField(Optimization, on_delete=models.CASCADE)
    # optimization variables
    vrc = models.FloatField()
    co = models.FloatField()
    ci = models.FloatField()
    cu = models.FloatField()
    tv = models.FloatField()
    tw = models.FloatField()
    ta = models.FloatField()
    t = models.FloatField()


class OptimizationResultPerMode(models.Model):
    optimization = models.OneToOneField(Optimization, on_delete=models.CASCADE)
    transport_mode = models.ForeignKey(TransportMode, on_delete=models.CASCADE)
    # optimization variables
    b = models.FloatField()
    k = models.FloatField()
    l = models.FloatField()


class OptimizationResultPerRoute(models.Model):
    optimization = models.OneToOneField(Optimization, on_delete=models.CASCADE)
    route = models.ForeignKey(Route, on_delete=models.CASCADE)
    # optimization variables
    frequency = models.FloatField()
    k = models.FloatField()
    b = models.FloatField()
    tc = models.FloatField()
    co = models.FloatField()
    lambda_min = models.FloatField()


class OptimizationResultPerRouteDetail(models.Model):
    """ result for each arc related to route """
    opt_route = models.ForeignKey(OptimizationResultPerRoute, on_delete=models.CASCADE)
    origin_node = models.IntegerField()
    destination_node = models.IntegerField()
    lambda_value = models.FloatField()
