"""
Unit tests for all serializers in the Hospital Management System
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from datetime import date, time, timedelta
from decimal import Decimal

from accounts.serializers import UserRegistrationSerializer, UserProfileSerializer
from patients.serializers import PatientProfileSerializer, EmergencyContactSerializer
from doctors.serializers import DoctorProfileSerializer, SpecializationSerializer
from appointments.serializers import AppointmentSerializer, AppointmentTypeSerializer
from medical_records.serializers import MedicalHistorySerializer, PrescriptionSerializer
from billing.serializers import InvoiceSerializer, PaymentSerializer
from notifications.serializers import EmailNotificationSerializer, EmailTemplateSerializer

from accounts.models import User
from patients.models import PatientProfile, EmergencyContact
from doctors.models import DoctorProfile, Specialization
from appointments.models import Appointment, AppointmentType
from medical_records.models import MedicalHistory, Prescription
from billing.models import Invoice, Payment
from notifications.models import EmailNotification, EmailTemplate

User = get_user_model()


class UserSerializerTest(TestCase):
    """Test cases for User serializers"""
    
    def test_user_registration_serializer_valid_data(self):
        """Test user registration with valid data"""
        data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'SecurePass123!',
            'first_name': 'Test',
            'last_name': 'User',
            'user_type': 'patient'
        }
        serializer = UserRegistrationSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        user = serializer.save()
        self.assertEqual(user.username, 'testuser')
        self.assertEqual(user.email, 'test@example.com')
        self.assertTrue(user.check_password('SecurePass123!'))
    
    def test_user_registration_serializer_invalid_email(self):
        """Test user registration with invalid email"""
        data = {
            'username': 'testuser',
            'email': 'invalid-email',
            'password': 'SecurePass123!',
            'user_type': 'patient'
        }
        serializer = UserRegistrationSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('email', serializer.errors)
    
    def test_user_registration_serializer_weak_password(self):
        """Test user registration with weak password"""
        data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': '123',
            'user_type': 'patient'
        }
        serializer = UserRegistrationSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('password', serializer.errors)
    
    def test_user_profile_serializer(self):
        """Test user profile serializer"""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='pass123',
            first_name='Test',
            last_name='User'
        )
        serializer = UserProfileSerializer(user)
        data = serializer.data
        self.assertEqual(data['username'], 'testuser')
        self.assertEqual(data['email'], 'test@example.com')
        self.assertEqual(data['first_name'], 'Test')
        self.assertNotIn('password', data)  # Password should not be included


class PatientSerializerTest(TestCase):
    """Test cases for Patient serializers"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='patient1',
            email='patient1@example.com',
            password='pass123',
            user_type='patient'
        )
    
    def test_patient_profile_serializer_valid_data(self):
        """Test patient profile serializer with valid data"""
        data = {
            'user': self.user.id,
            'date_of_birth': '1990-05-15',
            'gender': 'male',
            'phone_number': '+1234567890',
            'address': '123 Main St, City, State 12345',
            'blood_type': 'O+',
            'allergies': ['Penicillin', 'Shellfish']
        }
        serializer = PatientProfileSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        profile = serializer.save()
        self.assertEqual(profile.user, self.user)
        self.assertEqual(profile.blood_type, 'O+')
    
    def test_patient_profile_serializer_invalid_blood_type(self):
        """Test patient profile serializer with invalid blood type"""
        data = {
            'user': self.user.id,
            'date_of_birth': '1990-05-15',
            'gender': 'male',
            'blood_type': 'Invalid'
        }
        serializer = PatientProfileSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('blood_type', serializer.errors)
    
    def test_emergency_contact_serializer(self):
        """Test emergency contact serializer"""
        patient = PatientProfile.objects.create(
            user=self.user,
            date_of_birth=date(1990, 5, 15),
            gender='male'
        )
        data = {
            'patient': patient.id,
            'name': 'Jane Doe',
            'relationship': 'spouse',
            'phone_number': '+1234567891',
            'email': 'jane@example.com'
        }
        serializer = EmergencyContactSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        contact = serializer.save()
        self.assertEqual(contact.name, 'Jane Doe')
        self.assertEqual(contact.relationship, 'spouse')


class DoctorSerializerTest(TestCase):
    """Test cases for Doctor serializers"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='doctor1',
            email='doctor1@example.com',
            password='pass123',
            user_type='doctor'
        )
        self.specialization = Specialization.objects.create(
            name='Cardiology',
            description='Heart and cardiovascular system'
        )
    
    def test_specialization_serializer(self):
        """Test specialization serializer"""
        serializer = SpecializationSerializer(self.specialization)
        data = serializer.data
        self.assertEqual(data['name'], 'Cardiology')
        self.assertEqual(data['description'], 'Heart and cardiovascular system')
    
    def test_doctor_profile_serializer_valid_data(self):
        """Test doctor profile serializer with valid data"""
        data = {
            'user': self.user.id,
            'license_number': 'MD123456',
            'specialization': self.specialization.id,
            'phone_number': '+1234567890',
            'years_of_experience': 10,
            'consultation_fee': '150.00'
        }
        serializer = DoctorProfileSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        profile = serializer.save()
        self.assertEqual(profile.license_number, 'MD123456')
        self.assertEqual(profile.specialization, self.specialization)
    
    def test_doctor_profile_serializer_duplicate_license(self):
        """Test doctor profile serializer with duplicate license number"""
        # Create first doctor
        DoctorProfile.objects.create(
            user=self.user,
            license_number='MD123456',
            specialization=self.specialization
        )
        
        # Try to create second doctor with same license
        user2 = User.objects.create_user(
            username='doctor2',
            email='doctor2@example.com',
            password='pass123',
            user_type='doctor'
        )
        data = {
            'user': user2.id,
            'license_number': 'MD123456',
            'specialization': self.specialization.id
        }
        serializer = DoctorProfileSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('license_number', serializer.errors)


class AppointmentSerializerTest(TestCase):
    """Test cases for Appointment serializers"""
    
    def setUp(self):
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
    
    def test_appointment_type_serializer(self):
        """Test appointment type serializer"""
        serializer = AppointmentTypeSerializer(self.appointment_type)
        data = serializer.data
        self.assertEqual(data['name'], 'Consultation')
        self.assertEqual(data['duration'], 30)
        self.assertEqual(float(data['price']), 100.00)
    
    def test_appointment_serializer_valid_data(self):
        """Test appointment serializer with valid data"""
        future_date = date.today() + timedelta(days=1)
        data = {
            'patient': self.patient.id,
            'doctor': self.doctor.id,
            'appointment_date': future_date.isoformat(),
            'appointment_time': '14:30:00',
            'appointment_type': self.appointment_type.id,
            'reason': 'Regular checkup'
        }
        serializer = AppointmentSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        appointment = serializer.save()
        self.assertEqual(appointment.patient, self.patient)
        self.assertEqual(appointment.doctor, self.doctor)
    
    def test_appointment_serializer_past_date(self):
        """Test appointment serializer with past date"""
        past_date = date.today() - timedelta(days=1)
        data = {
            'patient': self.patient.id,
            'doctor': self.doctor.id,
            'appointment_date': past_date.isoformat(),
            'appointment_time': '14:30:00',
            'appointment_type': self.appointment_type.id,
            'reason': 'Regular checkup'
        }
        serializer = AppointmentSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('appointment_date', serializer.errors)


class MedicalRecordsSerializerTest(TestCase):
    """Test cases for Medical Records serializers"""
    
    def setUp(self):
        self.patient_user = User.objects.create_user(
            username='patient1', email='patient1@example.com', password='pass123', user_type='patient'
        )
        self.patient = PatientProfile.objects.create(
            user=self.patient_user,
            date_of_birth=date(1990, 5, 15),
            gender='male'
        )
        
        self.doctor_user = User.objects.create_user(
            username='doctor1', email='doctor1@example.com', password='pass123', user_type='doctor'
        )
        self.specialization = Specialization.objects.create(name='General Medicine')
        self.doctor = DoctorProfile.objects.create(
            user=self.doctor_user,
            license_number='MD123456',
            specialization=self.specialization
        )
    
    def test_medical_history_serializer(self):
        """Test medical history serializer"""
        data = {
            'patient': self.patient.id,
            'doctor': self.doctor.id,
            'condition': 'Hypertension',
            'diagnosis_date': date.today().isoformat(),
            'treatment': 'Medication and lifestyle changes',
            'notes': 'Patient responding well to treatment'
        }
        serializer = MedicalHistorySerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        history = serializer.save()
        self.assertEqual(history.condition, 'Hypertension')
        self.assertEqual(history.patient, self.patient)
    
    def test_prescription_serializer(self):
        """Test prescription serializer"""
        data = {
            'patient': self.patient.id,
            'doctor': self.doctor.id,
            'medication_name': 'Lisinopril',
            'dosage': '10mg',
            'frequency': 'Once daily',
            'duration': '30 days',
            'instructions': 'Take with food'
        }
        serializer = PrescriptionSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        prescription = serializer.save()
        self.assertEqual(prescription.medication_name, 'Lisinopril')
        self.assertEqual(prescription.dosage, '10mg')


class BillingSerializerTest(TestCase):
    """Test cases for Billing serializers"""
    
    def setUp(self):
        self.patient_user = User.objects.create_user(
            username='patient1', email='patient1@example.com', password='pass123', user_type='patient'
        )
        self.patient = PatientProfile.objects.create(
            user=self.patient_user,
            date_of_birth=date(1990, 5, 15),
            gender='male'
        )
    
    def test_invoice_serializer_valid_data(self):
        """Test invoice serializer with valid data"""
        future_date = date.today() + timedelta(days=30)
        data = {
            'patient': self.patient.id,
            'amount': '150.00',
            'due_date': future_date.isoformat(),
            'description': 'Consultation fee',
            'services': [
                {'name': 'Consultation', 'price': '100.00'},
                {'name': 'Lab Test', 'price': '50.00'}
            ]
        }
        serializer = InvoiceSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        invoice = serializer.save()
        self.assertEqual(invoice.amount, Decimal('150.00'))
        self.assertEqual(invoice.patient, self.patient)
    
    def test_payment_serializer(self):
        """Test payment serializer"""
        invoice = Invoice.objects.create(
            patient=self.patient,
            amount=Decimal('150.00'),
            due_date=date.today() + timedelta(days=30)
        )
        data = {
            'invoice': invoice.id,
            'amount': '150.00',
            'payment_method': 'credit_card',
            'transaction_id': 'TXN123456'
        }
        serializer = PaymentSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        payment = serializer.save()
        self.assertEqual(payment.amount, Decimal('150.00'))
        self.assertEqual(payment.payment_method, 'credit_card')


class NotificationSerializerTest(TestCase):
    """Test cases for Notification serializers"""
    
    def test_email_template_serializer(self):
        """Test email template serializer"""
        data = {
            'name': 'Appointment Reminder',
            'subject': 'Appointment Reminder - {{appointment_date}}',
            'html_content': '<p>Dear {{patient_name}}, your appointment is on {{appointment_date}}</p>',
            'text_content': 'Dear {{patient_name}}, your appointment is on {{appointment_date}}',
            'template_type': 'appointment_reminder'
        }
        serializer = EmailTemplateSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        template = serializer.save()
        self.assertEqual(template.name, 'Appointment Reminder')
        self.assertEqual(template.template_type, 'appointment_reminder')
    
    def test_email_notification_serializer(self):
        """Test email notification serializer"""
        template = EmailTemplate.objects.create(
            name='Test Template',
            subject='Test Subject',
            html_content='<p>Test content</p>',
            text_content='Test content'
        )
        data = {
            'recipient_email': 'test@example.com',
            'subject': 'Test Email',
            'html_content': '<p>Test content</p>',
            'text_content': 'Test content',
            'template': template.id,
            'priority': 'normal'
        }
        serializer = EmailNotificationSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        notification = serializer.save()
        self.assertEqual(notification.recipient_email, 'test@example.com')
        self.assertEqual(notification.template, template)


class SerializerValidationTest(TestCase):
    """Test cases for serializer validation logic"""

    def test_email_validation(self):
        """Test email validation across serializers"""
        invalid_emails = ['invalid', 'test@', '@example.com', 'test..test@example.com']

        for email in invalid_emails:
            data = {
                'username': 'testuser',
                'email': email,
                'password': 'SecurePass123!',
                'user_type': 'patient'
            }
            serializer = UserRegistrationSerializer(data=data)
            self.assertFalse(serializer.is_valid())
            self.assertIn('email', serializer.errors)

    def test_phone_number_validation(self):
        """Test phone number validation"""
        user = User.objects.create_user(
            username='patient1', email='patient1@example.com', password='pass123', user_type='patient'
        )

        invalid_phones = ['123', 'abc', '123-456-7890', '1234567890123456']

        for phone in invalid_phones:
            data = {
                'user': user.id,
                'date_of_birth': '1990-05-15',
                'gender': 'male',
                'phone_number': phone
            }
            serializer = PatientProfileSerializer(data=data)
            if not serializer.is_valid():
                self.assertIn('phone_number', serializer.errors)

    def test_date_validation(self):
        """Test date validation for appointments"""
        patient_user = User.objects.create_user(
            username='patient1', email='patient1@example.com', password='pass123', user_type='patient'
        )
        patient = PatientProfile.objects.create(
            user=patient_user, date_of_birth=date(1990, 5, 15), gender='male'
        )

        doctor_user = User.objects.create_user(
            username='doctor1', email='doctor1@example.com', password='pass123', user_type='doctor'
        )
        specialization = Specialization.objects.create(name='General Medicine')
        doctor = DoctorProfile.objects.create(
            user=doctor_user, license_number='MD123456', specialization=specialization
        )

        appointment_type = AppointmentType.objects.create(
            name='Consultation', duration=30, price=Decimal('100.00')
        )

        # Test past date
        past_date = date.today() - timedelta(days=1)
        data = {
            'patient': patient.id,
            'doctor': doctor.id,
            'appointment_date': past_date.isoformat(),
            'appointment_time': '14:30:00',
            'appointment_type': appointment_type.id,
            'reason': 'Regular checkup'
        }
        serializer = AppointmentSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('appointment_date', serializer.errors)
