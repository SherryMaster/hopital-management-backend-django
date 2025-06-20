#!/usr/bin/env python
"""
Comprehensive test runner for Hospital Management System
"""
import os
import sys
import django
from django.conf import settings
from django.test.utils import get_runner
from django.core.management import execute_from_command_line
import coverage
import time
from datetime import datetime

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hospital_backend.settings')
django.setup()


class HospitalTestRunner:
    """
    Custom test runner for Hospital Management System
    """
    
    def __init__(self):
        self.start_time = None
        self.end_time = None
        self.coverage = None
        
    def setup_coverage(self):
        """Setup code coverage tracking"""
        self.coverage = coverage.Coverage(
            source=['accounts', 'patients', 'doctors', 'appointments', 
                   'medical_records', 'billing', 'notifications', 'infrastructure'],
            omit=[
                '*/migrations/*',
                '*/tests/*',
                '*/venv/*',
                '*/env/*',
                'manage.py',
                '*/settings/*',
                '*/wsgi.py',
                '*/asgi.py'
            ]
        )
        self.coverage.start()
    
    def run_all_tests(self, verbosity=2, with_coverage=True):
        """Run all tests with optional coverage"""
        print("=" * 70)
        print("🏥 HOSPITAL MANAGEMENT SYSTEM - COMPREHENSIVE TEST SUITE")
        print("=" * 70)
        print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        self.start_time = time.time()
        
        if with_coverage:
            self.setup_coverage()
        
        # Run tests
        TestRunner = get_runner(settings)
        test_runner = TestRunner(verbosity=verbosity, interactive=False, keepdb=False)
        
        # Test all apps
        test_labels = [
            'tests.test_models',
            'tests.test_serializers', 
            'tests.test_views',
            'tests.test_utils',
            'accounts.tests',
            'patients.tests',
            'doctors.tests',
            'appointments.tests',
            'medical_records.tests',
            'billing.tests',
            'notifications.tests',
            'infrastructure.tests'
        ]
        
        failures = test_runner.run_tests(test_labels)
        
        self.end_time = time.time()
        
        if with_coverage:
            self.coverage.stop()
            self.generate_coverage_report()
        
        self.print_summary(failures)
        
        return failures
    
    def run_specific_tests(self, test_labels, verbosity=2):
        """Run specific test modules"""
        print(f"🧪 Running specific tests: {', '.join(test_labels)}")
        print("=" * 50)
        
        self.start_time = time.time()
        
        TestRunner = get_runner(settings)
        test_runner = TestRunner(verbosity=verbosity, interactive=False)
        failures = test_runner.run_tests(test_labels)
        
        self.end_time = time.time()
        self.print_summary(failures)
        
        return failures
    
    def run_model_tests(self):
        """Run only model tests"""
        return self.run_specific_tests(['tests.test_models'])
    
    def run_serializer_tests(self):
        """Run only serializer tests"""
        return self.run_specific_tests(['tests.test_serializers'])
    
    def run_view_tests(self):
        """Run only view tests"""
        return self.run_specific_tests(['tests.test_views'])
    
    def run_utility_tests(self):
        """Run only utility/service tests"""
        return self.run_specific_tests(['tests.test_utils'])
    
    def run_app_tests(self, app_name):
        """Run tests for a specific app"""
        return self.run_specific_tests([f'{app_name}.tests'])
    
    def generate_coverage_report(self):
        """Generate coverage report"""
        print("\n" + "=" * 50)
        print("📊 CODE COVERAGE REPORT")
        print("=" * 50)
        
        # Console report
        self.coverage.report(show_missing=True)
        
        # HTML report
        try:
            html_dir = 'htmlcov'
            self.coverage.html_report(directory=html_dir)
            print(f"\n📄 HTML coverage report generated in '{html_dir}/' directory")
            print(f"   Open '{html_dir}/index.html' in your browser to view detailed report")
        except Exception as e:
            print(f"❌ Error generating HTML report: {e}")
        
        # XML report for CI/CD
        try:
            self.coverage.xml_report(outfile='coverage.xml')
            print("📄 XML coverage report generated as 'coverage.xml'")
        except Exception as e:
            print(f"❌ Error generating XML report: {e}")
    
    def print_summary(self, failures):
        """Print test execution summary"""
        duration = self.end_time - self.start_time if self.start_time and self.end_time else 0
        
        print("\n" + "=" * 50)
        print("📋 TEST EXECUTION SUMMARY")
        print("=" * 50)
        print(f"⏱️  Execution time: {duration:.2f} seconds")
        print(f"📅 Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        if failures == 0:
            print("✅ All tests passed successfully!")
            print("🎉 Hospital Management System is ready for deployment!")
        else:
            print(f"❌ {failures} test(s) failed")
            print("🔧 Please fix the failing tests before deployment")
        
        print("=" * 50)


def main():
    """Main test execution function"""
    runner = HospitalTestRunner()
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == 'all':
            failures = runner.run_all_tests()
        elif command == 'models':
            failures = runner.run_model_tests()
        elif command == 'serializers':
            failures = runner.run_serializer_tests()
        elif command == 'views':
            failures = runner.run_view_tests()
        elif command == 'utils':
            failures = runner.run_utility_tests()
        elif command == 'coverage':
            failures = runner.run_all_tests(with_coverage=True)
        elif command in ['accounts', 'patients', 'doctors', 'appointments', 
                        'medical_records', 'billing', 'notifications', 'infrastructure']:
            failures = runner.run_app_tests(command)
        elif command == 'help':
            print_help()
            return 0
        else:
            print(f"❌ Unknown command: {command}")
            print_help()
            return 1
    else:
        # Default: run all tests with coverage
        failures = runner.run_all_tests(with_coverage=True)
    
    return failures


def print_help():
    """Print help information"""
    print("🏥 Hospital Management System Test Runner")
    print("=" * 50)
    print("Usage: python run_tests.py [command]")
    print()
    print("Commands:")
    print("  all          - Run all tests (default)")
    print("  coverage     - Run all tests with coverage report")
    print("  models       - Run only model tests")
    print("  serializers  - Run only serializer tests")
    print("  views        - Run only view tests")
    print("  utils        - Run only utility/service tests")
    print("  accounts     - Run accounts app tests")
    print("  patients     - Run patients app tests")
    print("  doctors      - Run doctors app tests")
    print("  appointments - Run appointments app tests")
    print("  medical_records - Run medical records app tests")
    print("  billing      - Run billing app tests")
    print("  notifications - Run notifications app tests")
    print("  infrastructure - Run infrastructure app tests")
    print("  help         - Show this help message")
    print()
    print("Examples:")
    print("  python run_tests.py all")
    print("  python run_tests.py models")
    print("  python run_tests.py accounts")
    print("  python run_tests.py coverage")


def run_quick_tests():
    """Run a quick subset of critical tests"""
    print("🚀 Running Quick Test Suite (Critical Tests Only)")
    print("=" * 50)
    
    runner = HospitalTestRunner()
    
    # Critical test modules
    critical_tests = [
        'tests.test_models.UserModelTest',
        'tests.test_models.PatientProfileModelTest',
        'tests.test_models.AppointmentModelTest',
        'tests.test_views.AuthenticationViewTest',
        'tests.test_serializers.UserSerializerTest'
    ]
    
    failures = runner.run_specific_tests(critical_tests, verbosity=1)
    
    if failures == 0:
        print("✅ Quick tests passed! System core functionality is working.")
    else:
        print("❌ Quick tests failed! Critical issues detected.")
    
    return failures


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
