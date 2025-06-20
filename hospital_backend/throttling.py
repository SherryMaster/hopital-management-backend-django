"""
Advanced Rate Limiting and Throttling for Hospital Management System
Implements comprehensive API protection and fair usage policies
"""
import time
import hashlib
from datetime import datetime, timedelta
from django.core.cache import cache
from django.conf import settings
from rest_framework.throttling import BaseThrottle
from rest_framework.exceptions import Throttled
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)
security_logger = logging.getLogger('security')


class HospitalBaseThrottle(BaseThrottle):
    """
    Base throttle class for hospital-specific rate limiting
    """
    
    def __init__(self):
        self.cache = cache
        self.timer = time.time
    
    def get_cache_key(self, request, view):
        """
        Generate cache key for rate limiting
        """
        raise NotImplementedError('Subclasses must implement get_cache_key')
    
    def get_rate_limit(self, request, view):
        """
        Get rate limit for the request
        """
        raise NotImplementedError('Subclasses must implement get_rate_limit')
    
    def allow_request(self, request, view):
        """
        Check if request should be allowed
        """
        cache_key = self.get_cache_key(request, view)
        rate_limit, window = self.get_rate_limit(request, view)
        
        if not cache_key or not rate_limit:
            return True
        
        # Get current request count
        current_requests = self.cache.get(cache_key, 0)
        
        # Check if limit exceeded
        if current_requests >= rate_limit:
            self._log_rate_limit_exceeded(request, view, cache_key, current_requests, rate_limit)
            return False
        
        # Increment counter
        self.cache.set(cache_key, current_requests + 1, window)
        
        return True
    
    def wait(self):
        """
        Return time to wait before next request
        """
        return 60  # Default 1 minute
    
    def _log_rate_limit_exceeded(self, request, view, cache_key, current_requests, rate_limit):
        """
        Log rate limit exceeded events
        """
        client_ip = self._get_client_ip(request)
        user_id = request.user.id if hasattr(request, 'user') and request.user.is_authenticated else None
        
        security_logger.warning(
            f"Rate limit exceeded for {client_ip}",
            extra={
                'event_type': 'rate_limit_exceeded',
                'ip_address': client_ip,
                'user_id': user_id,
                'path': request.path,
                'method': request.method,
                'cache_key': cache_key,
                'current_requests': current_requests,
                'rate_limit': rate_limit,
                'timestamp': timezone.now().isoformat(),
            }
        )
    
    def _get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '127.0.0.1')
        return ip


class UserRateThrottle(HospitalBaseThrottle):
    """
    Rate limiting based on authenticated user
    """
    
    def get_cache_key(self, request, view):
        """
        Generate cache key based on user ID
        """
        if not hasattr(request, 'user') or not request.user.is_authenticated:
            return None
        
        return f"throttle_user_{request.user.id}_{view.__class__.__name__}"
    
    def get_rate_limit(self, request, view):
        """
        Get rate limit based on user type and endpoint
        """
        if not hasattr(request, 'user') or not request.user.is_authenticated:
            return None, None
        
        user_type = getattr(request.user, 'user_type', 'patient')
        
        # Different limits for different user types
        rate_limits = {
            'admin': (1000, 3600),      # 1000 requests per hour
            'doctor': (500, 3600),      # 500 requests per hour
            'nurse': (300, 3600),       # 300 requests per hour
            'receptionist': (400, 3600), # 400 requests per hour
            'patient': (100, 3600),     # 100 requests per hour
            'lab_technician': (200, 3600), # 200 requests per hour
            'pharmacist': (150, 3600),  # 150 requests per hour
        }
        
        return rate_limits.get(user_type, (100, 3600))


class IPRateThrottle(HospitalBaseThrottle):
    """
    Rate limiting based on IP address
    """
    
    def get_cache_key(self, request, view):
        """
        Generate cache key based on IP address
        """
        client_ip = self._get_client_ip(request)
        return f"throttle_ip_{client_ip}_{view.__class__.__name__}"
    
    def get_rate_limit(self, request, view):
        """
        Get rate limit for IP-based throttling
        """
        # More restrictive for anonymous users
        if not hasattr(request, 'user') or not request.user or not request.user.is_authenticated:
            return 50, 3600  # 50 requests per hour for anonymous

        return 200, 3600  # 200 requests per hour for authenticated


class LoginRateThrottle(HospitalBaseThrottle):
    """
    Special rate limiting for login attempts
    """
    
    def get_cache_key(self, request, view):
        """
        Generate cache key for login attempts
        """
        client_ip = self._get_client_ip(request)
        return f"throttle_login_{client_ip}"
    
    def get_rate_limit(self, request, view):
        """
        Strict rate limiting for login attempts
        """
        return 5, 300  # 5 attempts per 5 minutes
    
    def allow_request(self, request, view):
        """
        Enhanced login throttling with progressive delays
        """
        cache_key = self.get_cache_key(request, view)
        
        # Get failed attempt count
        failed_attempts = self.cache.get(f"{cache_key}_failed", 0)
        
        # Progressive rate limiting based on failed attempts
        if failed_attempts >= 10:
            rate_limit, window = 1, 3600  # 1 attempt per hour after 10 failures
        elif failed_attempts >= 5:
            rate_limit, window = 2, 1800  # 2 attempts per 30 minutes after 5 failures
        else:
            rate_limit, window = 5, 300   # 5 attempts per 5 minutes normally
        
        # Check current attempts
        current_attempts = self.cache.get(cache_key, 0)
        
        if current_attempts >= rate_limit:
            self._log_rate_limit_exceeded(request, view, cache_key, current_attempts, rate_limit)
            return False
        
        # Increment counter
        self.cache.set(cache_key, current_attempts + 1, window)
        
        return True
    
    def record_failed_attempt(self, request):
        """
        Record a failed login attempt
        """
        cache_key = self.get_cache_key(request, None)
        failed_key = f"{cache_key}_failed"
        
        failed_attempts = self.cache.get(failed_key, 0) + 1
        self.cache.set(failed_key, failed_attempts, 86400)  # Store for 24 hours


class EndpointSpecificThrottle(HospitalBaseThrottle):
    """
    Endpoint-specific rate limiting
    """
    
    def get_cache_key(self, request, view):
        """
        Generate cache key based on endpoint and user/IP
        """
        identifier = self._get_identifier(request)
        endpoint = self._get_endpoint_category(request.path)
        return f"throttle_endpoint_{endpoint}_{identifier}"
    
    def _get_identifier(self, request):
        """
        Get user ID or IP as identifier
        """
        if hasattr(request, 'user') and request.user and request.user.is_authenticated:
            return f"user_{request.user.id}"
        else:
            return f"ip_{self._get_client_ip(request)}"
    
    def _get_endpoint_category(self, path):
        """
        Categorize endpoint for specific rate limiting
        """
        if '/auth/' in path:
            return 'auth'
        elif '/upload/' in path or '/files/' in path:
            return 'upload'
        elif '/search/' in path:
            return 'search'
        elif '/reports/' in path:
            return 'reports'
        elif '/billing/' in path:
            return 'billing'
        elif '/medical_records/' in path:
            return 'medical_records'
        else:
            return 'general'
    
    def get_rate_limit(self, request, view):
        """
        Get rate limit based on endpoint category
        """
        endpoint = self._get_endpoint_category(request.path)
        
        # Endpoint-specific rate limits
        limits = {
            'auth': (10, 300),          # 10 auth requests per 5 minutes
            'upload': (5, 3600),        # 5 uploads per hour
            'search': (100, 3600),      # 100 searches per hour
            'reports': (20, 3600),      # 20 report requests per hour
            'billing': (50, 3600),      # 50 billing requests per hour
            'medical_records': (200, 3600), # 200 medical record requests per hour
            'general': (300, 3600),     # 300 general requests per hour
        }
        
        return limits.get(endpoint, (100, 3600))


class BurstRateThrottle(HospitalBaseThrottle):
    """
    Burst rate limiting for short-term protection
    """
    
    def get_cache_key(self, request, view):
        """
        Generate cache key for burst protection
        """
        identifier = self._get_identifier(request)
        return f"throttle_burst_{identifier}"
    
    def _get_identifier(self, request):
        """
        Get user ID or IP as identifier
        """
        if hasattr(request, 'user') and request.user and request.user.is_authenticated:
            return f"user_{request.user.id}"
        else:
            return f"ip_{self._get_client_ip(request)}"
    
    def get_rate_limit(self, request, view):
        """
        Burst rate limiting - very short window, higher limit
        """
        return 20, 60  # 20 requests per minute


class AdaptiveRateThrottle(HospitalBaseThrottle):
    """
    Adaptive rate limiting based on system load and user behavior
    """
    
    def get_cache_key(self, request, view):
        """
        Generate cache key for adaptive throttling
        """
        identifier = self._get_identifier(request)
        return f"throttle_adaptive_{identifier}"
    
    def _get_identifier(self, request):
        """
        Get user ID or IP as identifier
        """
        if hasattr(request, 'user') and request.user and request.user.is_authenticated:
            return f"user_{request.user.id}"
        else:
            return f"ip_{self._get_client_ip(request)}"
    
    def get_rate_limit(self, request, view):
        """
        Adaptive rate limiting based on various factors
        """
        base_limit = 100
        window = 3600
        
        # Adjust based on user reputation
        if hasattr(request, 'user') and request.user.is_authenticated:
            user_reputation = self._get_user_reputation(request.user)
            base_limit = int(base_limit * user_reputation)
        
        # Adjust based on system load
        system_load = self._get_system_load()
        if system_load > 0.8:
            base_limit = int(base_limit * 0.5)  # Reduce by 50% under high load
        elif system_load > 0.6:
            base_limit = int(base_limit * 0.7)  # Reduce by 30% under medium load
        
        return max(base_limit, 10), window  # Minimum 10 requests
    
    def _get_user_reputation(self, user):
        """
        Calculate user reputation score (1.0 = normal, higher = better)
        """
        # Check for recent violations
        violations_key = f"user_violations_{user.id}"
        violations = self.cache.get(violations_key, 0)
        
        if violations >= 5:
            return 0.3  # Heavily restricted
        elif violations >= 3:
            return 0.5  # Moderately restricted
        elif violations >= 1:
            return 0.7  # Slightly restricted
        else:
            return 1.0  # Normal
    
    def _get_system_load(self):
        """
        Get current system load (0.0 to 1.0)
        """
        # Simple implementation - in production, use actual system metrics
        load_key = "system_load"
        return self.cache.get(load_key, 0.3)  # Default to 30% load


# Throttle configuration for different views
THROTTLE_CLASSES = {
    'default': [UserRateThrottle, IPRateThrottle, BurstRateThrottle],
    'login': [LoginRateThrottle, IPRateThrottle],
    'upload': [EndpointSpecificThrottle, UserRateThrottle],
    'search': [EndpointSpecificThrottle, BurstRateThrottle],
    'reports': [EndpointSpecificThrottle, UserRateThrottle],
    'adaptive': [AdaptiveRateThrottle, BurstRateThrottle],
}


def get_throttle_classes(view_name='default'):
    """
    Get appropriate throttle classes for a view
    """
    return THROTTLE_CLASSES.get(view_name, THROTTLE_CLASSES['default'])


def record_violation(user_or_ip, violation_type='rate_limit'):
    """
    Record a throttling violation for reputation tracking
    """
    if hasattr(user_or_ip, 'id'):
        # User object
        key = f"user_violations_{user_or_ip.id}"
    else:
        # IP address
        key = f"ip_violations_{user_or_ip}"
    
    violations = cache.get(key, 0) + 1
    cache.set(key, violations, 86400)  # Store for 24 hours
    
    security_logger.warning(
        f"Throttling violation recorded: {violation_type}",
        extra={
            'violation_type': violation_type,
            'identifier': str(user_or_ip),
            'violation_count': violations,
            'timestamp': timezone.now().isoformat(),
        }
    )
