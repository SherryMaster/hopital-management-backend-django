import json
import logging
import re
import hashlib
import time
from datetime import datetime, timedelta
from django.utils.deprecation import MiddlewareMixin
from django.utils import timezone
from django.http import JsonResponse
from django.core.cache import cache
from django.conf import settings
from django.core.exceptions import SuspiciousOperation
from .models import UserActivity

logger = logging.getLogger(__name__)
security_logger = logging.getLogger('security')


class UserActivityMiddleware(MiddlewareMixin):
    """
    Middleware to log user activities for audit trail.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        super().__init__(get_response)
    
    def process_request(self, request):
        """
        Process the request and log user activity.
        """
        # Skip logging for certain paths
        skip_paths = [
            '/admin/jsi18n/',
            '/api/schema/',
            '/api/docs/',
            '/api/redoc/',
            '/static/',
            '/media/',
            '/favicon.ico',
        ]
        
        if any(request.path.startswith(path) for path in skip_paths):
            return None
        
        # Skip logging for non-authenticated users on certain endpoints
        if not request.user.is_authenticated and request.path.startswith('/api/accounts/auth/'):
            return None
        
        return None
    
    def process_response(self, request, response):
        """
        Process the response and log successful activities.
        """
        # Only log for authenticated users
        if not request.user.is_authenticated:
            return response
        
        # Only log successful requests (2xx status codes)
        if not (200 <= response.status_code < 300):
            return response
        
        # Skip logging for certain paths
        skip_paths = [
            '/admin/jsi18n/',
            '/api/schema/',
            '/api/docs/',
            '/api/redoc/',
            '/static/',
            '/media/',
            '/favicon.ico',
        ]
        
        if any(request.path.startswith(path) for path in skip_paths):
            return response
        
        try:
            self._log_activity(request, response)
        except Exception as e:
            logger.error(f"Error logging user activity: {e}")
        
        return response
    
    def _log_activity(self, request, response):
        """
        Log the user activity.
        """
        # Determine action type based on HTTP method
        action_mapping = {
            'GET': 'view',
            'POST': 'create',
            'PUT': 'update',
            'PATCH': 'update',
            'DELETE': 'delete',
        }
        
        action = action_mapping.get(request.method, 'unknown')
        
        # Determine resource type from URL path
        resource_type = self._extract_resource_type(request.path)
        
        # Extract resource ID if available
        resource_id = self._extract_resource_id(request.path)
        
        # Create description
        description = f"{request.method} {request.path}"
        if hasattr(request, 'data') and request.data:
            # Don't log sensitive data
            safe_data = self._sanitize_data(request.data)
            if safe_data:
                description += f" - Data: {json.dumps(safe_data)[:200]}"
        
        # Get client IP address
        ip_address = self._get_client_ip(request)
        
        # Create activity log
        UserActivity.objects.create(
            user=request.user,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            description=description,
            ip_address=ip_address,
            timestamp=timezone.now()
        )
    
    def _extract_resource_type(self, path):
        """
        Extract resource type from URL path.
        """
        # Remove leading/trailing slashes and split
        parts = path.strip('/').split('/')
        
        if len(parts) >= 2 and parts[0] == 'api':
            if len(parts) >= 3:
                return parts[1]  # e.g., 'accounts', 'patients', 'appointments'
        
        return 'unknown'
    
    def _extract_resource_id(self, path):
        """
        Extract resource ID from URL path if available.
        """
        # Look for UUID patterns in the path
        import re
        uuid_pattern = r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
        matches = re.findall(uuid_pattern, path, re.IGNORECASE)
        
        if matches:
            return matches[0]
        
        # Look for numeric IDs
        numeric_pattern = r'/(\d+)/'
        matches = re.findall(numeric_pattern, path)
        
        if matches:
            return matches[-1]  # Return the last numeric ID found
        
        return ''
    
    def _sanitize_data(self, data):
        """
        Remove sensitive information from request data.
        """
        if not isinstance(data, dict):
            return None
        
        # List of sensitive fields to exclude
        sensitive_fields = [
            'password', 'token', 'secret', 'key', 'authorization',
            'social_security_number', 'ssn', 'credit_card', 'cvv'
        ]
        
        sanitized = {}
        for key, value in data.items():
            if any(sensitive in key.lower() for sensitive in sensitive_fields):
                sanitized[key] = '[REDACTED]'
            elif isinstance(value, (str, int, float, bool)):
                sanitized[key] = value
            elif isinstance(value, list) and len(value) < 10:  # Limit array size
                sanitized[key] = value
        
        return sanitized
    
    def _get_client_ip(self, request):
        """
        Get the client's IP address from the request.
        """
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR', '127.0.0.1')
        return ip


class APIAuthenticationMiddleware(MiddlewareMixin):
    """
    Comprehensive API Authentication Middleware with proper error handling.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        super().__init__(get_response)

    def process_request(self, request):
        """
        Process API requests and handle authentication.
        """
        # Only process API requests
        if not request.path.startswith('/api/'):
            return None

        # Skip authentication for public endpoints
        public_endpoints = [
            '/api/schema/',
            '/api/docs/',
            '/api/redoc/',
            '/api/accounts/auth/login/',
            '/api/accounts/auth/refresh/',
            '/api/accounts/register/',
            '/api/accounts/password/reset/',
            '/api/accounts/password/reset/confirm/',
            '/api/patients/register/',
        ]

        if any(request.path.startswith(endpoint) for endpoint in public_endpoints):
            return None

        # Check for JWT token in Authorization header
        auth_header = request.META.get('HTTP_AUTHORIZATION')
        if not auth_header:
            return self._create_error_response(
                'Authentication credentials were not provided.',
                status_code=401
            )

        # Validate JWT token format
        if not auth_header.startswith('Bearer '):
            return self._create_error_response(
                'Invalid authentication header format. Use "Bearer <token>".',
                status_code=401
            )

        token = auth_header.split(' ')[1]

        # Validate token using JWT
        try:
            from rest_framework_simplejwt.tokens import AccessToken
            from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

            # Validate the token
            access_token = AccessToken(token)
            user_id = access_token['user_id']

            # Get user from database
            from .models import User
            try:
                user = User.objects.get(id=user_id, is_active=True)
                request.user = user
            except User.DoesNotExist:
                return self._create_error_response(
                    'User not found or inactive.',
                    status_code=401
                )

        except (InvalidToken, TokenError) as e:
            return self._create_error_response(
                f'Invalid or expired token: {str(e)}',
                status_code=401
            )
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return self._create_error_response(
                'Authentication failed.',
                status_code=401
            )

        return None

    def _create_error_response(self, message, status_code=401):
        """Create standardized error response"""
        from django.http import JsonResponse
        return JsonResponse(
            {
                'error': message,
                'status_code': status_code,
                'timestamp': timezone.now().isoformat()
            },
            status=status_code
        )


class RoleBasedAccessMiddleware(MiddlewareMixin):
    """
    Enhanced Role-Based Access Control Middleware.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        super().__init__(get_response)

    def process_request(self, request):
        """
        Process the request and check role-based access.
        """
        # Only process authenticated API requests
        if not request.path.startswith('/api/') or not hasattr(request, 'user'):
            return None

        # Skip for public endpoints
        public_endpoints = [
            '/api/schema/',
            '/api/docs/',
            '/api/redoc/',
            '/api/accounts/auth/',
            '/api/accounts/register/',
        ]

        if any(request.path.startswith(endpoint) for endpoint in public_endpoints):
            return None

        # Check if user is authenticated
        if not request.user.is_authenticated:
            return None  # Let APIAuthenticationMiddleware handle this

        # Role-based access control
        access_granted = self._check_role_based_access(request)

        if not access_granted:
            return self._create_error_response(
                'Insufficient permissions for this resource.',
                status_code=403
            )

        return None

    def _check_role_based_access(self, request):
        """
        Check if user has access based on their role and the requested resource.
        """
        user = request.user
        path = request.path
        method = request.method

        # Admin users have access to everything
        if user.user_type == 'admin' or user.is_superuser:
            return True

        # Define role-based access rules
        access_rules = {
            'doctor': {
                'allowed_paths': [
                    '/api/accounts/',
                    '/api/patients/',
                    '/api/appointments/',
                    '/api/medical_records/',
                    '/api/doctors/',
                ],
                'restricted_methods': {
                    '/api/accounts/roles/': ['POST', 'PUT', 'DELETE'],
                    '/api/billing/': ['POST', 'PUT', 'DELETE'],
                }
            },
            'nurse': {
                'allowed_paths': [
                    '/api/accounts/profile/',
                    '/api/patients/',
                    '/api/appointments/',
                    '/api/medical_records/',
                ],
                'restricted_methods': {
                    '/api/patients/': ['DELETE'],
                    '/api/medical_records/': ['DELETE'],
                }
            },
            'receptionist': {
                'allowed_paths': [
                    '/api/accounts/profile/',
                    '/api/patients/',
                    '/api/appointments/',
                    '/api/billing/',
                ],
                'restricted_methods': {
                    '/api/medical_records/': ['GET', 'POST', 'PUT', 'DELETE'],
                }
            },
            'patient': {
                'allowed_paths': [
                    '/api/accounts/profile/',
                    '/api/appointments/',
                ],
                'restricted_methods': {
                    '/api/appointments/': ['DELETE'],  # Patients can't delete appointments
                }
            },
            'lab_technician': {
                'allowed_paths': [
                    '/api/accounts/profile/',
                    '/api/medical_records/',
                    '/api/patients/',
                ],
                'restricted_methods': {
                    '/api/patients/': ['POST', 'DELETE'],
                    '/api/appointments/': ['GET', 'POST', 'PUT', 'DELETE'],
                }
            },
            'pharmacist': {
                'allowed_paths': [
                    '/api/accounts/profile/',
                    '/api/medical_records/',
                    '/api/patients/',
                ],
                'restricted_methods': {
                    '/api/patients/': ['POST', 'PUT', 'DELETE'],
                    '/api/appointments/': ['GET', 'POST', 'PUT', 'DELETE'],
                }
            }
        }

        user_rules = access_rules.get(user.user_type, {})
        allowed_paths = user_rules.get('allowed_paths', [])
        restricted_methods = user_rules.get('restricted_methods', {})

        # Check if path is allowed
        path_allowed = any(path.startswith(allowed_path) for allowed_path in allowed_paths)

        if not path_allowed:
            return False

        # Check method restrictions
        for restricted_path, methods in restricted_methods.items():
            if path.startswith(restricted_path) and method in methods:
                return False

        return True

    def _create_error_response(self, message, status_code=403):
        """Create standardized error response"""
        from django.http import JsonResponse
        return JsonResponse(
            {
                'error': message,
                'status_code': status_code,
                'timestamp': timezone.now().isoformat()
            },
            status=status_code
        )


class APIErrorHandlingMiddleware(MiddlewareMixin):
    """
    Middleware to handle API errors and provide consistent error responses.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        super().__init__(get_response)

    def process_exception(self, request, exception):
        """
        Handle exceptions for API requests.
        """
        # Only handle API requests
        if not request.path.startswith('/api/'):
            return None

        from django.http import JsonResponse
        from django.core.exceptions import ValidationError, PermissionDenied
        from rest_framework.exceptions import AuthenticationFailed, NotAuthenticated

        # Log the exception
        logger.error(f"API Exception: {exception}", exc_info=True)

        # Handle different types of exceptions
        if isinstance(exception, ValidationError):
            return JsonResponse(
                {
                    'error': 'Validation Error',
                    'details': exception.messages if hasattr(exception, 'messages') else str(exception),
                    'status_code': 400,
                    'timestamp': timezone.now().isoformat()
                },
                status=400
            )

        elif isinstance(exception, PermissionDenied):
            return JsonResponse(
                {
                    'error': 'Permission Denied',
                    'details': str(exception),
                    'status_code': 403,
                    'timestamp': timezone.now().isoformat()
                },
                status=403
            )

        elif isinstance(exception, (AuthenticationFailed, NotAuthenticated)):
            return JsonResponse(
                {
                    'error': 'Authentication Failed',
                    'details': str(exception),
                    'status_code': 401,
                    'timestamp': timezone.now().isoformat()
                },
                status=401
            )

        elif isinstance(exception, Exception):
            # Generic exception handling for production
            return JsonResponse(
                {
                    'error': 'Internal Server Error',
                    'details': 'An unexpected error occurred. Please try again later.',
                    'status_code': 500,
                    'timestamp': timezone.now().isoformat()
                },
                status=500
            )

        return None


class APIRequestValidationMiddleware(MiddlewareMixin):
    """
    Middleware to validate API requests and enforce rate limiting.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        super().__init__(get_response)

    def process_request(self, request):
        """
        Validate API requests.
        """
        # Only process API requests
        if not request.path.startswith('/api/'):
            return None

        # Check content type for POST/PUT requests
        if request.method in ['POST', 'PUT', 'PATCH']:
            content_type = request.META.get('CONTENT_TYPE', '')

            # Skip validation for file uploads
            if 'multipart/form-data' in content_type:
                return None

            # Require JSON content type for data endpoints
            if not content_type.startswith('application/json'):
                return self._create_error_response(
                    'Content-Type must be application/json for data requests.',
                    status_code=400
                )

        # Rate limiting check
        if self._is_rate_limited(request):
            return self._create_error_response(
                'Rate limit exceeded. Please try again later.',
                status_code=429
            )

        return None

    def _is_rate_limited(self, request):
        """
        Check if request is rate limited.
        """
        from django.core.cache import cache

        ip_address = self._get_client_ip(request)

        # Different rate limits for different endpoints
        if request.path.startswith('/api/accounts/auth/login/'):
            # Login attempts: 5 per minute
            key = f"rate_limit_login_{ip_address}"
            limit = 5
            window = 60
        elif request.path.startswith('/api/accounts/auth/'):
            # Auth endpoints: 10 per minute
            key = f"rate_limit_auth_{ip_address}"
            limit = 10
            window = 60
        else:
            # General API: 100 per minute
            key = f"rate_limit_api_{ip_address}"
            limit = 100
            window = 60

        current_requests = cache.get(key, 0)

        if current_requests >= limit:
            return True

        # Increment counter
        cache.set(key, current_requests + 1, window)
        return False

    def _get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR', '127.0.0.1')
        return ip

    def _create_error_response(self, message, status_code=400):
        """Create standardized error response"""
        from django.http import JsonResponse
        return JsonResponse(
            {
                'error': message,
                'status_code': status_code,
                'timestamp': timezone.now().isoformat()
            },
            status=status_code
        )


class SecurityHeadersMiddleware(MiddlewareMixin):
    """
    Middleware to add security headers to all responses
    """

    def __init__(self, get_response):
        self.get_response = get_response
        super().__init__(get_response)

    def process_response(self, request, response):
        """
        Add security headers to response
        """
        # Content Security Policy
        csp_directives = [
            "default-src 'self'",
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net",
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
            "font-src 'self' https://fonts.gstatic.com",
            "img-src 'self' data: https:",
            "connect-src 'self'",
            "frame-ancestors 'none'",
            "base-uri 'self'",
            "form-action 'self'",
        ]
        response['Content-Security-Policy'] = '; '.join(csp_directives)

        # Security headers
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response['X-Frame-Options'] = 'DENY'

        # Permissions Policy
        permissions_policy = [
            'geolocation=()',
            'microphone=()',
            'camera=()',
            'payment=()',
            'usb=()',
            'magnetometer=()',
            'gyroscope=()',
            'speaker=()',
        ]
        response['Permissions-Policy'] = ', '.join(permissions_policy)

        # HSTS (only in production)
        if not settings.DEBUG:
            response['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains; preload'

        return response


class RateLimitingMiddleware(MiddlewareMixin):
    """
    Advanced rate limiting middleware with different limits for different endpoints
    """

    def __init__(self, get_response):
        self.get_response = get_response
        super().__init__(get_response)

    def process_request(self, request):
        """
        Check rate limits before processing request
        """
        # Skip rate limiting for certain paths
        skip_paths = [
            '/admin/',
            '/static/',
            '/media/',
            '/api/schema/',
            '/api/docs/',
            '/api/redoc/',
        ]

        if any(request.path.startswith(path) for path in skip_paths):
            return None

        # Get client identifier
        client_id = self._get_client_identifier(request)

        # Check rate limits
        if self._is_rate_limited(request, client_id):
            security_logger.warning(
                f"Rate limit exceeded for {client_id} on {request.path}",
                extra={
                    'client_id': client_id,
                    'path': request.path,
                    'method': request.method,
                    'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                }
            )

            return JsonResponse(
                {
                    'error': 'Rate limit exceeded',
                    'message': 'Too many requests. Please try again later.',
                    'status_code': 429,
                    'timestamp': timezone.now().isoformat()
                },
                status=429
            )

        return None

    def _get_client_identifier(self, request):
        """
        Get unique client identifier for rate limiting
        """
        # Use user ID if authenticated
        if hasattr(request, 'user') and request.user and request.user.is_authenticated:
            return f"user_{request.user.id}"

        # Use IP address for anonymous users
        ip_address = self._get_client_ip(request)
        return f"ip_{ip_address}"

    def _get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '127.0.0.1')
        return ip

    def _is_rate_limited(self, request, client_id):
        """
        Check if client has exceeded rate limits
        """
        try:
            # Define rate limits for different endpoint types
            rate_limits = {
                'login': {'limit': 5, 'window': 300},      # 5 attempts per 5 minutes
                'auth': {'limit': 20, 'window': 300},      # 20 requests per 5 minutes
                'api': {'limit': 100, 'window': 300},      # 100 requests per 5 minutes
                'upload': {'limit': 10, 'window': 300},    # 10 uploads per 5 minutes
                'password_reset': {'limit': 3, 'window': 3600},  # 3 resets per hour
            }

            # Determine endpoint type
            endpoint_type = self._get_endpoint_type(request.path)
            rate_config = rate_limits.get(endpoint_type, rate_limits['api'])

            # Create cache key
            cache_key = f"rate_limit_{endpoint_type}_{client_id}"

            # Get current request count
            current_count = cache.get(cache_key, 0)

            # Check if limit exceeded
            if current_count >= rate_config['limit']:
                return True

            # Increment counter
            cache.set(cache_key, current_count + 1, rate_config['window'])

            return False

        except Exception as e:
            # If cache is unavailable, allow the request but log the error
            logger.warning(f"Rate limiting cache error: {e}")
            return False

    def _get_endpoint_type(self, path):
        """
        Determine endpoint type for rate limiting
        """
        if '/auth/login/' in path:
            return 'login'
        elif '/auth/' in path:
            return 'auth'
        elif '/password/reset/' in path:
            return 'password_reset'
        elif '/upload/' in path or 'multipart/form-data' in path:
            return 'upload'
        else:
            return 'api'


class IPFilteringMiddleware(MiddlewareMixin):
    """
    IP filtering middleware for blocking/allowing specific IPs
    """

    def __init__(self, get_response):
        self.get_response = get_response
        super().__init__(get_response)

    def process_request(self, request):
        """
        Filter requests based on IP address
        """
        client_ip = self._get_client_ip(request)

        # Check IP blacklist
        if self._is_ip_blacklisted(client_ip):
            security_logger.warning(
                f"Blocked request from blacklisted IP: {client_ip}",
                extra={
                    'ip_address': client_ip,
                    'path': request.path,
                    'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                }
            )

            return JsonResponse(
                {
                    'error': 'Access Denied',
                    'message': 'Your IP address has been blocked.',
                    'status_code': 403,
                    'timestamp': timezone.now().isoformat()
                },
                status=403
            )

        # Check IP whitelist (if enabled)
        if hasattr(settings, 'IP_WHITELIST_ENABLED') and settings.IP_WHITELIST_ENABLED:
            if not self._is_ip_whitelisted(client_ip):
                security_logger.warning(
                    f"Blocked request from non-whitelisted IP: {client_ip}",
                    extra={
                        'ip_address': client_ip,
                        'path': request.path,
                        'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                    }
                )

                return JsonResponse(
                    {
                        'error': 'Access Denied',
                        'message': 'Your IP address is not authorized.',
                        'status_code': 403,
                        'timestamp': timezone.now().isoformat()
                    },
                    status=403
                )

        return None

    def _get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '127.0.0.1')
        return ip

    def _is_ip_blacklisted(self, ip):
        """
        Check if IP is in blacklist
        """
        # Get blacklist from cache or database
        blacklist_key = 'ip_blacklist'
        blacklist = cache.get(blacklist_key, set())

        # Check if IP is in blacklist
        return ip in blacklist

    def _is_ip_whitelisted(self, ip):
        """
        Check if IP is in whitelist
        """
        # Get whitelist from cache or database
        whitelist_key = 'ip_whitelist'
        whitelist = cache.get(whitelist_key, set())

        # Always allow localhost
        if ip in ['127.0.0.1', 'localhost', '::1']:
            return True

        # Check if IP is in whitelist
        return ip in whitelist


class SecurityAuditMiddleware(MiddlewareMixin):
    """
    Security audit middleware for logging security events
    """

    def __init__(self, get_response):
        self.get_response = get_response
        super().__init__(get_response)

    def process_request(self, request):
        """
        Log security-relevant requests
        """
        # Log authentication attempts
        if '/auth/login/' in request.path:
            self._log_login_attempt(request)

        # Log admin access attempts
        if request.path.startswith('/admin/'):
            self._log_admin_access(request)

        # Log sensitive API access
        sensitive_paths = [
            '/api/accounts/',
            '/api/medical_records/',
            '/api/billing/',
        ]

        if any(request.path.startswith(path) for path in sensitive_paths):
            self._log_sensitive_access(request)

        return None

    def process_response(self, request, response):
        """
        Log security-relevant responses
        """
        # Log failed authentication
        if '/auth/login/' in request.path and response.status_code == 401:
            self._log_failed_login(request, response)

        # Log permission denied
        if response.status_code == 403:
            self._log_permission_denied(request, response)

        # Log suspicious activity
        if response.status_code in [429, 400] and request.path.startswith('/api/'):
            self._log_suspicious_activity(request, response)

        return response

    def _log_login_attempt(self, request):
        """Log login attempt"""
        client_ip = self._get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')

        security_logger.info(
            f"Login attempt from {client_ip}",
            extra={
                'event_type': 'login_attempt',
                'ip_address': client_ip,
                'user_agent': user_agent,
                'timestamp': timezone.now().isoformat(),
                'path': request.path,
            }
        )

    def _log_admin_access(self, request):
        """Log admin access attempt"""
        client_ip = self._get_client_ip(request)
        user = getattr(request, 'user', None)

        security_logger.info(
            f"Admin access attempt from {client_ip}",
            extra={
                'event_type': 'admin_access',
                'ip_address': client_ip,
                'user_id': user.id if user and user.is_authenticated else None,
                'username': user.username if user and user.is_authenticated else None,
                'path': request.path,
                'timestamp': timezone.now().isoformat(),
            }
        )

    def _log_sensitive_access(self, request):
        """Log sensitive API access"""
        client_ip = self._get_client_ip(request)
        user = getattr(request, 'user', None)

        security_logger.info(
            f"Sensitive API access from {client_ip}",
            extra={
                'event_type': 'sensitive_access',
                'ip_address': client_ip,
                'user_id': user.id if user and user.is_authenticated else None,
                'path': request.path,
                'method': request.method,
                'timestamp': timezone.now().isoformat(),
            }
        )

    def _log_failed_login(self, request, response):
        """Log failed login attempt"""
        client_ip = self._get_client_ip(request)

        # Try to get username from request data
        username = None
        if hasattr(request, 'data') and isinstance(request.data, dict):
            username = request.data.get('username')

        security_logger.warning(
            f"Failed login attempt from {client_ip}",
            extra={
                'event_type': 'failed_login',
                'ip_address': client_ip,
                'username': username,
                'status_code': response.status_code,
                'timestamp': timezone.now().isoformat(),
            }
        )

        # Track failed attempts for potential blocking
        self._track_failed_attempts(client_ip, username)

    def _log_permission_denied(self, request, response):
        """Log permission denied events"""
        client_ip = self._get_client_ip(request)
        user = getattr(request, 'user', None)

        security_logger.warning(
            f"Permission denied for {client_ip}",
            extra={
                'event_type': 'permission_denied',
                'ip_address': client_ip,
                'user_id': user.id if user and user.is_authenticated else None,
                'path': request.path,
                'method': request.method,
                'status_code': response.status_code,
                'timestamp': timezone.now().isoformat(),
            }
        )

    def _log_suspicious_activity(self, request, response):
        """Log suspicious activity"""
        client_ip = self._get_client_ip(request)
        user = getattr(request, 'user', None)

        security_logger.warning(
            f"Suspicious activity from {client_ip}",
            extra={
                'event_type': 'suspicious_activity',
                'ip_address': client_ip,
                'user_id': user.id if user and user.is_authenticated else None,
                'path': request.path,
                'method': request.method,
                'status_code': response.status_code,
                'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                'timestamp': timezone.now().isoformat(),
            }
        )

    def _track_failed_attempts(self, ip_address, username):
        """Track failed login attempts for potential blocking"""
        # Track by IP
        ip_key = f"failed_attempts_ip_{ip_address}"
        ip_attempts = cache.get(ip_key, 0) + 1
        cache.set(ip_key, ip_attempts, 3600)  # 1 hour

        # Track by username if provided
        if username:
            user_key = f"failed_attempts_user_{username}"
            user_attempts = cache.get(user_key, 0) + 1
            cache.set(user_key, user_attempts, 3600)  # 1 hour

        # Auto-block if threshold exceeded
        threshold = getattr(settings, 'FAILED_LOGIN_THRESHOLD', 5)

        if ip_attempts >= threshold:
            self._auto_block_ip(ip_address)

        if username and user_attempts >= threshold:
            self._auto_lock_user(username)

    def _auto_block_ip(self, ip_address):
        """Automatically block IP after too many failed attempts"""
        # Add to blacklist
        blacklist_key = 'ip_blacklist'
        blacklist = cache.get(blacklist_key, set())
        blacklist.add(ip_address)
        cache.set(blacklist_key, blacklist, 86400)  # 24 hours

        security_logger.critical(
            f"Auto-blocked IP {ip_address} due to excessive failed login attempts",
            extra={
                'event_type': 'auto_ip_block',
                'ip_address': ip_address,
                'timestamp': timezone.now().isoformat(),
            }
        )

    def _auto_lock_user(self, username):
        """Automatically lock user account after too many failed attempts"""
        try:
            from .models import User
            user = User.objects.get(username=username)
            user.is_active = False
            user.save()

            security_logger.critical(
                f"Auto-locked user {username} due to excessive failed login attempts",
                extra={
                    'event_type': 'auto_user_lock',
                    'username': username,
                    'user_id': user.id,
                    'timestamp': timezone.now().isoformat(),
                }
            )
        except User.DoesNotExist:
            pass

    def _get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '127.0.0.1')
        return ip


class InputValidationMiddleware(MiddlewareMixin):
    """
    Middleware for comprehensive input validation and sanitization
    """

    def __init__(self, get_response):
        self.get_response = get_response
        super().__init__(get_response)

    def process_request(self, request):
        """
        Validate and sanitize all incoming request data
        """
        # Skip validation for certain paths
        skip_paths = [
            '/admin/',
            '/static/',
            '/media/',
            '/api/schema/',
            '/api/docs/',
            '/api/redoc/',
        ]

        if any(request.path.startswith(path) for path in skip_paths):
            return None

        try:
            # Validate and sanitize GET parameters
            if request.GET:
                self._validate_query_params(request)

            # Validate and sanitize POST data
            if request.method in ['POST', 'PUT', 'PATCH'] and hasattr(request, 'data'):
                self._validate_request_data(request)

            # Validate file uploads
            if request.FILES:
                self._validate_file_uploads(request)

        except Exception as e:
            security_logger.warning(
                f"Input validation failed for {request.path}",
                extra={
                    'ip_address': self._get_client_ip(request),
                    'path': request.path,
                    'method': request.method,
                    'validation_error': str(e),
                    'timestamp': timezone.now().isoformat(),
                }
            )

            return JsonResponse(
                {
                    'error': 'Invalid input data',
                    'message': 'The submitted data contains invalid or potentially dangerous content.',
                    'details': str(e),
                    'status_code': 400,
                    'timestamp': timezone.now().isoformat()
                },
                status=400
            )

        return None

    def _validate_query_params(self, request):
        """
        Validate URL query parameters
        """
        from hospital_backend.validators import SecurityValidator, InputSanitizer

        for key, value in request.GET.items():
            # Security validation
            SecurityValidator.validate_no_script_tags(value)
            SecurityValidator.validate_no_sql_injection(value)

            # Sanitize the value
            sanitized_value = InputSanitizer.sanitize_text(value)

            # Update the query parameter with sanitized value
            request.GET._mutable = True
            request.GET[key] = sanitized_value
            request.GET._mutable = False

    def _validate_request_data(self, request):
        """
        Validate request body data
        """
        from hospital_backend.validators import SecurityValidator, InputSanitizer

        if not hasattr(request, 'data') or not request.data:
            return

        # Validate each field
        for field, value in request.data.items():
            if value is None or value == '':
                continue

            str_value = str(value)

            # Basic security validation for all fields
            SecurityValidator.validate_no_script_tags(str_value)
            SecurityValidator.validate_no_sql_injection(str_value)

            # Sanitize the value
            if isinstance(value, str):
                if field.endswith('_html') or field in ['description', 'notes']:
                    sanitized_value = InputSanitizer.sanitize_html(value)
                else:
                    sanitized_value = InputSanitizer.sanitize_text(value)

                # Update the request data with sanitized value
                request.data[field] = sanitized_value

    def _validate_file_uploads(self, request):
        """
        Validate file uploads
        """
        from hospital_backend.validators import SecurityValidator
        from django.conf import settings

        allowed_extensions = getattr(settings, 'ALLOWED_FILE_EXTENSIONS', [
            '.pdf', '.doc', '.docx', '.txt', '.jpg', '.jpeg', '.png'
        ])
        max_file_size = getattr(settings, 'MAX_FILE_SIZE', 10 * 1024 * 1024)  # 10MB

        for field_name, uploaded_file in request.FILES.items():
            # Validate file extension
            SecurityValidator.validate_file_extension(
                uploaded_file.name,
                allowed_extensions
            )

            # Validate file size
            SecurityValidator.validate_file_size(
                uploaded_file.size,
                max_file_size
            )

            # Sanitize filename
            from hospital_backend.validators import InputSanitizer
            sanitized_name = InputSanitizer.sanitize_filename(uploaded_file.name)
            uploaded_file.name = sanitized_name

    def _get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '127.0.0.1')
        return ip
