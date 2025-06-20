from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CustomTokenObtainPairView,
    CustomTokenRefreshView,
    CustomTokenVerifyView,
    LogoutView,
    UserRegistrationView,
    UserProfileView,
    PasswordChangeView,
    PasswordResetRequestView,
    PasswordResetConfirmView,
    UserActivityListView,
    UserSessionListView,
    RoleManagementViewSet,
)

app_name = 'accounts'

# Create router for ViewSets
router = DefaultRouter()
router.register(r'roles', RoleManagementViewSet, basename='roles')

urlpatterns = [
    # Authentication endpoints
    path('auth/login/', CustomTokenObtainPairView.as_view(), name='login'),
    path('auth/refresh/', CustomTokenRefreshView.as_view(), name='token_refresh'),
    path('auth/verify/', CustomTokenVerifyView.as_view(), name='token_verify'),
    path('auth/logout/', LogoutView.as_view(), name='logout'),

    # User management endpoints
    path('register/', UserRegistrationView.as_view(), name='register'),
    path('profile/', UserProfileView.as_view(), name='profile'),

    # Password management endpoints
    path('password/change/', PasswordChangeView.as_view(), name='password_change'),
    path('password/reset/', PasswordResetRequestView.as_view(), name='password_reset'),
    path('password/reset/confirm/', PasswordResetConfirmView.as_view(), name='password_reset_confirm'),

    # Activity and session endpoints
    path('activities/', UserActivityListView.as_view(), name='user_activities'),
    path('sessions/', UserSessionListView.as_view(), name='user_sessions'),

    # Role management endpoints (Admin only)
    path('', include(router.urls)),
]
