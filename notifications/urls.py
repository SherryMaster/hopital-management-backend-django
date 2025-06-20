from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'email-templates', views.EmailTemplateViewSet, basename='email-templates')
router.register(r'email-notifications', views.EmailNotificationViewSet, basename='email-notifications')
router.register(r'sms-templates', views.SMSTemplateViewSet, basename='sms-templates')
router.register(r'sms-notifications', views.SMSNotificationViewSet, basename='sms-notifications')
router.register(r'push-templates', views.PushNotificationTemplateViewSet, basename='push-templates')
router.register(r'push-notifications', views.PushNotificationViewSet, basename='push-notifications')
router.register(r'unified-templates', views.UnifiedTemplateViewSet, basename='unified-templates')
router.register(r'preferences', views.NotificationPreferenceViewSet, basename='preferences')
router.register(r'settings', views.NotificationSettingsViewSet, basename='settings')

urlpatterns = [
    path('', include(router.urls)),
]
