"""
Django management command for test data management
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.contrib.auth import get_user_model
import time
from datetime import datetime

from tests.fixtures import TestFixtures, TestDataSeeder

User = get_user_model()


class Command(BaseCommand):
    help = 'Manage test data for Hospital Management System'
    
    def add_arguments(self, parser):
        parser.add_argument(
            'action',
            choices=[
                'create_minimal',
                'create_comprehensive', 
                'create_performance',
                'seed_development',
                'seed_demo',
                'export_fixtures',
                'load_fixtures',
                'cleanup',
                'status'
            ],
            help='Action to perform'
        )
        
        parser.add_argument(
            '--filename',
            type=str,
            default='test_fixtures.json',
            help='Filename for fixture export/import'
        )
        
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force action without confirmation'
        )
        
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Verbose output'
        )
    
    def handle(self, *args, **options):
        action = options['action']
        filename = options['filename']
        force = options['force']
        verbose = options['verbose']
        
        if verbose:
            self.stdout.write(f"Executing action: {action}")
            self.stdout.write(f"Timestamp: {datetime.now()}")
        
        try:
            if action == 'create_minimal':
                self.create_minimal_data(force, verbose)
            elif action == 'create_comprehensive':
                self.create_comprehensive_data(force, verbose)
            elif action == 'create_performance':
                self.create_performance_data(force, verbose)
            elif action == 'seed_development':
                self.seed_development_data(force, verbose)
            elif action == 'seed_demo':
                self.seed_demo_data(force, verbose)
            elif action == 'export_fixtures':
                self.export_fixtures(filename, verbose)
            elif action == 'load_fixtures':
                self.load_fixtures(filename, force, verbose)
            elif action == 'cleanup':
                self.cleanup_data(force, verbose)
            elif action == 'status':
                self.show_status(verbose)
            
        except Exception as e:
            raise CommandError(f'Error executing {action}: {str(e)}')
    
    def create_minimal_data(self, force, verbose):
        """Create minimal test data"""
        
        if not force and User.objects.exists():
            if not self.confirm_action("Database contains data. Continue?"):
                return
        
        self.stdout.write("Creating minimal test data...")
        
        start_time = time.time()
        
        with transaction.atomic():
            data = TestFixtures.create_minimal_test_data()
        
        duration = time.time() - start_time
        
        self.stdout.write(
            self.style.SUCCESS(
                f"✅ Minimal test data created successfully in {duration:.2f}s"
            )
        )
        
        if verbose:
            self.stdout.write("Created:")
            self.stdout.write(f"  - Admin user: {data['admin'].username}")
            self.stdout.write(f"  - Patient: {data['patient'].user.get_full_name()}")
            self.stdout.write(f"  - Doctor: {data['doctor'].user.get_full_name()}")
            self.stdout.write(f"  - Specialization: {data['specialization'].name}")
    
    def create_comprehensive_data(self, force, verbose):
        """Create comprehensive test data"""
        
        if not force and User.objects.count() > 10:
            if not self.confirm_action("Database contains significant data. Continue?"):
                return
        
        self.stdout.write("Creating comprehensive test data...")
        
        start_time = time.time()
        
        with transaction.atomic():
            data = TestFixtures.create_comprehensive_test_data()
        
        duration = time.time() - start_time
        
        self.stdout.write(
            self.style.SUCCESS(
                f"✅ Comprehensive test data created successfully in {duration:.2f}s"
            )
        )
        
        if verbose:
            self.stdout.write("Created:")
            self.stdout.write(f"  - Patients: {len(data['additional_patients']) + 1}")
            self.stdout.write(f"  - Doctors: {len(data['additional_doctors']) + 1}")
            self.stdout.write(f"  - Appointments: {len(data['appointments'])}")
            self.stdout.write(f"  - Medical histories: {len(data['medical_histories'])}")
            self.stdout.write(f"  - Prescriptions: {len(data['prescriptions'])}")
            self.stdout.write(f"  - Invoices: {len(data['invoices'])}")
            self.stdout.write(f"  - Email templates: {len(data['email_templates'])}")
    
    def create_performance_data(self, force, verbose):
        """Create performance test data"""
        
        if not force:
            self.stdout.write(
                self.style.WARNING(
                    "⚠️  This will create a large amount of test data for performance testing."
                )
            )
            if not self.confirm_action("Continue?"):
                return
        
        self.stdout.write("Creating performance test data...")
        
        start_time = time.time()
        
        with transaction.atomic():
            data = TestFixtures.create_performance_test_data()
        
        duration = time.time() - start_time
        
        self.stdout.write(
            self.style.SUCCESS(
                f"✅ Performance test data created successfully in {duration:.2f}s"
            )
        )
        
        if verbose:
            self.stdout.write("Created:")
            self.stdout.write(f"  - Patients: {len(data['patients'])}")
            self.stdout.write(f"  - Doctors: {len(data['doctors'])}")
            self.stdout.write(f"  - Appointments: {len(data['appointments'])}")
    
    def seed_development_data(self, force, verbose):
        """Seed development environment data"""
        
        self.stdout.write("Seeding development data...")
        
        start_time = time.time()
        
        with transaction.atomic():
            data = TestDataSeeder.seed_development_data()
        
        duration = time.time() - start_time
        
        self.stdout.write(
            self.style.SUCCESS(
                f"✅ Development data seeded successfully in {duration:.2f}s"
            )
        )
    
    def seed_demo_data(self, force, verbose):
        """Seed demo environment data"""
        
        self.stdout.write("Seeding demo data...")
        
        start_time = time.time()
        
        with transaction.atomic():
            data = TestDataSeeder.seed_demo_data()
        
        duration = time.time() - start_time
        
        self.stdout.write(
            self.style.SUCCESS(
                f"✅ Demo data seeded successfully in {duration:.2f}s"
            )
        )
        
        if verbose:
            self.stdout.write("Demo accounts created:")
            self.stdout.write(f"  - Patient: {data['demo_patient'].username} / demo123")
            self.stdout.write(f"  - Doctor: {data['demo_doctor'].username} / demo123")
    
    def export_fixtures(self, filename, verbose):
        """Export current data to fixtures"""
        
        self.stdout.write(f"Exporting fixtures to {filename}...")
        
        start_time = time.time()
        
        exported_file = TestFixtures.export_fixtures_to_json(filename)
        
        duration = time.time() - start_time
        
        self.stdout.write(
            self.style.SUCCESS(
                f"✅ Fixtures exported to {exported_file} in {duration:.2f}s"
            )
        )
    
    def load_fixtures(self, filename, force, verbose):
        """Load fixtures from file"""
        
        if not force and User.objects.exists():
            if not self.confirm_action(f"Load fixtures from {filename}? This may overwrite existing data."):
                return
        
        self.stdout.write(f"Loading fixtures from {filename}...")
        
        start_time = time.time()
        
        success = TestFixtures.load_fixtures_from_json(filename)
        
        duration = time.time() - start_time
        
        if success:
            self.stdout.write(
                self.style.SUCCESS(
                    f"✅ Fixtures loaded successfully in {duration:.2f}s"
                )
            )
        else:
            self.stdout.write(
                self.style.ERROR(
                    f"❌ Failed to load fixtures from {filename}"
                )
            )
    
    def cleanup_data(self, force, verbose):
        """Clean up all test data"""
        
        if not force:
            self.stdout.write(
                self.style.WARNING(
                    "⚠️  This will delete ALL data from the database!"
                )
            )
            if not self.confirm_action("Are you sure you want to continue?"):
                return
        
        self.stdout.write("Cleaning up test data...")
        
        start_time = time.time()
        
        with transaction.atomic():
            deleted_counts = TestFixtures.cleanup_test_data()
        
        duration = time.time() - start_time
        
        self.stdout.write(
            self.style.SUCCESS(
                f"✅ Test data cleaned up successfully in {duration:.2f}s"
            )
        )
        
        if verbose:
            total_deleted = sum(deleted_counts.values())
            self.stdout.write(f"Total records deleted: {total_deleted}")
    
    def show_status(self, verbose):
        """Show current database status"""
        
        self.stdout.write("📊 Database Status:")
        self.stdout.write("=" * 50)
        
        # Count records in each model
        from patients.models import PatientProfile
        from doctors.models import DoctorProfile, Specialization
        from appointments.models import Appointment, AppointmentType
        from medical_records.models import MedicalHistory, Prescription
        from billing.models import Invoice, Payment
        from notifications.models import EmailTemplate, EmailNotification
        
        models_to_check = [
            (User, "Users"),
            (PatientProfile, "Patients"),
            (DoctorProfile, "Doctors"),
            (Specialization, "Specializations"),
            (Appointment, "Appointments"),
            (AppointmentType, "Appointment Types"),
            (MedicalHistory, "Medical Histories"),
            (Prescription, "Prescriptions"),
            (Invoice, "Invoices"),
            (Payment, "Payments"),
            (EmailTemplate, "Email Templates"),
            (EmailNotification, "Email Notifications")
        ]
        
        total_records = 0
        for model, name in models_to_check:
            try:
                count = model.objects.count()
                total_records += count
                self.stdout.write(f"  {name}: {count}")
            except Exception as e:
                self.stdout.write(f"  {name}: Error - {e}")
        
        self.stdout.write("=" * 50)
        self.stdout.write(f"Total Records: {total_records}")
        
        if verbose:
            # Show recent activity
            self.stdout.write("\n📈 Recent Activity:")
            try:
                recent_users = User.objects.order_by('-date_joined')[:5]
                for user in recent_users:
                    self.stdout.write(f"  User: {user.username} ({user.date_joined})")
            except Exception as e:
                self.stdout.write(f"  Error getting recent activity: {e}")
    
    def confirm_action(self, message):
        """Ask for user confirmation"""
        
        response = input(f"{message} [y/N]: ")
        return response.lower() in ['y', 'yes']
