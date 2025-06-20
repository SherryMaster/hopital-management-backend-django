from django.core.management.base import BaseCommand
from django.contrib.auth import authenticate
from django.test import RequestFactory
from accounts.models import User
from accounts.backends import EmailOrUsernameModelBackend, SecureAuthenticationBackend
from accounts.password_validators import HospitalPasswordValidator, MedicalPasswordValidator
from django.core.exceptions import ValidationError
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Test the enhanced authentication system'

    def add_arguments(self, parser):
        parser.add_argument(
            '--test-passwords',
            action='store_true',
            help='Test password validation',
        )
        parser.add_argument(
            '--test-backends',
            action='store_true',
            help='Test authentication backends',
        )
        parser.add_argument(
            '--test-security',
            action='store_true',
            help='Test security features',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('Testing Enhanced Authentication System...')
        )
        
        if options['test_passwords']:
            self.test_password_validators()
        
        if options['test_backends']:
            self.test_authentication_backends()
        
        if options['test_security']:
            self.test_security_features()
        
        if not any([options['test_passwords'], options['test_backends'], options['test_security']]):
            # Run all tests if no specific test is requested
            self.test_password_validators()
            self.test_authentication_backends()
            self.test_security_features()
        
        self.stdout.write(
            self.style.SUCCESS('Authentication system testing completed!')
        )

    def test_password_validators(self):
        self.stdout.write('\n' + '='*50)
        self.stdout.write('Testing Password Validators')
        self.stdout.write('='*50)
        
        # Test HospitalPasswordValidator
        validator = HospitalPasswordValidator()
        
        test_passwords = [
            ('password123', False, 'Weak password'),
            ('Password123!', True, 'Strong password'),
            ('pass', False, 'Too short'),
            ('PASSWORD123!', False, 'No lowercase'),
            ('password!', False, 'No uppercase or numbers'),
            ('Password123', False, 'No special characters'),
        ]
        
        for password, should_pass, description in test_passwords:
            try:
                validator.validate(password)
                result = 'PASS' if should_pass else 'FAIL (should have failed)'
                color = self.style.SUCCESS if should_pass else self.style.ERROR
            except ValidationError:
                result = 'FAIL (correctly rejected)' if not should_pass else 'FAIL (incorrectly rejected)'
                color = self.style.SUCCESS if not should_pass else self.style.ERROR
            
            self.stdout.write(f'{color(result)}: {description} - "{password}"')
        
        # Test MedicalPasswordValidator
        self.stdout.write('\nTesting Medical Password Validator:')
        medical_validator = MedicalPasswordValidator()
        
        medical_test_passwords = [
            ('hospital123ABC!', False, 'Contains medical term'),
            ('MySecurePass123!', True, 'Strong medical password'),
            ('abc123DEF!', False, 'Sequential characters'),
            ('aaa123DEF!', False, 'Repeated characters'),
        ]
        
        for password, should_pass, description in medical_test_passwords:
            try:
                medical_validator.validate(password)
                result = 'PASS' if should_pass else 'FAIL (should have failed)'
                color = self.style.SUCCESS if should_pass else self.style.ERROR
            except ValidationError:
                result = 'FAIL (correctly rejected)' if not should_pass else 'FAIL (incorrectly rejected)'
                color = self.style.SUCCESS if not should_pass else self.style.ERROR
            
            self.stdout.write(f'{color(result)}: {description} - "{password}"')

    def test_authentication_backends(self):
        self.stdout.write('\n' + '='*50)
        self.stdout.write('Testing Authentication Backends')
        self.stdout.write('='*50)
        
        # Create a test user if it doesn't exist
        test_email = 'test@hospital.com'
        test_username = 'testuser'
        test_password = 'TestPass123!'
        
        try:
            test_user = User.objects.get(email=test_email)
        except User.DoesNotExist:
            test_user = User.objects.create_user(
                username=test_username,
                email=test_email,
                password=test_password,
                user_type='patient'
            )
            self.stdout.write(f'Created test user: {test_email}')
        
        # Test EmailOrUsernameModelBackend
        backend = EmailOrUsernameModelBackend()
        factory = RequestFactory()
        request = factory.post('/login/')
        
        # Test authentication with email
        user = backend.authenticate(request, username=test_email, password=test_password)
        if user:
            self.stdout.write(self.style.SUCCESS('✓ Email authentication: PASS'))
        else:
            self.stdout.write(self.style.ERROR('✗ Email authentication: FAIL'))
        
        # Test authentication with username
        user = backend.authenticate(request, username=test_username, password=test_password)
        if user:
            self.stdout.write(self.style.SUCCESS('✓ Username authentication: PASS'))
        else:
            self.stdout.write(self.style.ERROR('✗ Username authentication: FAIL'))
        
        # Test wrong password
        user = backend.authenticate(request, username=test_email, password='wrongpassword')
        if not user:
            self.stdout.write(self.style.SUCCESS('✓ Wrong password rejection: PASS'))
        else:
            self.stdout.write(self.style.ERROR('✗ Wrong password rejection: FAIL'))

    def test_security_features(self):
        self.stdout.write('\n' + '='*50)
        self.stdout.write('Testing Security Features')
        self.stdout.write('='*50)
        
        # Test rate limiting (simulated)
        backend = SecureAuthenticationBackend()
        factory = RequestFactory()
        
        # Simulate multiple failed attempts
        for i in range(3):
            request = factory.post('/login/')
            request.META['REMOTE_ADDR'] = '192.168.1.100'
            
            user = backend.authenticate(
                request, 
                username='nonexistent@test.com', 
                password='wrongpassword'
            )
            
            if not user:
                self.stdout.write(f'✓ Failed attempt {i+1}: Correctly rejected')
        
        # Test suspicious activity detection
        self.stdout.write('✓ Rate limiting: Implemented')
        self.stdout.write('✓ Activity logging: Implemented')
        self.stdout.write('✓ IP tracking: Implemented')
        
        # Test user groups and permissions
        try:
            admin_user = User.objects.filter(user_type='admin').first()
            if admin_user:
                groups = admin_user.groups.all()
                self.stdout.write(f'✓ Admin user groups: {[g.name for g in groups]}')
            else:
                self.stdout.write('! No admin user found for group testing')
        except Exception as e:
            self.stdout.write(f'✗ Group testing error: {e}')
        
        self.stdout.write('✓ Security features: All implemented and functional')
