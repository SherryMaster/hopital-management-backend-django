from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.exceptions import ValidationError
import uuid


class AppointmentType(models.Model):
    """
    Types of appointments (consultation, follow-up, emergency, etc.)
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    duration_minutes = models.PositiveIntegerField(default=30)
    color_code = models.CharField(max_length=7, default='#007bff', help_text="Hex color code for calendar display")
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Appointment(models.Model):
    """
    Main appointment model
    """
    STATUS_CHOICES = (
        ('scheduled', 'Scheduled'),
        ('confirmed', 'Confirmed'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('no_show', 'No Show'),
        ('rescheduled', 'Rescheduled'),
    )

    PRIORITY_CHOICES = (
        ('low', 'Low'),
        ('normal', 'Normal'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    appointment_number = models.CharField(max_length=20, unique=True)

    # Core appointment details
    patient = models.ForeignKey('patients.Patient', on_delete=models.CASCADE, related_name='appointments')
    doctor = models.ForeignKey('doctors.Doctor', on_delete=models.CASCADE, related_name='appointments')
    appointment_type = models.ForeignKey(AppointmentType, on_delete=models.SET_NULL, null=True)

    # Scheduling
    appointment_date = models.DateField()
    appointment_time = models.TimeField()
    duration_minutes = models.PositiveIntegerField(default=30)

    # Status and priority
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='normal')

    # Details
    reason_for_visit = models.TextField()
    symptoms = models.TextField(blank=True)
    notes = models.TextField(blank=True)

    # Tracking
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='created_appointments')
    checked_in_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    # Follow-up
    follow_up_required = models.BooleanField(default=False)
    follow_up_date = models.DateField(null=True, blank=True)
    follow_up_notes = models.TextField(blank=True)

    # Recurring appointments
    is_recurring = models.BooleanField(default=False)
    recurring_pattern = models.ForeignKey('RecurringPattern', on_delete=models.SET_NULL, null=True, blank=True)
    parent_appointment = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='recurring_instances')

    # Cancellation tracking
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancellation_reason = models.TextField(blank=True)
    cancelled_by = models.CharField(max_length=20, blank=True)  # 'patient', 'doctor', 'staff', 'system'
    no_show_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['appointment_date', 'appointment_time']
        indexes = [
            models.Index(fields=['appointment_date', 'appointment_time']),
            models.Index(fields=['patient', 'appointment_date']),
            models.Index(fields=['doctor', 'appointment_date']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.appointment_number} - {self.patient.user.get_full_name()} with Dr. {self.doctor.user.get_full_name()}"

    def clean(self):
        """Validate appointment scheduling"""
        if self.appointment_date and self.appointment_time:
            # Check for overlapping appointments with the same doctor
            overlapping = Appointment.objects.filter(
                doctor=self.doctor,
                appointment_date=self.appointment_date,
                status__in=['scheduled', 'confirmed', 'in_progress']
            ).exclude(id=self.id)

            appointment_start = timezone.datetime.combine(self.appointment_date, self.appointment_time)
            appointment_end = appointment_start + timezone.timedelta(minutes=self.duration_minutes)

            for apt in overlapping:
                existing_start = timezone.datetime.combine(apt.appointment_date, apt.appointment_time)
                existing_end = existing_start + timezone.timedelta(minutes=apt.duration_minutes)

                if (appointment_start < existing_end and appointment_end > existing_start):
                    raise ValidationError(
                        f"This appointment overlaps with an existing appointment from {existing_start.time()} to {existing_end.time()}"
                    )

    def save(self, *args, **kwargs):
        if not self.appointment_number:
            # Simple appointment number generation for debugging
            import random
            self.appointment_number = f'APT{random.randint(100000, 999999)}'

        if self.appointment_type and not self.duration_minutes:
            self.duration_minutes = self.appointment_type.duration_minutes

        # Skip clean() for now to avoid double validation
        # self.clean()
        super().save(*args, **kwargs)


class RecurringPattern(models.Model):
    """
    Defines patterns for recurring appointments
    """
    FREQUENCY_CHOICES = (
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('biweekly', 'Bi-weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('yearly', 'Yearly'),
    )

    WEEKDAY_CHOICES = (
        (0, 'Monday'),
        (1, 'Tuesday'),
        (2, 'Wednesday'),
        (3, 'Thursday'),
        (4, 'Friday'),
        (5, 'Saturday'),
        (6, 'Sunday'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES)
    interval = models.PositiveIntegerField(default=1, help_text="Repeat every X intervals")

    # For weekly patterns
    weekdays = models.JSONField(default=list, blank=True, help_text="List of weekday numbers (0=Monday, 6=Sunday)")

    # For monthly patterns
    day_of_month = models.PositiveIntegerField(null=True, blank=True, help_text="Day of month (1-31)")
    week_of_month = models.PositiveIntegerField(null=True, blank=True, help_text="Week of month (1-4)")
    weekday_of_month = models.IntegerField(null=True, blank=True, choices=WEEKDAY_CHOICES, help_text="Weekday of month")

    # End conditions
    end_date = models.DateField(null=True, blank=True, help_text="End date for recurring pattern")
    max_occurrences = models.PositiveIntegerField(null=True, blank=True, help_text="Maximum number of occurrences")

    # Metadata
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} - {self.get_frequency_display()}"


class AppointmentHistory(models.Model):
    """
    Track changes to appointments for audit purposes
    """
    ACTION_CHOICES = (
        ('created', 'Created'),
        ('updated', 'Updated'),
        ('cancelled', 'Cancelled'),
        ('rescheduled', 'Rescheduled'),
        ('completed', 'Completed'),
        ('no_show', 'No Show'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    appointment = models.ForeignKey(Appointment, on_delete=models.CASCADE, related_name='history')
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    old_values = models.JSONField(null=True, blank=True)
    new_values = models.JSONField(null=True, blank=True)
    reason = models.TextField(blank=True)
    performed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    timestamp = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.appointment.appointment_number} - {self.action} - {self.timestamp}"


class AppointmentReminder(models.Model):
    """
    Appointment reminders
    """
    REMINDER_TYPES = (
        ('email', 'Email'),
        ('sms', 'SMS'),
        ('phone', 'Phone Call'),
        ('push', 'Push Notification'),
    )

    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    appointment = models.ForeignKey(Appointment, on_delete=models.CASCADE, related_name='reminders')
    reminder_type = models.CharField(max_length=20, choices=REMINDER_TYPES)
    scheduled_time = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    sent_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['scheduled_time']

    def __str__(self):
        return f"{self.appointment.appointment_number} - {self.reminder_type} - {self.scheduled_time}"
