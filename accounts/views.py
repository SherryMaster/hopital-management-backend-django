from rest_framework import status, permissions, generics, viewsets, serializers
from rest_framework.decorators import action
from django.contrib.auth.models import Group, Permission
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView, TokenVerifyView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.template.loader import render_to_string
from drf_spectacular.utils import extend_schema

from .models import User, UserProfile, UserActivity, UserSession
from .serializers import (
    CustomTokenObtainPairSerializer,
    UserSerializer,
    UserRegistrationSerializer,
    UserProfileSerializer,
    PasswordChangeSerializer,
    PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer,
    UserActivitySerializer
)
import logging

logger = logging.getLogger(__name__)


class CustomTokenObtainPairView(TokenObtainPairView):
    """
    Custom JWT token obtain view with enhanced logging and session tracking
    """
    serializer_class = CustomTokenObtainPairSerializer

    @extend_schema(
        tags=['Authentication & User Management'],
        summary="Obtain JWT token pair",
        description="Login with email and password to get access and refresh tokens",
        responses={200: CustomTokenObtainPairSerializer}
    )
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)

        if response.status_code == 200:
            # Create user session record
            serializer = self.get_serializer(data=request.data)
            if serializer.is_valid():
                user_email = serializer.validated_data.get('email')
                try:
                    user = User.objects.get(email=user_email)
                    UserSession.objects.create(
                        user=user,
                        session_key=request.session.session_key or 'api_session',
                        ip_address=request.META.get('REMOTE_ADDR', ''),
                        user_agent=request.META.get('HTTP_USER_AGENT', '')
                    )
                except User.DoesNotExist:
                    pass

        return response


class CustomTokenRefreshView(TokenRefreshView):
    """
    Custom JWT token refresh view with logging
    """
    @extend_schema(
        tags=['Authentication & User Management'],
        summary="Refresh JWT token",
        description="Refresh access token using refresh token"
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class CustomTokenVerifyView(TokenVerifyView):
    """
    Custom JWT token verify view with proper tagging
    """
    @extend_schema(
        tags=['Authentication & User Management'],
        summary="Verify JWT token",
        description="Verify the validity of a JWT token"
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class LogoutView(APIView):
    """
    Logout view that blacklists the refresh token
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=['Authentication & User Management'],
        summary="Logout user",
        description="Logout user and blacklist refresh token",
        request=None,
        responses={200: {"description": "Successfully logged out"}}
    )
    def post(self, request):
        try:
            refresh_token = request.data.get("refresh_token")
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()

            # Update user session
            try:
                session = UserSession.objects.filter(
                    user=request.user,
                    is_active=True
                ).first()
                if session:
                    session.is_active = False
                    session.logout_time = timezone.now()
                    session.save()
            except Exception as e:
                logger.warning(f"Could not update session: {e}")

            # Log logout activity
            UserActivity.objects.create(
                user=request.user,
                action='logout',
                resource_type='authentication',
                description='User logged out',
                ip_address=request.META.get('REMOTE_ADDR', ''),
            )

            return Response(
                {"message": "Successfully logged out"},
                status=status.HTTP_200_OK
            )
        except Exception as e:
            logger.error(f"Logout error: {e}")
            return Response(
                {"error": "Error during logout"},
                status=status.HTTP_400_BAD_REQUEST
            )


@extend_schema(tags=['Authentication & User Management'])
class UserRegistrationView(generics.CreateAPIView):
    """
    User registration view
    """
    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        tags=['Authentication & User Management'],
        summary="Register new user",
        description="Register a new user account",
        responses={201: UserSerializer}
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Update IP address in activity log
        user = serializer.save()

        # Update the activity log with correct IP
        activity = UserActivity.objects.filter(
            user=user,
            action='create',
            resource_type='user_account'
        ).first()
        if activity:
            activity.ip_address = request.META.get('REMOTE_ADDR', '')
            activity.save()

        headers = self.get_success_headers(serializer.data)
        return Response(
            UserSerializer(user).data,
            status=status.HTTP_201_CREATED,
            headers=headers
        )


class UserProfileView(generics.RetrieveUpdateAPIView):
    """
    User profile view for authenticated users
    """
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user

    @extend_schema(
        tags=['Authentication & User Management'],
        summary="Get user profile",
        description="Get current user's profile information"
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        tags=['Authentication & User Management'],
        summary="Update user profile",
        description="Update current user's profile information"
    )
    def patch(self, request, *args, **kwargs):
        response = super().patch(request, *args, **kwargs)

        if response.status_code == 200:
            # Log profile update
            UserActivity.objects.create(
                user=request.user,
                action='update',
                resource_type='user_profile',
                description='User profile updated',
                ip_address=request.META.get('REMOTE_ADDR', ''),
            )

        return response

    @extend_schema(
        tags=['Authentication & User Management'],
        summary="Update user profile",
        description="Update current user's profile information"
    )
    def put(self, request, *args, **kwargs):
        response = super().put(request, *args, **kwargs)

        if response.status_code == 200:
            # Log profile update
            UserActivity.objects.create(
                user=request.user,
                action='update',
                resource_type='user_profile',
                description='User profile updated',
                ip_address=request.META.get('REMOTE_ADDR', ''),
            )

        return response


class PasswordChangeView(APIView):
    """
    Password change view for authenticated users
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=['Authentication & User Management'],
        summary="Change password",
        description="Change current user's password",
        request=PasswordChangeSerializer,
        responses={200: {"description": "Password changed successfully"}}
    )
    def post(self, request):
        serializer = PasswordChangeSerializer(
            data=request.data,
            context={'request': request}
        )

        if serializer.is_valid():
            serializer.save()
            return Response(
                {"message": "Password changed successfully"},
                status=status.HTTP_200_OK
            )

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )


class PasswordResetRequestView(APIView):
    """
    Enhanced password reset request view with security features
    """
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        tags=['Authentication & User Management'],
        summary="Request password reset",
        description="Request password reset with enhanced security",
        request=PasswordResetRequestSerializer,
        responses={200: {"description": "Password reset email sent"}}
    )
    def post(self, request):
        serializer = PasswordResetRequestSerializer(
            data=request.data,
            context={'request': request}
        )

        if serializer.is_valid():
            try:
                result = serializer.save()
                return Response(result, status=status.HTTP_200_OK)
            except serializers.ValidationError as e:
                return Response(
                    {"error": str(e)},
                    status=status.HTTP_429_TOO_MANY_REQUESTS
                )

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )


class PasswordResetConfirmView(APIView):
    """
    Enhanced password reset confirmation view
    """
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        tags=['Authentication & User Management'],
        summary="Confirm password reset",
        description="Confirm password reset with token",
        request=PasswordResetConfirmSerializer,
        responses={200: {"description": "Password reset successful"}}
    )
    def post(self, request):
        serializer = PasswordResetConfirmSerializer(
            data=request.data,
            context={'request': request}
        )

        if serializer.is_valid():
            try:
                user = serializer.save()
                return Response(
                    {"message": "Password reset successful"},
                    status=status.HTTP_200_OK
                )
            except Exception as e:
                return Response(
                    {"error": "Password reset failed"},
                    status=status.HTTP_400_BAD_REQUEST
                )

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )


class UserActivityListView(generics.ListAPIView):
    """
    User activity list view for audit logs
    """
    serializer_class = UserActivitySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Handle swagger schema generation
        if getattr(self, 'swagger_fake_view', False):
            return UserActivity.objects.none()

        user = self.request.user
        if not user.is_authenticated:
            return UserActivity.objects.none()

        if user.is_staff or getattr(user, 'user_type', None) == 'admin':
            # Admins can see all activities
            return UserActivity.objects.all()
        else:
            # Regular users can only see their own activities
            return UserActivity.objects.filter(user=user)

    @extend_schema(
        tags=['Authentication & User Management'],
        summary="Get user activities",
        description="Get list of user activities (audit log)"
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class UserSessionListView(generics.ListAPIView):
    """
    User session list view
    """
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return UserSession.objects.filter(user=self.request.user)

    @extend_schema(
        tags=['Authentication & User Management'],
        summary="Get user sessions",
        description="Get list of user sessions"
    )
    def get(self, request, *args, **kwargs):
        sessions = self.get_queryset()
        data = []

        for session in sessions:
            data.append({
                'id': session.id,
                'session_key': session.session_key,
                'ip_address': session.ip_address,
                'user_agent': session.user_agent,
                'login_time': session.login_time,
                'logout_time': session.logout_time,
                'is_active': session.is_active,
            })

        return Response(data, status=status.HTTP_200_OK)


@extend_schema(tags=['Authentication & User Management'])
class RoleManagementViewSet(viewsets.ViewSet):
    """
    ViewSet for managing user roles and permissions (Admin only)
    """
    permission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):
        """
        Only allow admin users to access role management
        """
        if self.request.user.is_authenticated and (
            self.request.user.user_type == 'admin' or
            self.request.user.is_superuser
        ):
            return [permissions.IsAuthenticated()]
        return [permissions.IsAdminUser()]

    @extend_schema(
        tags=['Authentication & User Management'],
        summary="List all user groups",
        description="Get list of all user groups and their permissions"
    )
    def list(self, request):
        """List all groups with their permissions"""
        groups = Group.objects.all()
        data = []

        for group in groups:
            permissions_list = list(group.permissions.values('id', 'name', 'codename'))
            user_count = group.user_set.count()

            data.append({
                'id': group.id,
                'name': group.name,
                'permissions': permissions_list,
                'user_count': user_count,
                'users': list(group.user_set.values('id', 'username', 'email', 'user_type'))
            })

        return Response(data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'])
    @extend_schema(
        tags=['Authentication & User Management'],
        summary="List all permissions",
        description="Get list of all available permissions"
    )
    def permissions(self, request):
        """List all available permissions"""
        permissions_list = Permission.objects.all().values(
            'id', 'name', 'codename', 'content_type__app_label'
        )
        return Response(list(permissions_list), status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'])
    @extend_schema(
        tags=['Authentication & User Management'],
        summary="Assign user to group",
        description="Assign a user to a specific group",
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'user_id': {'type': 'string', 'format': 'uuid'},
                    'group_name': {'type': 'string'}
                },
                'required': ['user_id', 'group_name']
            }
        }
    )
    def assign_user_to_group(self, request):
        """Assign user to group"""
        user_id = request.data.get('user_id')
        group_name = request.data.get('group_name')

        if not user_id or not group_name:
            return Response(
                {'error': 'user_id and group_name are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = User.objects.get(id=user_id)
            group = Group.objects.get(name=group_name)

            # Remove user from all groups first
            user.groups.clear()
            # Add user to new group
            user.groups.add(group)

            # Log the action
            UserActivity.objects.create(
                user=request.user,
                action='update',
                resource_type='user_role',
                resource_id=str(user.id),
                description=f'Assigned user {user.username} to group {group_name}',
                ip_address=request.META.get('REMOTE_ADDR', ''),
            )

            return Response(
                {'message': f'User {user.username} assigned to group {group_name}'},
                status=status.HTTP_200_OK
            )

        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Group.DoesNotExist:
            return Response(
                {'error': 'Group not found'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False, methods=['get'])
    @extend_schema(
        tags=['Authentication & User Management'],
        summary="Get user permissions",
        description="Get all permissions for a specific user"
    )
    def user_permissions(self, request):
        """Get user permissions"""
        user_id = request.query_params.get('user_id')

        if not user_id:
            return Response(
                {'error': 'user_id parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = User.objects.get(id=user_id)

            # Get user's groups
            groups = list(user.groups.values('id', 'name'))

            # Get all permissions (from groups and direct permissions)
            all_permissions = user.get_all_permissions()

            # Get group permissions
            group_permissions = []
            for group in user.groups.all():
                group_perms = list(group.permissions.values('id', 'name', 'codename'))
                group_permissions.extend(group_perms)

            return Response({
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'user_type': user.user_type,
                },
                'groups': groups,
                'permissions': list(all_permissions),
                'group_permissions': group_permissions,
            }, status=status.HTTP_200_OK)

        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )
