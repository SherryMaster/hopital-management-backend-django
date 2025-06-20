from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'service-categories', views.ServiceCategoryViewSet, basename='service-categories')
router.register(r'services', views.ServiceViewSet, basename='services')
router.register(r'invoices', views.InvoiceViewSet, basename='invoices')
router.register(r'payments', views.PaymentViewSet, basename='payments')
router.register(r'insurance-claims', views.InsuranceClaimViewSet, basename='insurance-claims')
router.register(r'financial-reports', views.FinancialReportViewSet, basename='financial-reports')
router.register(r'billing-notifications', views.BillingNotificationViewSet, basename='billing-notifications')

urlpatterns = [
    path('', include(router.urls)),
]
