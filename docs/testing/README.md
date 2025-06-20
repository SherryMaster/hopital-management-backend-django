# Hospital Management System - Testing Documentation

## 🏥 Overview

This documentation covers the comprehensive testing framework for the Hospital Management System, including unit tests, integration tests, performance tests, and test data management.

## 📋 Table of Contents

1. [Quick Start](#quick-start)
2. [Testing Framework Overview](#testing-framework-overview)
3. [Unit Testing](#unit-testing)
4. [Integration Testing](#integration-testing)
5. [Performance Testing](#performance-testing)
6. [Test Data Management](#test-data-management)
7. [Best Practices](#best-practices)
8. [Troubleshooting](#troubleshooting)

## 🚀 Quick Start

### Prerequisites

```bash
# Ensure virtual environment is activated
hospital_env\Scripts\activate  # Windows
source hospital_env/bin/activate  # Linux/Mac

# Install testing dependencies
pip install coverage pytest pytest-django factory-boy faker psutil

# Setup cache tables (for development without Redis)
python setup_cache_tables.py
```

### Cache Configuration

The system supports both Redis (production) and database caching (development):

```bash
# For development (default - uses database cache)
# No additional setup required after running setup_cache_tables.py

# For production with Redis
# Set environment variable: USE_REDIS=true
# Ensure Redis server is running on localhost:6379
```

### Run All Tests

```bash
# Run comprehensive test suite
python scripts/run_tests.py all

# Run with coverage report
python scripts/run_tests.py coverage

# Run quick smoke tests
python scripts/run_tests.py models
```

### Run Specific Test Categories

```bash
# Unit tests
python scripts/run_tests.py models
python scripts/run_tests.py serializers
python scripts/run_tests.py views

# Integration tests
python scripts/run_integration_tests.py all
python scripts/run_integration_tests.py workflow

# Performance tests
python scripts/run_performance_tests.py quick
python scripts/run_performance_tests.py load
```

## 🧪 Testing Framework Overview

### Architecture

```
tests/
├── __init__.py
├── test_basic.py              # Basic functionality tests
├── test_models.py             # Model unit tests
├── test_serializers.py        # Serializer unit tests
├── test_views.py              # View/API unit tests
├── test_utils.py              # Utility function tests
├── test_integration.py        # Integration tests
├── test_integration_basic.py  # Basic integration tests
├── test_performance.py        # Performance tests
├── factories.py               # Test data factories
├── fixtures.py                # Test fixtures and utilities
└── management/
    └── commands/
        └── manage_test_data.py # Test data management
```

### Test Runners

| Runner | Purpose | Command |
|--------|---------|---------|
| `run_tests.py` | Unit tests | `python run_tests.py [category]` |
| `run_integration_tests.py` | Integration tests | `python run_integration_tests.py [type]` |
| `run_performance_tests.py` | Performance tests | `python run_performance_tests.py [test]` |

### Coverage Reports

- **Console Report**: Real-time coverage during test execution
- **HTML Report**: Detailed coverage in `htmlcov/` directory
- **XML Report**: CI/CD compatible coverage in `coverage.xml`

## 🔬 Unit Testing

### Overview

Unit tests validate individual components in isolation using Django's built-in testing framework.

### Test Categories

#### Model Tests (`test_models.py`)

```python
class UserModelTest(TestCase):
    def test_create_user(self):
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.assertEqual(user.username, 'testuser')
        self.assertTrue(user.check_password('testpass123'))
```

#### Serializer Tests (`test_serializers.py`)

```python
class UserSerializerTest(TestCase):
    def test_user_registration_serializer_valid_data(self):
        data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'SecurePass123!',
            'user_type': 'patient'
        }
        serializer = UserRegistrationSerializer(data=data)
        self.assertTrue(serializer.is_valid())
```

#### View Tests (`test_views.py`)

```python
class AuthenticationViewTest(APITestCase):
    def test_user_registration_success(self):
        response = self.client.post(self.register_url, self.user_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
```

### Running Unit Tests

```bash
# All unit tests
python scripts/run_tests.py all

# Specific categories
python scripts/run_tests.py models
python scripts/run_tests.py serializers
python scripts/run_tests.py views
python scripts/run_tests.py utils

# Specific test class
python manage.py test tests.test_models.UserModelTest

# Specific test method
python manage.py test tests.test_models.UserModelTest.test_create_user
```

### Unit Test Best Practices

1. **Isolation**: Each test should be independent
2. **Naming**: Use descriptive test method names
3. **Setup/Teardown**: Use `setUp()` and `tearDown()` methods
4. **Assertions**: Use specific assertion methods
5. **Coverage**: Aim for >90% code coverage

## 🔗 Integration Testing

### Overview

Integration tests validate complete workflows and cross-module functionality.

### Test Categories

#### Authentication Integration
- User registration and login workflow
- JWT token generation and validation
- Token refresh mechanism

#### Patient Management Integration
- Complete patient onboarding
- Profile creation and updates
- Emergency contact management

#### Appointment Booking Integration
- Doctor search and availability
- Appointment scheduling
- Status updates and notifications

#### Cross-Module Integration
- End-to-end patient journey
- Data consistency across modules
- Notification integration

### Running Integration Tests

```bash
# All integration tests
python scripts/run_integration_tests.py all

# Specific categories
python scripts/run_integration_tests.py workflow
python scripts/run_integration_tests.py api
python scripts/run_integration_tests.py database
python scripts/run_integration_tests.py cross-module

# Smoke tests (critical paths only)
python scripts/run_integration_tests.py smoke

# Environment validation
python scripts/run_integration_tests.py validate
```

### Integration Test Example

```python
def test_complete_patient_journey(self):
    """Test complete patient journey across all modules"""
    
    # Step 1: Patient registers and creates profile
    patient_data = {...}
    response = self.client.post('/api/accounts/register/', patient_data)
    
    # Step 2: Patient books appointment
    appointment_data = {...}
    response = self.client.post('/api/appointments/', appointment_data)
    
    # Step 3: Doctor completes appointment and adds records
    # ... (switch to doctor authentication)
    
    # Step 4: Invoice generated and payment processed
    # ... (billing workflow)
    
    # Verify complete workflow
    self.assertEqual(appointment.status, 'completed')
    self.assertEqual(invoice.status, 'paid')
```

## ⚡ Performance Testing

### Overview

Performance tests validate system performance under various load conditions.

### Test Categories

#### Load Testing
- Concurrent user simulation
- API endpoint performance
- Response time measurement

#### Stress Testing
- High volume operations
- System limit identification
- Error rate monitoring

#### Benchmark Testing
- Performance baseline establishment
- Regression detection
- Historical comparison

#### Memory Testing
- Memory usage monitoring
- Memory leak detection
- Resource utilization

### Running Performance Tests

```bash
# All performance tests
python scripts/run_performance_tests.py all

# Specific categories
python scripts/run_performance_tests.py load
python scripts/run_performance_tests.py stress
python scripts/run_performance_tests.py benchmark
python scripts/run_performance_tests.py database
python scripts/run_performance_tests.py api

# Quick performance check
python scripts/run_performance_tests.py quick

# Environment validation
python scripts/run_performance_tests.py validate

# Generate performance report
python scripts/run_performance_tests.py report
```

### Performance Metrics

| Metric | Description | Target |
|--------|-------------|--------|
| Response Time | Average API response time | < 200ms |
| Throughput | Requests per second | > 100 RPS |
| Success Rate | Percentage of successful requests | > 99% |
| Memory Usage | Memory consumption per operation | < 50MB |
| Database Performance | Query execution time | < 50ms |

### Performance Test Example

```python
def test_concurrent_authentication(self):
    """Test concurrent authentication requests"""
    
    def authenticate_user(user_index):
        login_data = {
            'username': f'user_{user_index}',
            'password': 'testpass123'
        }
        start_time = time.time()
        response = self.client.post('/api/accounts/login/', login_data)
        end_time = time.time()
        
        return {
            'response_time': (end_time - start_time) * 1000,
            'status_code': response.status_code,
            'success': 200 <= response.status_code < 400
        }
    
    # Run concurrent requests
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(authenticate_user, i) for i in range(25)]
        results = [future.result() for future in as_completed(futures)]
    
    # Analyze results
    avg_response_time = statistics.mean([r['response_time'] for r in results])
    success_rate = sum(1 for r in results if r['success']) / len(results) * 100
    
    self.assertGreater(success_rate, 90)
    self.assertLess(avg_response_time, 500)
```

## 📊 Test Data Management

### Overview

Comprehensive test data management using Factory Boy and custom fixtures.

### Factory Classes

| Factory | Purpose | Usage |
|---------|---------|-------|
| `UserFactory` | Create users | `UserFactory()` |
| `PatientProfileFactory` | Create patients | `PatientProfileFactory()` |
| `DoctorProfileFactory` | Create doctors | `DoctorProfileFactory()` |
| `AppointmentFactory` | Create appointments | `AppointmentFactory()` |
| `InvoiceFactory` | Create invoices | `InvoiceFactory()` |

### Management Commands

```bash
# Create test data
python manage.py manage_test_data create_minimal
python manage.py manage_test_data create_comprehensive
python manage.py manage_test_data create_performance

# Environment seeding
python manage.py manage_test_data seed_development
python manage.py manage_test_data seed_demo

# Fixture management
python manage.py manage_test_data export_fixtures
python manage.py manage_test_data load_fixtures

# Data cleanup
python manage.py manage_test_data cleanup
python manage.py manage_test_data status
```

### Factory Usage Examples

```python
# Create single instances
user = UserFactory()
patient = PatientProfileFactory()
doctor = DoctorProfileFactory()

# Create batches
users = UserFactory.create_batch(10)
patients = PatientProfileFactory.create_batch(5)

# Build without saving
user = UserFactory.build()  # Not saved to database

# Custom attributes
admin = UserFactory(user_type='admin', is_staff=True)
emergency_patient = PatientProfileFactory(blood_type='O-')

# Related objects
appointment = AppointmentFactory(
    patient=patient,
    doctor=doctor,
    status='scheduled'
)
```

### Batch Data Creation

```python
from tests.factories import TestDataBatch

# Complete patient data (profile + contacts + insurance)
patients = TestDataBatch.create_complete_patient_data(count=5)

# Complete doctor data (profile + availability)
doctors = TestDataBatch.create_complete_doctor_data(count=3)

# Full appointment workflow
workflow_data = TestDataBatch.create_appointment_workflow_data()

# Hospital infrastructure
infrastructure = TestDataBatch.create_hospital_infrastructure()
```

## 📚 Best Practices

### General Testing Principles

1. **Test Pyramid**: More unit tests, fewer integration tests, minimal E2E tests
2. **Independence**: Tests should not depend on each other
3. **Repeatability**: Tests should produce consistent results
4. **Fast Execution**: Tests should run quickly
5. **Clear Assertions**: Use descriptive assertion messages

### Code Coverage

```bash
# Generate coverage report
python run_tests.py coverage

# View HTML report
open htmlcov/index.html

# Coverage targets
# - Unit tests: >90%
# - Integration tests: >80%
# - Overall: >85%
```

### Test Data Best Practices

1. **Use Factories**: Prefer factories over fixtures for flexibility
2. **Minimal Data**: Create only necessary data for each test
3. **Realistic Data**: Use Faker for realistic test data
4. **Cleanup**: Always clean up test data
5. **Isolation**: Each test should have its own data

### Performance Testing Best Practices

1. **Baseline**: Establish performance baselines
2. **Monitoring**: Monitor key metrics consistently
3. **Regression**: Test for performance regressions
4. **Environment**: Use consistent test environments
5. **Documentation**: Document performance requirements

### CI/CD Integration

```yaml
# Example GitHub Actions workflow
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.11
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
      - name: Run tests
        run: |
          python run_tests.py coverage
      - name: Upload coverage
        uses: codecov/codecov-action@v1
```

## 🔧 Troubleshooting

### Common Issues

#### Database Connection Errors
```bash
# Check database configuration
python manage.py check --database default

# Run migrations
python manage.py migrate

# Reset test database
python manage.py flush --verbosity=0 --noinput
```

#### Import Errors
```bash
# Check Python path
python -c "import sys; print(sys.path)"

# Verify Django settings
python manage.py check

# Check installed packages
pip list
```

#### Test Failures
```bash
# Run specific failing test
python manage.py test tests.test_models.UserModelTest.test_create_user --verbosity=2

# Debug with pdb
python manage.py test tests.test_models.UserModelTest.test_create_user --debug-mode

# Check test database
python manage.py dbshell --database test
```

#### Performance Issues
```bash
# Check system resources
python run_performance_tests.py validate

# Monitor memory usage
python -c "import psutil; print(f'Memory: {psutil.virtual_memory().percent}%')"

# Database performance
python manage.py dbshell
EXPLAIN ANALYZE SELECT * FROM auth_user;
```

### Getting Help

1. **Documentation**: Check this documentation first
2. **Logs**: Review test output and error messages
3. **Debug Mode**: Use `--verbosity=2` for detailed output
4. **Isolation**: Run individual tests to isolate issues
5. **Clean Environment**: Try with fresh test data

## 📈 Metrics and Reporting

### Test Metrics

- **Test Count**: Total number of tests
- **Coverage**: Code coverage percentage
- **Execution Time**: Test suite execution time
- **Success Rate**: Percentage of passing tests

### Performance Metrics

- **Response Time**: API endpoint response times
- **Throughput**: Requests per second
- **Memory Usage**: Memory consumption
- **Database Performance**: Query execution times

### Reporting

- **Console Output**: Real-time test results
- **HTML Reports**: Detailed coverage and performance reports
- **XML Reports**: CI/CD compatible reports
- **JSON Reports**: Machine-readable test results

---

## 📞 Support

For questions or issues with the testing framework:

1. Check this documentation
2. Review test output and logs
3. Run diagnostic commands
4. Check system requirements
5. Contact the development team

**Happy Testing! 🧪**

---

## 📖 Additional Documentation

- [Unit Testing Guide](unit-testing-guide.md) - Detailed unit testing practices
- [Integration Testing Guide](integration-testing-guide.md) - Integration testing workflows
- [Performance Testing Guide](performance-testing-guide.md) - Performance testing strategies
- [Test Data Management Guide](test-data-guide.md) - Test data creation and management
- [CI/CD Testing Guide](cicd-testing-guide.md) - Continuous integration setup
- [API Testing Guide](api-testing-guide.md) - API endpoint testing
- [Testing Cheat Sheet](testing-cheat-sheet.md) - Quick reference guide
