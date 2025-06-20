"""
Unit tests for all models in the Hospital Management System
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from datetime import date, time, datetime, timedelta
from decimal import Decimal

from accounts.models import User
from patients.models import PatientProfile, EmergencyContact, Insurance
from doctors.models import DoctorProfile, Specialization, DoctorAvailability
from appointments.models import Appointment, AppointmentType
from medical_records.models import MedicalHistory, Prescription, VitalSigns
from billing.models import Invoice, Payment, InsuranceClaim
from notifications.models import EmailNotification, SMSNotification, EmailTemplate
from infrastructure.models import Building, Floor, Room, Equipment

User = get_user_model()


class UserModelTest(TestCase):
    """Test cases for User model"""
    
    def setUp(self):
        self.user_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'first_name': 'Test',
            'last_name': 'User',
            'user_type': 'patient'
        }
    
    def test_create_user(self):
        """Test creating a new user"""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            user_type='patient'
        )
        self.assertEqual(user.username, 'testuser')
        self.assertEqual(user.email, 'test@example.com')
        self.assertEqual(user.user_type, 'patient')
        self.assertTrue(user.check_password('testpass123'))
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
    
    def test_create_superuser(self):
        """Test creating a superuser"""
        admin = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminpass123'
        )
        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superuser)
        self.assertEqual(admin.user_type, 'admin')
    
    def test_user_str_representation(self):
        """Test user string representation"""
        user = User(**self.user_data)
        expected = f"{user.first_name} {user.last_name} ({user.username})"
        self.assertEqual(str(user), expected)
    
    def test_user_email_unique(self):
        """Test that email must be unique"""
        User.objects.create_user(username='user1', email='test@example.com', password='pass123')
        with self.assertRaises(IntegrityError):
            User.objects.create_user(username='user2', email='test@example.com', password='pass123')
    
    def test_user_type_choices(self):
        """Test user type validation"""
        valid_types = ['admin', 'doctor', 'patient', 'staff']
        for user_type in valid_types:
            user = User(username=f'user_{user_type}', email=f'{user_type}@example.com', user_type=user_type)
            user.full_clean()  # Should not raise ValidationError


class PatientProfileModelTest(TestCase):
    """Test cases for PatientProfile model"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='patient1',
            email='patient1@example.com',
            password='pass123',
            user_type='patient'
        )
        self.profile_data = {
            'user': self.user,
            'date_of_birth': date(1990, 5, 15),
            'gender': 'male',
            'phone_number': '+1234567890',
            'address': '123 Main St, City, State 12345',
            'blood_type': 'O+'
        }
    
    def test_create_patient_profile(self):
        """Test creating a patient profile"""
        profile = PatientProfile.objects.create(**self.profile_data)
        self.assertEqual(profile.user, self.user)
        self.assertEqual(profile.blood_type, 'O+')
        self.assertEqual(profile.gender, 'male')
    
    def test_patient_profile_str(self):
        """Test patient profile string representation"""
        profile = PatientProfile(**self.profile_data)
        expected = f"Patient: {self.user.get_full_name()}"
        self.assertEqual(str(profile), expected)
    
    def test_patient_age_calculation(self):
        """Test age calculation property"""
        profile = PatientProfile.objects.create(**self.profile_data)
        expected_age = (date.today() - profile.date_of_birth).days // 365
        self.assertEqual(profile.age, expected_age)
    
    def test_blood_type_choices(self):
        """Test blood type validation"""
        valid_blood_types = ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-']
        for blood_type in valid_blood_types:
            profile_data = self.profile_data.copy()
            profile_data['blood_type'] = blood_type
            profile = PatientProfile(**profile_data)
            profile.full_clean()  # Should not raise ValidationError


class DoctorProfileModelTest(TestCase):
    """Test cases for DoctorProfile model"""
    
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
        self.profile_data = {
            'user': self.user,
            'license_number': 'MD123456',
            'specialization': self.specialization,
            'phone_number': '+1234567890',
            'years_of_experience': 10
        }
    
    def test_create_doctor_profile(self):
        """Test creating a doctor profile"""
        profile = DoctorProfile.objects.create(**self.profile_data)
        self.assertEqual(profile.user, self.user)
        self.assertEqual(profile.license_number, 'MD123456')
        self.assertEqual(profile.specialization, self.specialization)
    
    def test_doctor_profile_str(self):
        """Test doctor profile string representation"""
        profile = DoctorProfile(**self.profile_data)
        expected = f"Dr. {self.user.get_full_name()} - {self.specialization.name}"
        self.assertEqual(str(profile), expected)
    
    def test_license_number_unique(self):
        """Test that license number must be unique"""
        DoctorProfile.objects.create(**self.profile_data)
        profile_data_2 = self.profile_data.copy()
        user2 = User.objects.create_user(username='doctor2', email='doctor2@example.com', password='pass123')
        profile_data_2['user'] = user2
        with self.assertRaises(IntegrityError):
            DoctorProfile.objects.create(**profile_data_2)


class AppointmentModelTest(TestCase):
    """Test cases for Appointment model"""
    
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
        
        self.appointment_data = {
            'patient': self.patient,
            'doctor': self.doctor,
            'appointment_date': date.today() + timedelta(days=1),
            'appointment_time': time(14, 30),
            'appointment_type': self.appointment_type,
            'reason': 'Regular checkup'
        }
    
    def test_create_appointment(self):
        """Test creating an appointment"""
        appointment = Appointment.objects.create(**self.appointment_data)
        self.assertEqual(appointment.patient, self.patient)
        self.assertEqual(appointment.doctor, self.doctor)
        self.assertEqual(appointment.status, 'scheduled')
    
    def test_appointment_str(self):
        """Test appointment string representation"""
        appointment = Appointment(**self.appointment_data)
        expected = f"{self.patient.user.get_full_name()} with Dr. {self.doctor.user.get_full_name()} on {appointment.appointment_date}"
        self.assertEqual(str(appointment), expected)
    
    def test_appointment_datetime_property(self):
        """Test appointment datetime property"""
        appointment = Appointment.objects.create(**self.appointment_data)
        expected_datetime = datetime.combine(appointment.appointment_date, appointment.appointment_time)
        self.assertEqual(appointment.appointment_datetime, expected_datetime)


class MedicalHistoryModelTest(TestCase):
    """Test cases for MedicalHistory model"""
    
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
    
    def test_create_medical_history(self):
        """Test creating medical history record"""
        history = MedicalHistory.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            condition='Hypertension',
            diagnosis_date=date.today(),
            treatment='Medication and lifestyle changes',
            notes='Patient responding well to treatment'
        )
        self.assertEqual(history.patient, self.patient)
        self.assertEqual(history.condition, 'Hypertension')
    
    def test_medical_history_str(self):
        """Test medical history string representation"""
        history = MedicalHistory(
            patient=self.patient,
            condition='Hypertension',
            diagnosis_date=date.today()
        )
        expected = f"{self.patient.user.get_full_name()} - Hypertension ({date.today()})"
        self.assertEqual(str(history), expected)


class InvoiceModelTest(TestCase):
    """Test cases for Invoice model"""
    
    def setUp(self):
        self.patient_user = User.objects.create_user(
            username='patient1', email='patient1@example.com', password='pass123', user_type='patient'
        )
        self.patient = PatientProfile.objects.create(
            user=self.patient_user,
            date_of_birth=date(1990, 5, 15),
            gender='male'
        )
    
    def test_create_invoice(self):
        """Test creating an invoice"""
        invoice = Invoice.objects.create(
            patient=self.patient,
            amount=Decimal('150.00'),
            due_date=date.today() + timedelta(days=30),
            description='Consultation fee'
        )
        self.assertEqual(invoice.patient, self.patient)
        self.assertEqual(invoice.amount, Decimal('150.00'))
        self.assertEqual(invoice.status, 'pending')
    
    def test_invoice_str(self):
        """Test invoice string representation"""
        invoice = Invoice(
            patient=self.patient,
            amount=Decimal('150.00'),
            invoice_number='INV-001'
        )
        expected = f"Invoice INV-001 - {self.patient.user.get_full_name()} - $150.00"
        self.assertEqual(str(invoice), expected)
    
    def test_invoice_number_generation(self):
        """Test automatic invoice number generation"""
        invoice = Invoice.objects.create(
            patient=self.patient,
            amount=Decimal('150.00'),
            due_date=date.today() + timedelta(days=30)
        )
        self.assertTrue(invoice.invoice_number.startswith('INV'))
        self.assertTrue(len(invoice.invoice_number) > 3)


class NotificationModelTest(TestCase):
    """Test cases for Notification models"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='user1', email='user1@example.com', password='pass123'
        )
        self.template = EmailTemplate.objects.create(
            name='Test Template',
            subject='Test Subject',
            html_content='<p>Hello {{name}}</p>',
            text_content='Hello {{name}}'
        )
    
    def test_create_email_notification(self):
        """Test creating email notification"""
        notification = EmailNotification.objects.create(
            recipient_email='test@example.com',
            subject='Test Email',
            html_content='<p>Test content</p>',
            text_content='Test content',
            template=self.template
        )
        self.assertEqual(notification.recipient_email, 'test@example.com')
        self.assertEqual(notification.status, 'pending')
    
    def test_email_notification_str(self):
        """Test email notification string representation"""
        notification = EmailNotification(
            recipient_email='test@example.com',
            subject='Test Email'
        )
        expected = f"Email to test@example.com: Test Email"
        self.assertEqual(str(notification), expected)
