from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.test import Client
from django.utils import timezone
from datetime import timedelta
import json

User = get_user_model()


class Command(BaseCommand):
    help = 'Test Password Security Features'

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('Testing Password Security Features...')
        )
        
        # Create test client
        client = Client()
        
        # Test 1: Password History Tracking
        self.test_password_history()
        
        # Test 2: Account Lockout Features
        self.test_account_lockout()
        
        # Test 3: Password Reset Security
        self.test_password_reset_security(client)
        
        # Test 4: Password Validation
        self.test_password_validation()
        
        # Test 5: Rate Limiting
        self.test_rate_limiting(client)
        
        self.stdout.write(
            self.style.SUCCESS('Password Security testing completed!')
        )

    def test_password_history(self):
        self.stdout.write('\n' + '='*50)
        self.stdout.write('Testing Password History')
        self.stdout.write('='*50)
        
        try:
            # Get or create test user
            user, created = User.objects.get_or_create(
                email='test_history@hospital.com',
                defaults={
                    'username': 'test_history',
                    'user_type': 'patient'
                }
            )
            
            if created:
                user.set_password('initial_password123!')
                user.save()
                self.stdout.write('✓ Created test user for password history')
            
            # Test password history tracking
            old_password_count = user.password_history.count()
            
            # Change password
            user.set_password('new_password123!')
            user.save()
            
            new_password_count = user.password_history.count()
            
            if new_password_count > old_password_count:
                self.stdout.write('✓ Password history is being tracked')
            else:
                self.stdout.write('✗ Password history tracking failed')
            
            # Test password reuse prevention
            if user.check_password_history('initial_password123!'):
                self.stdout.write('✓ Password history check working - old password detected')
            else:
                self.stdout.write('? Password history check - old password not found')
                
        except Exception as e:
            self.stdout.write(f'✗ Password history test error: {e}')

    def test_account_lockout(self):
        self.stdout.write('\n' + '='*50)
        self.stdout.write('Testing Account Lockout')
        self.stdout.write('='*50)
        
        try:
            # Get or create test user
            user, created = User.objects.get_or_create(
                email='test_lockout@hospital.com',
                defaults={
                    'username': 'test_lockout',
                    'user_type': 'patient'
                }
            )
            
            # Test account locking
            user.lock_account(
                reason='Testing lockout functionality',
                duration_minutes=1,
                ip_address='127.0.0.1',
                failed_attempts=5
            )
            
            if user.is_account_locked():
                self.stdout.write('✓ Account lockout working')
            else:
                self.stdout.write('✗ Account lockout failed')
            
            # Test account unlocking
            user.unlock_account()
            
            if not user.is_account_locked():
                self.stdout.write('✓ Account unlock working')
            else:
                self.stdout.write('✗ Account unlock failed')
                
        except Exception as e:
            self.stdout.write(f'✗ Account lockout test error: {e}')

    def test_password_reset_security(self, client):
        self.stdout.write('\n' + '='*50)
        self.stdout.write('Testing Password Reset Security')
        self.stdout.write('='*50)
        
        try:
            # Test password reset request
            reset_data = {
                'email': 'admin@hospital.com'
            }
            
            response = client.post(
                '/api/accounts/password/reset/',
                data=json.dumps(reset_data),
                content_type='application/json'
            )
            
            if response.status_code == 200:
                self.stdout.write('✓ Password reset request successful')
                
                # Check if token was generated (in development mode)
                response_data = response.json()
                if 'token' in response_data:
                    token = response_data['token']
                    self.stdout.write(f'✓ Reset token generated: {token[:10]}...')
                    
                    # Test password reset confirmation
                    confirm_data = {
                        'token': token,
                        'new_password': 'NewSecurePassword123!',
                        'new_password_confirm': 'NewSecurePassword123!'
                    }
                    
                    confirm_response = client.post(
                        '/api/accounts/password/reset/confirm/',
                        data=json.dumps(confirm_data),
                        content_type='application/json'
                    )
                    
                    if confirm_response.status_code == 200:
                        self.stdout.write('✓ Password reset confirmation successful')
                    else:
                        self.stdout.write(f'✗ Password reset confirmation failed: {confirm_response.status_code}')
                        self.stdout.write(f'   Response: {confirm_response.content.decode()}')
                else:
                    self.stdout.write('? Reset token not in response (production mode)')
            else:
                self.stdout.write(f'✗ Password reset request failed: {response.status_code}')
                self.stdout.write(f'   Response: {response.content.decode()}')
                
        except Exception as e:
            self.stdout.write(f'✗ Password reset security test error: {e}')

    def test_password_validation(self):
        self.stdout.write('\n' + '='*50)
        self.stdout.write('Testing Password Validation')
        self.stdout.write('='*50)
        
        try:
            from django.contrib.auth.password_validation import validate_password
            from django.core.exceptions import ValidationError
            
            # Test weak passwords
            weak_passwords = [
                '123456',
                'password',
                'admin',
                'qwerty',
                '12345678'
            ]
            
            for weak_password in weak_passwords:
                try:
                    validate_password(weak_password)
                    self.stdout.write(f'✗ Weak password accepted: {weak_password}')
                except ValidationError:
                    self.stdout.write(f'✓ Weak password rejected: {weak_password}')
            
            # Test strong password
            try:
                validate_password('StrongPassword123!')
                self.stdout.write('✓ Strong password accepted')
            except ValidationError as e:
                self.stdout.write(f'? Strong password rejected: {e}')
                
        except Exception as e:
            self.stdout.write(f'✗ Password validation test error: {e}')

    def test_rate_limiting(self, client):
        self.stdout.write('\n' + '='*50)
        self.stdout.write('Testing Rate Limiting')
        self.stdout.write('='*50)
        
        try:
            # Test password reset rate limiting
            reset_data = {
                'email': 'nonexistent@test.com'
            }
            
            success_count = 0
            rate_limited_count = 0
            
            for i in range(5):  # Try 5 times
                response = client.post(
                    '/api/accounts/password/reset/',
                    data=json.dumps(reset_data),
                    content_type='application/json'
                )
                
                if response.status_code == 429:
                    rate_limited_count += 1
                    self.stdout.write(f'✓ Request {i+1}: Rate limited (429)')
                elif response.status_code == 200:
                    success_count += 1
                    self.stdout.write(f'? Request {i+1}: Successful (200)')
                else:
                    self.stdout.write(f'? Request {i+1}: Status {response.status_code}')
            
            if rate_limited_count > 0:
                self.stdout.write(f'✓ Rate limiting working: {rate_limited_count} requests blocked')
            else:
                self.stdout.write('? Rate limiting may not be working as expected')
                
        except Exception as e:
            self.stdout.write(f'✗ Rate limiting test error: {e}')

    def test_security_features_summary(self):
        self.stdout.write('\n' + '='*50)
        self.stdout.write('Security Features Summary')
        self.stdout.write('='*50)
        
        features = [
            'Password History Tracking',
            'Account Lockout Protection',
            'Secure Password Reset Tokens',
            'Rate Limiting',
            'Password Strength Validation',
            'JWT Token Authentication',
            'Role-Based Access Control',
            'Activity Logging',
            'Session Management'
        ]
        
        for feature in features:
            self.stdout.write(f'✓ {feature}')
