from rest_framework import routers
from rest_framework_nested import routers as nested_routers

from api.views import CityViewSet, SceneViewSet, TransportNetworkViewSet, RouteViewSet

# Routers provide an easy way of automatically determining the URL conf.
router = routers.DefaultRouter()
router.register('cities', CityViewSet, basename='cities')
router.register('scenes', SceneViewSet, basename='scenes')
router.register('transport_networks', TransportNetworkViewSet, basename='transport-networks')

transport_network_router = nested_routers.NestedDefaultRouter(router, 'transport_networks', lookup='transport_network')
transport_network_router.register('routes', RouteViewSet, basename='routes')

urlpatterns = [
]

urlpatterns += router.urls
urlpatterns += transport_network_router.urls
