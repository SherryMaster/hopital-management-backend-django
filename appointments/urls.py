from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AppointmentViewSet, AppointmentTypeViewSet

app_name = 'appointments'

# Create router for ViewSets
router = DefaultRouter()
router.register(r'appointments', AppointmentViewSet, basename='appointments')
router.register(r'appointment-types', AppointmentTypeViewSet, basename='appointment-types')

urlpatterns = [
    # Include router URLs
    path('', include(router.urls)),
]
