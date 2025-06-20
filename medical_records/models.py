from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid


class MedicalRecord(models.Model):
    """
    Main medical record for each patient visit/appointment
    """
    RECORD_TYPES = (
        ('consultation', 'Consultation'),
        ('emergency', 'Emergency'),
        ('surgery', 'Surgery'),
        ('lab_result', 'Lab Result'),
        ('imaging', 'Imaging'),
        ('discharge', 'Discharge Summary'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    record_number = models.CharField(max_length=20, unique=True)
    patient = models.ForeignKey('patients.Patient', on_delete=models.CASCADE, related_name='medical_records')
    doctor = models.ForeignKey('doctors.Doctor', on_delete=models.CASCADE, related_name='medical_records')
    appointment = models.ForeignKey('appointments.Appointment', on_delete=models.SET_NULL, null=True, blank=True)

    record_type = models.CharField(max_length=20, choices=RECORD_TYPES, default='consultation')
    record_date = models.DateTimeField(default=timezone.now)

    # Chief complaint and history
    chief_complaint = models.TextField()
    history_of_present_illness = models.TextField(blank=True)
    past_medical_history = models.TextField(blank=True)
    family_history = models.TextField(blank=True)
    social_history = models.TextField(blank=True)

    # Physical examination
    physical_examination = models.TextField(blank=True)

    # Assessment and plan
    assessment = models.TextField(blank=True)
    treatment_plan = models.TextField(blank=True)

    # Additional notes
    notes = models.TextField(blank=True)

    # Status
    is_finalized = models.BooleanField(default=False)
    finalized_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-record_date']
        indexes = [
            models.Index(fields=['patient', 'record_date']),
            models.Index(fields=['doctor', 'record_date']),
            models.Index(fields=['record_type']),
        ]

    def __str__(self):
        return f"{self.record_number} - {self.patient.user.get_full_name()}"

    def save(self, *args, **kwargs):
        if not self.record_number:
            # Generate record number if not provided
            today = timezone.now().date()
            today_records = MedicalRecord.objects.filter(
                record_date__date=today
            ).count()
            self.record_number = f'MR{today.strftime("%Y%m%d")}{today_records + 1:04d}'
        super().save(*args, **kwargs)


class VitalSigns(models.Model):
    """
    Patient vital signs
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    medical_record = models.ForeignKey(MedicalRecord, on_delete=models.CASCADE, related_name='vital_signs')

    # Vital measurements
    temperature = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True, help_text="Temperature in Celsius")
    blood_pressure_systolic = models.PositiveIntegerField(null=True, blank=True)
    blood_pressure_diastolic = models.PositiveIntegerField(null=True, blank=True)
    heart_rate = models.PositiveIntegerField(null=True, blank=True, help_text="Beats per minute")
    respiratory_rate = models.PositiveIntegerField(null=True, blank=True, help_text="Breaths per minute")
    oxygen_saturation = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text="SpO2 percentage")
    height = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text="Height in cm")
    weight = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text="Weight in kg")

    # Additional measurements
    pain_scale = models.PositiveIntegerField(
        null=True, blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(10)],
        help_text="Pain scale 0-10"
    )

    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    recorded_at = models.DateTimeField(default=timezone.now)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-recorded_at']

    def __str__(self):
        return f"Vitals for {self.medical_record.patient.user.get_full_name()} - {self.recorded_at}"

    @property
    def bmi(self):
        """Calculate BMI if height and weight are available"""
        if self.height and self.weight:
            height_m = float(self.height) / 100  # Convert cm to meters
            return round(float(self.weight) / (height_m ** 2), 2)
        return None


class Diagnosis(models.Model):
    """
    Medical diagnoses
    """
    DIAGNOSIS_TYPES = (
        ('primary', 'Primary'),
        ('secondary', 'Secondary'),
        ('differential', 'Differential'),
        ('rule_out', 'Rule Out'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    medical_record = models.ForeignKey(MedicalRecord, on_delete=models.CASCADE, related_name='diagnoses')

    # ICD-10 coding
    icd10_code = models.CharField(max_length=10, blank=True)
    diagnosis_name = models.CharField(max_length=200)
    diagnosis_type = models.CharField(max_length=20, choices=DIAGNOSIS_TYPES, default='primary')

    description = models.TextField(blank=True)
    severity = models.CharField(max_length=50, blank=True)
    onset_date = models.DateField(null=True, blank=True)

    # Status
    is_chronic = models.BooleanField(default=False)
    is_resolved = models.BooleanField(default=False)
    resolution_date = models.DateField(null=True, blank=True)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['diagnosis_type', 'diagnosis_name']

    def __str__(self):
        return f"{self.diagnosis_name} ({self.diagnosis_type})"


class Prescription(models.Model):
    """
    Medication prescriptions
    """
    STATUS_CHOICES = (
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('discontinued', 'Discontinued'),
        ('on_hold', 'On Hold'),
    )

    FREQUENCY_CHOICES = (
        ('once_daily', 'Once Daily'),
        ('twice_daily', 'Twice Daily'),
        ('three_times_daily', 'Three Times Daily'),
        ('four_times_daily', 'Four Times Daily'),
        ('as_needed', 'As Needed'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    medical_record = models.ForeignKey(MedicalRecord, on_delete=models.CASCADE, related_name='prescriptions')

    # Medication details
    medication_name = models.CharField(max_length=200)
    generic_name = models.CharField(max_length=200, blank=True)
    dosage = models.CharField(max_length=100)
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES)
    route = models.CharField(max_length=50, default='Oral')  # Oral, IV, IM, etc.

    # Prescription details
    quantity = models.PositiveIntegerField()
    refills = models.PositiveIntegerField(default=0)
    start_date = models.DateField(default=timezone.now)
    end_date = models.DateField(null=True, blank=True)

    # Instructions
    instructions = models.TextField()
    special_instructions = models.TextField(blank=True)

    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')

    # Pharmacy information
    pharmacy_name = models.CharField(max_length=100, blank=True)
    pharmacy_phone = models.CharField(max_length=17, blank=True)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.medication_name} - {self.dosage} - {self.frequency}"


class LabTest(models.Model):
    """
    Laboratory tests and results
    """
    STATUS_CHOICES = (
        ('ordered', 'Ordered'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    )

    PRIORITY_CHOICES = (
        ('routine', 'Routine'),
        ('urgent', 'Urgent'),
        ('stat', 'STAT'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    medical_record = models.ForeignKey(MedicalRecord, on_delete=models.CASCADE, related_name='lab_tests')

    # Test details
    test_name = models.CharField(max_length=200)
    test_code = models.CharField(max_length=50, blank=True)
    category = models.CharField(max_length=100, blank=True)

    # Ordering information
    ordered_by = models.ForeignKey('doctors.Doctor', on_delete=models.CASCADE, related_name='ordered_lab_tests')
    ordered_date = models.DateTimeField(default=timezone.now)
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='routine')

    # Collection and processing
    specimen_type = models.CharField(max_length=100, blank=True)
    collection_date = models.DateTimeField(null=True, blank=True)
    collected_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='collected_lab_tests')

    # Results
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ordered')
    result_value = models.TextField(blank=True)
    reference_range = models.CharField(max_length=100, blank=True)
    units = models.CharField(max_length=50, blank=True)
    is_abnormal = models.BooleanField(default=False)

    # Reporting
    result_date = models.DateTimeField(null=True, blank=True)
    reported_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='reported_lab_tests')
    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-ordered_date']

    def __str__(self):
        return f"{self.test_name} - {self.medical_record.patient.user.get_full_name()}"


class MedicalDocument(models.Model):
    """
    Medical documents and files
    """
    DOCUMENT_TYPES = (
        ('lab_report', 'Lab Report'),
        ('imaging', 'Imaging'),
        ('discharge_summary', 'Discharge Summary'),
        ('referral', 'Referral'),
        ('consent_form', 'Consent Form'),
        ('insurance_document', 'Insurance Document'),
        ('other', 'Other'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    medical_record = models.ForeignKey(MedicalRecord, on_delete=models.CASCADE, related_name='documents')

    # Document details
    title = models.CharField(max_length=200)
    document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPES)
    description = models.TextField(blank=True)

    # File information
    file = models.FileField(upload_to='medical_documents/')
    file_size = models.PositiveIntegerField(null=True, blank=True)
    mime_type = models.CharField(max_length=100, blank=True)

    # Metadata
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    upload_date = models.DateTimeField(default=timezone.now)
    is_confidential = models.BooleanField(default=True)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-upload_date']

    def __str__(self):
        return f"{self.title} - {self.document_type}"


# Import alert models
from .alert_models import MedicalAlert, PatientAllergy, DrugInteraction, CriticalCondition
