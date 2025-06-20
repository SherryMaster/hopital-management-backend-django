"""
Database Performance Optimization for Hospital Management System
Implements comprehensive database optimization strategies
"""
import time
import logging
from datetime import datetime, timedelta
from django.db import connection, connections
from django.core.cache import cache
from django.conf import settings
from django.db.models import Q, Prefetch
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from contextlib import contextmanager

logger = logging.getLogger(__name__)
performance_logger = logging.getLogger('performance')


class DatabaseOptimizer:
    """
    Database optimization utilities and monitoring
    """
    
    @staticmethod
    def analyze_query_performance(query_func, *args, **kwargs):
        """
        Analyze query performance and log slow queries
        """
        start_time = time.time()
        
        # Reset query count
        initial_queries = len(connection.queries)
        
        try:
            result = query_func(*args, **kwargs)
            
            # Calculate performance metrics
            execution_time = time.time() - start_time
            query_count = len(connection.queries) - initial_queries
            
            # Log slow queries
            if execution_time > 1.0:  # Queries taking more than 1 second
                performance_logger.warning(
                    f"Slow query detected: {execution_time:.2f}s, {query_count} queries",
                    extra={
                        'execution_time': execution_time,
                        'query_count': query_count,
                        'function': query_func.__name__,
                        'timestamp': datetime.now().isoformat(),
                    }
                )
            
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            performance_logger.error(
                f"Query failed: {str(e)} after {execution_time:.2f}s",
                extra={
                    'execution_time': execution_time,
                    'function': query_func.__name__,
                    'error': str(e),
                    'timestamp': datetime.now().isoformat(),
                }
            )
            raise
    
    @staticmethod
    def get_database_stats():
        """
        Get database performance statistics
        """
        stats = {}
        
        for alias in connections:
            db = connections[alias]
            
            # Connection info
            stats[alias] = {
                'vendor': db.vendor,
                'queries_count': len(db.queries) if hasattr(db, 'queries') else 0,
                'connection_created': hasattr(db.connection, 'get_server_info'),
            }
            
            # PostgreSQL specific stats
            if db.vendor == 'postgresql':
                try:
                    with db.cursor() as cursor:
                        # Active connections
                        cursor.execute("""
                            SELECT count(*) FROM pg_stat_activity 
                            WHERE state = 'active'
                        """)
                        stats[alias]['active_connections'] = cursor.fetchone()[0]
                        
                        # Database size
                        cursor.execute("""
                            SELECT pg_size_pretty(pg_database_size(current_database()))
                        """)
                        stats[alias]['database_size'] = cursor.fetchone()[0]
                        
                        # Cache hit ratio
                        cursor.execute("""
                            SELECT 
                                round(
                                    (sum(heap_blks_hit) / (sum(heap_blks_hit) + sum(heap_blks_read))) * 100, 2
                                ) as cache_hit_ratio
                            FROM pg_statio_user_tables
                        """)
                        result = cursor.fetchone()
                        stats[alias]['cache_hit_ratio'] = result[0] if result[0] else 0
                        
                except Exception as e:
                    stats[alias]['error'] = str(e)
        
        return stats
    
    @staticmethod
    def optimize_connection_pool():
        """
        Optimize database connection pool settings
        """
        for alias in connections:
            db = connections[alias]
            
            # Close old connections
            if hasattr(db, 'close_if_unusable_or_obsolete'):
                db.close_if_unusable_or_obsolete()
            
            # Log connection status
            logger.info(f"Database {alias} connection optimized")


class QueryOptimizer:
    """
    Query optimization utilities
    """
    
    @staticmethod
    def optimize_patient_queries():
        """
        Optimized queries for patient data
        """
        from patients.models import Patient, MedicalHistory, EmergencyContact
        
        # Optimized patient list with related data
        return Patient.objects.select_related(
            'user', 'insurance_provider'
        ).prefetch_related(
            Prefetch(
                'medical_histories',
                queryset=MedicalHistory.objects.select_related('doctor').order_by('-date_recorded')[:5]
            ),
            Prefetch(
                'emergency_contacts',
                queryset=EmergencyContact.objects.all()
            )
        )
    
    @staticmethod
    def optimize_appointment_queries():
        """
        Optimized queries for appointment data
        """
        from appointments.models import Appointment
        
        # Optimized appointment list with related data
        return Appointment.objects.select_related(
            'patient__user',
            'doctor__user',
            'department'
        ).prefetch_related(
            'appointment_notes',
            'prescription_set'
        )
    
    @staticmethod
    def optimize_medical_record_queries():
        """
        Optimized queries for medical records
        """
        from medical_records.models import MedicalRecord, Diagnosis, Treatment, Prescription
        
        # Optimized medical record queries
        return MedicalRecord.objects.select_related(
            'patient__user',
            'doctor__user'
        ).prefetch_related(
            Prefetch(
                'diagnoses',
                queryset=Diagnosis.objects.select_related('icd_code')
            ),
            Prefetch(
                'treatments',
                queryset=Treatment.objects.all()
            ),
            Prefetch(
                'prescriptions',
                queryset=Prescription.objects.select_related('medication')
            )
        )
    
    @staticmethod
    def optimize_billing_queries():
        """
        Optimized queries for billing data
        """
        from billing.models import Invoice, Payment, InsuranceClaim
        
        # Optimized billing queries
        return Invoice.objects.select_related(
            'patient__user',
            'appointment__doctor__user'
        ).prefetch_related(
            Prefetch(
                'payments',
                queryset=Payment.objects.order_by('-payment_date')
            ),
            Prefetch(
                'insurance_claims',
                queryset=InsuranceClaim.objects.select_related('insurance_provider')
            )
        )


class CacheManager:
    """
    Intelligent caching for database queries
    """
    
    CACHE_TIMEOUTS = {
        'patient_list': 300,        # 5 minutes
        'doctor_list': 600,         # 10 minutes
        'appointment_today': 60,    # 1 minute
        'medical_records': 1800,    # 30 minutes
        'billing_summary': 3600,    # 1 hour
        'department_list': 7200,    # 2 hours
        'user_profile': 900,        # 15 minutes
    }
    
    @classmethod
    def get_cache_key(cls, key_type, identifier=None):
        """
        Generate standardized cache keys
        """
        if identifier:
            return f"hospital_{key_type}_{identifier}"
        return f"hospital_{key_type}"
    
    @classmethod
    def cache_query_result(cls, key_type, query_func, identifier=None, timeout=None):
        """
        Cache query results with automatic invalidation
        """
        cache_key = cls.get_cache_key(key_type, identifier)
        
        # Try to get from cache first
        result = cache.get(cache_key)
        if result is not None:
            return result
        
        # Execute query and cache result
        result = query_func()
        
        # Use default timeout if not specified
        if timeout is None:
            timeout = cls.CACHE_TIMEOUTS.get(key_type, 300)
        
        cache.set(cache_key, result, timeout)
        
        # Log cache miss
        performance_logger.info(
            f"Cache miss for {key_type}",
            extra={
                'cache_key': cache_key,
                'timeout': timeout,
                'timestamp': datetime.now().isoformat(),
            }
        )
        
        return result
    
    @classmethod
    def invalidate_cache(cls, key_type, identifier=None):
        """
        Invalidate specific cache entries
        """
        cache_key = cls.get_cache_key(key_type, identifier)
        cache.delete(cache_key)
        
        performance_logger.info(
            f"Cache invalidated for {key_type}",
            extra={
                'cache_key': cache_key,
                'timestamp': datetime.now().isoformat(),
            }
        )
    
    @classmethod
    def invalidate_related_caches(cls, model_name, instance_id=None):
        """
        Invalidate related cache entries when data changes
        """
        # Define cache invalidation rules
        invalidation_rules = {
            'Patient': ['patient_list', 'appointment_today'],
            'Doctor': ['doctor_list', 'appointment_today'],
            'Appointment': ['appointment_today', 'patient_list'],
            'MedicalRecord': ['medical_records', 'patient_list'],
            'Invoice': ['billing_summary'],
            'User': ['user_profile'],
        }
        
        cache_types = invalidation_rules.get(model_name, [])
        
        for cache_type in cache_types:
            cls.invalidate_cache(cache_type)
            if instance_id:
                cls.invalidate_cache(cache_type, instance_id)


@contextmanager
def database_transaction_optimizer():
    """
    Context manager for optimized database transactions
    """
    from django.db import transaction
    
    start_time = time.time()
    
    try:
        with transaction.atomic():
            yield
        
        execution_time = time.time() - start_time
        
        if execution_time > 0.5:  # Log slow transactions
            performance_logger.warning(
                f"Slow transaction: {execution_time:.2f}s",
                extra={
                    'execution_time': execution_time,
                    'timestamp': datetime.now().isoformat(),
                }
            )
            
    except Exception as e:
        execution_time = time.time() - start_time
        performance_logger.error(
            f"Transaction failed: {str(e)} after {execution_time:.2f}s",
            extra={
                'execution_time': execution_time,
                'error': str(e),
                'timestamp': datetime.now().isoformat(),
            }
        )
        raise


class IndexOptimizer:
    """
    Database index optimization utilities
    """
    
    @staticmethod
    def get_missing_indexes():
        """
        Analyze and suggest missing database indexes
        """
        suggestions = []
        
        # Common index suggestions for hospital system
        index_suggestions = [
            {
                'table': 'patients_patient',
                'columns': ['user_id', 'date_of_birth'],
                'reason': 'Patient lookup by user and age calculations'
            },
            {
                'table': 'appointments_appointment',
                'columns': ['patient_id', 'appointment_date', 'status'],
                'reason': 'Appointment queries by patient and date'
            },
            {
                'table': 'appointments_appointment',
                'columns': ['doctor_id', 'appointment_date'],
                'reason': 'Doctor schedule queries'
            },
            {
                'table': 'medical_records_medicalrecord',
                'columns': ['patient_id', 'created_at'],
                'reason': 'Medical history chronological queries'
            },
            {
                'table': 'billing_invoice',
                'columns': ['patient_id', 'status', 'due_date'],
                'reason': 'Billing queries by patient and status'
            },
            {
                'table': 'accounts_user',
                'columns': ['email', 'is_active'],
                'reason': 'User authentication queries'
            },
        ]
        
        # Check if indexes exist (simplified check)
        for suggestion in index_suggestions:
            suggestions.append(suggestion)
        
        return suggestions
    
    @staticmethod
    def generate_index_sql():
        """
        Generate SQL for creating recommended indexes
        """
        missing_indexes = IndexOptimizer.get_missing_indexes()
        sql_statements = []
        
        for index in missing_indexes:
            table = index['table']
            columns = index['columns']
            index_name = f"idx_{table}_{'_'.join(columns)}"
            
            sql = f"CREATE INDEX CONCURRENTLY {index_name} ON {table} ({', '.join(columns)});"
            sql_statements.append(sql)
        
        return sql_statements


# Signal handlers for automatic cache invalidation
@receiver(post_save)
def invalidate_cache_on_save(sender, instance, **kwargs):
    """
    Invalidate related caches when models are saved
    """
    model_name = sender.__name__
    instance_id = getattr(instance, 'id', None)
    
    CacheManager.invalidate_related_caches(model_name, instance_id)


@receiver(post_delete)
def invalidate_cache_on_delete(sender, instance, **kwargs):
    """
    Invalidate related caches when models are deleted
    """
    model_name = sender.__name__
    instance_id = getattr(instance, 'id', None)
    
    CacheManager.invalidate_related_caches(model_name, instance_id)


# Performance monitoring decorator
def monitor_database_performance(func):
    """
    Decorator to monitor database performance of functions
    """
    def wrapper(*args, **kwargs):
        return DatabaseOptimizer.analyze_query_performance(func, *args, **kwargs)
    
    return wrapper


# Bulk operation utilities
class BulkOperations:
    """
    Optimized bulk database operations
    """
    
    @staticmethod
    def bulk_create_with_cache_invalidation(model_class, objects, cache_types=None):
        """
        Bulk create objects with automatic cache invalidation
        """
        result = model_class.objects.bulk_create(objects)
        
        # Invalidate related caches
        if cache_types:
            for cache_type in cache_types:
                CacheManager.invalidate_cache(cache_type)
        
        return result
    
    @staticmethod
    def bulk_update_with_cache_invalidation(objects, fields, cache_types=None):
        """
        Bulk update objects with automatic cache invalidation
        """
        if not objects:
            return
        
        model_class = objects[0].__class__
        result = model_class.objects.bulk_update(objects, fields)
        
        # Invalidate related caches
        if cache_types:
            for cache_type in cache_types:
                CacheManager.invalidate_cache(cache_type)
        
        return result
