from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.validators import RegexValidator
import uuid


class Patient(models.Model):
    """
    Patient model extending the User model with medical-specific information
    """
    BLOOD_TYPE_CHOICES = (
        ('A+', 'A+'),
        ('A-', 'A-'),
        ('B+', 'B+'),
        ('B-', 'B-'),
        ('AB+', 'AB+'),
        ('AB-', 'AB-'),
        ('O+', 'O+'),
        ('O-', 'O-'),
    )

    MARITAL_STATUS_CHOICES = (
        ('single', 'Single'),
        ('married', 'Married'),
        ('divorced', 'Divorced'),
        ('widowed', 'Widowed'),
        ('separated', 'Separated'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='patient_profile')
    patient_id = models.CharField(max_length=20, unique=True)  # Hospital-specific patient ID

    # Medical Information
    blood_type = models.CharField(max_length=3, choices=BLOOD_TYPE_CHOICES, blank=True)
    height = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text="Height in cm")
    weight = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text="Weight in kg")

    # Personal Information
    marital_status = models.CharField(max_length=20, choices=MARITAL_STATUS_CHOICES, blank=True)
    occupation = models.CharField(max_length=100, blank=True)
    employer = models.CharField(max_length=100, blank=True)

    # Medical History
    allergies = models.TextField(blank=True, help_text="List of known allergies")
    chronic_conditions = models.TextField(blank=True, help_text="List of chronic medical conditions")
    current_medications = models.TextField(blank=True, help_text="Current medications and dosages")
    family_medical_history = models.TextField(blank=True)

    # Registration Information
    registration_date = models.DateTimeField(default=timezone.now)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True, help_text="Additional notes about the patient")

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['patient_id']
        indexes = [
            models.Index(fields=['patient_id']),
            models.Index(fields=['user']),
            models.Index(fields=['registration_date']),
        ]

    def __str__(self):
        return f"{self.patient_id} - {self.user.get_full_name()}"

    @property
    def bmi(self):
        """Calculate BMI if height and weight are available"""
        if self.height and self.weight:
            height_m = float(self.height) / 100  # Convert cm to meters
            return round(float(self.weight) / (height_m ** 2), 2)
        return None

    def save(self, *args, **kwargs):
        if not self.patient_id:
            # Generate patient ID if not provided
            last_patient = Patient.objects.order_by('id').last()
            if last_patient:
                last_id = int(last_patient.patient_id.split('P')[1])
                self.patient_id = f'P{last_id + 1:06d}'
            else:
                self.patient_id = 'P000001'
        super().save(*args, **kwargs)


class EmergencyContact(models.Model):
    """
    Emergency contact information for patients
    """
    RELATIONSHIP_CHOICES = (
        ('spouse', 'Spouse'),
        ('parent', 'Parent'),
        ('child', 'Child'),
        ('sibling', 'Sibling'),
        ('friend', 'Friend'),
        ('guardian', 'Guardian'),
        ('other', 'Other'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='emergency_contacts')
    name = models.CharField(max_length=100)
    relationship = models.CharField(max_length=20, choices=RELATIONSHIP_CHOICES)
    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
    )
    primary_phone = models.CharField(validators=[phone_regex], max_length=17)
    secondary_phone = models.CharField(validators=[phone_regex], max_length=17, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    is_primary = models.BooleanField(default=False)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_primary', 'name']

    def __str__(self):
        return f"{self.name} ({self.relationship}) - {self.patient.patient_id}"


class InsuranceInformation(models.Model):
    """
    Insurance information for patients
    """
    INSURANCE_TYPE_CHOICES = (
        ('primary', 'Primary'),
        ('secondary', 'Secondary'),
        ('tertiary', 'Tertiary'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='insurance_info')
    insurance_type = models.CharField(max_length=20, choices=INSURANCE_TYPE_CHOICES, default='primary')

    # Insurance Details
    provider_name = models.CharField(max_length=100)
    policy_number = models.CharField(max_length=50)
    group_number = models.CharField(max_length=50, blank=True)
    subscriber_name = models.CharField(max_length=100)
    subscriber_id = models.CharField(max_length=50)
    relationship_to_subscriber = models.CharField(max_length=50, default='self')

    # Coverage Details
    effective_date = models.DateField()
    expiration_date = models.DateField(null=True, blank=True)
    copay_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    deductible_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    # Contact Information
    provider_phone = models.CharField(max_length=17, blank=True)
    provider_address = models.TextField(blank=True)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['insurance_type', 'provider_name']
        unique_together = ['patient', 'insurance_type']

    def __str__(self):
        return f"{self.provider_name} ({self.insurance_type}) - {self.patient.patient_id}"
