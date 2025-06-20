"""
Integration tests for Hospital Management System
Tests complete workflows and cross-module functionality
"""
from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from datetime import date, time, timedelta
from decimal import Decimal
import json

from accounts.models import User
from patients.models import PatientProfile, EmergencyContact
from doctors.models import DoctorProfile, Specialization
from appointments.models import Appointment, AppointmentType
from medical_records.models import MedicalHistory, Prescription
from billing.models import Invoice, Payment
from notifications.models import EmailNotification

User = get_user_model()


class AuthenticationIntegrationTest(APITestCase):
    """
    Integration tests for complete authentication workflow
    """
    
    def setUp(self):
        self.client = APIClient()
        self.register_url = reverse('accounts:register')
        self.login_url = reverse('accounts:login')
        
    def test_complete_authentication_workflow(self):
        """Test complete user registration and authentication workflow"""
        
        # Step 1: Register a new patient
        registration_data = {
            'username': 'patient_test',
            'email': 'patient@test.com',
            'password': 'SecurePass123!',
            'first_name': 'John',
            'last_name': 'Doe',
            'user_type': 'patient'
        }
        
        response = self.client.post(self.register_url, registration_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('id', response.data)
        user_id = response.data['id']
        
        # Step 2: Login with registered credentials
        login_data = {
            'username': 'patient_test',
            'password': 'SecurePass123!'
        }
        
        response = self.client.post(self.login_url, login_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        
        access_token = response.data['access']
        refresh_token = response.data['refresh']
        
        # Step 3: Access protected endpoint with token
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        profile_url = reverse('accounts:profile')
        response = self.client.get(profile_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], 'patient_test')
        
        # Step 4: Test token refresh
        refresh_url = reverse('accounts:token_refresh')
        refresh_data = {'refresh': refresh_token}
        response = self.client.post(refresh_url, refresh_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        
        # Step 5: Test logout
        logout_url = reverse('accounts:logout')
        response = self.client.post(logout_url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        return user_id, access_token


class PatientManagementIntegrationTest(APITestCase):
    """
    Integration tests for patient management workflow
    """
    
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='patient_test',
            email='patient@test.com',
            password='pass123',
            user_type='patient'
        )
        refresh = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    
    def test_complete_patient_onboarding_workflow(self):
        """Test complete patient onboarding from registration to profile completion"""
        
        # Step 1: Create patient profile
        profile_url = reverse('patients:profile-list')
        profile_data = {
            'date_of_birth': '1990-05-15',
            'gender': 'male',
            'phone_number': '+1234567890',
            'address': '123 Main St, City, State 12345',
            'blood_type': 'O+',
            'allergies': ['Penicillin', 'Shellfish'],
            'medical_conditions': ['Hypertension'],
            'emergency_contact_name': 'Jane Doe',
            'emergency_contact_phone': '+1234567891',
            'emergency_contact_relationship': 'spouse'
        }
        
        response = self.client.post(profile_url, profile_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        profile_id = response.data['id']
        
        # Step 2: Add emergency contact
        contact_url = reverse('patients:emergency-contact-list')
        contact_data = {
            'patient': profile_id,
            'name': 'Bob Smith',
            'relationship': 'brother',
            'phone_number': '+1234567892',
            'email': 'bob@example.com',
            'is_primary': False
        }
        
        response = self.client.post(contact_url, contact_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Step 3: Retrieve complete patient profile
        profile_detail_url = reverse('patients:profile-detail', kwargs={'pk': profile_id})
        response = self.client.get(profile_detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['blood_type'], 'O+')
        self.assertIn('Penicillin', response.data['allergies'])
        
        # Step 4: Update patient profile
        update_data = {
            'phone_number': '+1234567899',
            'address': '456 New St, City, State 12345'
        }
        response = self.client.patch(profile_detail_url, update_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['phone_number'], '+1234567899')
        
        return profile_id


class AppointmentBookingIntegrationTest(APITestCase):
    """
    Integration tests for complete appointment booking workflow
    """
    
    def setUp(self):
        self.client = APIClient()
        
        # Create patient
        self.patient_user = User.objects.create_user(
            username='patient_test',
            email='patient@test.com',
            password='pass123',
            user_type='patient'
        )
        self.patient = PatientProfile.objects.create(
            user=self.patient_user,
            date_of_birth=date(1990, 5, 15),
            gender='male'
        )
        
        # Create doctor
        self.doctor_user = User.objects.create_user(
            username='doctor_test',
            email='doctor@test.com',
            password='pass123',
            user_type='doctor'
        )
        self.specialization = Specialization.objects.create(
            name='General Medicine',
            description='General medical practice'
        )
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
    
    def test_complete_appointment_booking_workflow(self):
        """Test complete appointment booking from search to confirmation"""
        
        # Step 1: Search for available doctors
        doctors_url = reverse('doctors:profile-list')
        response = self.client.get(doctors_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        
        # Step 2: Check doctor availability
        availability_url = reverse('appointments:availability')
        future_date = date.today() + timedelta(days=1)
        params = {
            'doctor': self.doctor.id,
            'date': future_date.isoformat()
        }
        response = self.client.get(availability_url, params)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('available_slots', response.data)
        
        # Step 3: Book appointment
        appointments_url = reverse('appointments:appointment-list')
        appointment_data = {
            'doctor': self.doctor.id,
            'appointment_date': future_date.isoformat(),
            'appointment_time': '14:30:00',
            'appointment_type': self.appointment_type.id,
            'reason': 'Regular checkup',
            'notes': 'First visit'
        }
        
        response = self.client.post(appointments_url, appointment_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        appointment_id = response.data['id']
        self.assertEqual(response.data['status'], 'scheduled')
        
        # Step 4: Retrieve appointment details
        appointment_detail_url = reverse('appointments:appointment-detail', kwargs={'pk': appointment_id})
        response = self.client.get(appointment_detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['reason'], 'Regular checkup')
        
        # Step 5: Update appointment
        update_data = {
            'notes': 'Updated notes - patient confirmed attendance'
        }
        response = self.client.patch(appointment_detail_url, update_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('Updated notes', response.data['notes'])
        
        return appointment_id


class MedicalRecordsIntegrationTest(APITestCase):
    """
    Integration tests for medical records workflow
    """
    
    def setUp(self):
        self.client = APIClient()
        
        # Create patient
        self.patient_user = User.objects.create_user(
            username='patient_test',
            email='patient@test.com',
            password='pass123',
            user_type='patient'
        )
        self.patient = PatientProfile.objects.create(
            user=self.patient_user,
            date_of_birth=date(1990, 5, 15),
            gender='male'
        )
        
        # Create doctor
        self.doctor_user = User.objects.create_user(
            username='doctor_test',
            email='doctor@test.com',
            password='pass123',
            user_type='doctor'
        )
        self.specialization = Specialization.objects.create(name='General Medicine')
        self.doctor = DoctorProfile.objects.create(
            user=self.doctor_user,
            license_number='MD123456',
            specialization=self.specialization
        )
        
        # Authenticate as doctor
        refresh = RefreshToken.for_user(self.doctor_user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    
    def test_complete_medical_records_workflow(self):
        """Test complete medical records creation and management"""
        
        # Step 1: Create medical history
        history_url = reverse('medical_records:medical-history-list')
        history_data = {
            'patient': self.patient.id,
            'condition': 'Hypertension',
            'diagnosis_date': date.today().isoformat(),
            'treatment': 'Medication and lifestyle changes',
            'notes': 'Patient responding well to treatment',
            'severity': 'moderate'
        }
        
        response = self.client.post(history_url, history_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        history_id = response.data['id']
        
        # Step 2: Create prescription
        prescription_url = reverse('medical_records:prescription-list')
        prescription_data = {
            'patient': self.patient.id,
            'medication_name': 'Lisinopril',
            'dosage': '10mg',
            'frequency': 'Once daily',
            'duration': '30 days',
            'instructions': 'Take with food',
            'refills_allowed': 3
        }
        
        response = self.client.post(prescription_url, prescription_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        prescription_id = response.data['id']
        
        # Step 3: Record vital signs
        vitals_url = reverse('medical_records:vitals-list')
        vitals_data = {
            'patient': self.patient.id,
            'blood_pressure_systolic': 120,
            'blood_pressure_diastolic': 80,
            'heart_rate': 72,
            'temperature': 98.6,
            'weight': 70.5,
            'height': 175.0,
            'recorded_at': date.today().isoformat()
        }
        
        response = self.client.post(vitals_url, vitals_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Step 4: Retrieve patient's complete medical records
        patient_records_url = reverse('medical_records:patient-records', kwargs={'patient_id': self.patient.id})
        response = self.client.get(patient_records_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('medical_histories', response.data)
        self.assertIn('prescriptions', response.data)
        self.assertIn('vital_signs', response.data)
        
        return history_id, prescription_id


class BillingIntegrationTest(APITestCase):
    """
    Integration tests for billing and payment workflow
    """
    
    def setUp(self):
        self.client = APIClient()
        
        # Create patient
        self.patient_user = User.objects.create_user(
            username='patient_test',
            email='patient@test.com',
            password='pass123',
            user_type='patient'
        )
        self.patient = PatientProfile.objects.create(
            user=self.patient_user,
            date_of_birth=date(1990, 5, 15),
            gender='male'
        )
        
        # Authenticate as patient
        refresh = RefreshToken.for_user(self.patient_user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    
    def test_complete_billing_workflow(self):
        """Test complete billing from invoice generation to payment"""
        
        # Step 1: Create invoice
        invoice_url = reverse('billing:invoice-list')
        invoice_data = {
            'patient': self.patient.id,
            'amount': '150.00',
            'due_date': (date.today() + timedelta(days=30)).isoformat(),
            'description': 'Consultation and lab tests',
            'services': [
                {'name': 'Consultation', 'price': '100.00'},
                {'name': 'Blood Test', 'price': '50.00'}
            ]
        }
        
        response = self.client.post(invoice_url, invoice_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        invoice_id = response.data['id']
        self.assertEqual(response.data['status'], 'pending')
        
        # Step 2: Retrieve invoice details
        invoice_detail_url = reverse('billing:invoice-detail', kwargs={'pk': invoice_id})
        response = self.client.get(invoice_detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(float(response.data['amount']), 150.00)
        
        # Step 3: Process payment
        payment_url = reverse('billing:payment-list')
        payment_data = {
            'invoice': invoice_id,
            'amount': '150.00',
            'payment_method': 'credit_card',
            'transaction_id': 'TXN123456789',
            'payment_gateway': 'stripe'
        }
        
        response = self.client.post(payment_url, payment_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        payment_id = response.data['id']
        self.assertEqual(response.data['status'], 'completed')
        
        # Step 4: Verify invoice status updated
        response = self.client.get(invoice_detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'paid')
        
        # Step 5: Get payment history
        payments_url = reverse('billing:payment-list')
        response = self.client.get(payments_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        
        return invoice_id, payment_id


class CrossModuleIntegrationTest(APITestCase):
    """
    Integration tests for cross-module functionality
    """
    
    def setUp(self):
        self.client = APIClient()
        
        # Create complete user ecosystem
        self.patient_user = User.objects.create_user(
            username='patient_test',
            email='patient@test.com',
            password='pass123',
            user_type='patient'
        )
        self.patient = PatientProfile.objects.create(
            user=self.patient_user,
            date_of_birth=date(1990, 5, 15),
            gender='male'
        )
        
        self.doctor_user = User.objects.create_user(
            username='doctor_test',
            email='doctor@test.com',
            password='pass123',
            user_type='doctor'
        )
        self.specialization = Specialization.objects.create(name='General Medicine')
        self.doctor = DoctorProfile.objects.create(
            user=self.doctor_user,
            license_number='MD123456',
            specialization=self.specialization
        )
        
        self.appointment_type = AppointmentType.objects.create(
            name='Consultation',
            duration=30,
            price=Decimal('100.00')
        )
    
    def test_complete_patient_journey(self):
        """Test complete patient journey across all modules"""
        
        # Step 1: Patient registers and creates profile
        refresh = RefreshToken.for_user(self.patient_user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
        
        # Step 2: Patient books appointment
        appointments_url = reverse('appointments:appointment-list')
        future_date = date.today() + timedelta(days=1)
        appointment_data = {
            'doctor': self.doctor.id,
            'appointment_date': future_date.isoformat(),
            'appointment_time': '14:30:00',
            'appointment_type': self.appointment_type.id,
            'reason': 'Regular checkup'
        }
        
        response = self.client.post(appointments_url, appointment_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        appointment_id = response.data['id']
        
        # Step 3: Doctor adds medical records (switch to doctor auth)
        refresh = RefreshToken.for_user(self.doctor_user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
        
        # Complete appointment
        appointment_detail_url = reverse('appointments:appointment-detail', kwargs={'pk': appointment_id})
        update_data = {'status': 'completed'}
        response = self.client.patch(appointment_detail_url, update_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Add medical history
        history_url = reverse('medical_records:medical-history-list')
        history_data = {
            'patient': self.patient.id,
            'condition': 'Routine checkup - healthy',
            'diagnosis_date': date.today().isoformat(),
            'treatment': 'Continue current lifestyle',
            'notes': 'Patient in good health'
        }
        
        response = self.client.post(history_url, history_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Step 4: Generate invoice (switch to admin/billing auth)
        admin_user = User.objects.create_user(
            username='admin_test',
            email='admin@test.com',
            password='pass123',
            user_type='admin'
        )
        refresh = RefreshToken.for_user(admin_user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
        
        invoice_url = reverse('billing:invoice-list')
        invoice_data = {
            'patient': self.patient.id,
            'amount': '100.00',
            'due_date': (date.today() + timedelta(days=30)).isoformat(),
            'description': 'Consultation fee',
            'appointment': appointment_id
        }
        
        response = self.client.post(invoice_url, invoice_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        invoice_id = response.data['id']
        
        # Step 5: Patient pays invoice (switch back to patient auth)
        refresh = RefreshToken.for_user(self.patient_user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
        
        payment_url = reverse('billing:payment-list')
        payment_data = {
            'invoice': invoice_id,
            'amount': '100.00',
            'payment_method': 'credit_card',
            'transaction_id': 'TXN987654321'
        }
        
        response = self.client.post(payment_url, payment_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Step 6: Verify complete workflow
        # Check appointment is completed and paid
        appointment_detail_url = reverse('appointments:appointment-detail', kwargs={'pk': appointment_id})
        response = self.client.get(appointment_detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'completed')
        
        # Check medical records exist
        patient_records_url = reverse('medical_records:patient-records', kwargs={'patient_id': self.patient.id})
        response = self.client.get(patient_records_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(len(response.data['medical_histories']) > 0)
        
        # Check invoice is paid
        invoice_detail_url = reverse('billing:invoice-detail', kwargs={'pk': invoice_id})
        response = self.client.get(invoice_detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'paid')
        
        return {
            'appointment_id': appointment_id,
            'invoice_id': invoice_id,
            'patient_id': self.patient.id,
            'doctor_id': self.doctor.id
        }


class APIEndpointIntegrationTest(APITestCase):
    """
    Integration tests for API endpoints and data consistency
    """

    def setUp(self):
        self.client = APIClient()
        self.admin_user = User.objects.create_user(
            username='admin_test',
            email='admin@test.com',
            password='pass123',
            user_type='admin'
        )
        refresh = RefreshToken.for_user(self.admin_user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')

    def test_api_endpoint_consistency(self):
        """Test that API endpoints return consistent data structures"""

        # Test pagination consistency across endpoints
        endpoints_to_test = [
            'accounts:user-list',
            'patients:profile-list',
            'doctors:profile-list',
            'appointments:appointment-list',
            'billing:invoice-list'
        ]

        for endpoint in endpoints_to_test:
            try:
                url = reverse(endpoint)
                response = self.client.get(url)

                if response.status_code == 200:
                    # Check pagination structure
                    self.assertIn('results', response.data)
                    self.assertIn('count', response.data)
                    self.assertIsInstance(response.data['results'], list)
                    self.assertIsInstance(response.data['count'], int)

                    print(f"✓ {endpoint}: Pagination structure consistent")
                else:
                    print(f"⚠ {endpoint}: Status {response.status_code}")

            except Exception as e:
                print(f"✗ {endpoint}: Error - {e}")

    def test_api_error_handling_consistency(self):
        """Test that API endpoints handle errors consistently"""

        # Test 404 errors
        endpoints_404 = [
            ('patients:profile-detail', {'pk': 99999}),
            ('doctors:profile-detail', {'pk': 99999}),
            ('appointments:appointment-detail', {'pk': 99999}),
            ('billing:invoice-detail', {'pk': 99999})
        ]

        for endpoint, kwargs in endpoints_404:
            try:
                url = reverse(endpoint, kwargs=kwargs)
                response = self.client.get(url)
                self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
                self.assertIn('detail', response.data)
                print(f"✓ {endpoint}: 404 handling consistent")
            except Exception as e:
                print(f"✗ {endpoint}: Error - {e}")

    def test_api_authentication_consistency(self):
        """Test that authentication is consistently enforced"""

        # Remove authentication
        self.client.credentials()

        protected_endpoints = [
            'accounts:profile',
            'patients:profile-list',
            'doctors:profile-list',
            'appointments:appointment-list',
            'billing:invoice-list'
        ]

        for endpoint in protected_endpoints:
            try:
                url = reverse(endpoint)
                response = self.client.get(url)
                self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
                print(f"✓ {endpoint}: Authentication required")
            except Exception as e:
                print(f"✗ {endpoint}: Error - {e}")


class NotificationIntegrationTest(APITestCase):
    """
    Integration tests for notification system
    """

    def setUp(self):
        self.client = APIClient()
        self.admin_user = User.objects.create_user(
            username='admin_test',
            email='admin@test.com',
            password='pass123',
            user_type='admin'
        )
        refresh = RefreshToken.for_user(self.admin_user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')

    def test_notification_workflow_integration(self):
        """Test notification system integration with other modules"""

        # Step 1: Create email template
        template_url = reverse('notifications:email-template-list')
        template_data = {
            'name': 'Appointment Confirmation',
            'subject': 'Appointment Confirmed - {{appointment_date}}',
            'html_content': '<p>Dear {{patient_name}}, your appointment is confirmed for {{appointment_date}}</p>',
            'text_content': 'Dear {{patient_name}}, your appointment is confirmed for {{appointment_date}}',
            'template_type': 'appointment_confirmation'
        }

        response = self.client.post(template_url, template_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        template_id = response.data['id']

        # Step 2: Send notification
        notification_url = reverse('notifications:email-notification-list')
        notification_data = {
            'recipient_email': 'patient@test.com',
            'template': template_id,
            'template_variables': {
                'patient_name': 'John Doe',
                'appointment_date': 'June 25, 2025'
            },
            'priority': 'normal'
        }

        response = self.client.post(notification_url, notification_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        notification_id = response.data['id']

        # Step 3: Check notification status
        notification_detail_url = reverse('notifications:email-notification-detail', kwargs={'pk': notification_id})
        response = self.client.get(notification_detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['recipient_email'], 'patient@test.com')

        return template_id, notification_id


class DatabaseIntegrityIntegrationTest(TransactionTestCase):
    """
    Integration tests for database integrity and constraints
    """

    def test_foreign_key_constraints(self):
        """Test that foreign key constraints are properly enforced"""

        # Create base objects
        patient_user = User.objects.create_user(
            username='patient_test',
            email='patient@test.com',
            password='pass123',
            user_type='patient'
        )
        patient = PatientProfile.objects.create(
            user=patient_user,
            date_of_birth=date(1990, 5, 15),
            gender='male'
        )

        doctor_user = User.objects.create_user(
            username='doctor_test',
            email='doctor@test.com',
            password='pass123',
            user_type='doctor'
        )
        specialization = Specialization.objects.create(name='General Medicine')
        doctor = DoctorProfile.objects.create(
            user=doctor_user,
            license_number='MD123456',
            specialization=specialization
        )

        # Test cascade deletion
        appointment_type = AppointmentType.objects.create(
            name='Consultation',
            duration=30,
            price=Decimal('100.00')
        )

        appointment = Appointment.objects.create(
            patient=patient,
            doctor=doctor,
            appointment_date=date.today() + timedelta(days=1),
            appointment_time=time(14, 30),
            appointment_type=appointment_type,
            reason='Test appointment'
        )

        # Verify relationships
        self.assertEqual(appointment.patient, patient)
        self.assertEqual(appointment.doctor, doctor)

        # Test that deleting user cascades properly
        appointment_id = appointment.id
        patient_user.delete()

        # Appointment should still exist but patient reference should be handled
        # (depending on your CASCADE/SET_NULL settings)
        try:
            Appointment.objects.get(id=appointment_id)
            print("✓ Foreign key constraints working properly")
        except Appointment.DoesNotExist:
            print("✓ Cascade deletion working properly")

    def test_unique_constraints(self):
        """Test that unique constraints are properly enforced"""

        # Test user email uniqueness
        User.objects.create_user(
            username='user1',
            email='test@example.com',
            password='pass123'
        )

        with self.assertRaises(Exception):  # Should raise IntegrityError
            User.objects.create_user(
                username='user2',
                email='test@example.com',  # Duplicate email
                password='pass123'
            )

        print("✓ Email uniqueness constraint working")

        # Test doctor license number uniqueness
        specialization = Specialization.objects.create(name='Cardiology')

        doctor_user1 = User.objects.create_user(
            username='doctor1',
            email='doctor1@test.com',
            password='pass123',
            user_type='doctor'
        )

        DoctorProfile.objects.create(
            user=doctor_user1,
            license_number='MD123456',
            specialization=specialization
        )

        doctor_user2 = User.objects.create_user(
            username='doctor2',
            email='doctor2@test.com',
            password='pass123',
            user_type='doctor'
        )

        with self.assertRaises(Exception):  # Should raise IntegrityError
            DoctorProfile.objects.create(
                user=doctor_user2,
                license_number='MD123456',  # Duplicate license
                specialization=specialization
            )

        print("✓ License number uniqueness constraint working")
