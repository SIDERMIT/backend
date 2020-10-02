import uuid

from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.utils import timezone
from sidermit.city import Graph, GraphContentFormat
from sidermit.publictransportsystem import Passenger as SidermitPassenger, TransportMode as SidermitTransportMode, \
    TransportNetwork as SidermitTransportNetwork, Route as SidermitRoute


class City(models.Model):
    """ city == project """
    created_at = models.DateTimeField(default=timezone.now)
    public_id = models.UUIDField(default=uuid.uuid4)
    name = models.CharField(max_length=50)
    graph = models.TextField(null=False)
    demand_matrix = ArrayField(ArrayField(models.FloatField()), null=True)
    # graph parameters
    n = models.IntegerField(null=True)
    p = models.FloatField(null=True)
    l = models.FloatField(null=True)
    g = models.FloatField(null=True)
    # matrix parameters
    y = models.FloatField(null=True)
    a = models.FloatField(null=True)
    alpha = models.FloatField(null=True)
    beta = models.FloatField(null=True)

    def get_sidermit_graph(self):
        return Graph.build_from_content(self.graph, GraphContentFormat.PAJEK)


class Scene(models.Model):
    city = models.ForeignKey(City, on_delete=models.CASCADE)
    public_id = models.UUIDField(default=uuid.uuid4)
    created_at = models.DateTimeField(default=timezone.now)
    name = models.CharField(max_length=50)


class Passenger(models.Model):
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

    def get_sidermit_passenger(self):
        return SidermitPassenger(self.va, self.pv, self.pw, self.pa, self.pt, self.spv, self.spw, self.spa, self.spt)


class TransportMode(models.Model):
    created_at = models.DateTimeField(default=timezone.now)
    name = models.CharField(max_length=50)
    scene = models.ForeignKey(Scene, on_delete=models.CASCADE)
    public_id = models.UUIDField(default=uuid.uuid4)
    # transport mode variables
    bya = models.IntegerField()  # b&a
    co = models.FloatField()
    c1 = models.FloatField()
    c2 = models.FloatField()
    v = models.FloatField()
    t = models.FloatField()
    fini = models.FloatField()
    fmax = models.FloatField()
    kmax = models.FloatField()
    theta = models.FloatField()
    tat = models.FloatField()
    d = models.FloatField()

    def get_sidermit_transport_mode(self):
        return SidermitTransportMode(self.name, self.bya, self.co, self.c1, self.c2, self.v, self.t, self.fmax,
                                     self.kmax, self.theta, self.tat, self.d, self.fini)


class TransportNetwork(models.Model):
    scene = models.ForeignKey(Scene, on_delete=models.CASCADE)
    created_at = models.DateTimeField(default=timezone.now)
    name = models.CharField(max_length=50)
    public_id = models.UUIDField(default=uuid.uuid4)

    def get_sidermit_network(self, city_graph):
        return SidermitTransportNetwork(city_graph)


class Route(models.Model):
    transport_network = models.ForeignKey(TransportNetwork, on_delete=models.CASCADE)
    transport_mode = models.ForeignKey(TransportMode, on_delete=models.CASCADE)
    created_at = models.DateTimeField(default=timezone.now)
    public_id = models.UUIDField(default=uuid.uuid4)
    name = models.CharField(max_length=50)
    node_sequence_i = models.CharField(max_length=50)
    stop_sequence_i = models.CharField(max_length=50)
    node_sequence_r = models.CharField(max_length=50, null=True)
    stop_sequence_r = models.CharField(max_length=50, null=True)
    CUSTOM = 1
    PREDEFINED = 2
    CIRCULAR = 3
    TYPE_CHOICES = (
        (CUSTOM, 'CUSTOM'),
        (PREDEFINED, 'PREDEFINED'),
        (CIRCULAR, 'CIRCULAR')
    )
    type = models.IntegerField(null=False, choices=TYPE_CHOICES)

    def get_sidermit_route(self, transport_mode_obj, route_type):
        return SidermitRoute(self.name, transport_mode_obj, self.node_sequence_i, self.node_sequence_r,
                             self.stop_sequence_i, self.stop_sequence_r, route_type)

    class Meta:
        unique_together = ('transport_network', 'name')


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
    optimization = models.ForeignKey(Optimization, on_delete=models.CASCADE)
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
