from django.urls import path
from rest_framework import routers
from rest_framework_nested import routers as nested_routers

from api.views import CityViewSet, SceneViewSet, TransportNetworkViewSet, RouteViewSet, TransportModeViewSet, \
    validate_route, validate_passenger, validate_transport_mode, recent_optimizations

# Routers provide an easy way of automatically determining the URL conf.
router = routers.DefaultRouter()
router.register('cities', CityViewSet, basename='cities')
router.register('scenes', SceneViewSet, basename='scenes')
router.register('transport_networks', TransportNetworkViewSet, basename='transport-networks')

scene_transport_mode_router = nested_routers.NestedDefaultRouter(router, 'scenes', lookup='scene')
scene_transport_mode_router.register('transport_modes', TransportModeViewSet, basename='transport-modes')

urlpatterns = [
    path('recent_optimizations', recent_optimizations, name='recent-optimizations'),
    path('validation/route', validate_route, name='validate-route'),
    path('validation/passenger', validate_passenger, name='validate-passenger'),
    path('validation/transport_mode', validate_transport_mode, name='validate-transport-mode'),
    path('validation/graph_file', validate_route, name='validate-graph-file'),
    path('validation/graph_parameters', validate_route, name='validate-graph-parameters'),
    path('validation/matrix_file', validate_route, name='validate-matrix-file'),
    path('validation/matrix_parameters', validate_route, name='validate-matrix-parameters'),
]

urlpatterns += router.urls
urlpatterns += scene_transport_mode_router.urls
