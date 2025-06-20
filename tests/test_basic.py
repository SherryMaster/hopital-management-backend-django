"""
Basic unit tests for core functionality
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError

User = get_user_model()


class BasicUserModelTest(TestCase):
    """Basic test cases for User model"""
    
    def test_create_user(self):
        """Test creating a basic user"""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.assertEqual(user.username, 'testuser')
        self.assertEqual(user.email, 'test@example.com')
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
    
    def test_user_str_representation(self):
        """Test user string representation"""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='pass123',
            first_name='Test',
            last_name='User'
        )
        expected = f"{user.first_name} {user.last_name} ({user.username})"
        self.assertEqual(str(user), expected)
    
    def test_user_email_unique(self):
        """Test that email must be unique"""
        User.objects.create_user(username='user1', email='test@example.com', password='pass123')
        with self.assertRaises(IntegrityError):
            User.objects.create_user(username='user2', email='test@example.com', password='pass123')
    
    def test_user_username_unique(self):
        """Test that username must be unique"""
        User.objects.create_user(username='testuser', email='test1@example.com', password='pass123')
        with self.assertRaises(IntegrityError):
            User.objects.create_user(username='testuser', email='test2@example.com', password='pass123')


class BasicDatabaseTest(TestCase):
    """Basic database connectivity tests"""
    
    def test_database_connection(self):
        """Test that database connection works"""
        # This test will fail if database connection is broken
        user_count = User.objects.count()
        self.assertIsInstance(user_count, int)
    
    def test_create_and_retrieve_user(self):
        """Test creating and retrieving a user"""
        # Create user
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='pass123'
        )
        
        # Retrieve user
        retrieved_user = User.objects.get(username='testuser')
        self.assertEqual(user.id, retrieved_user.id)
        self.assertEqual(user.email, retrieved_user.email)
    
    def test_user_update(self):
        """Test updating user information"""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='pass123'
        )
        
        # Update user
        user.first_name = 'Updated'
        user.last_name = 'Name'
        user.save()
        
        # Verify update
        updated_user = User.objects.get(username='testuser')
        self.assertEqual(updated_user.first_name, 'Updated')
        self.assertEqual(updated_user.last_name, 'Name')
    
    def test_user_deletion(self):
        """Test deleting a user"""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='pass123'
        )
        user_id = user.id
        
        # Delete user
        user.delete()
        
        # Verify deletion
        with self.assertRaises(User.DoesNotExist):
            User.objects.get(id=user_id)


class BasicValidationTest(TestCase):
    """Basic validation tests"""
    
    def test_email_validation(self):
        """Test email validation"""
        # Valid email should work
        user = User(
            username='testuser',
            email='valid@example.com',
            password='pass123'
        )
        user.full_clean()  # Should not raise ValidationError
        
        # Invalid email should fail
        user_invalid = User(
            username='testuser2',
            email='invalid-email',
            password='pass123'
        )
        with self.assertRaises(ValidationError):
            user_invalid.full_clean()
    
    def test_required_fields(self):
        """Test required field validation"""
        # Missing username should fail
        user_no_username = User(
            email='test@example.com',
            password='pass123'
        )
        with self.assertRaises(ValidationError):
            user_no_username.full_clean()
        
        # Missing email should fail
        user_no_email = User(
            username='testuser',
            password='pass123'
        )
        with self.assertRaises(ValidationError):
            user_no_email.full_clean()


class BasicSystemTest(TestCase):
    """Basic system functionality tests"""
    
    def test_django_settings_loaded(self):
        """Test that Django settings are properly loaded"""
        from django.conf import settings
        self.assertTrue(settings.configured)
        self.assertIsNotNone(settings.SECRET_KEY)
        self.assertIsNotNone(settings.DATABASES)
    
    def test_apps_installed(self):
        """Test that required apps are installed"""
        from django.conf import settings
        
        required_apps = [
            'django.contrib.auth',
            'django.contrib.contenttypes',
            'rest_framework',
            'accounts',
            'patients',
            'doctors',
            'appointments',
            'medical_records',
            'billing',
            'notifications',
            'infrastructure'
        ]
        
        for app in required_apps:
            self.assertIn(app, settings.INSTALLED_APPS)
    
    def test_database_tables_exist(self):
        """Test that basic database tables exist"""
        from django.db import connection
        
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name LIKE 'auth_%'
            """)
            tables = cursor.fetchall()
            
        # Should have at least auth_user table
        table_names = [table[0] for table in tables]
        self.assertIn('auth_user', table_names)


class BasicAPITest(TestCase):
    """Basic API functionality tests"""
    
    def test_rest_framework_installed(self):
        """Test that Django REST Framework is properly installed"""
        try:
            from rest_framework import status
            from rest_framework.test import APIClient
            self.assertTrue(True)  # If imports work, test passes
        except ImportError:
            self.fail("Django REST Framework not properly installed")
    
    def test_api_client_creation(self):
        """Test that API client can be created"""
        from rest_framework.test import APIClient
        client = APIClient()
        self.assertIsNotNone(client)
    
    def test_jwt_tokens_configured(self):
        """Test that JWT tokens are configured"""
        try:
            from rest_framework_simplejwt.tokens import RefreshToken
            user = User.objects.create_user(
                username='testuser',
                email='test@example.com',
                password='pass123'
            )
            refresh = RefreshToken.for_user(user)
            self.assertIsNotNone(refresh)
            self.assertIsNotNone(refresh.access_token)
        except ImportError:
            self.fail("JWT tokens not properly configured")
