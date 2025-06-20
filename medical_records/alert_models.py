from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid


class MedicalAlert(models.Model):
    """
    Medical alerts for patients including allergies, drug interactions, and critical conditions
    """
    ALERT_TYPES = (
        ('allergy', 'Allergy'),
        ('drug_interaction', 'Drug Interaction'),
        ('critical_condition', 'Critical Condition'),
        ('vital_signs', 'Vital Signs Alert'),
        ('lab_result', 'Lab Result Alert'),
        ('medication_warning', 'Medication Warning'),
        ('procedure_warning', 'Procedure Warning'),
    )
    
    SEVERITY_LEVELS = (
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    )
    
    STATUS_CHOICES = (
        ('active', 'Active'),
        ('acknowledged', 'Acknowledged'),
        ('resolved', 'Resolved'),
        ('dismissed', 'Dismissed'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey('patients.Patient', on_delete=models.CASCADE, related_name='medical_alerts')
    medical_record = models.ForeignKey('MedicalRecord', on_delete=models.CASCADE, null=True, blank=True, related_name='alerts')
    
    alert_type = models.CharField(max_length=20, choices=ALERT_TYPES)
    severity = models.CharField(max_length=10, choices=SEVERITY_LEVELS)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='active')
    
    title = models.CharField(max_length=200)
    description = models.TextField()
    
    # Alert details (JSON field for flexible data)
    alert_data = models.JSONField(default=dict, blank=True)
    
    # Trigger information
    triggered_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    triggered_at = models.DateTimeField(default=timezone.now)
    
    # Resolution information
    acknowledged_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, blank=True,
        related_name='acknowledged_alerts'
    )
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, blank=True,
        related_name='resolved_alerts'
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolution_notes = models.TextField(blank=True)
    
    # Auto-dismiss settings
    auto_dismiss_after = models.DurationField(null=True, blank=True, help_text="Auto-dismiss after this duration")
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-severity', '-triggered_at']
        indexes = [
            models.Index(fields=['patient', 'status']),
            models.Index(fields=['alert_type', 'severity']),
            models.Index(fields=['triggered_at']),
        ]
    
    def __str__(self):
        return f"{self.get_alert_type_display()} - {self.title} ({self.get_severity_display()})"


class PatientAllergy(models.Model):
    """
    Patient allergies and adverse reactions
    """
    ALLERGY_TYPES = (
        ('drug', 'Drug Allergy'),
        ('food', 'Food Allergy'),
        ('environmental', 'Environmental Allergy'),
        ('latex', 'Latex Allergy'),
        ('contrast', 'Contrast Media Allergy'),
        ('other', 'Other'),
    )
    
    REACTION_SEVERITY = (
        ('mild', 'Mild'),
        ('moderate', 'Moderate'),
        ('severe', 'Severe'),
        ('life_threatening', 'Life Threatening'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey('patients.Patient', on_delete=models.CASCADE, related_name='allergy_records')
    
    allergy_type = models.CharField(max_length=20, choices=ALLERGY_TYPES)
    allergen = models.CharField(max_length=200, help_text="Name of the allergen")
    
    # Reaction details
    reaction_description = models.TextField()
    severity = models.CharField(max_length=20, choices=REACTION_SEVERITY)
    
    # Clinical details
    onset_date = models.DateField(null=True, blank=True)
    last_reaction_date = models.DateField(null=True, blank=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    verified_by_doctor = models.BooleanField(default=False)
    
    # Additional information
    notes = models.TextField(blank=True)
    treatment_given = models.TextField(blank=True, help_text="Treatment given for reaction")
    
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-severity', 'allergen']
        unique_together = ['patient', 'allergen']
    
    def __str__(self):
        return f"{self.patient.user.get_full_name()} - {self.allergen} ({self.get_severity_display()})"


class DrugInteraction(models.Model):
    """
    Drug interaction warnings and contraindications
    """
    INTERACTION_TYPES = (
        ('major', 'Major Interaction'),
        ('moderate', 'Moderate Interaction'),
        ('minor', 'Minor Interaction'),
        ('contraindication', 'Contraindication'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Drugs involved in interaction
    drug1 = models.CharField(max_length=200, help_text="First drug name")
    drug2 = models.CharField(max_length=200, help_text="Second drug name")
    
    interaction_type = models.CharField(max_length=20, choices=INTERACTION_TYPES)
    
    # Interaction details
    description = models.TextField(help_text="Description of the interaction")
    clinical_effect = models.TextField(help_text="Clinical effect of the interaction")
    mechanism = models.TextField(blank=True, help_text="Mechanism of interaction")
    
    # Management
    management_recommendation = models.TextField(help_text="Recommended management")
    
    # Severity scoring
    severity_score = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        help_text="Severity score 1-10"
    )
    
    # Evidence level
    evidence_level = models.CharField(
        max_length=20,
        choices=(
            ('established', 'Established'),
            ('probable', 'Probable'),
            ('suspected', 'Suspected'),
            ('theoretical', 'Theoretical'),
        ),
        default='established'
    )
    
    # Status
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-severity_score', 'drug1', 'drug2']
        unique_together = ['drug1', 'drug2']
    
    def __str__(self):
        return f"{self.drug1} + {self.drug2} ({self.get_interaction_type_display()})"


class CriticalCondition(models.Model):
    """
    Critical medical conditions that require immediate attention
    """
    CONDITION_TYPES = (
        ('cardiac_arrest', 'Cardiac Arrest'),
        ('respiratory_failure', 'Respiratory Failure'),
        ('sepsis', 'Sepsis'),
        ('stroke', 'Stroke'),
        ('myocardial_infarction', 'Myocardial Infarction'),
        ('anaphylaxis', 'Anaphylaxis'),
        ('diabetic_emergency', 'Diabetic Emergency'),
        ('seizure', 'Seizure'),
        ('trauma', 'Major Trauma'),
        ('poisoning', 'Poisoning'),
        ('other', 'Other Critical Condition'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey('patients.Patient', on_delete=models.CASCADE, related_name='critical_conditions')
    medical_record = models.ForeignKey('MedicalRecord', on_delete=models.CASCADE, related_name='critical_conditions')
    
    condition_type = models.CharField(max_length=30, choices=CONDITION_TYPES)
    condition_name = models.CharField(max_length=200)
    
    # Clinical details
    description = models.TextField()
    onset_time = models.DateTimeField()
    
    # Severity and urgency
    severity_score = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        help_text="Severity score 1-10"
    )
    
    # Status
    is_active = models.BooleanField(default=True)
    is_resolved = models.BooleanField(default=False)
    resolution_time = models.DateTimeField(null=True, blank=True)
    
    # Response information
    response_team_notified = models.BooleanField(default=False)
    response_time = models.DateTimeField(null=True, blank=True)
    
    # Treatment
    immediate_treatment = models.TextField(blank=True)
    outcome = models.TextField(blank=True)
    
    # Staff involved
    attending_physician = models.ForeignKey(
        'doctors.Doctor', 
        on_delete=models.SET_NULL, 
        null=True, blank=True,
        related_name='critical_conditions_attended'
    )
    
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-onset_time', '-severity_score']
    
    def __str__(self):
        return f"{self.condition_name} - {self.patient.user.get_full_name()} ({self.onset_time})"
