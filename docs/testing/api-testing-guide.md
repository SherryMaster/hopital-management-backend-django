# API Testing Guide - Hospital Management System

## 🌐 Overview

This guide covers comprehensive API testing strategies for the Hospital Management System, including authentication, CRUD operations, error handling, and performance testing.

## 📋 Table of Contents

1. [API Testing Setup](#api-testing-setup)
2. [Authentication Testing](#authentication-testing)
3. [CRUD Operations Testing](#crud-operations-testing)
4. [Error Handling Testing](#error-handling-testing)
5. [Validation Testing](#validation-testing)
6. [Permission Testing](#permission-testing)
7. [Performance Testing](#performance-testing)
8. [Integration Testing](#integration-testing)

## 🚀 API Testing Setup

### Base Test Class

```python
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from django.urls import reverse
from django.contrib.auth import get_user_model

User = get_user_model()

class BaseAPITestCase(APITestCase):
    """Base class for API tests"""
    
    def setUp(self):
        self.client = APIClient()
        self.admin_user = User.objects.create_user(
            username='admin_test',
            email='admin@test.com',
            password='testpass123',
            user_type='admin',
            is_staff=True
        )
        self.patient_user = User.objects.create_user(
            username='patient_test',
            email='patient@test.com',
            password='testpass123',
            user_type='patient'
        )
        self.doctor_user = User.objects.create_user(
            username='doctor_test',
            email='doctor@test.com',
            password='testpass123',
            user_type='doctor'
        )
    
    def authenticate_user(self, user):
        """Authenticate a user and set authorization header"""
        refresh = RefreshToken.for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
        return refresh.access_token
    
    def remove_authentication(self):
        """Remove authentication credentials"""
        self.client.credentials()
```

### Test Data Setup

```python
from tests.factories import (
    PatientProfileFactory, DoctorProfileFactory, 
    AppointmentFactory, InvoiceFactory
)

class APITestWithData(BaseAPITestCase):
    """API test class with test data"""
    
    def setUp(self):
        super().setUp()
        self.patient_profile = PatientProfileFactory(user=self.patient_user)
        self.doctor_profile = DoctorProfileFactory(user=self.doctor_user)
        self.appointment = AppointmentFactory(
            patient=self.patient_profile,
            doctor=self.doctor_profile
        )
```

## 🔐 Authentication Testing

### JWT Token Testing

```python
class AuthenticationAPITest(BaseAPITestCase):
    """Test authentication endpoints"""
    
    def test_user_registration(self):
        """Test user registration endpoint"""
        url = reverse('accounts:register')
        data = {
            'username': 'newuser',
            'email': 'newuser@test.com',
            'password': 'SecurePass123!',
            'first_name': 'New',
            'last_name': 'User',
            'user_type': 'patient'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('id', response.data)
        self.assertEqual(response.data['username'], 'newuser')
        self.assertNotIn('password', response.data)
    
    def test_user_login(self):
        """Test user login endpoint"""
        url = reverse('accounts:login')
        data = {
            'username': 'patient_test',
            'password': 'testpass123'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertIn('user', response.data)
    
    def test_token_refresh(self):
        """Test token refresh endpoint"""
        # Get initial tokens
        refresh = RefreshToken.for_user(self.patient_user)
        
        url = reverse('accounts:token_refresh')
        data = {'refresh': str(refresh)}
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
    
    def test_protected_endpoint_without_auth(self):
        """Test accessing protected endpoint without authentication"""
        url = reverse('accounts:profile')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_protected_endpoint_with_auth(self):
        """Test accessing protected endpoint with authentication"""
        self.authenticate_user(self.patient_user)
        
        url = reverse('accounts:profile')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], 'patient_test')
    
    def test_invalid_credentials(self):
        """Test login with invalid credentials"""
        url = reverse('accounts:login')
        data = {
            'username': 'patient_test',
            'password': 'wrongpassword'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_expired_token(self):
        """Test using expired token"""
        # This would require mocking time or using a very short token lifetime
        pass
```

## 📝 CRUD Operations Testing

### Patient Profile CRUD

```python
class PatientProfileAPITest(APITestWithData):
    """Test patient profile CRUD operations"""
    
    def test_create_patient_profile(self):
        """Test creating patient profile"""
        self.authenticate_user(self.patient_user)
        
        url = reverse('patients:profile-list')
        data = {
            'date_of_birth': '1990-05-15',
            'gender': 'male',
            'phone_number': '+1234567890',
            'address': '123 Main St, City, State 12345',
            'blood_type': 'O+',
            'allergies': ['Penicillin', 'Shellfish']
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['blood_type'], 'O+')
        self.assertEqual(response.data['gender'], 'male')
    
    def test_get_patient_profile(self):
        """Test retrieving patient profile"""
        self.authenticate_user(self.patient_user)
        
        url = reverse('patients:profile-detail', kwargs={'pk': self.patient_profile.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.patient_profile.id)
    
    def test_update_patient_profile(self):
        """Test updating patient profile"""
        self.authenticate_user(self.patient_user)
        
        url = reverse('patients:profile-detail', kwargs={'pk': self.patient_profile.pk})
        data = {'blood_type': 'A+'}
        
        response = self.client.patch(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['blood_type'], 'A+')
    
    def test_delete_patient_profile(self):
        """Test deleting patient profile"""
        self.authenticate_user(self.admin_user)
        
        url = reverse('patients:profile-detail', kwargs={'pk': self.patient_profile.pk})
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
    
    def test_list_patient_profiles(self):
        """Test listing patient profiles"""
        self.authenticate_user(self.admin_user)
        
        url = reverse('patients:profile-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
        self.assertIn('count', response.data)
```

### Appointment CRUD

```python
class AppointmentAPITest(APITestWithData):
    """Test appointment CRUD operations"""
    
    def test_create_appointment(self):
        """Test creating an appointment"""
        self.authenticate_user(self.patient_user)
        
        url = reverse('appointments:appointment-list')
        future_date = (datetime.now() + timedelta(days=1)).date()
        data = {
            'doctor': self.doctor_profile.id,
            'appointment_date': future_date.isoformat(),
            'appointment_time': '14:30:00',
            'appointment_type': self.appointment.appointment_type.id,
            'reason': 'Regular checkup'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['reason'], 'Regular checkup')
        self.assertEqual(response.data['status'], 'scheduled')
    
    def test_get_appointment(self):
        """Test retrieving appointment"""
        self.authenticate_user(self.patient_user)
        
        url = reverse('appointments:appointment-detail', kwargs={'pk': self.appointment.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.appointment.id)
    
    def test_update_appointment_status(self):
        """Test updating appointment status"""
        self.authenticate_user(self.doctor_user)
        
        url = reverse('appointments:appointment-detail', kwargs={'pk': self.appointment.pk})
        data = {'status': 'completed'}
        
        response = self.client.patch(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'completed')
    
    def test_cancel_appointment(self):
        """Test canceling appointment"""
        self.authenticate_user(self.patient_user)
        
        url = reverse('appointments:appointment-detail', kwargs={'pk': self.appointment.pk})
        data = {'status': 'cancelled'}
        
        response = self.client.patch(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'cancelled')
```

## ❌ Error Handling Testing

### HTTP Error Codes

```python
class ErrorHandlingAPITest(APITestWithData):
    """Test API error handling"""
    
    def test_404_not_found(self):
        """Test 404 error for non-existent resource"""
        self.authenticate_user(self.patient_user)
        
        url = reverse('patients:profile-detail', kwargs={'pk': 99999})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn('detail', response.data)
    
    def test_400_bad_request(self):
        """Test 400 error for invalid data"""
        self.authenticate_user(self.patient_user)
        
        url = reverse('patients:profile-list')
        data = {
            'date_of_birth': 'invalid-date',
            'gender': 'invalid-gender'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('date_of_birth', response.data)
        self.assertIn('gender', response.data)
    
    def test_401_unauthorized(self):
        """Test 401 error for unauthenticated request"""
        url = reverse('patients:profile-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_403_forbidden(self):
        """Test 403 error for insufficient permissions"""
        self.authenticate_user(self.patient_user)
        
        # Try to access admin-only endpoint
        url = reverse('admin:user-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_405_method_not_allowed(self):
        """Test 405 error for unsupported HTTP method"""
        self.authenticate_user(self.patient_user)
        
        url = reverse('patients:profile-detail', kwargs={'pk': self.patient_profile.pk})
        response = self.client.put(url)  # If PUT is not allowed
        
        # This depends on your API design
        # self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
```

## ✅ Validation Testing

### Field Validation

```python
class ValidationAPITest(BaseAPITestCase):
    """Test API validation"""
    
    def test_required_fields(self):
        """Test required field validation"""
        self.authenticate_user(self.patient_user)
        
        url = reverse('patients:profile-list')
        data = {}  # Missing required fields
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        # Check for specific required fields
        required_fields = ['date_of_birth', 'gender']
        for field in required_fields:
            self.assertIn(field, response.data)
    
    def test_email_validation(self):
        """Test email format validation"""
        url = reverse('accounts:register')
        data = {
            'username': 'testuser',
            'email': 'invalid-email',
            'password': 'SecurePass123!',
            'user_type': 'patient'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data)
    
    def test_unique_constraint_validation(self):
        """Test unique constraint validation"""
        # Create first user
        url = reverse('accounts:register')
        data = {
            'username': 'uniqueuser',
            'email': 'unique@test.com',
            'password': 'SecurePass123!',
            'user_type': 'patient'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Try to create second user with same username
        data['email'] = 'different@test.com'
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('username', response.data)
    
    def test_date_validation(self):
        """Test date field validation"""
        self.authenticate_user(self.patient_user)
        
        url = reverse('patients:profile-list')
        data = {
            'date_of_birth': '2030-01-01',  # Future date
            'gender': 'male'
        }
        
        response = self.client.post(url, data, format='json')
        
        # Depending on your validation logic
        # self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        # self.assertIn('date_of_birth', response.data)
```

## 🔒 Permission Testing

### Role-Based Access Control

```python
class PermissionAPITest(APITestWithData):
    """Test API permissions"""
    
    def test_patient_can_access_own_profile(self):
        """Test patient can access their own profile"""
        self.authenticate_user(self.patient_user)
        
        url = reverse('patients:profile-detail', kwargs={'pk': self.patient_profile.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_patient_cannot_access_other_profile(self):
        """Test patient cannot access another patient's profile"""
        other_patient = PatientProfileFactory()
        self.authenticate_user(self.patient_user)
        
        url = reverse('patients:profile-detail', kwargs={'pk': other_patient.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_doctor_can_access_patient_profiles(self):
        """Test doctor can access patient profiles"""
        self.authenticate_user(self.doctor_user)
        
        url = reverse('patients:profile-detail', kwargs={'pk': self.patient_profile.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_admin_can_access_all_profiles(self):
        """Test admin can access all profiles"""
        self.authenticate_user(self.admin_user)
        
        url = reverse('patients:profile-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_patient_cannot_delete_profile(self):
        """Test patient cannot delete profiles"""
        self.authenticate_user(self.patient_user)
        
        url = reverse('patients:profile-detail', kwargs={'pk': self.patient_profile.pk})
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
```

## ⚡ Performance Testing

### Response Time Testing

```python
import time
from concurrent.futures import ThreadPoolExecutor

class APIPerformanceTest(APITestWithData):
    """Test API performance"""
    
    def test_response_time(self):
        """Test API response time"""
        self.authenticate_user(self.patient_user)
        
        url = reverse('patients:profile-list')
        
        start_time = time.time()
        response = self.client.get(url)
        end_time = time.time()
        
        response_time = (end_time - start_time) * 1000  # milliseconds
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertLess(response_time, 200)  # Should be under 200ms
    
    def test_concurrent_requests(self):
        """Test concurrent API requests"""
        self.authenticate_user(self.patient_user)
        
        url = reverse('patients:profile-list')
        
        def make_request():
            return self.client.get(url)
        
        # Make 10 concurrent requests
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_request) for _ in range(10)]
            responses = [future.result() for future in futures]
        
        # All requests should succeed
        success_count = sum(1 for r in responses if r.status_code == 200)
        self.assertEqual(success_count, 10)
    
    def test_pagination_performance(self):
        """Test pagination performance with large datasets"""
        # Create many records
        PatientProfileFactory.create_batch(100)
        
        self.authenticate_user(self.admin_user)
        
        url = reverse('patients:profile-list')
        
        start_time = time.time()
        response = self.client.get(url)
        end_time = time.time()
        
        response_time = (end_time - start_time) * 1000
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
        self.assertIn('count', response.data)
        self.assertLess(response_time, 500)  # Should be under 500ms
```

## 🔗 Integration Testing

### End-to-End Workflows

```python
class APIIntegrationTest(BaseAPITestCase):
    """Test complete API workflows"""
    
    def test_complete_patient_registration_workflow(self):
        """Test complete patient registration and profile creation"""
        
        # Step 1: Register user
        register_url = reverse('accounts:register')
        register_data = {
            'username': 'newpatient',
            'email': 'newpatient@test.com',
            'password': 'SecurePass123!',
            'first_name': 'New',
            'last_name': 'Patient',
            'user_type': 'patient'
        }
        
        response = self.client.post(register_url, register_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user_id = response.data['id']
        
        # Step 2: Login
        login_url = reverse('accounts:login')
        login_data = {
            'username': 'newpatient',
            'password': 'SecurePass123!'
        }
        
        response = self.client.post(login_url, login_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        access_token = response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        
        # Step 3: Create profile
        profile_url = reverse('patients:profile-list')
        profile_data = {
            'date_of_birth': '1990-05-15',
            'gender': 'female',
            'phone_number': '+1234567890',
            'blood_type': 'A+'
        }
        
        response = self.client.post(profile_url, profile_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Step 4: Verify profile
        profile_id = response.data['id']
        profile_detail_url = reverse('patients:profile-detail', kwargs={'pk': profile_id})
        response = self.client.get(profile_detail_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['blood_type'], 'A+')
    
    def test_appointment_booking_workflow(self):
        """Test complete appointment booking workflow"""
        
        # Setup: Create patient and doctor
        patient_profile = PatientProfileFactory(user=self.patient_user)
        doctor_profile = DoctorProfileFactory(user=self.doctor_user)
        appointment_type = AppointmentTypeFactory()
        
        self.authenticate_user(self.patient_user)
        
        # Step 1: Check doctor availability
        availability_url = reverse('appointments:availability')
        future_date = (datetime.now() + timedelta(days=1)).date()
        params = {
            'doctor': doctor_profile.id,
            'date': future_date.isoformat()
        }
        
        response = self.client.get(availability_url, params)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Step 2: Book appointment
        appointment_url = reverse('appointments:appointment-list')
        appointment_data = {
            'doctor': doctor_profile.id,
            'appointment_date': future_date.isoformat(),
            'appointment_time': '14:30:00',
            'appointment_type': appointment_type.id,
            'reason': 'Regular checkup'
        }
        
        response = self.client.post(appointment_url, appointment_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        appointment_id = response.data['id']
        
        # Step 3: Verify appointment
        appointment_detail_url = reverse('appointments:appointment-detail', kwargs={'pk': appointment_id})
        response = self.client.get(appointment_detail_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'scheduled')
```

---

**API Testing Complete! 🌐**
