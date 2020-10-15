import logging

from django.conf import settings
from django.utils import timezone
from django_rq import job
from sidermit.exceptions import SIDERMITException
from sidermit.optimization import Optimizer

from storage.models import TransportNetwork, OptimizationResult, OptimizationResultPerMode, TransportMode, \
    OptimizationResultPerRoute, OptimizationResultPerRouteDetail, Route

logger = logging.getLogger(__name__)


@job(settings.OPTIMIZER_QUEUE_NAME, timeout=60 * 60 * 24 * 3)
def optimize_transport_network(transport_network_public_id):
    start_time = timezone.now()
    transport_network_obj = TransportNetwork.objects.select_related('scene__city', 'scene__passenger').get(
        public_id=transport_network_public_id)
    transport_network_obj.optimization_status = TransportNetwork.STATUS_PROCESSING
    transport_network_obj.optimization_ran_at = timezone.now()
    transport_network_obj.save()

    graph = transport_network_obj.scene.city.get_sidermit_graph()
    demand = transport_network_obj.scene.city.get_sidermit_demand_matrix(graph)

    passenger = transport_network_obj.scene.passenger.get_sidermit_passenger()
    network = transport_network_obj.get_sidermit_network(graph)

    transport_mode_dict = dict()
    for transport_mode_obj in transport_network_obj.scene.transportmode_set.all():
        transport_mode_dict[transport_mode_obj.id] = transport_mode_obj.get_sidermit_transport_mode()

    for route_obj in transport_network_obj.route_set.all():
        network.add_route(route_obj.get_sidermit_route(transport_mode_dict[route_obj.transport_mode_id]))

    try:
        # build optimizer object
        opt_obj = Optimizer(graph, demand, passenger, network, f=None)
        # run optimizer
        res = Optimizer.network_optimization(graph, demand, passenger, network, f=None, tolerance=0.01)

        ov_results = opt_obj.overall_results(res)

        opt_result_obj, created = OptimizationResult.objects.get_or_create(
            transport_network=transport_network_obj,
            defaults=dict(vrc=ov_results['VRC'], co=ov_results['operators_cost'], ci=ov_results['infrastructure_cost'],
                          cu=ov_results['users_cost'], tv=ov_results['travel_time_on_board'],
                          tw=ov_results['waiting_time'], ta=ov_results['access_time'], t=ov_results['transfers']))
        if not created:
            opt_result_obj.vrc = ov_results['VRC']
            opt_result_obj.co = ov_results['operators_cost']
            opt_result_obj.ci = ov_results['infrastructure_cost']
            opt_result_obj.cu = ov_results['users_cost']
            opt_result_obj.tv = ov_results['travel_time_on_board']
            opt_result_obj.tw = ov_results['waiting_time']
            opt_result_obj.ta = ov_results['access_time']
            opt_result_obj.t = ov_results['transfers']
            opt_result_obj.save()

        for mode in ov_results['vehicles_mode']:
            b = ov_results['vehicles_mode'][mode]
            k = ov_results['vehicle_capacity_mode'][mode]
            l = ov_results['lines_mode'][mode]

            transport_mode_obj = TransportMode.objects.get(scene=transport_network_obj.scene, name=mode.name)
            opt_per_mode, created = OptimizationResultPerMode.objects.get_or_create(
                transport_network=transport_network_obj,
                transport_mode=transport_mode_obj,
                defaults=dict(b=b, k=k, l=l))

            if not created:
                opt_per_mode.b = b
                opt_per_mode.k = k
                opt_per_mode.l = l
                opt_per_mode.save()

        network_results = opt_obj.network_results(res)

        for route in network_results:
            route_name = route[0]
            route_obj = Route.objects.get(transport_network=transport_network_obj, name=route_name)
            opt_result_per_route_obj, _ = OptimizationResultPerRoute.objects.get_or_create(
                transport_network=transport_network_obj, route=route_obj,
                defaults=dict(frequency=route[1], frequency_per_line=route[2], k=route[3], b=route[4], tc=route[5],
                              co=route[6], lambda_min=route[7]))
            opt_result_per_route_obj.frequency = route[1]
            opt_result_per_route_obj.frequency_per_line = route[2]
            opt_result_per_route_obj.k = route[3]
            opt_result_per_route_obj.b = route[4]
            opt_result_per_route_obj.tc = route[5]
            opt_result_per_route_obj.co = route[6]
            opt_result_per_route_obj.lambda_min = route[7]
            opt_result_per_route_obj.save()

            sub_table_i = route[8]
            sub_table_r = route[9]

            OptimizationResultPerRouteDetail.objects.filter(opt_route=opt_result_per_route_obj).delete()
            for node_i, node_j, charge_ij in sub_table_i:
                OptimizationResultPerRouteDetail.objects.create(opt_route=opt_result_per_route_obj,
                                                                direction=OptimizationResultPerRouteDetail.DIRECTION_I,
                                                                origin_node=node_i, destination_node=node_j,
                                                                lambda_value=charge_ij)
            for node_i, node_j, charge_ij in sub_table_r:
                OptimizationResultPerRouteDetail.objects.create(opt_route=opt_result_per_route_obj,
                                                                direction=OptimizationResultPerRouteDetail.DIRECTION_R,
                                                                origin_node=node_i, destination_node=node_j,
                                                                lambda_value=charge_ij)

        transport_network_obj.optimization_status = TransportNetwork.STATUS_FINISHED
        transport_network_obj.optimization_duration = timezone.now() - start_time
        transport_network_obj.optimization_error_message = None
        transport_network_obj.save()
    except (SIDERMITException, Exception) as e:
        transport_network_obj.optimization_status = TransportNetwork.STATUS_ERROR
        transport_network_obj.optimization_duration = timezone.now() - start_time
        transport_network_obj.optimization_error_message = str(e)
        transport_network_obj.save()
