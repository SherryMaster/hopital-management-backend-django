"""
Test fixtures and data management utilities for Hospital Management System
"""
import json
import os
from django.core.management.base import BaseCommand
from django.core import serializers
from django.contrib.auth import get_user_model
from datetime import date, time, datetime, timedelta
from decimal import Decimal

from .factories import (
    UserFactory, AdminUserFactory, PatientUserFactory, DoctorUserFactory,
    PatientProfileFactory, DoctorProfileFactory, SpecializationFactory,
    AppointmentFactory, AppointmentTypeFactory, MedicalHistoryFactory,
    PrescriptionFactory, InvoiceFactory, PaymentFactory,
    EmailTemplateFactory, EmailNotificationFactory,
    TestDataBatch
)

User = get_user_model()


class TestFixtures:
    """
    Centralized test fixtures management
    """
    
    @staticmethod
    def create_minimal_test_data():
        """Create minimal test data for basic testing"""
        
        # Create basic users
        admin = AdminUserFactory(
            username='admin_test',
            email='admin@test.com',
            first_name='Admin',
            last_name='User'
        )
        
        patient_user = PatientUserFactory(
            username='patient_test',
            email='patient@test.com',
            first_name='John',
            last_name='Doe'
        )
        
        doctor_user = DoctorUserFactory(
            username='doctor_test',
            email='doctor@test.com',
            first_name='Dr. Jane',
            last_name='Smith'
        )
        
        # Create specialization
        specialization = SpecializationFactory(
            name='General Medicine',
            description='General medical practice'
        )
        
        # Create profiles
        patient = PatientProfileFactory(
            user=patient_user,
            date_of_birth=date(1990, 1, 15),
            gender='male',
            blood_type='O+'
        )
        
        doctor = DoctorProfileFactory(
            user=doctor_user,
            license_number='MD123456',
            specialization=specialization
        )
        
        # Create appointment type
        appointment_type = AppointmentTypeFactory(
            name='Consultation',
            duration=30,
            price=Decimal('100.00')
        )
        
        return {
            'admin': admin,
            'patient_user': patient_user,
            'doctor_user': doctor_user,
            'patient': patient,
            'doctor': doctor,
            'specialization': specialization,
            'appointment_type': appointment_type
        }
    
    @staticmethod
    def create_comprehensive_test_data():
        """Create comprehensive test data for full system testing"""
        
        # Start with minimal data
        minimal_data = TestFixtures.create_minimal_test_data()
        
        # Create additional patients and doctors
        additional_patients = TestDataBatch.create_complete_patient_data(count=5)
        additional_doctors = TestDataBatch.create_complete_doctor_data(count=3)
        
        # Create appointments
        appointments = []
        for i in range(10):
            appointment = AppointmentFactory(
                patient=additional_patients[i % len(additional_patients)],
                doctor=additional_doctors[i % len(additional_doctors)],
                appointment_type=minimal_data['appointment_type']
            )
            appointments.append(appointment)
        
        # Create medical records
        medical_histories = []
        prescriptions = []
        for patient in additional_patients:
            history = MedicalHistoryFactory(
                patient=patient,
                doctor=additional_doctors[0]
            )
            medical_histories.append(history)
            
            prescription = PrescriptionFactory(
                patient=patient,
                doctor=additional_doctors[0]
            )
            prescriptions.append(prescription)
        
        # Create invoices and payments
        invoices = []
        payments = []
        for patient in additional_patients:
            invoice = InvoiceFactory(patient=patient)
            invoices.append(invoice)
            
            if invoice.status == 'paid':
                payment = PaymentFactory(invoice=invoice)
                payments.append(payment)
        
        # Create email templates
        email_templates = []
        template_types = [
            ('Appointment Reminder', 'appointment_reminder'),
            ('Appointment Confirmation', 'appointment_confirmation'),
            ('Test Results', 'test_results'),
            ('Payment Reminder', 'payment_reminder')
        ]
        
        for name, template_type in template_types:
            template = EmailTemplateFactory(
                name=name,
                template_type=template_type
            )
            email_templates.append(template)
        
        # Create hospital infrastructure
        infrastructure = TestDataBatch.create_hospital_infrastructure()
        
        return {
            **minimal_data,
            'additional_patients': additional_patients,
            'additional_doctors': additional_doctors,
            'appointments': appointments,
            'medical_histories': medical_histories,
            'prescriptions': prescriptions,
            'invoices': invoices,
            'payments': payments,
            'email_templates': email_templates,
            'infrastructure': infrastructure
        }
    
    @staticmethod
    def create_performance_test_data():
        """Create large dataset for performance testing"""
        
        print("Creating performance test data...")
        
        # Create users in batches
        patients = TestDataBatch.create_complete_patient_data(count=100)
        doctors = TestDataBatch.create_complete_doctor_data(count=20)
        
        print(f"Created {len(patients)} patients and {len(doctors)} doctors")
        
        # Create appointment types
        appointment_types = []
        for name in ['Consultation', 'Follow-up', 'Emergency', 'Surgery']:
            appointment_type = AppointmentTypeFactory(name=name)
            appointment_types.append(appointment_type)
        
        # Create appointments
        appointments = []
        for i in range(500):
            appointment = AppointmentFactory(
                patient=patients[i % len(patients)],
                doctor=doctors[i % len(doctors)],
                appointment_type=appointment_types[i % len(appointment_types)]
            )
            appointments.append(appointment)
        
        print(f"Created {len(appointments)} appointments")
        
        # Create medical records
        for i in range(200):
            MedicalHistoryFactory(
                patient=patients[i % len(patients)],
                doctor=doctors[i % len(doctors)]
            )
            
            PrescriptionFactory(
                patient=patients[i % len(patients)],
                doctor=doctors[i % len(doctors)]
            )
        
        print("Created medical records and prescriptions")
        
        # Create invoices
        for i in range(300):
            InvoiceFactory(patient=patients[i % len(patients)])
        
        print("Created invoices")
        
        return {
            'patients': patients,
            'doctors': doctors,
            'appointments': appointments,
            'appointment_types': appointment_types
        }
    
    @staticmethod
    def export_fixtures_to_json(filename='test_fixtures.json'):
        """Export current test data to JSON fixtures"""
        
        # Get all model data
        models_to_export = [
            'auth.User',
            'patients.PatientProfile',
            'doctors.DoctorProfile',
            'doctors.Specialization',
            'appointments.Appointment',
            'appointments.AppointmentType',
            'medical_records.MedicalHistory',
            'medical_records.Prescription',
            'billing.Invoice',
            'billing.Payment',
            'notifications.EmailTemplate'
        ]
        
        fixtures = []
        for model in models_to_export:
            try:
                app_label, model_name = model.split('.')
                from django.apps import apps
                model_class = apps.get_model(app_label, model_name)
                
                for obj in model_class.objects.all():
                    fixture_data = serializers.serialize('json', [obj])
                    fixtures.extend(json.loads(fixture_data))
            except Exception as e:
                print(f"Error exporting {model}: {e}")
        
        # Save to file
        with open(filename, 'w') as f:
            json.dump(fixtures, f, indent=2, default=str)
        
        print(f"Exported {len(fixtures)} fixtures to {filename}")
        return filename
    
    @staticmethod
    def load_fixtures_from_json(filename='test_fixtures.json'):
        """Load test data from JSON fixtures"""
        
        if not os.path.exists(filename):
            print(f"Fixture file {filename} not found")
            return False
        
        try:
            with open(filename, 'r') as f:
                fixtures = json.load(f)
            
            # Convert back to Django fixture format
            django_fixtures = []
            for fixture in fixtures:
                django_fixtures.append(fixture)
            
            # Load fixtures
            from django.core.management import call_command
            from io import StringIO
            
            fixture_data = json.dumps(django_fixtures)
            call_command('loaddata', StringIO(fixture_data))
            
            print(f"Loaded {len(fixtures)} fixtures from {filename}")
            return True
            
        except Exception as e:
            print(f"Error loading fixtures: {e}")
            return False
    
    @staticmethod
    def cleanup_test_data():
        """Clean up all test data"""
        
        # Delete in reverse dependency order
        from appointments.models import Appointment
        from medical_records.models import MedicalHistory, Prescription
        from billing.models import Payment, Invoice
        from patients.models import PatientProfile, EmergencyContact
        from doctors.models import DoctorProfile, DoctorAvailability
        from notifications.models import EmailNotification, EmailTemplate
        
        models_to_clean = [
            Appointment,
            MedicalHistory,
            Prescription,
            Payment,
            Invoice,
            EmergencyContact,
            PatientProfile,
            DoctorAvailability,
            DoctorProfile,
            EmailNotification,
            EmailTemplate,
            User
        ]
        
        deleted_counts = {}
        for model in models_to_clean:
            try:
                count = model.objects.count()
                model.objects.all().delete()
                deleted_counts[model.__name__] = count
            except Exception as e:
                print(f"Error deleting {model.__name__}: {e}")
        
        print("Cleanup completed:")
        for model_name, count in deleted_counts.items():
            print(f"  {model_name}: {count} records deleted")
        
        return deleted_counts


class TestDataSeeder:
    """
    Database seeding utility for test environments
    """
    
    @staticmethod
    def seed_development_data():
        """Seed data for development environment"""
        
        print("Seeding development data...")
        
        # Create admin user
        admin, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@hospital.com',
                'first_name': 'System',
                'last_name': 'Administrator',
                'user_type': 'admin',
                'is_staff': True,
                'is_superuser': True
            }
        )
        if created:
            admin.set_password('admin123')
            admin.save()
            print("Created admin user")
        
        # Create sample data
        data = TestFixtures.create_comprehensive_test_data()
        
        print("Development data seeded successfully")
        return data
    
    @staticmethod
    def seed_demo_data():
        """Seed data for demo environment"""
        
        print("Seeding demo data...")
        
        # Create demo users with realistic data
        demo_patient = PatientUserFactory(
            username='demo_patient',
            email='patient@demo.com',
            first_name='Alice',
            last_name='Johnson'
        )
        demo_patient.set_password('demo123')
        demo_patient.save()
        
        demo_doctor = DoctorUserFactory(
            username='demo_doctor',
            email='doctor@demo.com',
            first_name='Dr. Robert',
            last_name='Wilson'
        )
        demo_doctor.set_password('demo123')
        demo_doctor.save()
        
        # Create profiles and related data
        specialization = SpecializationFactory(
            name='Family Medicine',
            description='Comprehensive healthcare for individuals and families'
        )
        
        patient_profile = PatientProfileFactory(
            user=demo_patient,
            date_of_birth=date(1985, 3, 20),
            gender='female',
            blood_type='A+'
        )
        
        doctor_profile = DoctorProfileFactory(
            user=demo_doctor,
            license_number='MD789012',
            specialization=specialization,
            years_of_experience=15
        )
        
        # Create sample appointment
        appointment_type = AppointmentTypeFactory(
            name='Annual Checkup',
            duration=45,
            price=Decimal('150.00')
        )
        
        appointment = AppointmentFactory(
            patient=patient_profile,
            doctor=doctor_profile,
            appointment_type=appointment_type,
            appointment_date=date.today() + timedelta(days=7),
            status='scheduled',
            reason='Annual health checkup'
        )
        
        print("Demo data seeded successfully")
        return {
            'demo_patient': demo_patient,
            'demo_doctor': demo_doctor,
            'patient_profile': patient_profile,
            'doctor_profile': doctor_profile,
            'appointment': appointment
        }
