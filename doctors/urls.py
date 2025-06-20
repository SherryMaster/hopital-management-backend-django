from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_nested import routers
from .views import (
    DoctorRegistrationView,
    DoctorViewSet,
    DoctorProfileView,
    SpecializationViewSet,
    DepartmentViewSet,
    DoctorQualificationViewSet,
    DoctorAvailabilityViewSet,
)

# Create main router
router = DefaultRouter()
router.register(r'doctors', DoctorViewSet, basename='doctor')
router.register(r'specializations', SpecializationViewSet, basename='specialization')
router.register(r'departments', DepartmentViewSet, basename='department')
router.register(r'availability', DoctorAvailabilityViewSet, basename='doctor-availability')

# Create nested routers for doctor-related resources
doctors_router = routers.NestedDefaultRouter(router, r'doctors', lookup='doctor')
doctors_router.register(r'qualifications', DoctorQualificationViewSet, basename='doctor-qualifications')

app_name = 'doctors'

urlpatterns = [
    # Doctor registration (admin endpoint)
    path('register/', DoctorRegistrationView.as_view(), name='doctor_register'),
    
    # Doctor profile for authenticated doctors
    path('profile/', DoctorProfileView.as_view(), name='doctor_profile'),
    
    # Include router URLs
    path('', include(router.urls)),
    path('', include(doctors_router.urls)),
]
