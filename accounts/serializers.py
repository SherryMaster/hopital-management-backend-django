from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import User, UserProfile, UserActivity, PasswordResetToken
import logging

logger = logging.getLogger(__name__)


class CustomTokenObtainPairSerializer(serializers.Serializer):
    """
    Custom JWT token serializer with additional user information
    """
    username = serializers.CharField()  # Changed from email to username for debugging
    password = serializers.CharField()

    @classmethod
    def get_token(cls, user):
        from rest_framework_simplejwt.tokens import RefreshToken
        token = RefreshToken.for_user(user)

        # Add custom claims
        token['user_id'] = str(user.id)
        token['email'] = user.email
        token['user_type'] = user.user_type
        token['full_name'] = user.get_full_name()
        token['is_staff'] = user.is_staff
        token['is_superuser'] = user.is_superuser

        return token

    def validate(self, attrs):
        username = attrs.get('username')  # Changed from email to username
        password = attrs.get('password')

        if username and password:
            user = authenticate(
                request=self.context.get('request'),
                username=username,  # Now using username directly
                password=password
            )

            if not user:
                raise serializers.ValidationError(
                    'No active account found with the given credentials'
                )

            if not user.is_active:
                raise serializers.ValidationError(
                    'User account is disabled.'
                )

            # Log successful login
            request = self.context.get('request')
            if request:
                UserActivity.objects.create(
                    user=user,
                    action='login',
                    resource_type='authentication',
                    description='User logged in successfully',
                    ip_address=request.META.get('REMOTE_ADDR', ''),
                )

            refresh = self.get_token(user)

            return {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'user': UserSerializer(user).data
            }
        else:
            raise serializers.ValidationError(
                'Must include "email" and "password".'
            )


class UserSerializer(serializers.ModelSerializer):
    """
    User serializer for API responses
    """
    age = serializers.ReadOnlyField()
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 'full_name',
            'user_type', 'phone_number', 'date_of_birth', 'age', 'gender',
            'address', 'profile_picture', 'is_active', 'date_joined',
            'emergency_contact_name', 'emergency_contact_phone', 
            'emergency_contact_relationship'
        ]
        read_only_fields = ['id', 'date_joined', 'age']
    
    def get_full_name(self, obj):
        return obj.get_full_name()


class UserRegistrationSerializer(serializers.ModelSerializer):
    """
    User registration serializer
    """
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = [
            'username', 'email', 'password', 'password_confirm',
            'first_name', 'last_name', 'user_type', 'phone_number',
            'date_of_birth', 'gender', 'address'
        ]
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError("Passwords don't match")
        return attrs
    
    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already exists")
        return value
    
    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Username already exists")
        return value
    
    def create(self, validated_data):
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        
        user = User.objects.create_user(
            password=password,
            **validated_data
        )
        
        # Create user profile
        UserProfile.objects.create(user=user)
        
        # Log user registration
        UserActivity.objects.create(
            user=user,
            action='create',
            resource_type='user_account',
            description='User account created',
            ip_address='127.0.0.1',  # Will be updated in view
        )
        
        return user


class UserProfileSerializer(serializers.ModelSerializer):
    """
    User profile serializer
    """
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = UserProfile
        fields = [
            'user', 'bio', 'website', 'social_security_number',
            'insurance_provider', 'insurance_policy_number',
            'preferred_language', 'user_timezone', 'notification_preferences'
        ]


class PasswordChangeSerializer(serializers.Serializer):
    """
    Enhanced password change serializer with security features
    """
    old_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(required=True, write_only=True, validators=[validate_password])
    new_password_confirm = serializers.CharField(required=True, write_only=True)

    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError("New passwords don't match")

        # Check if new password is same as old password
        if attrs['old_password'] == attrs['new_password']:
            raise serializers.ValidationError("New password must be different from current password")

        return attrs

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Old password is incorrect")
        return value

    def validate_new_password(self, value):
        user = self.context['request'].user

        # Additional validation for medical staff
        if hasattr(user, 'user_type') and user.user_type in ['doctor', 'nurse', 'admin']:
            from .password_validators import MedicalPasswordValidator
            validator = MedicalPasswordValidator()
            try:
                validator.validate(value, user)
            except ValidationError as e:
                raise serializers.ValidationError(e.messages)

        return value

    def save(self):
        user = self.context['request'].user

        user.set_password(self.validated_data['new_password'])
        user.save()

        # Log password change
        UserActivity.objects.create(
            user=user,
            action='update',
            resource_type='password',
            description='Password changed successfully',
            ip_address=self.context['request'].META.get('REMOTE_ADDR', ''),
        )

        return user


class PasswordResetRequestSerializer(serializers.Serializer):
    """
    Enhanced password reset request serializer with security features
    """
    email = serializers.EmailField(required=True)

    def validate_email(self, value):
        try:
            user = User.objects.get(email=value, is_active=True)

            # Check if account is locked
            if user.is_account_locked():
                raise serializers.ValidationError("Account is temporarily locked. Please try again later.")

        except User.DoesNotExist:
            # Don't reveal if email exists or not for security
            pass
        return value

    def save(self):
        email = self.validated_data['email']
        request = self.context['request']
        ip_address = request.META.get('REMOTE_ADDR', '127.0.0.1')
        user_agent = request.META.get('HTTP_USER_AGENT', '')

        try:
            user = User.objects.get(email=email, is_active=True)

            # Check rate limiting for password reset requests
            from django.core.cache import cache
            reset_key = f"password_reset_{ip_address}_{email}"
            recent_requests = cache.get(reset_key, 0)

            if recent_requests >= 3:  # Max 3 reset requests per hour
                raise serializers.ValidationError("Too many password reset requests. Please try again later.")

            # Generate secure reset token
            import secrets
            from datetime import timedelta

            token = secrets.token_urlsafe(32)
            expires_at = timezone.now() + timedelta(hours=1)  # Token expires in 1 hour

            # Invalidate any existing reset tokens for this user
            PasswordResetToken.objects.filter(user=user, is_used=False).update(is_used=True)

            # Create new reset token
            reset_token = PasswordResetToken.objects.create(
                user=user,
                token=token,
                expires_at=expires_at,
                ip_address=ip_address,
                user_agent=user_agent
            )

            # Update rate limiting
            cache.set(reset_key, recent_requests + 1, 3600)  # 1 hour

            # Log password reset request
            UserActivity.objects.create(
                user=user,
                action='update',
                resource_type='password_reset',
                description='Password reset requested',
                ip_address=ip_address,
            )

            return {
                'message': 'Password reset instructions sent to your email',
                'token': token,  # In production, this would be sent via email
                'expires_at': expires_at.isoformat()
            }

        except User.DoesNotExist:
            # Return success message even if user doesn't exist (security)
            # But still apply rate limiting
            from django.core.cache import cache
            reset_key = f"password_reset_{ip_address}_{email}"
            recent_requests = cache.get(reset_key, 0)
            cache.set(reset_key, recent_requests + 1, 3600)

            return {'message': 'Password reset instructions sent to your email'}


class PasswordResetConfirmSerializer(serializers.Serializer):
    """
    Enhanced password reset confirmation serializer with security validation
    """
    token = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, validators=[validate_password])
    new_password_confirm = serializers.CharField(required=True)

    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError("Passwords don't match")
        return attrs

    def validate_token(self, value):
        try:
            reset_token = PasswordResetToken.objects.get(token=value, is_used=False)
            if not reset_token.is_valid():
                raise serializers.ValidationError("Invalid or expired reset token")
            return value
        except PasswordResetToken.DoesNotExist:
            raise serializers.ValidationError("Invalid reset token")

    def validate_new_password(self, value):
        # Get the user from the token to validate password against user info
        token = self.initial_data.get('token')
        if token:
            try:
                reset_token = PasswordResetToken.objects.get(token=token, is_used=False)
                user = reset_token.user

                # Check password history
                if user.check_password_history(value):
                    raise serializers.ValidationError("You cannot reuse a recent password")

                # Additional validation for medical staff
                if hasattr(user, 'user_type') and user.user_type in ['doctor', 'nurse', 'admin']:
                    from .password_validators import MedicalPasswordValidator
                    validator = MedicalPasswordValidator()
                    try:
                        validator.validate(value, user)
                    except ValidationError as e:
                        raise serializers.ValidationError(e.messages)

            except PasswordResetToken.DoesNotExist:
                pass  # Token validation will be handled in validate_token

        return value

    def save(self):
        token = self.validated_data['token']
        new_password = self.validated_data['new_password']

        try:
            reset_token = PasswordResetToken.objects.get(token=token, is_used=False)
            user = reset_token.user

            # Set new password
            user.set_password(new_password)
            user.save()

            # Mark token as used
            reset_token.is_used = True
            reset_token.save()

            # Log password reset completion
            UserActivity.objects.create(
                user=user,
                action='update',
                resource_type='password_reset',
                description='Password reset completed',
                ip_address=self.context['request'].META.get('REMOTE_ADDR', '127.0.0.1'),
            )

            return user

        except PasswordResetToken.DoesNotExist:
            raise serializers.ValidationError("Invalid reset token")


class UserActivitySerializer(serializers.ModelSerializer):
    """
    User activity serializer for audit logs
    """
    user_email = serializers.CharField(source='user.email', read_only=True)
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    
    class Meta:
        model = UserActivity
        fields = [
            'id', 'user', 'user_email', 'user_name', 'action',
            'resource_type', 'resource_id', 'description',
            'ip_address', 'timestamp'
        ]
        read_only_fields = ['id', 'timestamp']
