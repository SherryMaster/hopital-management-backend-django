from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'buildings', views.BuildingViewSet)
router.register(r'rooms', views.RoomViewSet)
router.register(r'equipment', views.EquipmentViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
