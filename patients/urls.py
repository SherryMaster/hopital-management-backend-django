from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_nested import routers
from .views import (
    PatientRegistrationView,
    PatientViewSet,
    PatientProfileView,
    EmergencyContactViewSet,
    InsuranceInformationViewSet,
)

# Create main router
router = DefaultRouter()
router.register(r'patients', PatientViewSet, basename='patient')

# Create nested routers for patient-related resources
patients_router = routers.NestedDefaultRouter(router, r'patients', lookup='patient')
patients_router.register(r'emergency-contacts', EmergencyContactViewSet, basename='patient-emergency-contacts')
patients_router.register(r'insurance', InsuranceInformationViewSet, basename='patient-insurance')

app_name = 'patients'

urlpatterns = [
    # Patient registration (public endpoint)
    path('register/', PatientRegistrationView.as_view(), name='patient_register'),
    
    # Patient profile for authenticated patients
    path('profile/', PatientProfileView.as_view(), name='patient_profile'),
    
    # Include router URLs
    path('', include(router.urls)),
    path('', include(patients_router.urls)),
]
