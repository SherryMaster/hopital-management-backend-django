from django.contrib.auth.models import AbstractUser, Group
from django.db import models
from django.core.validators import RegexValidator
from django.utils import timezone
import uuid


class User(AbstractUser):
    """
    Custom User model extending Django's AbstractUser
    """
    USER_TYPES = (
        ('admin', 'Administrator'),
        ('doctor', 'Doctor'),
        ('nurse', 'Nurse'),
        ('receptionist', 'Receptionist'),
        ('patient', 'Patient'),
        ('lab_technician', 'Lab Technician'),
        ('pharmacist', 'Pharmacist'),
    )

    GENDER_CHOICES = (
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_type = models.CharField(max_length=20, choices=USER_TYPES)
    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
    )
    phone_number = models.CharField(validators=[phone_regex], max_length=17, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True)
    address = models.TextField(blank=True)
    profile_picture = models.ImageField(upload_to='profile_pictures/', null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    # Emergency contact information
    emergency_contact_name = models.CharField(max_length=100, blank=True)
    emergency_contact_phone = models.CharField(validators=[phone_regex], max_length=17, blank=True)
    emergency_contact_relationship = models.CharField(max_length=50, blank=True)

    class Meta:
        db_table = 'accounts_user'

    def __str__(self):
        return f"{self.get_full_name()} ({self.user_type})"

    @property
    def age(self):
        if self.date_of_birth:
            today = timezone.now().date()
            return today.year - self.date_of_birth.year - ((today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day))
        return None

    def save(self, *args, **kwargs):
        """
        Override save method to automatically assign user to appropriate group
        and track password history
        """
        is_new = self.pk is None
        old_user_type = None
        old_password = None

        if not is_new:
            # Get the old user_type and password if this is an update
            try:
                old_user = User.objects.get(pk=self.pk)
                old_user_type = old_user.user_type
                old_password = old_user.password
            except User.DoesNotExist:
                # Handle case where user doesn't exist yet
                is_new = True

        super().save(*args, **kwargs)

        # Track password history if password changed
        if not is_new and old_password and old_password != self.password:
            self._save_password_history(old_password)

        # Assign to group if new user or user_type changed
        if is_new or (old_user_type and old_user_type != self.user_type):
            self._assign_to_group()

    def _assign_to_group(self):
        """
        Assign user to appropriate group based on user_type
        """
        group_mapping = {
            'admin': 'Administrators',
            'doctor': 'Doctors',
            'nurse': 'Nurses',
            'receptionist': 'Receptionists',
            'patient': 'Patients',
            'lab_technician': 'Lab Technicians',
            'pharmacist': 'Pharmacists',
        }

        # Remove user from all existing groups
        self.groups.clear()

        # Add user to appropriate group
        group_name = group_mapping.get(self.user_type)
        if group_name:
            try:
                group = Group.objects.get(name=group_name)
                self.groups.add(group)
            except Group.DoesNotExist:
                # If group doesn't exist, create it
                from .permissions import create_user_groups
                create_user_groups()
                try:
                    group = Group.objects.get(name=group_name)
                    self.groups.add(group)
                except Group.DoesNotExist:
                    pass  # Silently fail if group still doesn't exist

    def _save_password_history(self, old_password):
        """
        Save the old password to password history
        """

        # Create password history entry
        PasswordHistory.objects.create(
            user=self,
            password_hash=old_password
        )

        # Keep only last 5 passwords
        history_limit = 5
        old_passwords = PasswordHistory.objects.filter(user=self).order_by('-created_at')
        if old_passwords.count() > history_limit:
            # Delete oldest passwords beyond the limit
            passwords_to_delete = old_passwords[history_limit:]
            PasswordHistory.objects.filter(
                id__in=[p.id for p in passwords_to_delete]
            ).delete()

    def check_password_history(self, password):
        """
        Check if password was used recently
        """
        from django.contrib.auth.hashers import check_password

        recent_passwords = self.password_history.all()[:5]  # Check last 5 passwords
        for password_entry in recent_passwords:
            if check_password(password, password_entry.password_hash):
                return True
        return False

    def is_account_locked(self):
        """
        Check if account is currently locked
        """
        active_lockouts = self.lockouts.filter(is_active=True)
        for lockout in active_lockouts:
            if lockout.is_locked():
                return True
        return False

    def lock_account(self, reason, duration_minutes=30, ip_address='127.0.0.1', failed_attempts=0):
        """
        Lock the user account for security reasons
        """
        from datetime import timedelta

        # Deactivate any existing lockouts
        self.lockouts.filter(is_active=True).update(is_active=False)

        # Create new lockout
        locked_until = timezone.now() + timedelta(minutes=duration_minutes)
        AccountLockout.objects.create(
            user=self,
            locked_until=locked_until,
            reason=reason,
            ip_address=ip_address,
            failed_attempts=failed_attempts
        )

    def unlock_account(self):
        """
        Unlock the user account
        """
        self.lockouts.filter(is_active=True).update(is_active=False)


class UserProfile(models.Model):
    """
    Extended profile information for users
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    bio = models.TextField(blank=True)
    website = models.URLField(blank=True)
    social_security_number = models.CharField(max_length=20, blank=True)
    insurance_provider = models.CharField(max_length=100, blank=True)
    insurance_policy_number = models.CharField(max_length=50, blank=True)
    preferred_language = models.CharField(max_length=20, default='English')
    user_timezone = models.CharField(max_length=50, default='UTC')
    notification_preferences = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Profile of {self.user.get_full_name()}"


class UserSession(models.Model):
    """
    Track user sessions for security and analytics
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sessions')
    session_key = models.CharField(max_length=40, unique=True)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()
    login_time = models.DateTimeField(default=timezone.now)
    logout_time = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-login_time']

    def __str__(self):
        return f"{self.user.username} - {self.login_time}"


class UserActivity(models.Model):
    """
    Log user activities for audit trail
    """
    ACTION_TYPES = (
        ('login', 'Login'),
        ('logout', 'Logout'),
        ('create', 'Create'),
        ('update', 'Update'),
        ('delete', 'Delete'),
        ('view', 'View'),
        ('download', 'Download'),
        ('upload', 'Upload'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='activities')
    action = models.CharField(max_length=20, choices=ACTION_TYPES)
    resource_type = models.CharField(max_length=50)  # e.g., 'patient', 'appointment', 'medical_record'
    resource_id = models.CharField(max_length=100, blank=True)  # ID of the resource
    description = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField()
    timestamp = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['action', 'timestamp']),
            models.Index(fields=['resource_type', 'timestamp']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.action} - {self.timestamp}"


class PasswordHistory(models.Model):
    """
    Model to track user password history for security purposes
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='password_history')
    password_hash = models.CharField(max_length=128)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Password History'
        verbose_name_plural = 'Password Histories'

    def __str__(self):
        return f"{self.user.username} - {self.created_at}"


class PasswordResetToken(models.Model):
    """
    Model to track password reset tokens with enhanced security
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reset_tokens')
    token = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.token[:10]}... - {self.created_at}"

    def is_expired(self):
        return timezone.now() > self.expires_at

    def is_valid(self):
        return not self.is_used and not self.is_expired()


class AccountLockout(models.Model):
    """
    Model to track account lockouts for security
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='lockouts')
    locked_at = models.DateTimeField(auto_now_add=True)
    locked_until = models.DateTimeField()
    reason = models.CharField(max_length=200)
    ip_address = models.GenericIPAddressField()
    failed_attempts = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-locked_at']

    def __str__(self):
        return f"{self.user.username} - Locked until {self.locked_until}"

    def is_locked(self):
        return self.is_active and timezone.now() < self.locked_until
