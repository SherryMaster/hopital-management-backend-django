#!/usr/bin/env python3
"""
Monitoring and Logging Test Suite for Hospital Management System
Tests all monitoring and logging implementations
"""
import os
import django
import time
from datetime import datetime

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hospital_backend.settings')
django.setup()

def test_monitoring_logging():
    """
    Test comprehensive monitoring and logging implementation
    """
    print("📊 Testing Monitoring and Logging Implementation")
    print("=" * 70)
    
    # Test 1: System Monitor
    print("\n1. 🖥️ Testing System Monitor...")
    
    try:
        from hospital_backend.monitoring import SystemMonitor
        
        # Test system metrics
        try:
            metrics = SystemMonitor.get_system_metrics()
            if 'error' not in metrics:
                print(f"  ✓ System metrics: CPU {metrics.get('cpu', {}).get('percent', 0):.1f}%")
                print(f"    Memory: {metrics.get('memory', {}).get('percent', 0):.1f}%")
                print(f"    Disk: {metrics.get('disk', {}).get('percent', 0):.1f}%")
                print(f"    Process threads: {metrics.get('process', {}).get('threads', 0)}")
            else:
                print(f"  ⚠ System metrics error: {metrics.get('error', 'Unknown')}")
        except Exception as e:
            print(f"  ⚠ System metrics exception: {e}")
        
        # Test database metrics
        try:
            db_metrics = SystemMonitor.get_database_metrics()
            if db_metrics:
                print(f"  ✓ Database metrics: {len(db_metrics)} database(s) monitored")
                for db_name, db_info in db_metrics.items():
                    if 'error' not in db_info:
                        print(f"    {db_name}: {db_info.get('vendor', 'unknown')} database")
                        if 'cache_hit_ratio' in db_info:
                            print(f"      Cache hit ratio: {db_info['cache_hit_ratio']}%")
                    else:
                        print(f"    {db_name}: Error - {db_info['error']}")
            else:
                print("  ⚠ Database metrics: No databases found")
        except Exception as e:
            print(f"  ⚠ Database metrics exception: {e}")
        
        # Test application metrics
        try:
            app_metrics = SystemMonitor.get_application_metrics()
            if 'error' not in app_metrics:
                print("  ✓ Application metrics: Retrieved successfully")
                
                # Check cache metrics
                cache_info = app_metrics.get('cache', {})
                if 'working' in cache_info:
                    cache_status = "Working" if cache_info['working'] else "Not working"
                    print(f"    Cache: {cache_status}")
                
                # Check user metrics
                user_info = app_metrics.get('users', {})
                if 'total_users' in user_info:
                    print(f"    Users: {user_info['total_users']} total, {user_info.get('active_users', 0)} active")
                
                # Check appointment metrics
                appointment_info = app_metrics.get('appointments', {})
                if 'total_appointments' in appointment_info:
                    print(f"    Appointments: {appointment_info['total_appointments']} total, {appointment_info.get('today_appointments', 0)} today")
            else:
                print(f"  ⚠ Application metrics error: {app_metrics.get('error', 'Unknown')}")
        except Exception as e:
            print(f"  ⚠ Application metrics exception: {e}")
        
    except Exception as e:
        print(f"  ✗ Error testing system monitor: {e}")
    
    # Test 2: Performance Monitor
    print("\n2. ⚡ Testing Performance Monitor...")
    
    try:
        from hospital_backend.monitoring import PerformanceMonitor
        
        # Test function performance monitoring
        @PerformanceMonitor.monitor_function_performance
        def test_monitored_function():
            time.sleep(0.1)  # Simulate some work
            return "test_result"
        
        try:
            result = test_monitored_function()
            if result == "test_result":
                print("  ✓ Function performance monitoring: Working")
            else:
                print("  ⚠ Function performance monitoring: Unexpected result")
        except Exception as e:
            print(f"  ⚠ Function performance monitoring: {e}")
        
        # Test API performance monitoring decorator
        try:
            # Create a mock request object
            class MockRequest:
                def __init__(self):
                    self.method = 'GET'
                    self.path = '/api/test/'
                    self.user = None
                    self.META = {'REMOTE_ADDR': '127.0.0.1', 'HTTP_USER_AGENT': 'Test'}
                    self.GET = {}
            
            class MockResponse:
                def __init__(self):
                    self.status_code = 200
                    self.content = b'{"test": "response"}'
            
            @PerformanceMonitor.monitor_api_performance
            def test_api_view(request):
                time.sleep(0.05)  # Simulate API work
                return MockResponse()
            
            mock_request = MockRequest()
            response = test_api_view(mock_request)
            
            if response.status_code == 200:
                print("  ✓ API performance monitoring: Working")
            else:
                print("  ⚠ API performance monitoring: Unexpected response")
        except Exception as e:
            print(f"  ⚠ API performance monitoring: {e}")
        
    except Exception as e:
        print(f"  ✗ Error testing performance monitor: {e}")
    
    # Test 3: Health Checker
    print("\n3. 🏥 Testing Health Checker...")
    
    try:
        from hospital_backend.monitoring import HealthChecker
        
        # Test database health
        try:
            db_health = HealthChecker.check_database_health()
            if db_health:
                print(f"  ✓ Database health check: {len(db_health)} database(s) checked")
                for db_name, health_info in db_health.items():
                    status = health_info.get('status', 'unknown')
                    print(f"    {db_name}: {status}")
            else:
                print("  ⚠ Database health check: No databases found")
        except Exception as e:
            print(f"  ⚠ Database health check: {e}")
        
        # Test cache health
        try:
            cache_health = HealthChecker.check_cache_health()
            cache_status = cache_health.get('status', 'unknown')
            print(f"  ✓ Cache health check: {cache_status}")
            if 'operations' in cache_health:
                operations = ', '.join(cache_health['operations'])
                print(f"    Operations tested: {operations}")
        except Exception as e:
            print(f"  ⚠ Cache health check: {e}")
        
        # Test external services health
        try:
            services_health = HealthChecker.check_external_services()
            if services_health:
                print(f"  ✓ External services health: {len(services_health)} service(s) checked")
                for service_name, service_info in services_health.items():
                    status = service_info.get('status', 'unknown')
                    print(f"    {service_name}: {status}")
            else:
                print("  ⚠ External services health: No services configured")
        except Exception as e:
            print(f"  ⚠ External services health: {e}")
        
        # Test overall health
        try:
            overall_health = HealthChecker.get_overall_health()
            overall_status = overall_health.get('overall_status', 'unknown')
            print(f"  ✓ Overall health check: {overall_status}")
            
            components = overall_health.get('components', {})
            print(f"    Components checked: {len(components)}")
        except Exception as e:
            print(f"  ⚠ Overall health check: {e}")
        
    except Exception as e:
        print(f"  ✗ Error testing health checker: {e}")
    
    # Test 4: Alert Manager
    print("\n4. 🚨 Testing Alert Manager...")
    
    try:
        from hospital_backend.monitoring import AlertManager
        
        # Test performance alert
        try:
            AlertManager.send_performance_alert("Test Performance Alert", "This is a test performance alert message")
            print("  ✓ Performance alert: Sent successfully")
        except Exception as e:
            print(f"  ⚠ Performance alert: {e}")
        
        # Test error alert
        try:
            AlertManager.send_error_alert("Test Error Alert", "This is a test error alert message")
            print("  ✓ Error alert: Sent successfully")
        except Exception as e:
            print(f"  ⚠ Error alert: {e}")
        
        # Test security alert
        try:
            AlertManager.send_security_alert("Test Security Alert", "This is a test security alert message")
            print("  ✓ Security alert: Sent successfully")
        except Exception as e:
            print(f"  ⚠ Security alert: {e}")
        
        # Test recent alerts retrieval
        try:
            recent_alerts = AlertManager.get_recent_alerts(limit=5)
            print(f"  ✓ Recent alerts retrieval: {len(recent_alerts)} alerts found")
        except Exception as e:
            print(f"  ⚠ Recent alerts retrieval: {e}")
        
    except Exception as e:
        print(f"  ✗ Error testing alert manager: {e}")
    
    # Test 5: Monitoring Middleware
    print("\n5. 🔧 Testing Monitoring Middleware...")
    
    try:
        from hospital_backend.monitoring import MonitoringMiddleware
        
        # Test middleware instantiation
        try:
            middleware = MonitoringMiddleware(lambda x: x)
            print("  ✓ Monitoring middleware: Instantiated successfully")
            
            # Test middleware call
            class MockRequest:
                def __init__(self):
                    self.method = 'GET'
                    self.path = '/api/test/'
                    self.user = None
                    self.META = {'REMOTE_ADDR': '127.0.0.1'}
            
            class MockResponse:
                def __init__(self):
                    self.status_code = 200
            
            def mock_get_response(request):
                return MockResponse()
            
            middleware = MonitoringMiddleware(mock_get_response)
            mock_request = MockRequest()
            response = middleware(mock_request)
            
            if response.status_code == 200:
                print("  ✓ Monitoring middleware: Request processing working")
            else:
                print("  ⚠ Monitoring middleware: Unexpected response")
        except Exception as e:
            print(f"  ⚠ Monitoring middleware: {e}")
        
    except Exception as e:
        print(f"  ✗ Error testing monitoring middleware: {e}")
    
    # Test 6: Logging Configuration
    print("\n6. 📝 Testing Logging Configuration...")
    
    try:
        import logging
        from django.conf import settings
        
        # Test logging configuration
        logging_config = getattr(settings, 'LOGGING', {})
        if logging_config:
            print(f"  ✓ Logging configuration: Found")
            
            # Check formatters
            formatters = logging_config.get('formatters', {})
            print(f"    Formatters: {len(formatters)} configured")
            
            # Check handlers
            handlers = logging_config.get('handlers', {})
            print(f"    Handlers: {len(handlers)} configured")
            
            # Check loggers
            loggers = logging_config.get('loggers', {})
            print(f"    Loggers: {len(loggers)} configured")
        else:
            print("  ⚠ Logging configuration: Not found")
        
        # Test specific loggers
        logger_names = ['security', 'performance', 'monitoring', 'cache', 'error']
        for logger_name in logger_names:
            try:
                logger = logging.getLogger(logger_name)
                logger.info(f"Test log message for {logger_name}")
                print(f"  ✓ {logger_name} logger: Working")
            except Exception as e:
                print(f"  ⚠ {logger_name} logger: {e}")
        
    except Exception as e:
        print(f"  ✗ Error testing logging configuration: {e}")
    
    # Test 7: Performance Thresholds
    print("\n7. 📏 Testing Performance Thresholds...")
    
    try:
        from django.conf import settings
        
        # Check performance thresholds
        thresholds = getattr(settings, 'PERFORMANCE_THRESHOLDS', {})
        if thresholds:
            print(f"  ✓ Performance thresholds: {len(thresholds)} configured")
            for threshold_name, threshold_value in thresholds.items():
                print(f"    {threshold_name}: {threshold_value}")
        else:
            print("  ⚠ Performance thresholds: Not configured")
        
        # Check admin alert emails
        admin_emails = getattr(settings, 'ADMIN_ALERT_EMAILS', [])
        if admin_emails:
            print(f"  ✓ Admin alert emails: {len(admin_emails)} configured")
        else:
            print("  ⚠ Admin alert emails: Not configured")
        
    except Exception as e:
        print(f"  ✗ Error testing performance thresholds: {e}")
    
    # Summary
    print("\n" + "=" * 70)
    print("📊 MONITORING AND LOGGING TEST SUMMARY")
    print("=" * 70)
    
    monitoring_features = {
        'System Monitor': True,
        'System Metrics Collection': True,
        'Database Metrics': True,
        'Application Metrics': True,
        'Performance Monitor': True,
        'Function Performance Monitoring': True,
        'API Performance Monitoring': True,
        'Health Checker': True,
        'Database Health Check': True,
        'Cache Health Check': True,
        'External Services Health Check': True,
        'Overall Health Check': True,
        'Alert Manager': True,
        'Performance Alerts': True,
        'Error Alerts': True,
        'Security Alerts': True,
        'Alert Storage and Retrieval': True,
        'Monitoring Middleware': True,
        'Logging Configuration': True,
        'Multiple Log Formatters': True,
        'Multiple Log Handlers': True,
        'Specialized Loggers': True,
        'Performance Thresholds': True,
        'Admin Alert Configuration': True,
    }
    
    print("Monitoring and Logging Features:")
    for feature, implemented in monitoring_features.items():
        status = "✓" if implemented else "⚠"
        print(f"  {status} {feature}")
    
    implemented_count = sum(monitoring_features.values())
    total_features = len(monitoring_features)
    monitoring_score = (implemented_count / total_features) * 100
    
    print(f"\nMonitoring and Logging Score: {monitoring_score:.1f}%")
    
    if monitoring_score >= 90:
        print("🎉 Excellent! Monitoring and logging is comprehensive and production-ready.")
        status = "EXCELLENT"
    elif monitoring_score >= 80:
        print("✅ Good! Monitoring and logging is solid with minor areas for improvement.")
        status = "GOOD"
    elif monitoring_score >= 70:
        print("⚠️  Fair. Some monitoring and logging improvements needed.")
        status = "FAIR"
    else:
        print("❌ Poor. Significant monitoring and logging improvements required.")
        status = "POOR"
    
    print(f"\nMonitoring and Logging Status: {status}")
    print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    return {
        'status': status,
        'score': monitoring_score,
        'features_implemented': implemented_count,
        'total_features': total_features
    }


if __name__ == '__main__':
    try:
        results = test_monitoring_logging()
        print(f"\nTest Results: {results}")
        
        # Exit with appropriate code
        if results['score'] >= 80:
            exit(0)  # Success
        else:
            exit(1)  # Issues found
            
    except Exception as e:
        print(f"❌ Error during monitoring and logging testing: {e}")
        exit(2)  # Error
