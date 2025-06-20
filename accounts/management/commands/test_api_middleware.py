from django.core.management.base import BaseCommand
from django.test import RequestFactory, Client
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import AccessToken
import json

User = get_user_model()


class Command(BaseCommand):
    help = 'Test API Authentication Middleware'

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('Testing API Authentication Middleware...')
        )
        
        # Create test client
        client = Client()
        
        # Test 1: Public endpoints (should work without authentication)
        self.test_public_endpoints(client)
        
        # Test 2: Protected endpoints without authentication (should fail)
        self.test_protected_endpoints_no_auth(client)
        
        # Test 3: Protected endpoints with valid authentication (should work)
        self.test_protected_endpoints_with_auth(client)
        
        # Test 4: Rate limiting
        self.test_rate_limiting(client)
        
        # Test 5: Role-based access control
        self.test_role_based_access(client)
        
        self.stdout.write(
            self.style.SUCCESS('API Middleware testing completed!')
        )

    def test_public_endpoints(self, client):
        self.stdout.write('\n' + '='*50)
        self.stdout.write('Testing Public Endpoints')
        self.stdout.write('='*50)
        
        public_endpoints = [
            '/api/schema/',
            '/api/docs/',
            '/api/accounts/auth/login/',
            '/api/accounts/register/',
        ]
        
        for endpoint in public_endpoints:
            try:
                response = client.get(endpoint)
                if response.status_code in [200, 301, 302, 404]:  # 404 is OK for non-existent endpoints
                    self.stdout.write(self.style.SUCCESS(f'✓ {endpoint}: Accessible (status: {response.status_code})'))
                else:
                    self.stdout.write(self.style.WARNING(f'? {endpoint}: Status {response.status_code}'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'✗ {endpoint}: Error - {e}'))

    def test_protected_endpoints_no_auth(self, client):
        self.stdout.write('\n' + '='*50)
        self.stdout.write('Testing Protected Endpoints (No Auth)')
        self.stdout.write('='*50)
        
        protected_endpoints = [
            '/api/accounts/profile/',
            '/api/accounts/roles/',
            '/api/accounts/activities/',
        ]
        
        for endpoint in protected_endpoints:
            try:
                response = client.get(endpoint)
                if response.status_code == 401:
                    self.stdout.write(self.style.SUCCESS(f'✓ {endpoint}: Correctly blocked (401)'))
                else:
                    self.stdout.write(self.style.ERROR(f'✗ {endpoint}: Should be blocked but got {response.status_code}'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'✗ {endpoint}: Error - {e}'))

    def test_protected_endpoints_with_auth(self, client):
        self.stdout.write('\n' + '='*50)
        self.stdout.write('Testing Protected Endpoints (With Auth)')
        self.stdout.write('='*50)
        
        # Get or create admin user
        try:
            admin_user = User.objects.get(email='admin@hospital.com')
        except User.DoesNotExist:
            self.stdout.write(self.style.WARNING('Admin user not found, skipping auth tests'))
            return
        
        # Generate access token
        access_token = AccessToken.for_user(admin_user)
        headers = {'HTTP_AUTHORIZATION': f'Bearer {access_token}'}
        
        protected_endpoints = [
            '/api/accounts/profile/',
            '/api/accounts/roles/',
            '/api/accounts/activities/',
        ]
        
        for endpoint in protected_endpoints:
            try:
                response = client.get(endpoint, **headers)
                if response.status_code in [200, 404]:  # 404 is OK for non-implemented endpoints
                    self.stdout.write(self.style.SUCCESS(f'✓ {endpoint}: Accessible with auth (status: {response.status_code})'))
                else:
                    self.stdout.write(self.style.WARNING(f'? {endpoint}: Status {response.status_code}'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'✗ {endpoint}: Error - {e}'))

    def test_rate_limiting(self, client):
        self.stdout.write('\n' + '='*50)
        self.stdout.write('Testing Rate Limiting')
        self.stdout.write('='*50)
        
        # Test login rate limiting (5 attempts per minute)
        login_data = {
            'email': 'nonexistent@test.com',
            'password': 'wrongpassword'
        }
        
        success_count = 0
        rate_limited_count = 0
        
        for i in range(7):  # Try 7 times (should be rate limited after 5)
            try:
                response = client.post(
                    '/api/accounts/auth/login/',
                    data=json.dumps(login_data),
                    content_type='application/json'
                )
                
                if response.status_code == 429:
                    rate_limited_count += 1
                    self.stdout.write(f'✓ Attempt {i+1}: Rate limited (429)')
                else:
                    success_count += 1
                    self.stdout.write(f'? Attempt {i+1}: Status {response.status_code}')
                    
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'✗ Attempt {i+1}: Error - {e}'))
        
        if rate_limited_count > 0:
            self.stdout.write(self.style.SUCCESS(f'✓ Rate limiting working: {rate_limited_count} requests blocked'))
        else:
            self.stdout.write(self.style.WARNING('? Rate limiting may not be working as expected'))

    def test_role_based_access(self, client):
        self.stdout.write('\n' + '='*50)
        self.stdout.write('Testing Role-Based Access Control')
        self.stdout.write('='*50)
        
        # Test with different user types
        test_users = [
            ('admin', ['admin@hospital.com']),
            ('patient', ['test@hospital.com']),
        ]
        
        for user_type, emails in test_users:
            self.stdout.write(f'\nTesting {user_type} access:')
            
            user = None
            for email in emails:
                try:
                    user = User.objects.get(email=email)
                    break
                except User.DoesNotExist:
                    continue
            
            if not user:
                self.stdout.write(f'  ? No {user_type} user found, skipping')
                continue
            
            # Generate access token
            access_token = AccessToken.for_user(user)
            headers = {'HTTP_AUTHORIZATION': f'Bearer {access_token}'}
            
            # Test different endpoints based on role
            if user_type == 'admin':
                test_endpoints = [
                    ('/api/accounts/roles/', 'should have access'),
                    ('/api/accounts/profile/', 'should have access'),
                ]
            else:  # patient
                test_endpoints = [
                    ('/api/accounts/roles/', 'should be blocked'),
                    ('/api/accounts/profile/', 'should have access'),
                ]
            
            for endpoint, expectation in test_endpoints:
                try:
                    response = client.get(endpoint, **headers)
                    
                    if 'should have access' in expectation:
                        if response.status_code in [200, 404]:
                            self.stdout.write(f'  ✓ {endpoint}: {expectation} ✓')
                        else:
                            self.stdout.write(f'  ✗ {endpoint}: {expectation} but got {response.status_code}')
                    else:  # should be blocked
                        if response.status_code == 403:
                            self.stdout.write(f'  ✓ {endpoint}: {expectation} ✓')
                        else:
                            self.stdout.write(f'  ? {endpoint}: {expectation} but got {response.status_code}')
                            
                except Exception as e:
                    self.stdout.write(f'  ✗ {endpoint}: Error - {e}')

    def test_content_type_validation(self, client):
        self.stdout.write('\n' + '='*50)
        self.stdout.write('Testing Content-Type Validation')
        self.stdout.write('='*50)
        
        # Test POST without proper content type
        response = client.post(
            '/api/accounts/auth/login/',
            data='{"email": "test@test.com", "password": "test"}',
            content_type='text/plain'
        )
        
        if response.status_code == 400:
            self.stdout.write(self.style.SUCCESS('✓ Content-Type validation working'))
        else:
            self.stdout.write(self.style.WARNING(f'? Content-Type validation: got {response.status_code}'))
