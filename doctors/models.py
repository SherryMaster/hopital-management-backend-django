from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.validators import RegexValidator, MinValueValidator, MaxValueValidator
import uuid


class Specialization(models.Model):
    """
    Medical specializations
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Department(models.Model):
    """
    Hospital departments
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    head_of_department = models.ForeignKey(
        'Doctor',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='headed_departments'
    )
    location = models.CharField(max_length=100, blank=True)
    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
    )
    phone_number = models.CharField(validators=[phone_regex], max_length=17, blank=True)
    email = models.EmailField(blank=True)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Doctor(models.Model):
    """
    Doctor model extending the User model with medical professional information
    """
    STATUS_CHOICES = (
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('on_leave', 'On Leave'),
        ('suspended', 'Suspended'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='doctor_profile')
    doctor_id = models.CharField(max_length=20, unique=True)  # Hospital-specific doctor ID

    # Professional Information
    medical_license_number = models.CharField(max_length=50, unique=True)
    license_expiry_date = models.DateField()
    specializations = models.ManyToManyField(Specialization, related_name='doctors')
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, related_name='doctors')

    # Employment Information
    hire_date = models.DateField()
    employment_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    consultation_fee = models.DecimalField(max_digits=10, decimal_places=2)

    # Professional Details
    years_of_experience = models.PositiveIntegerField(validators=[MinValueValidator(0), MaxValueValidator(70)])
    bio = models.TextField(blank=True)
    languages_spoken = models.CharField(max_length=200, blank=True, help_text="Comma-separated list of languages")

    # Availability
    is_available_for_consultation = models.BooleanField(default=True)
    max_patients_per_day = models.PositiveIntegerField(default=20)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['doctor_id']
        indexes = [
            models.Index(fields=['doctor_id']),
            models.Index(fields=['user']),
            models.Index(fields=['employment_status']),
        ]

    def __str__(self):
        return f"Dr. {self.user.get_full_name()} ({self.doctor_id})"

    def save(self, *args, **kwargs):
        if not self.doctor_id:
            # Generate doctor ID if not provided
            last_doctor = Doctor.objects.order_by('id').last()
            if last_doctor:
                last_id = int(last_doctor.doctor_id.split('D')[1])
                self.doctor_id = f'D{last_id + 1:06d}'
            else:
                self.doctor_id = 'D000001'
        super().save(*args, **kwargs)


class DoctorQualification(models.Model):
    """
    Educational qualifications and certifications for doctors
    """
    QUALIFICATION_TYPES = (
        ('degree', 'Degree'),
        ('diploma', 'Diploma'),
        ('certificate', 'Certificate'),
        ('fellowship', 'Fellowship'),
        ('residency', 'Residency'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='qualifications')
    qualification_type = models.CharField(max_length=20, choices=QUALIFICATION_TYPES)
    degree_name = models.CharField(max_length=100)
    institution = models.CharField(max_length=200)
    year_obtained = models.PositiveIntegerField()
    grade_or_score = models.CharField(max_length=50, blank=True)
    certificate_file = models.FileField(upload_to='doctor_certificates/', null=True, blank=True)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-year_obtained']

    def __str__(self):
        return f"{self.degree_name} - {self.doctor.user.get_full_name()}"


class DoctorAvailability(models.Model):
    """
    Doctor availability schedule
    """
    DAYS_OF_WEEK = (
        (0, 'Monday'),
        (1, 'Tuesday'),
        (2, 'Wednesday'),
        (3, 'Thursday'),
        (4, 'Friday'),
        (5, 'Saturday'),
        (6, 'Sunday'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='availability_schedule')
    day_of_week = models.IntegerField(choices=DAYS_OF_WEEK)
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_available = models.BooleanField(default=True)

    # Break times
    break_start_time = models.TimeField(null=True, blank=True)
    break_end_time = models.TimeField(null=True, blank=True)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['doctor', 'day_of_week']
        ordering = ['day_of_week', 'start_time']

    def __str__(self):
        return f"{self.doctor.user.get_full_name()} - {self.get_day_of_week_display()}"
