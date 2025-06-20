"""
Lightweight Performance Monitoring Middleware
Optimized for minimal overhead while providing essential metrics
"""
import time
import logging
from django.utils.deprecation import MiddlewareMixin
from django.db import connection
from django.conf import settings

performance_logger = logging.getLogger('performance')


class LightweightPerformanceMiddleware(MiddlewareMixin):
    """
    Lightweight middleware for tracking API performance with minimal overhead
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        super().__init__(get_response)
        
        # Performance thresholds
        self.slow_request_threshold = getattr(settings, 'SLOW_REQUEST_THRESHOLD', 2.0)  # 2 seconds
        self.slow_query_threshold = getattr(settings, 'SLOW_QUERY_THRESHOLD', 1.0)     # 1 second
        
    def process_request(self, request):
        """
        Start timing the request
        """
        request._performance_start_time = time.time()
        request._performance_start_queries = len(connection.queries)
        return None
    
    def process_response(self, request, response):
        """
        Log performance metrics for slow requests only
        """
        # Skip if timing wasn't started
        if not hasattr(request, '_performance_start_time'):
            return response
        
        # Calculate metrics
        execution_time = time.time() - request._performance_start_time
        query_count = len(connection.queries) - request._performance_start_queries
        
        # Only log slow requests to minimize overhead
        if execution_time > self.slow_request_threshold:
            self._log_slow_request(request, response, execution_time, query_count)
        
        # Check for slow queries
        if hasattr(settings, 'DEBUG') and settings.DEBUG:
            self._check_slow_queries(request)
        
        return response
    
    def _log_slow_request(self, request, response, execution_time, query_count):
        """
        Log slow request details
        """
        performance_logger.warning(
            f"Slow request detected: {request.method} {request.path}",
            extra={
                'method': request.method,
                'path': request.path,
                'execution_time': round(execution_time, 3),
                'query_count': query_count,
                'status_code': response.status_code,
                'user_id': request.user.id if hasattr(request, 'user') and request.user.is_authenticated else None,
                'ip_address': self._get_client_ip(request),
            }
        )
    
    def _check_slow_queries(self, request):
        """
        Check for slow database queries (debug mode only)
        """
        if not connection.queries:
            return
        
        slow_queries = [
            query for query in connection.queries[-10:]  # Check last 10 queries
            if float(query.get('time', 0)) > self.slow_query_threshold
        ]
        
        if slow_queries:
            performance_logger.warning(
                f"Slow queries detected for {request.method} {request.path}",
                extra={
                    'path': request.path,
                    'slow_query_count': len(slow_queries),
                    'slowest_query_time': max(float(q.get('time', 0)) for q in slow_queries),
                }
            )
    
    def _get_client_ip(self, request):
        """
        Get client IP address
        """
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '')


class RequestSizeMiddleware(MiddlewareMixin):
    """
    Monitor request/response sizes for optimization
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        super().__init__(get_response)
        
        # Size thresholds (in bytes)
        self.large_request_threshold = getattr(settings, 'LARGE_REQUEST_THRESHOLD', 1024 * 1024)  # 1MB
        self.large_response_threshold = getattr(settings, 'LARGE_RESPONSE_THRESHOLD', 5 * 1024 * 1024)  # 5MB
    
    def process_request(self, request):
        """
        Check request size
        """
        content_length = request.META.get('CONTENT_LENGTH')
        if content_length:
            try:
                size = int(content_length)
                if size > self.large_request_threshold:
                    performance_logger.info(
                        f"Large request: {request.method} {request.path}",
                        extra={
                            'path': request.path,
                            'request_size': size,
                            'size_mb': round(size / (1024 * 1024), 2),
                        }
                    )
            except (ValueError, TypeError):
                pass
        
        return None
    
    def process_response(self, request, response):
        """
        Check response size
        """
        if hasattr(response, 'content'):
            size = len(response.content)
            if size > self.large_response_threshold:
                performance_logger.info(
                    f"Large response: {request.method} {request.path}",
                    extra={
                        'path': request.path,
                        'response_size': size,
                        'size_mb': round(size / (1024 * 1024), 2),
                        'status_code': response.status_code,
                    }
                )
        
        return response


class CacheHitRateMiddleware(MiddlewareMixin):
    """
    Monitor cache hit rates for optimization
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        super().__init__(get_response)
    
    def process_response(self, request, response):
        """
        Log cache hit/miss information
        """
        # Check if response was served from cache
        cache_hit = getattr(response, '_cache_hit', False)
        
        if hasattr(request, 'path') and request.path.startswith('/api/'):
            cache_status = 'HIT' if cache_hit else 'MISS'
            
            # Only log cache misses for frequently accessed endpoints
            if not cache_hit and self._is_cacheable_endpoint(request.path):
                performance_logger.info(
                    f"Cache {cache_status}: {request.method} {request.path}",
                    extra={
                        'path': request.path,
                        'cache_status': cache_status,
                        'method': request.method,
                    }
                )
        
        return response
    
    def _is_cacheable_endpoint(self, path):
        """
        Check if endpoint should be cached
        """
        cacheable_patterns = [
            '/api/patients/',
            '/api/doctors/',
            '/api/appointments/',
            '/api/medical_records/',
            '/api/billing/',
        ]
        
        return any(path.startswith(pattern) for pattern in cacheable_patterns)


# Performance settings
PERFORMANCE_MIDDLEWARE_SETTINGS = {
    'SLOW_REQUEST_THRESHOLD': 2.0,      # Log requests slower than 2 seconds
    'SLOW_QUERY_THRESHOLD': 1.0,        # Log queries slower than 1 second
    'LARGE_REQUEST_THRESHOLD': 1048576,  # Log requests larger than 1MB
    'LARGE_RESPONSE_THRESHOLD': 5242880, # Log responses larger than 5MB
}
