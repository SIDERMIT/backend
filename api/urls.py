from rest_framework import routers

from api.views import CityViewSet, SceneViewSet

# Routers provide an easy way of automatically determining the URL conf.
router = routers.DefaultRouter()
router.register('cities', CityViewSet, basename='cities')
router.register('scenes', SceneViewSet, basename='scenes')

urlpatterns = [
]

urlpatterns += router.urls
