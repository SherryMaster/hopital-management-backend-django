from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'medical-records', views.MedicalRecordViewSet, basename='medical-records')
router.register(r'diagnoses', views.DiagnosisViewSet, basename='diagnoses')
router.register(r'prescriptions', views.PrescriptionViewSet, basename='prescriptions')
router.register(r'documents', views.MedicalDocumentViewSet, basename='documents')
router.register(r'vital-signs', views.VitalSignsViewSet, basename='vital-signs')
router.register(r'alerts', views.MedicalAlertViewSet, basename='alerts')

urlpatterns = [
    path('', include(router.urls)),
]
