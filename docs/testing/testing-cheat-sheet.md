# Testing Cheat Sheet - Hospital Management System

## 🚀 Quick Commands

### Test Execution
```bash
# Unit Tests
python scripts/run_tests.py all                    # All unit tests
python scripts/run_tests.py models                 # Model tests only
python scripts/run_tests.py serializers            # Serializer tests only
python scripts/run_tests.py views                  # View tests only
python scripts/run_tests.py utils                  # Utility tests only

# Integration Tests
python scripts/run_integration_tests.py all        # All integration tests
python scripts/run_integration_tests.py workflow   # Workflow tests
python scripts/run_integration_tests.py api        # API integration tests
python scripts/run_integration_tests.py smoke      # Critical path tests

# Performance Tests
python scripts/run_performance_tests.py quick      # Quick performance check
python scripts/run_performance_tests.py load       # Load testing
python scripts/run_performance_tests.py stress     # Stress testing
python scripts/run_performance_tests.py benchmark  # Benchmark tests
```

### Coverage Reports
```bash
python scripts/run_tests.py coverage              # Generate coverage report
open htmlcov/index.html                           # View HTML coverage report
```

### Test Data Management
```bash
# Create Test Data
python manage.py manage_test_data create_minimal
python manage.py manage_test_data create_comprehensive
python manage.py manage_test_data create_performance

# Environment Setup
python manage.py manage_test_data seed_development
python manage.py manage_test_data seed_demo

# Data Management
python manage.py manage_test_data status
python manage.py manage_test_data cleanup
python manage.py manage_test_data export_fixtures
python manage.py manage_test_data load_fixtures
```

## 🧪 Test Writing Patterns

### Unit Test Template
```python
from django.test import TestCase
from django.contrib.auth import get_user_model

User = get_user_model()

class ModelNameTest(TestCase):
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_model_creation(self):
        """Test model creation"""
        self.assertEqual(self.user.username, 'testuser')
        self.assertTrue(self.user.check_password('testpass123'))
    
    def test_model_str_method(self):
        """Test string representation"""
        expected = f"{self.user.first_name} {self.user.last_name} ({self.user.username})"
        self.assertEqual(str(self.user), expected)
    
    def tearDown(self):
        """Clean up after tests"""
        pass
```

### API Test Template
```python
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from django.urls import reverse

class APIViewTest(APITestCase):
    def setUp(self):
        """Set up test data"""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        refresh = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
        self.url = reverse('api-endpoint-name')
    
    def test_get_request(self):
        """Test GET request"""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_post_request(self):
        """Test POST request"""
        data = {'field': 'value'}
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
    
    def test_authentication_required(self):
        """Test authentication requirement"""
        self.client.credentials()  # Remove authentication
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
```

### Factory Usage
```python
from tests.factories import UserFactory, PatientProfileFactory

# Create single instance
user = UserFactory()
patient = PatientProfileFactory()

# Create with custom attributes
admin = UserFactory(user_type='admin', is_staff=True)

# Create batch
users = UserFactory.create_batch(10)

# Build without saving
user = UserFactory.build()

# Create related objects
patient = PatientProfileFactory(user=UserFactory())
```

## 🔍 Common Assertions

### Django Test Assertions
```python
# Equality
self.assertEqual(actual, expected)
self.assertNotEqual(actual, expected)

# Truth values
self.assertTrue(expression)
self.assertFalse(expression)

# None checks
self.assertIsNone(value)
self.assertIsNotNone(value)

# Membership
self.assertIn(item, container)
self.assertNotIn(item, container)

# Exceptions
self.assertRaises(ExceptionClass, callable, *args)
with self.assertRaises(ExceptionClass):
    # code that should raise exception

# Database
self.assertQuerysetEqual(qs, values)
self.assertNumQueries(num, func)

# HTTP responses
self.assertContains(response, text)
self.assertNotContains(response, text)
self.assertRedirects(response, expected_url)
```

### REST Framework Assertions
```python
from rest_framework import status

# Status codes
self.assertEqual(response.status_code, status.HTTP_200_OK)
self.assertEqual(response.status_code, status.HTTP_201_CREATED)
self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

# Response data
self.assertIn('field_name', response.data)
self.assertEqual(response.data['field'], 'expected_value')
self.assertEqual(len(response.data['results']), expected_count)

# JSON responses
self.assertEqual(response['Content-Type'], 'application/json')
```

## 🎯 Testing Scenarios

### Authentication Testing
```python
# Test user registration
def test_user_registration(self):
    data = {
        'username': 'newuser',
        'email': 'new@example.com',
        'password': 'SecurePass123!',
        'user_type': 'patient'
    }
    response = self.client.post('/api/accounts/register/', data)
    self.assertEqual(response.status_code, status.HTTP_201_CREATED)

# Test login
def test_user_login(self):
    data = {'username': 'testuser', 'password': 'testpass123'}
    response = self.client.post('/api/accounts/login/', data)
    self.assertEqual(response.status_code, status.HTTP_200_OK)
    self.assertIn('access', response.data)
    self.assertIn('refresh', response.data)

# Test protected endpoint
def test_protected_endpoint(self):
    # Without authentication
    self.client.credentials()
    response = self.client.get('/api/protected/')
    self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    # With authentication
    refresh = RefreshToken.for_user(self.user)
    self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    response = self.client.get('/api/protected/')
    self.assertEqual(response.status_code, status.HTTP_200_OK)
```

### CRUD Testing
```python
# Test CREATE
def test_create_object(self):
    data = {'name': 'Test Object', 'description': 'Test Description'}
    response = self.client.post(self.url, data, format='json')
    self.assertEqual(response.status_code, status.HTTP_201_CREATED)
    self.assertEqual(response.data['name'], 'Test Object')

# Test READ
def test_get_object(self):
    obj = ModelFactory()
    url = reverse('model-detail', kwargs={'pk': obj.pk})
    response = self.client.get(url)
    self.assertEqual(response.status_code, status.HTTP_200_OK)
    self.assertEqual(response.data['id'], obj.id)

# Test UPDATE
def test_update_object(self):
    obj = ModelFactory()
    url = reverse('model-detail', kwargs={'pk': obj.pk})
    data = {'name': 'Updated Name'}
    response = self.client.patch(url, data, format='json')
    self.assertEqual(response.status_code, status.HTTP_200_OK)
    self.assertEqual(response.data['name'], 'Updated Name')

# Test DELETE
def test_delete_object(self):
    obj = ModelFactory()
    url = reverse('model-detail', kwargs={'pk': obj.pk})
    response = self.client.delete(url)
    self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
    self.assertFalse(Model.objects.filter(pk=obj.pk).exists())
```

### Validation Testing
```python
# Test required fields
def test_required_fields(self):
    data = {}  # Missing required fields
    response = self.client.post(self.url, data, format='json')
    self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    self.assertIn('field_name', response.data)

# Test field validation
def test_email_validation(self):
    data = {'email': 'invalid-email'}
    response = self.client.post(self.url, data, format='json')
    self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    self.assertIn('email', response.data)

# Test unique constraints
def test_unique_constraint(self):
    ModelFactory(username='existing')
    data = {'username': 'existing'}
    response = self.client.post(self.url, data, format='json')
    self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
```

## 🐛 Debugging Tests

### Debug Commands
```bash
# Run with verbose output
python manage.py test tests.test_models --verbosity=2

# Run specific test
python manage.py test tests.test_models.UserModelTest.test_create_user

# Debug mode
python manage.py test tests.test_models --debug-mode

# Keep test database
python manage.py test tests.test_models --keepdb
```

### Debug Techniques
```python
# Print debugging
def test_debug_example(self):
    user = UserFactory()
    print(f"Created user: {user}")
    print(f"User ID: {user.id}")
    print(f"User data: {user.__dict__}")

# Use pdb debugger
import pdb

def test_with_debugger(self):
    user = UserFactory()
    pdb.set_trace()  # Debugger will stop here
    self.assertEqual(user.username, 'expected')

# Assert with custom messages
def test_with_messages(self):
    self.assertEqual(
        actual_value, 
        expected_value, 
        f"Expected {expected_value}, got {actual_value}"
    )
```

## 📊 Performance Testing Patterns

### Response Time Testing
```python
import time

def test_response_time(self):
    start_time = time.time()
    response = self.client.get(self.url)
    end_time = time.time()
    
    response_time = (end_time - start_time) * 1000  # milliseconds
    self.assertLess(response_time, 200)  # Should be under 200ms
```

### Concurrent Testing
```python
from concurrent.futures import ThreadPoolExecutor

def test_concurrent_requests(self):
    def make_request():
        return self.client.get(self.url)
    
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(make_request) for _ in range(10)]
        responses = [future.result() for future in futures]
    
    success_count = sum(1 for r in responses if r.status_code == 200)
    self.assertGreater(success_count, 8)  # At least 80% success rate
```

## 🔧 Environment Setup

### Test Settings
```python
# settings/test.py
from .base import *

# Test database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

# Disable migrations for faster tests
class DisableMigrations:
    def __contains__(self, item):
        return True
    def __getitem__(self, item):
        return None

MIGRATION_MODULES = DisableMigrations()

# Test-specific settings
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',  # Faster for tests
]

EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
```

### Environment Variables
```bash
# .env.test
DJANGO_SETTINGS_MODULE=hospital_backend.settings.test
DEBUG=False
SECRET_KEY=test-secret-key
DATABASE_URL=sqlite:///:memory:
```

## 📈 Coverage Targets

| Component | Target Coverage |
|-----------|----------------|
| Models | 95% |
| Serializers | 90% |
| Views | 85% |
| Utils | 90% |
| Overall | 85% |

## 🚨 Common Pitfalls

1. **Test Isolation**: Tests affecting each other
2. **Database State**: Not cleaning up test data
3. **Time Dependencies**: Tests failing due to time-sensitive code
4. **External Dependencies**: Tests depending on external services
5. **Hardcoded Values**: Using hardcoded IDs or dates
6. **Incomplete Mocking**: Not mocking external dependencies
7. **Assertion Order**: Wrong order of expected vs actual values

## 💡 Tips and Tricks

1. **Use Factories**: More flexible than fixtures
2. **Test Edge Cases**: Empty data, boundary values, invalid input
3. **Mock External Services**: Don't depend on external APIs
4. **Use Descriptive Names**: Test names should explain what they test
5. **Keep Tests Simple**: One concept per test
6. **Use setUp/tearDown**: For common test setup
7. **Test Error Conditions**: Not just happy paths
8. **Use Transactions**: For database test isolation

---

**Quick Reference Complete! 📋**
