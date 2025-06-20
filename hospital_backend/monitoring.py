"""
Comprehensive Monitoring and Logging for Hospital Management System
Implements logging, error tracking, performance monitoring, and alerting
"""
import os
import time
import psutil
import logging
import traceback
from datetime import datetime, timedelta
from functools import wraps
from typing import Dict, Any, Optional, List

from django.conf import settings
from django.core.cache import cache
from django.db import connection, connections
from django.utils import timezone
from django.http import JsonResponse
from django.core.mail import send_mail

logger = logging.getLogger(__name__)
monitoring_logger = logging.getLogger('monitoring')
performance_logger = logging.getLogger('performance')
security_logger = logging.getLogger('security')
error_logger = logging.getLogger('error')


class SystemMonitor:
    """
    System resource monitoring and health checks
    """
    
    @staticmethod
    def get_system_metrics() -> Dict[str, Any]:
        """
        Get comprehensive system metrics
        """
        try:
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            cpu_freq = psutil.cpu_freq()
            
            # Memory metrics
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()
            
            # Disk metrics
            disk = psutil.disk_usage('/')
            
            # Network metrics
            network = psutil.net_io_counters()
            
            # Process metrics
            process = psutil.Process()
            process_memory = process.memory_info()
            process_cpu = process.cpu_percent()
            
            metrics = {
                'timestamp': timezone.now().isoformat(),
                'cpu': {
                    'percent': cpu_percent,
                    'count': cpu_count,
                    'frequency': cpu_freq.current if cpu_freq else None,
                },
                'memory': {
                    'total': memory.total,
                    'available': memory.available,
                    'percent': memory.percent,
                    'used': memory.used,
                    'free': memory.free,
                },
                'swap': {
                    'total': swap.total,
                    'used': swap.used,
                    'free': swap.free,
                    'percent': swap.percent,
                },
                'disk': {
                    'total': disk.total,
                    'used': disk.used,
                    'free': disk.free,
                    'percent': (disk.used / disk.total) * 100,
                },
                'network': {
                    'bytes_sent': network.bytes_sent,
                    'bytes_recv': network.bytes_recv,
                    'packets_sent': network.packets_sent,
                    'packets_recv': network.packets_recv,
                },
                'process': {
                    'memory_rss': process_memory.rss,
                    'memory_vms': process_memory.vms,
                    'cpu_percent': process_cpu,
                    'pid': process.pid,
                    'threads': process.num_threads(),
                }
            }
            
            return metrics
            
        except Exception as e:
            error_logger.error(f"Failed to get system metrics: {str(e)}")
            return {'error': str(e), 'timestamp': timezone.now().isoformat()}
    
    @staticmethod
    def get_database_metrics() -> Dict[str, Any]:
        """
        Get database performance metrics
        """
        metrics = {}
        
        for alias in connections:
            try:
                db = connections[alias]
                
                with db.cursor() as cursor:
                    # PostgreSQL specific metrics
                    if db.vendor == 'postgresql':
                        # Active connections
                        cursor.execute("""
                            SELECT count(*) FROM pg_stat_activity 
                            WHERE state = 'active'
                        """)
                        active_connections = cursor.fetchone()[0]
                        
                        # Database size
                        cursor.execute("""
                            SELECT pg_size_pretty(pg_database_size(current_database()))
                        """)
                        db_size = cursor.fetchone()[0]
                        
                        # Cache hit ratio
                        cursor.execute("""
                            SELECT round(
                                (sum(heap_blks_hit) / (sum(heap_blks_hit) + sum(heap_blks_read))) * 100, 2
                            ) as cache_hit_ratio
                            FROM pg_statio_user_tables
                        """)
                        result = cursor.fetchone()
                        cache_hit_ratio = result[0] if result[0] else 0
                        
                        # Slow queries
                        cursor.execute("""
                            SELECT count(*) FROM pg_stat_statements 
                            WHERE mean_time > 1000
                        """)
                        slow_queries = cursor.fetchone()[0] if cursor.fetchone() else 0
                        
                        metrics[alias] = {
                            'vendor': db.vendor,
                            'active_connections': active_connections,
                            'database_size': db_size,
                            'cache_hit_ratio': cache_hit_ratio,
                            'slow_queries': slow_queries,
                        }
                    else:
                        # Generic database metrics
                        metrics[alias] = {
                            'vendor': db.vendor,
                            'queries_count': len(db.queries) if hasattr(db, 'queries') else 0,
                        }
                        
            except Exception as e:
                metrics[alias] = {'error': str(e)}
        
        return metrics
    
    @staticmethod
    def get_application_metrics() -> Dict[str, Any]:
        """
        Get application-specific metrics
        """
        try:
            # Cache metrics
            cache_stats = {}
            try:
                # Test cache connectivity
                cache.set('health_check', 'ok', 60)
                cache_working = cache.get('health_check') == 'ok'
                cache.delete('health_check')
                cache_stats['working'] = cache_working
            except Exception as e:
                cache_stats['error'] = str(e)
            
            # User metrics
            user_metrics = {}
            try:
                from django.contrib.auth import get_user_model
                User = get_user_model()
                
                user_metrics = {
                    'total_users': User.objects.count(),
                    'active_users': User.objects.filter(is_active=True).count(),
                    'recent_logins': User.objects.filter(
                        last_login__gte=timezone.now() - timedelta(hours=24)
                    ).count(),
                }
            except Exception as e:
                user_metrics['error'] = str(e)
            
            # Appointment metrics
            appointment_metrics = {}
            try:
                from appointments.models import Appointment
                
                today = timezone.now().date()
                appointment_metrics = {
                    'total_appointments': Appointment.objects.count(),
                    'today_appointments': Appointment.objects.filter(
                        appointment_date=today
                    ).count(),
                    'pending_appointments': Appointment.objects.filter(
                        status='scheduled'
                    ).count(),
                }
            except Exception as e:
                appointment_metrics['error'] = str(e)
            
            return {
                'timestamp': timezone.now().isoformat(),
                'cache': cache_stats,
                'users': user_metrics,
                'appointments': appointment_metrics,
            }
            
        except Exception as e:
            error_logger.error(f"Failed to get application metrics: {str(e)}")
            return {'error': str(e), 'timestamp': timezone.now().isoformat()}


class PerformanceMonitor:
    """
    Performance monitoring and profiling
    """
    
    @staticmethod
    def monitor_function_performance(func):
        """
        Decorator to monitor function performance
        """
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            start_queries = len(connection.queries)
            
            try:
                result = func(*args, **kwargs)
                
                execution_time = time.time() - start_time
                query_count = len(connection.queries) - start_queries
                
                # Log performance metrics
                performance_logger.info(
                    f"Function {func.__name__} executed",
                    extra={
                        'function': func.__name__,
                        'execution_time': execution_time,
                        'query_count': query_count,
                        'timestamp': timezone.now().isoformat(),
                    }
                )
                
                # Alert on slow functions
                if execution_time > 5.0:  # 5 seconds threshold
                    AlertManager.send_performance_alert(
                        f"Slow function detected: {func.__name__}",
                        f"Execution time: {execution_time:.2f}s, Queries: {query_count}"
                    )
                
                return result
                
            except Exception as e:
                execution_time = time.time() - start_time
                
                error_logger.error(
                    f"Function {func.__name__} failed",
                    extra={
                        'function': func.__name__,
                        'execution_time': execution_time,
                        'error': str(e),
                        'traceback': traceback.format_exc(),
                        'timestamp': timezone.now().isoformat(),
                    }
                )
                
                raise
        
        return wrapper
    
    @staticmethod
    def monitor_api_performance(view_func):
        """
        Decorator to monitor API endpoint performance
        """
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            start_time = time.time()
            start_queries = len(connection.queries)
            
            # Request info
            request_info = {
                'method': request.method,
                'path': request.path,
                'user_id': request.user.id if hasattr(request, 'user') and request.user.is_authenticated else None,
                'ip_address': request.META.get('REMOTE_ADDR', ''),
                'user_agent': request.META.get('HTTP_USER_AGENT', ''),
            }
            
            try:
                response = view_func(request, *args, **kwargs)
                
                execution_time = time.time() - start_time
                query_count = len(connection.queries) - start_queries
                status_code = getattr(response, 'status_code', 200)
                
                # Log API performance
                performance_logger.info(
                    f"API {request.method} {request.path}",
                    extra={
                        **request_info,
                        'execution_time': execution_time,
                        'query_count': query_count,
                        'status_code': status_code,
                        'timestamp': timezone.now().isoformat(),
                    }
                )
                
                # Alert on slow APIs
                if execution_time > 3.0:  # 3 seconds threshold
                    AlertManager.send_performance_alert(
                        f"Slow API detected: {request.method} {request.path}",
                        f"Execution time: {execution_time:.2f}s, Status: {status_code}"
                    )
                
                return response
                
            except Exception as e:
                execution_time = time.time() - start_time
                
                error_logger.error(
                    f"API {request.method} {request.path} failed",
                    extra={
                        **request_info,
                        'execution_time': execution_time,
                        'error': str(e),
                        'traceback': traceback.format_exc(),
                        'timestamp': timezone.now().isoformat(),
                    }
                )
                
                # Send error alert
                AlertManager.send_error_alert(
                    f"API Error: {request.method} {request.path}",
                    f"Error: {str(e)}\nUser: {request_info.get('user_id', 'Anonymous')}"
                )
                
                raise
        
        return wrapper


class HealthChecker:
    """
    System health checks and status monitoring
    """
    
    @staticmethod
    def check_database_health() -> Dict[str, Any]:
        """
        Check database connectivity and health
        """
        health_status = {}
        
        for alias in connections:
            try:
                db = connections[alias]
                
                with db.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    result = cursor.fetchone()
                    
                    if result[0] == 1:
                        health_status[alias] = {
                            'status': 'healthy',
                            'vendor': db.vendor,
                            'timestamp': timezone.now().isoformat(),
                        }
                    else:
                        health_status[alias] = {
                            'status': 'unhealthy',
                            'error': 'Unexpected query result',
                            'timestamp': timezone.now().isoformat(),
                        }
                        
            except Exception as e:
                health_status[alias] = {
                    'status': 'unhealthy',
                    'error': str(e),
                    'timestamp': timezone.now().isoformat(),
                }
        
        return health_status
    
    @staticmethod
    def check_cache_health() -> Dict[str, Any]:
        """
        Check cache connectivity and health
        """
        try:
            # Test cache operations
            test_key = 'health_check_cache'
            test_value = f"test_{int(time.time())}"
            
            # Set operation
            cache.set(test_key, test_value, 60)
            
            # Get operation
            retrieved_value = cache.get(test_key)
            
            # Delete operation
            cache.delete(test_key)
            
            if retrieved_value == test_value:
                return {
                    'status': 'healthy',
                    'operations': ['set', 'get', 'delete'],
                    'timestamp': timezone.now().isoformat(),
                }
            else:
                return {
                    'status': 'unhealthy',
                    'error': 'Cache value mismatch',
                    'timestamp': timezone.now().isoformat(),
                }
                
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': timezone.now().isoformat(),
            }
    
    @staticmethod
    def check_external_services() -> Dict[str, Any]:
        """
        Check external service connectivity
        """
        services_status = {}
        
        # Check email service
        try:
            # This is a basic check - in production, you might want to send a test email
            from django.core.mail import get_connection
            connection = get_connection()
            connection.open()
            connection.close()
            
            services_status['email'] = {
                'status': 'healthy',
                'timestamp': timezone.now().isoformat(),
            }
        except Exception as e:
            services_status['email'] = {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': timezone.now().isoformat(),
            }
        
        # Add other external service checks here (SMS, payment gateways, etc.)
        
        return services_status
    
    @staticmethod
    def get_overall_health() -> Dict[str, Any]:
        """
        Get overall system health status
        """
        database_health = HealthChecker.check_database_health()
        cache_health = HealthChecker.check_cache_health()
        external_services = HealthChecker.check_external_services()
        system_metrics = SystemMonitor.get_system_metrics()
        
        # Determine overall status
        all_healthy = True
        
        # Check database health
        for db_status in database_health.values():
            if db_status.get('status') != 'healthy':
                all_healthy = False
                break
        
        # Check cache health
        if cache_health.get('status') != 'healthy':
            all_healthy = False
        
        # Check external services
        for service_status in external_services.values():
            if service_status.get('status') != 'healthy':
                all_healthy = False
                break
        
        # Check system resources
        if 'error' not in system_metrics:
            cpu_percent = system_metrics.get('cpu', {}).get('percent', 0)
            memory_percent = system_metrics.get('memory', {}).get('percent', 0)
            disk_percent = system_metrics.get('disk', {}).get('percent', 0)
            
            if cpu_percent > 90 or memory_percent > 90 or disk_percent > 90:
                all_healthy = False
        
        return {
            'overall_status': 'healthy' if all_healthy else 'unhealthy',
            'timestamp': timezone.now().isoformat(),
            'components': {
                'database': database_health,
                'cache': cache_health,
                'external_services': external_services,
                'system_metrics': system_metrics,
            }
        }


class AlertManager:
    """
    Alert management and notification system
    """
    
    ALERT_THRESHOLDS = {
        'cpu_percent': 85,
        'memory_percent': 85,
        'disk_percent': 90,
        'response_time': 3.0,
        'error_rate': 5,  # errors per minute
    }
    
    @staticmethod
    def send_performance_alert(subject: str, message: str):
        """
        Send performance-related alerts
        """
        try:
            # Log the alert
            monitoring_logger.warning(
                f"Performance Alert: {subject}",
                extra={
                    'alert_type': 'performance',
                    'subject': subject,
                    'message': message,
                    'timestamp': timezone.now().isoformat(),
                }
            )
            
            # Send email alert (if configured)
            AlertManager._send_email_alert(f"[PERFORMANCE] {subject}", message)
            
            # Store alert in cache for dashboard
            AlertManager._store_alert('performance', subject, message)
            
        except Exception as e:
            error_logger.error(f"Failed to send performance alert: {str(e)}")
    
    @staticmethod
    def send_error_alert(subject: str, message: str):
        """
        Send error-related alerts
        """
        try:
            # Log the alert
            monitoring_logger.error(
                f"Error Alert: {subject}",
                extra={
                    'alert_type': 'error',
                    'subject': subject,
                    'message': message,
                    'timestamp': timezone.now().isoformat(),
                }
            )
            
            # Send email alert (if configured)
            AlertManager._send_email_alert(f"[ERROR] {subject}", message)
            
            # Store alert in cache for dashboard
            AlertManager._store_alert('error', subject, message)
            
        except Exception as e:
            error_logger.error(f"Failed to send error alert: {str(e)}")
    
    @staticmethod
    def send_security_alert(subject: str, message: str):
        """
        Send security-related alerts
        """
        try:
            # Log the alert
            security_logger.critical(
                f"Security Alert: {subject}",
                extra={
                    'alert_type': 'security',
                    'subject': subject,
                    'message': message,
                    'timestamp': timezone.now().isoformat(),
                }
            )
            
            # Send email alert (if configured)
            AlertManager._send_email_alert(f"[SECURITY] {subject}", message)
            
            # Store alert in cache for dashboard
            AlertManager._store_alert('security', subject, message)
            
        except Exception as e:
            error_logger.error(f"Failed to send security alert: {str(e)}")
    
    @staticmethod
    def _send_email_alert(subject: str, message: str):
        """
        Send email alert to administrators
        """
        try:
            admin_emails = getattr(settings, 'ADMIN_ALERT_EMAILS', [])
            if admin_emails:
                send_mail(
                    subject=subject,
                    message=message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=admin_emails,
                    fail_silently=False,
                )
        except Exception as e:
            error_logger.error(f"Failed to send email alert: {str(e)}")
    
    @staticmethod
    def _store_alert(alert_type: str, subject: str, message: str):
        """
        Store alert in cache for dashboard display
        """
        try:
            alert_key = f"alerts_{alert_type}"
            alerts = cache.get(alert_key, [])
            
            alert = {
                'type': alert_type,
                'subject': subject,
                'message': message,
                'timestamp': timezone.now().isoformat(),
            }
            
            alerts.append(alert)
            
            # Keep only last 100 alerts
            if len(alerts) > 100:
                alerts = alerts[-100:]
            
            cache.set(alert_key, alerts, 86400)  # Store for 24 hours
            
        except Exception as e:
            error_logger.error(f"Failed to store alert: {str(e)}")
    
    @staticmethod
    def get_recent_alerts(alert_type: str = None, limit: int = 50) -> List[Dict]:
        """
        Get recent alerts for dashboard display
        """
        try:
            if alert_type:
                alert_key = f"alerts_{alert_type}"
                alerts = cache.get(alert_key, [])
            else:
                # Get all alert types
                all_alerts = []
                for atype in ['performance', 'error', 'security']:
                    alert_key = f"alerts_{atype}"
                    alerts = cache.get(alert_key, [])
                    all_alerts.extend(alerts)
                
                # Sort by timestamp
                all_alerts.sort(key=lambda x: x['timestamp'], reverse=True)
                alerts = all_alerts
            
            return alerts[:limit]
            
        except Exception as e:
            error_logger.error(f"Failed to get recent alerts: {str(e)}")
            return []


# Monitoring middleware
class MonitoringMiddleware:
    """
    Middleware for automatic monitoring and logging
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        start_time = time.time()
        
        response = self.get_response(request)
        
        # Log request metrics
        execution_time = time.time() - start_time
        
        monitoring_logger.info(
            f"Request {request.method} {request.path}",
            extra={
                'method': request.method,
                'path': request.path,
                'status_code': response.status_code,
                'execution_time': execution_time,
                'user_id': request.user.id if hasattr(request, 'user') and request.user.is_authenticated else None,
                'ip_address': request.META.get('REMOTE_ADDR', ''),
                'timestamp': timezone.now().isoformat(),
            }
        )
        
        return response
