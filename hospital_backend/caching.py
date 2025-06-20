"""
Comprehensive Caching Strategy for Hospital Management System
Implements Redis caching, session management, and API response caching
"""
import json
import hashlib
import pickle
from datetime import datetime, timedelta
from functools import wraps
from typing import Any, Optional, Dict, List

from django.core.cache import cache
from django.core.cache.backends.redis import RedisCache
from django.conf import settings
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import QuerySet
from django.core.serializers.json import DjangoJSONEncoder

import logging

logger = logging.getLogger(__name__)
cache_logger = logging.getLogger('cache')


class HospitalCacheManager:
    """
    Centralized cache management for hospital system
    """
    
    # Cache timeout configurations (in seconds)
    CACHE_TIMEOUTS = {
        # User and authentication
        'user_profile': 900,           # 15 minutes
        'user_permissions': 1800,      # 30 minutes
        'user_session': 3600,          # 1 hour
        
        # Patient data
        'patient_profile': 600,        # 10 minutes
        'patient_list': 300,           # 5 minutes
        'patient_medical_history': 1800, # 30 minutes
        'patient_appointments': 300,   # 5 minutes
        
        # Doctor data
        'doctor_profile': 1800,        # 30 minutes
        'doctor_list': 600,            # 10 minutes
        'doctor_availability': 300,    # 5 minutes
        'doctor_schedule': 600,        # 10 minutes
        
        # Appointments
        'appointment_details': 300,    # 5 minutes
        'appointment_list': 180,       # 3 minutes
        'appointment_today': 60,       # 1 minute
        'appointment_conflicts': 120,  # 2 minutes
        
        # Medical records
        'medical_record': 1800,        # 30 minutes
        'medical_history': 3600,       # 1 hour
        'prescription_list': 600,      # 10 minutes
        'lab_results': 1800,           # 30 minutes
        
        # Billing
        'invoice_details': 1800,       # 30 minutes
        'billing_summary': 3600,       # 1 hour
        'payment_history': 1800,       # 30 minutes
        'insurance_info': 7200,        # 2 hours
        
        # System data
        'department_list': 7200,       # 2 hours
        'service_catalog': 3600,       # 1 hour
        'system_settings': 7200,       # 2 hours
        'notification_templates': 3600, # 1 hour
        
        # API responses
        'api_response': 300,           # 5 minutes
        'search_results': 180,         # 3 minutes
        'report_data': 1800,           # 30 minutes
        'dashboard_data': 300,         # 5 minutes
    }
    
    # Cache key prefixes
    CACHE_PREFIXES = {
        'user': 'hospital:user',
        'patient': 'hospital:patient',
        'doctor': 'hospital:doctor',
        'appointment': 'hospital:appointment',
        'medical': 'hospital:medical',
        'billing': 'hospital:billing',
        'system': 'hospital:system',
        'api': 'hospital:api',
        'session': 'hospital:session',
    }
    
    @classmethod
    def get_cache_key(cls, category: str, key_type: str, identifier: str = None) -> str:
        """
        Generate standardized cache keys
        """
        prefix = cls.CACHE_PREFIXES.get(category, 'hospital:general')
        
        if identifier:
            return f"{prefix}:{key_type}:{identifier}"
        return f"{prefix}:{key_type}"
    
    @classmethod
    def get_timeout(cls, key_type: str) -> int:
        """
        Get cache timeout for specific key type
        """
        return cls.CACHE_TIMEOUTS.get(key_type, 300)  # Default 5 minutes
    
    @classmethod
    def set_cache(cls, category: str, key_type: str, data: Any, 
                  identifier: str = None, timeout: int = None) -> bool:
        """
        Set cache with standardized key and timeout
        """
        cache_key = cls.get_cache_key(category, key_type, identifier)
        
        if timeout is None:
            timeout = cls.get_timeout(key_type)
        
        try:
            # Serialize complex objects
            if isinstance(data, (QuerySet, list, dict)):
                serialized_data = cls._serialize_data(data)
            else:
                serialized_data = data
            
            cache.set(cache_key, serialized_data, timeout)
            
            cache_logger.info(
                f"Cache set: {cache_key}",
                extra={
                    'cache_key': cache_key,
                    'timeout': timeout,
                    'data_type': type(data).__name__,
                    'timestamp': timezone.now().isoformat(),
                }
            )
            
            return True
            
        except Exception as e:
            cache_logger.error(
                f"Cache set failed: {cache_key} - {str(e)}",
                extra={
                    'cache_key': cache_key,
                    'error': str(e),
                    'timestamp': timezone.now().isoformat(),
                }
            )
            return False
    
    @classmethod
    def get_cache(cls, category: str, key_type: str, identifier: str = None) -> Any:
        """
        Get cache with standardized key
        """
        cache_key = cls.get_cache_key(category, key_type, identifier)
        
        try:
            data = cache.get(cache_key)
            
            if data is not None:
                cache_logger.info(
                    f"Cache hit: {cache_key}",
                    extra={
                        'cache_key': cache_key,
                        'timestamp': timezone.now().isoformat(),
                    }
                )
            else:
                cache_logger.info(
                    f"Cache miss: {cache_key}",
                    extra={
                        'cache_key': cache_key,
                        'timestamp': timezone.now().isoformat(),
                    }
                )
            
            return data
            
        except Exception as e:
            cache_logger.error(
                f"Cache get failed: {cache_key} - {str(e)}",
                extra={
                    'cache_key': cache_key,
                    'error': str(e),
                    'timestamp': timezone.now().isoformat(),
                }
            )
            return None
    
    @classmethod
    def delete_cache(cls, category: str, key_type: str, identifier: str = None) -> bool:
        """
        Delete cache with standardized key
        """
        cache_key = cls.get_cache_key(category, key_type, identifier)
        
        try:
            cache.delete(cache_key)
            
            cache_logger.info(
                f"Cache deleted: {cache_key}",
                extra={
                    'cache_key': cache_key,
                    'timestamp': timezone.now().isoformat(),
                }
            )
            
            return True
            
        except Exception as e:
            cache_logger.error(
                f"Cache delete failed: {cache_key} - {str(e)}",
                extra={
                    'cache_key': cache_key,
                    'error': str(e),
                    'timestamp': timezone.now().isoformat(),
                }
            )
            return False
    
    @classmethod
    def invalidate_pattern(cls, pattern: str) -> int:
        """
        Invalidate cache keys matching a pattern
        """
        try:
            # For Redis backend, use pattern matching
            if hasattr(cache, '_cache') and hasattr(cache._cache, 'delete_pattern'):
                deleted_count = cache._cache.delete_pattern(pattern)
            else:
                # Fallback for other cache backends
                deleted_count = 0
                # This would require implementing pattern matching for other backends
            
            cache_logger.info(
                f"Cache pattern invalidated: {pattern} ({deleted_count} keys)",
                extra={
                    'pattern': pattern,
                    'deleted_count': deleted_count,
                    'timestamp': timezone.now().isoformat(),
                }
            )
            
            return deleted_count
            
        except Exception as e:
            cache_logger.error(
                f"Cache pattern invalidation failed: {pattern} - {str(e)}",
                extra={
                    'pattern': pattern,
                    'error': str(e),
                    'timestamp': timezone.now().isoformat(),
                }
            )
            return 0
    
    @classmethod
    def _serialize_data(cls, data: Any) -> str:
        """
        Serialize complex data for caching
        """
        if isinstance(data, QuerySet):
            # Convert QuerySet to list of dictionaries
            return json.dumps(list(data.values()), cls=DjangoJSONEncoder)
        elif isinstance(data, (list, dict)):
            return json.dumps(data, cls=DjangoJSONEncoder)
        else:
            return str(data)


class CacheDecorators:
    """
    Decorators for automatic caching
    """
    
    @staticmethod
    def cache_result(category: str, key_type: str, timeout: int = None, 
                    use_args: bool = True, use_kwargs: bool = False):
        """
        Decorator to cache function results
        """
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                # Generate cache key based on function arguments
                if use_args or use_kwargs:
                    key_parts = []
                    if use_args and args:
                        key_parts.extend([str(arg) for arg in args])
                    if use_kwargs and kwargs:
                        key_parts.extend([f"{k}:{v}" for k, v in sorted(kwargs.items())])
                    
                    identifier = hashlib.md5(
                        ":".join(key_parts).encode('utf-8')
                    ).hexdigest()[:16]
                else:
                    identifier = None
                
                # Try to get from cache
                cached_result = HospitalCacheManager.get_cache(category, key_type, identifier)
                if cached_result is not None:
                    return cached_result
                
                # Execute function and cache result
                result = func(*args, **kwargs)
                HospitalCacheManager.set_cache(category, key_type, result, identifier, timeout)
                
                return result
            
            return wrapper
        return decorator
    
    @staticmethod
    def cache_api_response(timeout: int = 300):
        """
        Decorator to cache API responses
        """
        def decorator(func):
            @wraps(func)
            def wrapper(request, *args, **kwargs):
                # Generate cache key from request
                cache_key_data = {
                    'path': request.path,
                    'method': request.method,
                    'user_id': request.user.id if hasattr(request, 'user') and request.user.is_authenticated else None,
                    'query_params': dict(request.GET),
                }
                
                cache_key_hash = hashlib.md5(
                    json.dumps(cache_key_data, sort_keys=True).encode('utf-8')
                ).hexdigest()[:16]
                
                # Try to get from cache
                cached_response = HospitalCacheManager.get_cache('api', 'response', cache_key_hash)
                if cached_response is not None:
                    return JsonResponse(json.loads(cached_response))
                
                # Execute view and cache response
                response = func(request, *args, **kwargs)
                
                # Only cache successful responses
                if hasattr(response, 'status_code') and response.status_code == 200:
                    if hasattr(response, 'content'):
                        HospitalCacheManager.set_cache(
                            'api', 'response', response.content.decode('utf-8'), 
                            cache_key_hash, timeout
                        )
                
                return response
            
            return wrapper
        return decorator


class SessionCacheManager:
    """
    Enhanced session management with caching
    """
    
    @staticmethod
    def set_user_session_data(user_id: int, session_data: Dict) -> bool:
        """
        Store user session data in cache
        """
        return HospitalCacheManager.set_cache(
            'session', 'user_data', session_data, str(user_id)
        )
    
    @staticmethod
    def get_user_session_data(user_id: int) -> Optional[Dict]:
        """
        Retrieve user session data from cache
        """
        return HospitalCacheManager.get_cache('session', 'user_data', str(user_id))
    
    @staticmethod
    def invalidate_user_session(user_id: int) -> bool:
        """
        Invalidate user session data
        """
        return HospitalCacheManager.delete_cache('session', 'user_data', str(user_id))
    
    @staticmethod
    def set_user_permissions(user_id: int, permissions: List[str]) -> bool:
        """
        Cache user permissions
        """
        return HospitalCacheManager.set_cache(
            'user', 'permissions', permissions, str(user_id)
        )
    
    @staticmethod
    def get_user_permissions(user_id: int) -> Optional[List[str]]:
        """
        Get cached user permissions
        """
        return HospitalCacheManager.get_cache('user', 'permissions', str(user_id))


class SmartCacheInvalidation:
    """
    Intelligent cache invalidation based on data changes
    """
    
    # Define cache invalidation rules
    INVALIDATION_RULES = {
        'User': {
            'patterns': ['hospital:user:*', 'hospital:session:*'],
            'related': ['patient', 'doctor', 'appointment']
        },
        'Patient': {
            'patterns': ['hospital:patient:*'],
            'related': ['appointment', 'medical', 'billing']
        },
        'Doctor': {
            'patterns': ['hospital:doctor:*'],
            'related': ['appointment', 'medical']
        },
        'Appointment': {
            'patterns': ['hospital:appointment:*'],
            'related': ['patient', 'doctor']
        },
        'MedicalRecord': {
            'patterns': ['hospital:medical:*'],
            'related': ['patient']
        },
        'Invoice': {
            'patterns': ['hospital:billing:*'],
            'related': ['patient']
        },
    }
    
    @classmethod
    def invalidate_for_model(cls, model_name: str, instance_id: int = None) -> int:
        """
        Invalidate cache for specific model changes
        """
        total_invalidated = 0
        
        if model_name in cls.INVALIDATION_RULES:
            rules = cls.INVALIDATION_RULES[model_name]
            
            # Invalidate direct patterns
            for pattern in rules['patterns']:
                if instance_id:
                    specific_pattern = f"{pattern}:{instance_id}"
                    total_invalidated += HospitalCacheManager.invalidate_pattern(specific_pattern)
                
                total_invalidated += HospitalCacheManager.invalidate_pattern(pattern)
            
            # Invalidate related caches
            for related_category in rules.get('related', []):
                if instance_id:
                    related_pattern = f"hospital:{related_category}:*:{instance_id}"
                    total_invalidated += HospitalCacheManager.invalidate_pattern(related_pattern)
        
        return total_invalidated
    
    @classmethod
    def invalidate_user_related_cache(cls, user_id: int) -> int:
        """
        Invalidate all cache related to a specific user
        """
        patterns = [
            f"hospital:user:*:{user_id}",
            f"hospital:session:*:{user_id}",
            f"hospital:patient:*:{user_id}",
            f"hospital:doctor:*:{user_id}",
            f"hospital:appointment:*:{user_id}",
        ]
        
        total_invalidated = 0
        for pattern in patterns:
            total_invalidated += HospitalCacheManager.invalidate_pattern(pattern)
        
        return total_invalidated


# Cache warming utilities
class CacheWarmer:
    """
    Utilities for warming up cache with frequently accessed data
    """
    
    @staticmethod
    def warm_user_cache(user_id: int):
        """
        Pre-load user-related cache
        """
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        try:
            user = User.objects.get(id=user_id)
            
            # Cache user profile
            user_data = {
                'id': user.id,
                'email': user.email,
                'user_type': user.user_type,
                'is_active': user.is_active,
            }
            HospitalCacheManager.set_cache('user', 'profile', user_data, str(user_id))
            
            # Cache user permissions
            permissions = list(user.get_all_permissions())
            SessionCacheManager.set_user_permissions(user_id, permissions)
            
            cache_logger.info(f"Cache warmed for user {user_id}")
            
        except User.DoesNotExist:
            cache_logger.warning(f"User {user_id} not found for cache warming")
    
    @staticmethod
    def warm_system_cache():
        """
        Pre-load system-wide cache
        """
        # Cache department list
        try:
            from infrastructure.models import Department
            departments = list(Department.objects.values('id', 'name', 'description'))
            HospitalCacheManager.set_cache('system', 'department_list', departments)
        except:
            pass
        
        # Cache other system data as needed
        cache_logger.info("System cache warmed")


# Cache statistics and monitoring
class CacheMonitor:
    """
    Monitor cache performance and statistics
    """
    
    @staticmethod
    def get_cache_stats() -> Dict:
        """
        Get cache performance statistics
        """
        stats = {
            'timestamp': timezone.now().isoformat(),
            'backend': type(cache).__name__,
        }
        
        try:
            # Redis-specific stats
            if hasattr(cache, '_cache') and hasattr(cache._cache, 'get_stats'):
                redis_stats = cache._cache.get_stats()
                stats.update(redis_stats)
            
            # General cache info
            stats['cache_backend'] = settings.CACHES.get('default', {}).get('BACKEND', 'Unknown')
            
        except Exception as e:
            stats['error'] = str(e)
        
        return stats
    
    @staticmethod
    def clear_all_cache() -> bool:
        """
        Clear all cache (use with caution)
        """
        try:
            cache.clear()
            cache_logger.warning("All cache cleared")
            return True
        except Exception as e:
            cache_logger.error(f"Failed to clear cache: {str(e)}")
            return False
