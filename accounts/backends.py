from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone
from django.core.cache import cache
from django.conf import settings
import logging

User = get_user_model()
logger = logging.getLogger(__name__)


class EmailOrUsernameModelBackend(ModelBackend):
    """
    Enhanced authentication backend that allows users to login with either
    their username or email address, with additional security features.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None:
            username = kwargs.get(User.USERNAME_FIELD)

        if username is None or password is None:
            return None

        # Check for rate limiting
        if self._is_rate_limited(request, username):
            logger.warning(f"Rate limited login attempt for: {username}")
            return None

        try:
            # Try to find user by email or username
            user = User.objects.get(
                Q(username__iexact=username) | Q(email__iexact=username)
            )
        except User.DoesNotExist:
            # Run the default password hasher once to reduce the timing
            # difference between an existing and a nonexistent user
            User().set_password(password)
            self._record_failed_attempt(request, username)
            return None

        # Check if user account is locked
        if self._is_account_locked(user):
            logger.warning(f"Login attempt on locked account: {user.username}")
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            # Clear failed attempts on successful login
            self._clear_failed_attempts(request, username)
            # Update last login
            user.last_login = timezone.now()
            user.save(update_fields=['last_login'])
            logger.info(f"Successful login for user: {user.username}")
            return user
        else:
            # Record failed attempt
            self._record_failed_attempt(request, username)
            logger.warning(f"Failed login attempt for user: {username}")
            return None
    
    def get_user(self, user_id):
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
        
        return user if self.user_can_authenticate(user) else None

    def _is_rate_limited(self, request, username):
        """Check if the IP or username is rate limited"""
        if not request:
            return False

        ip_address = self._get_client_ip(request)

        # Check IP-based rate limiting
        ip_key = f"login_attempts_ip_{ip_address}"
        ip_attempts = cache.get(ip_key, 0)

        # Check username-based rate limiting
        username_key = f"login_attempts_user_{username}"
        username_attempts = cache.get(username_key, 0)

        # Rate limit: 5 attempts per IP per 15 minutes, 3 attempts per username per 15 minutes
        return ip_attempts >= 5 or username_attempts >= 3

    def _record_failed_attempt(self, request, username):
        """Record a failed login attempt"""
        if not request:
            return

        ip_address = self._get_client_ip(request)

        # Record IP-based attempt
        ip_key = f"login_attempts_ip_{ip_address}"
        ip_attempts = cache.get(ip_key, 0) + 1
        cache.set(ip_key, ip_attempts, 900)  # 15 minutes

        # Record username-based attempt
        username_key = f"login_attempts_user_{username}"
        username_attempts = cache.get(username_key, 0) + 1
        cache.set(username_key, username_attempts, 900)  # 15 minutes

    def _clear_failed_attempts(self, request, username):
        """Clear failed login attempts on successful login"""
        if not request:
            return

        ip_address = self._get_client_ip(request)

        # Clear IP-based attempts
        ip_key = f"login_attempts_ip_{ip_address}"
        cache.delete(ip_key)

        # Clear username-based attempts
        username_key = f"login_attempts_user_{username}"
        cache.delete(username_key)

    def _is_account_locked(self, user):
        """Check if user account is locked"""
        # Check if user is active
        if not user.is_active:
            return True

        # Check for account lockout (could be extended with more sophisticated logic)
        lockout_key = f"account_locked_{user.username}"
        return cache.get(lockout_key, False)

    def _get_client_ip(self, request):
        """Get client IP address from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR', '127.0.0.1')
        return ip


class ActiveUserModelBackend(ModelBackend):
    """
    Custom authentication backend that only allows active users to login.
    """

    def user_can_authenticate(self, user):
        """
        Reject users with is_active=False. Custom user models that don't have
        an is_active field are allowed.
        """
        is_active = getattr(user, 'is_active', None)
        return is_active or is_active is None


class RoleBasedAuthenticationBackend(ModelBackend):
    """
    Authentication backend that validates user roles and permissions.
    """

    def authenticate(self, request, username=None, password=None, required_role=None, **kwargs):
        # First authenticate with standard backend
        user = super().authenticate(request, username, password, **kwargs)

        if user and required_role:
            # Check if user has the required role
            if hasattr(user, 'user_type') and user.user_type == required_role:
                return user
            else:
                logger.warning(f"User {user.username} attempted access without required role: {required_role}")
                return None

        return user

    def user_can_authenticate(self, user):
        """
        Enhanced user authentication check with role validation.
        """
        if not super().user_can_authenticate(user):
            return False

        # Additional role-based checks can be added here
        return True


class SecureAuthenticationBackend(EmailOrUsernameModelBackend):
    """
    High-security authentication backend with additional security measures.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        # Check for suspicious activity
        if self._is_suspicious_activity(request, username):
            logger.warning(f"Suspicious activity detected for: {username}")
            return None

        # Call parent authentication
        user = super().authenticate(request, username, password, **kwargs)

        if user:
            # Additional security checks for sensitive roles
            if self._requires_additional_verification(user):
                # Could implement 2FA, device verification, etc.
                logger.info(f"Additional verification required for: {user.username}")

        return user

    def _is_suspicious_activity(self, request, username):
        """Detect suspicious login patterns"""
        if not request:
            return False

        # Check for rapid login attempts from different IPs
        ip_address = self._get_client_ip(request)
        recent_ips_key = f"recent_ips_{username}"
        recent_ips = cache.get(recent_ips_key, set())

        if isinstance(recent_ips, set) and len(recent_ips) > 3:
            return True

        # Add current IP to recent IPs
        if isinstance(recent_ips, set):
            recent_ips.add(ip_address)
        else:
            recent_ips = {ip_address}

        cache.set(recent_ips_key, recent_ips, 3600)  # 1 hour
        return False

    def _requires_additional_verification(self, user):
        """Check if user requires additional verification"""
        # Require additional verification for admin and doctor roles
        sensitive_roles = ['admin', 'doctor']
        return hasattr(user, 'user_type') and user.user_type in sensitive_roles
