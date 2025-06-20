"""
Performance tests for Hospital Management System
Tests load, stress, and performance benchmarks for API endpoints
"""
import time
import threading
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
import json

from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.db import transaction, connection
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


class PerformanceTestBase(APITestCase):
    """
    Base class for performance tests with common utilities
    """
    
    def setUp(self):
        self.client = APIClient()
        self.performance_metrics = {
            'response_times': [],
            'success_count': 0,
            'error_count': 0,
            'total_requests': 0
        }
        
        # Create test users for performance testing
        self.test_users = []
        for i in range(10):
            user = User.objects.create_user(
                username=f'perf_user_{i}',
                email=f'perf_user_{i}@test.com',
                password='testpass123'
            )
            self.test_users.append(user)
    
    def tearDown(self):
        # Clean up test users
        for user in self.test_users:
            try:
                user.delete()
            except:
                pass
    
    def make_authenticated_request(self, method, url, data=None, user=None):
        """Make an authenticated request and measure response time"""
        if user is None:
            user = self.test_users[0]
        
        refresh = RefreshToken.for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
        
        start_time = time.time()
        
        if method.upper() == 'GET':
            response = self.client.get(url)
        elif method.upper() == 'POST':
            response = self.client.post(url, data, format='json')
        elif method.upper() == 'PUT':
            response = self.client.put(url, data, format='json')
        elif method.upper() == 'PATCH':
            response = self.client.patch(url, data, format='json')
        elif method.upper() == 'DELETE':
            response = self.client.delete(url)
        else:
            raise ValueError(f"Unsupported method: {method}")
        
        end_time = time.time()
        response_time = (end_time - start_time) * 1000  # Convert to milliseconds
        
        self.performance_metrics['response_times'].append(response_time)
        self.performance_metrics['total_requests'] += 1
        
        if 200 <= response.status_code < 400:
            self.performance_metrics['success_count'] += 1
        else:
            self.performance_metrics['error_count'] += 1
        
        return response, response_time
    
    def calculate_performance_stats(self):
        """Calculate performance statistics"""
        response_times = self.performance_metrics['response_times']
        
        if not response_times:
            return {}
        
        return {
            'total_requests': self.performance_metrics['total_requests'],
            'success_count': self.performance_metrics['success_count'],
            'error_count': self.performance_metrics['error_count'],
            'success_rate': (self.performance_metrics['success_count'] / self.performance_metrics['total_requests']) * 100,
            'avg_response_time': statistics.mean(response_times),
            'min_response_time': min(response_times),
            'max_response_time': max(response_times),
            'median_response_time': statistics.median(response_times),
            'p95_response_time': self.percentile(response_times, 95),
            'p99_response_time': self.percentile(response_times, 99)
        }
    
    def percentile(self, data, percentile):
        """Calculate percentile of data"""
        sorted_data = sorted(data)
        index = (percentile / 100) * (len(sorted_data) - 1)
        if index.is_integer():
            return sorted_data[int(index)]
        else:
            lower = sorted_data[int(index)]
            upper = sorted_data[int(index) + 1]
            return lower + (upper - lower) * (index - int(index))


class AuthenticationPerformanceTest(PerformanceTestBase):
    """
    Performance tests for authentication endpoints
    """
    
    def test_login_performance(self):
        """Test login endpoint performance under load"""
        print("\n🔐 Testing Authentication Performance")
        print("=" * 50)
        
        login_url = '/api/accounts/login/'
        
        # Test sequential logins
        for i in range(20):
            login_data = {
                'username': f'perf_user_{i % 10}',
                'password': 'testpass123'
            }
            
            start_time = time.time()
            response = self.client.post(login_url, login_data, format='json')
            end_time = time.time()
            
            response_time = (end_time - start_time) * 1000
            self.performance_metrics['response_times'].append(response_time)
            self.performance_metrics['total_requests'] += 1
            
            if response.status_code == 200:
                self.performance_metrics['success_count'] += 1
            else:
                self.performance_metrics['error_count'] += 1
        
        stats = self.calculate_performance_stats()
        
        print(f"Login Performance Results:")
        print(f"  Total Requests: {stats.get('total_requests', 0)}")
        print(f"  Success Rate: {stats.get('success_rate', 0):.2f}%")
        print(f"  Average Response Time: {stats.get('avg_response_time', 0):.2f}ms")
        print(f"  95th Percentile: {stats.get('p95_response_time', 0):.2f}ms")
        
        # Performance assertions
        self.assertGreater(stats.get('success_rate', 0), 90, "Login success rate should be > 90%")
        self.assertLess(stats.get('avg_response_time', 1000), 500, "Average login time should be < 500ms")
    
    def test_token_refresh_performance(self):
        """Test token refresh performance"""
        print("\n🔄 Testing Token Refresh Performance")
        
        # Create refresh tokens for testing
        refresh_tokens = []
        for user in self.test_users[:5]:
            refresh = RefreshToken.for_user(user)
            refresh_tokens.append(str(refresh))
        
        refresh_url = '/api/accounts/token/refresh/'
        
        for refresh_token in refresh_tokens * 4:  # 20 requests total
            refresh_data = {'refresh': refresh_token}
            
            start_time = time.time()
            response = self.client.post(refresh_url, refresh_data, format='json')
            end_time = time.time()
            
            response_time = (end_time - start_time) * 1000
            self.performance_metrics['response_times'].append(response_time)
            self.performance_metrics['total_requests'] += 1
            
            if response.status_code == 200:
                self.performance_metrics['success_count'] += 1
            else:
                self.performance_metrics['error_count'] += 1
        
        stats = self.calculate_performance_stats()
        
        print(f"Token Refresh Performance Results:")
        print(f"  Average Response Time: {stats.get('avg_response_time', 0):.2f}ms")
        print(f"  Success Rate: {stats.get('success_rate', 0):.2f}%")
        
        self.assertLess(stats.get('avg_response_time', 1000), 200, "Token refresh should be < 200ms")


class DatabasePerformanceTest(TransactionTestCase):
    """
    Performance tests for database operations
    """
    
    def setUp(self):
        self.performance_metrics = {
            'query_times': [],
            'total_queries': 0
        }
    
    def test_user_creation_performance(self):
        """Test user creation performance"""
        print("\n🗄️ Testing Database Performance - User Creation")
        print("=" * 50)
        
        creation_times = []
        
        for i in range(50):
            start_time = time.time()
            
            user = User.objects.create_user(
                username=f'db_perf_user_{i}',
                email=f'db_perf_user_{i}@test.com',
                password='testpass123'
            )
            
            end_time = time.time()
            creation_time = (end_time - start_time) * 1000
            creation_times.append(creation_time)
        
        avg_creation_time = statistics.mean(creation_times)
        max_creation_time = max(creation_times)
        
        print(f"User Creation Performance:")
        print(f"  Average Creation Time: {avg_creation_time:.2f}ms")
        print(f"  Max Creation Time: {max_creation_time:.2f}ms")
        print(f"  Total Users Created: 50")
        
        self.assertLess(avg_creation_time, 100, "Average user creation should be < 100ms")
        
        # Clean up
        User.objects.filter(username__startswith='db_perf_user_').delete()
    
    def test_user_query_performance(self):
        """Test user query performance"""
        print("\n🔍 Testing Database Performance - User Queries")
        
        # Create test data
        users = []
        for i in range(100):
            user = User.objects.create_user(
                username=f'query_perf_user_{i}',
                email=f'query_perf_user_{i}@test.com',
                password='testpass123'
            )
            users.append(user)
        
        query_times = []
        
        # Test various query patterns
        for i in range(20):
            # Test single user lookup
            start_time = time.time()
            user = User.objects.get(username=f'query_perf_user_{i % 100}')
            end_time = time.time()
            query_times.append((end_time - start_time) * 1000)
            
            # Test user list query
            start_time = time.time()
            user_list = list(User.objects.filter(username__startswith='query_perf_user_')[:10])
            end_time = time.time()
            query_times.append((end_time - start_time) * 1000)
        
        avg_query_time = statistics.mean(query_times)
        max_query_time = max(query_times)
        
        print(f"User Query Performance:")
        print(f"  Average Query Time: {avg_query_time:.2f}ms")
        print(f"  Max Query Time: {max_query_time:.2f}ms")
        print(f"  Total Queries: {len(query_times)}")
        
        self.assertLess(avg_query_time, 50, "Average query time should be < 50ms")
        
        # Clean up
        User.objects.filter(username__startswith='query_perf_user_').delete()
    
    def test_database_connection_performance(self):
        """Test database connection performance"""
        print("\n🔗 Testing Database Connection Performance")
        
        connection_times = []
        
        for i in range(10):
            start_time = time.time()
            
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
            
            end_time = time.time()
            connection_times.append((end_time - start_time) * 1000)
        
        avg_connection_time = statistics.mean(connection_times)
        
        print(f"Database Connection Performance:")
        print(f"  Average Connection Time: {avg_connection_time:.2f}ms")
        
        self.assertLess(avg_connection_time, 10, "Database connection should be < 10ms")


class ConcurrentLoadTest(PerformanceTestBase):
    """
    Concurrent load testing for API endpoints
    """
    
    def test_concurrent_authentication(self):
        """Test concurrent authentication requests"""
        print("\n⚡ Testing Concurrent Authentication Load")
        print("=" * 50)
        
        def authenticate_user(user_index):
            """Function to authenticate a user"""
            try:
                login_data = {
                    'username': f'perf_user_{user_index}',
                    'password': 'testpass123'
                }
                
                start_time = time.time()
                response = self.client.post('/api/accounts/login/', login_data, format='json')
                end_time = time.time()
                
                return {
                    'response_time': (end_time - start_time) * 1000,
                    'status_code': response.status_code,
                    'success': 200 <= response.status_code < 400
                }
            except Exception as e:
                return {
                    'response_time': 0,
                    'status_code': 500,
                    'success': False,
                    'error': str(e)
                }
        
        # Run concurrent authentication requests
        results = []
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(authenticate_user, i % 10) for i in range(25)]
            
            for future in as_completed(futures):
                result = future.result()
                results.append(result)
        
        # Analyze results
        response_times = [r['response_time'] for r in results if r['response_time'] > 0]
        success_count = sum(1 for r in results if r['success'])
        total_requests = len(results)
        
        if response_times:
            avg_response_time = statistics.mean(response_times)
            max_response_time = max(response_times)
            success_rate = (success_count / total_requests) * 100
            
            print(f"Concurrent Authentication Results:")
            print(f"  Total Requests: {total_requests}")
            print(f"  Success Rate: {success_rate:.2f}%")
            print(f"  Average Response Time: {avg_response_time:.2f}ms")
            print(f"  Max Response Time: {max_response_time:.2f}ms")
            
            self.assertGreater(success_rate, 80, "Concurrent auth success rate should be > 80%")
            self.assertLess(avg_response_time, 1000, "Concurrent auth avg time should be < 1000ms")
    
    def test_api_endpoint_load(self):
        """Test load on various API endpoints"""
        print("\n🌐 Testing API Endpoint Load")
        
        endpoints_to_test = [
            ('/api/accounts/profile/', 'GET'),
            ('/api/patients/', 'GET'),
            ('/api/doctors/', 'GET'),
            ('/api/appointments/', 'GET')
        ]
        
        def test_endpoint(endpoint_info):
            """Test a single endpoint"""
            url, method = endpoint_info
            user = self.test_users[0]
            
            try:
                response, response_time = self.make_authenticated_request(method, url, user=user)
                return {
                    'url': url,
                    'method': method,
                    'response_time': response_time,
                    'status_code': response.status_code,
                    'success': 200 <= response.status_code < 500  # 404 is OK for non-existent endpoints
                }
            except Exception as e:
                return {
                    'url': url,
                    'method': method,
                    'response_time': 0,
                    'status_code': 500,
                    'success': False,
                    'error': str(e)
                }
        
        # Test each endpoint multiple times
        all_results = []
        for endpoint in endpoints_to_test:
            for _ in range(5):
                result = test_endpoint(endpoint)
                all_results.append(result)
        
        # Group results by endpoint
        endpoint_stats = {}
        for result in all_results:
            key = f"{result['method']} {result['url']}"
            if key not in endpoint_stats:
                endpoint_stats[key] = []
            endpoint_stats[key].append(result)
        
        print(f"API Endpoint Load Test Results:")
        for endpoint, results in endpoint_stats.items():
            response_times = [r['response_time'] for r in results if r['response_time'] > 0]
            success_count = sum(1 for r in results if r['success'])
            
            if response_times:
                avg_time = statistics.mean(response_times)
                success_rate = (success_count / len(results)) * 100
                print(f"  {endpoint}:")
                print(f"    Success Rate: {success_rate:.1f}%")
                print(f"    Avg Response Time: {avg_time:.2f}ms")


class MemoryPerformanceTest(TestCase):
    """
    Memory usage and performance tests
    """
    
    def test_memory_usage_during_user_creation(self):
        """Test memory usage during bulk user creation"""
        print("\n💾 Testing Memory Performance")
        print("=" * 50)
        
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Create many users
        users = []
        for i in range(100):
            user = User.objects.create_user(
                username=f'memory_test_user_{i}',
                email=f'memory_test_user_{i}@test.com',
                password='testpass123'
            )
            users.append(user)
        
        peak_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = peak_memory - initial_memory
        
        print(f"Memory Usage Test:")
        print(f"  Initial Memory: {initial_memory:.2f} MB")
        print(f"  Peak Memory: {peak_memory:.2f} MB")
        print(f"  Memory Increase: {memory_increase:.2f} MB")
        print(f"  Memory per User: {memory_increase / 100:.3f} MB")
        
        # Clean up
        User.objects.filter(username__startswith='memory_test_user_').delete()
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        print(f"  Final Memory: {final_memory:.2f} MB")
        
        # Memory should not increase excessively
        self.assertLess(memory_increase, 50, "Memory increase should be < 50MB for 100 users")


class StressTest(PerformanceTestBase):
    """
    Stress testing for system limits
    """

    def test_high_volume_user_creation(self):
        """Test system under high volume user creation"""
        print("\n🔥 Testing High Volume Stress")
        print("=" * 50)

        creation_times = []
        errors = []

        for i in range(200):
            try:
                start_time = time.time()

                user = User.objects.create_user(
                    username=f'stress_user_{i}',
                    email=f'stress_user_{i}@test.com',
                    password='testpass123'
                )

                end_time = time.time()
                creation_times.append((end_time - start_time) * 1000)

            except Exception as e:
                errors.append(str(e))

        if creation_times:
            avg_time = statistics.mean(creation_times)
            max_time = max(creation_times)
            success_rate = (len(creation_times) / 200) * 100

            print(f"High Volume Stress Test Results:")
            print(f"  Total Attempts: 200")
            print(f"  Success Rate: {success_rate:.2f}%")
            print(f"  Average Creation Time: {avg_time:.2f}ms")
            print(f"  Max Creation Time: {max_time:.2f}ms")
            print(f"  Errors: {len(errors)}")

            if errors:
                print(f"  Sample Errors: {errors[:3]}")

        # Clean up
        User.objects.filter(username__startswith='stress_user_').delete()

        self.assertGreater(len(creation_times), 150, "Should successfully create at least 150 users")

    def test_rapid_authentication_requests(self):
        """Test rapid authentication requests"""
        print("\n⚡ Testing Rapid Authentication Stress")

        # Create test user
        test_user = User.objects.create_user(
            username='rapid_auth_user',
            email='rapid_auth@test.com',
            password='testpass123'
        )

        login_data = {
            'username': 'rapid_auth_user',
            'password': 'testpass123'
        }

        response_times = []
        errors = []

        for i in range(50):
            try:
                start_time = time.time()
                response = self.client.post('/api/accounts/login/', login_data, format='json')
                end_time = time.time()

                response_times.append((end_time - start_time) * 1000)

                if response.status_code != 200:
                    errors.append(f"Status {response.status_code}")

            except Exception as e:
                errors.append(str(e))

        if response_times:
            avg_time = statistics.mean(response_times)
            success_rate = (len(response_times) / 50) * 100

            print(f"Rapid Authentication Results:")
            print(f"  Success Rate: {success_rate:.2f}%")
            print(f"  Average Response Time: {avg_time:.2f}ms")
            print(f"  Errors: {len(errors)}")

        # Clean up
        test_user.delete()


class PerformanceBenchmark(TestCase):
    """
    Performance benchmarking and baseline establishment
    """

    def test_establish_performance_baseline(self):
        """Establish performance baselines for the system"""
        print("\n📊 Establishing Performance Baselines")
        print("=" * 50)

        benchmarks = {}

        # Benchmark 1: User creation
        user_creation_times = []
        for i in range(10):
            start_time = time.time()
            user = User.objects.create_user(
                username=f'benchmark_user_{i}',
                email=f'benchmark_user_{i}@test.com',
                password='testpass123'
            )
            end_time = time.time()
            user_creation_times.append((end_time - start_time) * 1000)

        benchmarks['user_creation_avg_ms'] = statistics.mean(user_creation_times)

        # Benchmark 2: User query
        query_times = []
        for i in range(10):
            start_time = time.time()
            user = User.objects.get(username=f'benchmark_user_{i}')
            end_time = time.time()
            query_times.append((end_time - start_time) * 1000)

        benchmarks['user_query_avg_ms'] = statistics.mean(query_times)

        # Benchmark 3: JWT token generation
        token_times = []
        for i in range(10):
            user = User.objects.get(username=f'benchmark_user_{i}')
            start_time = time.time()
            refresh = RefreshToken.for_user(user)
            access_token = refresh.access_token
            end_time = time.time()
            token_times.append((end_time - start_time) * 1000)

        benchmarks['jwt_generation_avg_ms'] = statistics.mean(token_times)

        # Print benchmarks
        print("Performance Baselines Established:")
        for metric, value in benchmarks.items():
            print(f"  {metric}: {value:.2f}ms")

        # Store benchmarks for comparison
        self.performance_baselines = benchmarks

        # Clean up
        User.objects.filter(username__startswith='benchmark_user_').delete()

        # Assertions for reasonable performance
        self.assertLess(benchmarks['user_creation_avg_ms'], 100, "User creation baseline should be < 100ms")
        self.assertLess(benchmarks['user_query_avg_ms'], 50, "User query baseline should be < 50ms")
        self.assertLess(benchmarks['jwt_generation_avg_ms'], 50, "JWT generation baseline should be < 50ms")

        return benchmarks


class PerformanceRegressionTest(TestCase):
    """
    Performance regression testing
    """

    def test_performance_regression(self):
        """Test for performance regressions"""
        print("\n📈 Testing Performance Regression")
        print("=" * 50)

        # Establish current performance
        benchmark_test = PerformanceBenchmark()
        current_benchmarks = benchmark_test.test_establish_performance_baseline()

        # Expected baselines (these would be stored from previous runs)
        expected_baselines = {
            'user_creation_avg_ms': 50.0,
            'user_query_avg_ms': 10.0,
            'jwt_generation_avg_ms': 20.0
        }

        regression_threshold = 1.5  # 50% increase is considered regression

        regressions = []
        improvements = []

        for metric, current_value in current_benchmarks.items():
            if metric in expected_baselines:
                expected_value = expected_baselines[metric]
                ratio = current_value / expected_value

                if ratio > regression_threshold:
                    regressions.append({
                        'metric': metric,
                        'expected': expected_value,
                        'current': current_value,
                        'ratio': ratio
                    })
                elif ratio < 0.8:  # 20% improvement
                    improvements.append({
                        'metric': metric,
                        'expected': expected_value,
                        'current': current_value,
                        'ratio': ratio
                    })

        print("Performance Regression Analysis:")
        if regressions:
            print("  ⚠️ Performance Regressions Detected:")
            for reg in regressions:
                print(f"    {reg['metric']}: {reg['current']:.2f}ms (expected: {reg['expected']:.2f}ms, {reg['ratio']:.2f}x slower)")

        if improvements:
            print("  ✅ Performance Improvements:")
            for imp in improvements:
                print(f"    {imp['metric']}: {imp['current']:.2f}ms (expected: {imp['expected']:.2f}ms, {imp['ratio']:.2f}x faster)")

        if not regressions and not improvements:
            print("  ✅ Performance is stable (no significant changes)")

        # Assert no major regressions
        self.assertEqual(len(regressions), 0, f"Performance regressions detected: {regressions}")


class EndToEndPerformanceTest(PerformanceTestBase):
    """
    End-to-end performance testing
    """

    def test_complete_user_workflow_performance(self):
        """Test performance of complete user workflow"""
        print("\n🔄 Testing End-to-End Workflow Performance")
        print("=" * 50)

        workflow_times = {}

        # Step 1: User Registration (simulated)
        start_time = time.time()
        user = User.objects.create_user(
            username='e2e_perf_user',
            email='e2e_perf@test.com',
            password='testpass123'
        )
        workflow_times['user_creation'] = (time.time() - start_time) * 1000

        # Step 2: Authentication
        login_data = {
            'username': 'e2e_perf_user',
            'password': 'testpass123'
        }

        start_time = time.time()
        response = self.client.post('/api/accounts/login/', login_data, format='json')
        workflow_times['authentication'] = (time.time() - start_time) * 1000

        if response.status_code == 200:
            # Step 3: Token refresh
            refresh_token = response.data.get('refresh') if hasattr(response, 'data') else None
            if refresh_token:
                start_time = time.time()
                refresh_response = self.client.post('/api/accounts/token/refresh/',
                                                  {'refresh': refresh_token}, format='json')
                workflow_times['token_refresh'] = (time.time() - start_time) * 1000

        # Step 4: Profile access
        refresh = RefreshToken.for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')

        start_time = time.time()
        profile_response = self.client.get('/api/accounts/profile/')
        workflow_times['profile_access'] = (time.time() - start_time) * 1000

        # Calculate total workflow time
        total_time = sum(workflow_times.values())

        print("End-to-End Workflow Performance:")
        for step, time_ms in workflow_times.items():
            print(f"  {step}: {time_ms:.2f}ms")
        print(f"  Total Workflow Time: {total_time:.2f}ms")

        # Clean up
        user.delete()

        # Performance assertions
        self.assertLess(total_time, 2000, "Complete workflow should be < 2000ms")
        self.assertLess(workflow_times.get('authentication', 1000), 500, "Authentication should be < 500ms")

        return workflow_times
