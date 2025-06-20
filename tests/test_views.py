"""
Unit tests for all views in the Hospital Management System
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from datetime import date, time, timedelta
from decimal import Decimal

from accounts.models import User
from patients.models import PatientProfile, EmergencyContact
from doctors.models import DoctorProfile, Specialization
from appointments.models import Appointment, AppointmentType
from medical_records.models import MedicalHistory, Prescription
from billing.models import Invoice, Payment
from notifications.models import EmailNotification, EmailTemplate

User = get_user_model()


class AuthenticationViewTest(APITestCase):
    """Test cases for authentication views"""
    
    def setUp(self):
        self.client = APIClient()
        self.register_url = reverse('accounts:register')
        self.login_url = reverse('accounts:login')
        self.user_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'SecurePass123!',
            'first_name': 'Test',
            'last_name': 'User',
            'user_type': 'patient'
        }
    
    def test_user_registration_success(self):
        """Test successful user registration"""
        response = self.client.post(self.register_url, self.user_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('id', response.data)
        self.assertEqual(response.data['username'], 'testuser')
        self.assertEqual(response.data['email'], 'test@example.com')
        self.assertNotIn('password', response.data)
    
    def test_user_registration_invalid_data(self):
        """Test user registration with invalid data"""
        invalid_data = self.user_data.copy()
        invalid_data['email'] = 'invalid-email'
        response = self.client.post(self.register_url, invalid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data)
    
    def test_user_registration_duplicate_username(self):
        """Test user registration with duplicate username"""
        # Create first user
        self.client.post(self.register_url, self.user_data, format='json')
        
        # Try to create second user with same username
        duplicate_data = self.user_data.copy()
        duplicate_data['email'] = 'different@example.com'
        response = self.client.post(self.register_url, duplicate_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('username', response.data)
    
    def test_user_login_success(self):
        """Test successful user login"""
        # Create user first
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='SecurePass123!',
            user_type='patient'
        )
        
        login_data = {
            'username': 'testuser',
            'password': 'SecurePass123!'
        }
        response = self.client.post(self.login_url, login_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertIn('user', response.data)
    
    def test_user_login_invalid_credentials(self):
        """Test user login with invalid credentials"""
        login_data = {
            'username': 'nonexistent',
            'password': 'wrongpassword'
        }
        response = self.client.post(self.login_url, login_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_protected_endpoint_without_token(self):
        """Test accessing protected endpoint without authentication"""
        url = reverse('accounts:profile')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_protected_endpoint_with_token(self):
        """Test accessing protected endpoint with valid token"""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='pass123',
            user_type='patient'
        )
        refresh = RefreshToken.for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
        
        url = reverse('accounts:profile')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], 'testuser')


class PatientViewTest(APITestCase):
    """Test cases for patient management views"""
    
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='patient1',
            email='patient1@example.com',
            password='pass123',
            user_type='patient'
        )
        refresh = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
        
        self.profile_data = {
            'date_of_birth': '1990-05-15',
            'gender': 'male',
            'phone_number': '+1234567890',
            'address': '123 Main St, City, State 12345',
            'blood_type': 'O+',
            'allergies': ['Penicillin', 'Shellfish']
        }
    
    def test_create_patient_profile(self):
        """Test creating patient profile"""
        url = reverse('patients:profile-list')
        response = self.client.post(url, self.profile_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['blood_type'], 'O+')
        self.assertEqual(response.data['gender'], 'male')
    
    def test_get_patient_profile(self):
        """Test retrieving patient profile"""
        profile = PatientProfile.objects.create(
            user=self.user,
            date_of_birth=date(1990, 5, 15),
            gender='male',
            blood_type='O+'
        )
        url = reverse('patients:profile-detail', kwargs={'pk': profile.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['blood_type'], 'O+')
    
    def test_update_patient_profile(self):
        """Test updating patient profile"""
        profile = PatientProfile.objects.create(
            user=self.user,
            date_of_birth=date(1990, 5, 15),
            gender='male',
            blood_type='O+'
        )
        url = reverse('patients:profile-detail', kwargs={'pk': profile.pk})
        update_data = {'blood_type': 'A+'}
        response = self.client.patch(url, update_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['blood_type'], 'A+')
    
    def test_create_emergency_contact(self):
        """Test creating emergency contact"""
        profile = PatientProfile.objects.create(
            user=self.user,
            date_of_birth=date(1990, 5, 15),
            gender='male'
        )
        url = reverse('patients:emergency-contact-list')
        contact_data = {
            'patient': profile.id,
            'name': 'Jane Doe',
            'relationship': 'spouse',
            'phone_number': '+1234567891',
            'email': 'jane@example.com'
        }
        response = self.client.post(url, contact_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'Jane Doe')


class DoctorViewTest(APITestCase):
    """Test cases for doctor management views"""
    
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='doctor1',
            email='doctor1@example.com',
            password='pass123',
            user_type='doctor'
        )
        refresh = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
        
        self.specialization = Specialization.objects.create(
            name='Cardiology',
            description='Heart and cardiovascular system'
        )
    
    def test_create_doctor_profile(self):
        """Test creating doctor profile"""
        url = reverse('doctors:profile-list')
        profile_data = {
            'license_number': 'MD123456',
            'specialization': self.specialization.id,
            'phone_number': '+1234567890',
            'years_of_experience': 10,
            'consultation_fee': '150.00'
        }
        response = self.client.post(url, profile_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['license_number'], 'MD123456')
    
    def test_get_specializations(self):
        """Test retrieving specializations"""
        url = reverse('doctors:specialization-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['name'], 'Cardiology')


class AppointmentViewTest(APITestCase):
    """Test cases for appointment management views"""
    
    def setUp(self):
        self.client = APIClient()
        
        # Create patient
        self.patient_user = User.objects.create_user(
            username='patient1', email='patient1@example.com', password='pass123', user_type='patient'
        )
        self.patient = PatientProfile.objects.create(
            user=self.patient_user,
            date_of_birth=date(1990, 5, 15),
            gender='male'
        )
        
        # Create doctor
        self.doctor_user = User.objects.create_user(
            username='doctor1', email='doctor1@example.com', password='pass123', user_type='doctor'
        )
        self.specialization = Specialization.objects.create(name='General Medicine')
        self.doctor = DoctorProfile.objects.create(
            user=self.doctor_user,
            license_number='MD123456',
            specialization=self.specialization
        )
        
        # Create appointment type
        self.appointment_type = AppointmentType.objects.create(
            name='Consultation',
            duration=30,
            price=Decimal('100.00')
        )
        
        # Authenticate as patient
        refresh = RefreshToken.for_user(self.patient_user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    
    def test_create_appointment(self):
        """Test creating an appointment"""
        url = reverse('appointments:appointment-list')
        future_date = date.today() + timedelta(days=1)
        appointment_data = {
            'doctor': self.doctor.id,
            'appointment_date': future_date.isoformat(),
            'appointment_time': '14:30:00',
            'appointment_type': self.appointment_type.id,
            'reason': 'Regular checkup'
        }
        response = self.client.post(url, appointment_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['reason'], 'Regular checkup')
    
    def test_get_appointments(self):
        """Test retrieving appointments"""
        appointment = Appointment.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            appointment_date=date.today() + timedelta(days=1),
            appointment_time=time(14, 30),
            appointment_type=self.appointment_type,
            reason='Regular checkup'
        )
        url = reverse('appointments:appointment-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
    
    def test_check_doctor_availability(self):
        """Test checking doctor availability"""
        url = reverse('appointments:availability')
        params = {
            'doctor': self.doctor.id,
            'date': (date.today() + timedelta(days=1)).isoformat()
        }
        response = self.client.get(url, params)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('available_slots', response.data)


class BillingViewTest(APITestCase):
    """Test cases for billing views"""
    
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='patient1',
            email='patient1@example.com',
            password='pass123',
            user_type='patient'
        )
        self.patient = PatientProfile.objects.create(
            user=self.user,
            date_of_birth=date(1990, 5, 15),
            gender='male'
        )
        refresh = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    
    def test_create_invoice(self):
        """Test creating an invoice"""
        url = reverse('billing:invoice-list')
        invoice_data = {
            'patient': self.patient.id,
            'amount': '150.00',
            'due_date': (date.today() + timedelta(days=30)).isoformat(),
            'description': 'Consultation fee'
        }
        response = self.client.post(url, invoice_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(float(response.data['amount']), 150.00)
    
    def test_process_payment(self):
        """Test processing a payment"""
        invoice = Invoice.objects.create(
            patient=self.patient,
            amount=Decimal('150.00'),
            due_date=date.today() + timedelta(days=30)
        )
        url = reverse('billing:payment-list')
        payment_data = {
            'invoice': invoice.id,
            'amount': '150.00',
            'payment_method': 'credit_card',
            'transaction_id': 'TXN123456'
        }
        response = self.client.post(url, payment_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['payment_method'], 'credit_card')


class NotificationViewTest(APITestCase):
    """Test cases for notification views"""
    
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='admin1',
            email='admin1@example.com',
            password='pass123',
            user_type='admin'
        )
        refresh = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    
    def test_create_email_template(self):
        """Test creating email template"""
        url = reverse('notifications:email-template-list')
        template_data = {
            'name': 'Appointment Reminder',
            'subject': 'Appointment Reminder - {{appointment_date}}',
            'html_content': '<p>Dear {{patient_name}}, your appointment is on {{appointment_date}}</p>',
            'text_content': 'Dear {{patient_name}}, your appointment is on {{appointment_date}}',
            'template_type': 'appointment_reminder'
        }
        response = self.client.post(url, template_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'Appointment Reminder')
    
    def test_send_email_notification(self):
        """Test sending email notification"""
        template = EmailTemplate.objects.create(
            name='Test Template',
            subject='Test Subject',
            html_content='<p>Test content</p>',
            text_content='Test content'
        )
        url = reverse('notifications:email-notification-list')
        notification_data = {
            'recipient_email': 'test@example.com',
            'subject': 'Test Email',
            'html_content': '<p>Test content</p>',
            'text_content': 'Test content',
            'template': template.id,
            'priority': 'normal'
        }
        response = self.client.post(url, notification_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['recipient_email'], 'test@example.com')
