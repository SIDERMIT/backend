from rest_framework import routers

from api.views import CityViewSet

# Routers provide an easy way of automatically determining the URL conf.
router = routers.DefaultRouter()
router.register('cities', CityViewSet, basename='cities')

urlpatterns = [
]

urlpatterns += router.urls
