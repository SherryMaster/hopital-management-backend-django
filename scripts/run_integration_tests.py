#!/usr/bin/env python
"""
Integration test runner for Hospital Management System
"""
import os
import sys
import django
from django.conf import settings
from django.test.utils import get_runner
import time
from datetime import datetime

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hospital_backend.settings')
django.setup()


class IntegrationTestRunner:
    """
    Custom integration test runner for Hospital Management System
    """
    
    def __init__(self):
        self.start_time = None
        self.end_time = None
        
    def run_all_integration_tests(self, verbosity=2):
        """Run all integration tests"""
        print("=" * 70)
        print("🏥 HOSPITAL MANAGEMENT SYSTEM - INTEGRATION TEST SUITE")
        print("=" * 70)
        print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        self.start_time = time.time()
        
        # Run integration tests
        TestRunner = get_runner(settings)
        test_runner = TestRunner(verbosity=verbosity, interactive=False, keepdb=False)
        
        # Integration test modules
        test_labels = [
            'tests.test_integration.AuthenticationIntegrationTest',
            'tests.test_integration.PatientManagementIntegrationTest',
            'tests.test_integration.AppointmentBookingIntegrationTest',
            'tests.test_integration.MedicalRecordsIntegrationTest',
            'tests.test_integration.BillingIntegrationTest',
            'tests.test_integration.CrossModuleIntegrationTest',
            'tests.test_integration.APIEndpointIntegrationTest',
            'tests.test_integration.NotificationIntegrationTest',
            'tests.test_integration.DatabaseIntegrityIntegrationTest'
        ]
        
        failures = test_runner.run_tests(test_labels)
        
        self.end_time = time.time()
        self.print_summary(failures)
        
        return failures
    
    def run_workflow_tests(self):
        """Run workflow integration tests"""
        print("🔄 Running Workflow Integration Tests")
        print("=" * 50)
        
        workflow_tests = [
            'tests.test_integration.AuthenticationIntegrationTest',
            'tests.test_integration.PatientManagementIntegrationTest',
            'tests.test_integration.AppointmentBookingIntegrationTest',
            'tests.test_integration.CrossModuleIntegrationTest'
        ]
        
        return self.run_specific_tests(workflow_tests)
    
    def run_api_tests(self):
        """Run API integration tests"""
        print("🌐 Running API Integration Tests")
        print("=" * 50)
        
        api_tests = [
            'tests.test_integration.APIEndpointIntegrationTest',
            'tests.test_integration.AuthenticationIntegrationTest'
        ]
        
        return self.run_specific_tests(api_tests)
    
    def run_database_tests(self):
        """Run database integration tests"""
        print("🗄️ Running Database Integration Tests")
        print("=" * 50)
        
        db_tests = [
            'tests.test_integration.DatabaseIntegrityIntegrationTest'
        ]
        
        return self.run_specific_tests(db_tests)
    
    def run_cross_module_tests(self):
        """Run cross-module integration tests"""
        print("🔗 Running Cross-Module Integration Tests")
        print("=" * 50)
        
        cross_module_tests = [
            'tests.test_integration.CrossModuleIntegrationTest',
            'tests.test_integration.NotificationIntegrationTest'
        ]
        
        return self.run_specific_tests(cross_module_tests)
    
    def run_specific_tests(self, test_labels, verbosity=2):
        """Run specific test modules"""
        self.start_time = time.time()
        
        TestRunner = get_runner(settings)
        test_runner = TestRunner(verbosity=verbosity, interactive=False)
        failures = test_runner.run_tests(test_labels)
        
        self.end_time = time.time()
        self.print_summary(failures)
        
        return failures
    
    def print_summary(self, failures):
        """Print test execution summary"""
        duration = self.end_time - self.start_time if self.start_time and self.end_time else 0
        
        print("\n" + "=" * 50)
        print("📋 INTEGRATION TEST SUMMARY")
        print("=" * 50)
        print(f"⏱️  Execution time: {duration:.2f} seconds")
        print(f"📅 Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        if failures == 0:
            print("✅ All integration tests passed successfully!")
            print("🎉 System integration is working correctly!")
        else:
            print(f"❌ {failures} integration test(s) failed")
            print("🔧 Please fix the failing tests before deployment")
        
        print("=" * 50)
    
    def run_smoke_tests(self):
        """Run smoke tests for critical integration points"""
        print("💨 Running Integration Smoke Tests")
        print("=" * 50)
        
        smoke_tests = [
            'tests.test_integration.AuthenticationIntegrationTest.test_complete_authentication_workflow',
            'tests.test_integration.CrossModuleIntegrationTest.test_complete_patient_journey'
        ]
        
        return self.run_specific_tests(smoke_tests, verbosity=1)
    
    def validate_integration_setup(self):
        """Validate that integration test setup is correct"""
        print("🔍 Validating Integration Test Setup")
        print("=" * 50)
        
        validation_results = {
            'database_connection': False,
            'api_framework': False,
            'authentication': False,
            'test_data': False
        }
        
        try:
            # Test database connection
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                validation_results['database_connection'] = True
                print("✓ Database connection working")
        except Exception as e:
            print(f"✗ Database connection failed: {e}")
        
        try:
            # Test API framework
            from rest_framework.test import APIClient
            from rest_framework import status
            client = APIClient()
            validation_results['api_framework'] = True
            print("✓ API framework available")
        except Exception as e:
            print(f"✗ API framework error: {e}")
        
        try:
            # Test authentication
            from rest_framework_simplejwt.tokens import RefreshToken
            from django.contrib.auth import get_user_model
            User = get_user_model()
            test_user = User.objects.create_user(
                username='test_validation',
                email='test@validation.com',
                password='pass123'
            )
            refresh = RefreshToken.for_user(test_user)
            access_token = refresh.access_token
            test_user.delete()  # Clean up
            validation_results['authentication'] = True
            print("✓ Authentication system working")
        except Exception as e:
            print(f"✗ Authentication error: {e}")
        
        try:
            # Test test data creation
            from accounts.models import User
            from patients.models import PatientProfile
            test_user = User.objects.create_user(
                username='test_data_validation',
                email='testdata@validation.com',
                password='pass123',
                user_type='patient'
            )
            test_profile = PatientProfile.objects.create(
                user=test_user,
                date_of_birth='1990-01-01',
                gender='male'
            )
            # Clean up
            test_profile.delete()
            test_user.delete()
            validation_results['test_data'] = True
            print("✓ Test data creation working")
        except Exception as e:
            print(f"✗ Test data creation error: {e}")
        
        # Summary
        passed = sum(validation_results.values())
        total = len(validation_results)
        
        print(f"\nValidation Results: {passed}/{total} checks passed")
        
        if passed == total:
            print("🎉 Integration test environment is ready!")
            return True
        else:
            print("⚠️ Integration test environment needs attention")
            return False


def main():
    """Main integration test execution function"""
    runner = IntegrationTestRunner()
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == 'all':
            failures = runner.run_all_integration_tests()
        elif command == 'workflow':
            failures = runner.run_workflow_tests()
        elif command == 'api':
            failures = runner.run_api_tests()
        elif command == 'database':
            failures = runner.run_database_tests()
        elif command == 'cross-module':
            failures = runner.run_cross_module_tests()
        elif command == 'smoke':
            failures = runner.run_smoke_tests()
        elif command == 'validate':
            success = runner.validate_integration_setup()
            return 0 if success else 1
        elif command == 'help':
            print_help()
            return 0
        else:
            print(f"❌ Unknown command: {command}")
            print_help()
            return 1
    else:
        # Default: run all integration tests
        failures = runner.run_all_integration_tests()
    
    return failures


def print_help():
    """Print help information"""
    print("🏥 Hospital Management System Integration Test Runner")
    print("=" * 60)
    print("Usage: python run_integration_tests.py [command]")
    print()
    print("Commands:")
    print("  all          - Run all integration tests (default)")
    print("  workflow     - Run workflow integration tests")
    print("  api          - Run API integration tests")
    print("  database     - Run database integration tests")
    print("  cross-module - Run cross-module integration tests")
    print("  smoke        - Run smoke tests (critical paths only)")
    print("  validate     - Validate integration test environment")
    print("  help         - Show this help message")
    print()
    print("Examples:")
    print("  python run_integration_tests.py all")
    print("  python run_integration_tests.py workflow")
    print("  python run_integration_tests.py smoke")
    print("  python run_integration_tests.py validate")
    print()
    print("Integration Test Categories:")
    print("  🔐 Authentication - User registration, login, token management")
    print("  👥 Patient Management - Profile creation, updates, data flow")
    print("  📅 Appointment Booking - Complete booking workflow")
    print("  📋 Medical Records - EHR creation and management")
    print("  💰 Billing - Invoice generation and payment processing")
    print("  🔗 Cross-Module - End-to-end patient journey")
    print("  🌐 API Endpoints - Consistency and error handling")
    print("  📧 Notifications - Template and delivery system")
    print("  🗄️ Database - Integrity and constraint validation")


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
