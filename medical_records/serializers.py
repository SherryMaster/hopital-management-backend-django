from rest_framework import serializers
from django.utils import timezone
from .models import (
    MedicalRecord, VitalSigns, Diagnosis, Prescription,
    LabTest, MedicalDocument
)
from .alert_models import MedicalAlert, PatientAllergy, DrugInteraction, CriticalCondition


class VitalSignsSerializer(serializers.ModelSerializer):
    """
    Serializer for vital signs
    """
    bmi = serializers.ReadOnlyField()
    recorded_by_name = serializers.SerializerMethodField()
    
    class Meta:
        model = VitalSigns
        fields = [
            'id', 'medical_record', 'temperature', 'blood_pressure_systolic', 'blood_pressure_diastolic',
            'heart_rate', 'respiratory_rate', 'oxygen_saturation', 'height', 'weight',
            'pain_scale', 'bmi', 'recorded_by', 'recorded_by_name', 'recorded_at', 'notes'
        ]
        read_only_fields = ['id', 'recorded_at', 'bmi']
    
    def get_recorded_by_name(self, obj):
        return obj.recorded_by.get_full_name() if obj.recorded_by else None


class DiagnosisSerializer(serializers.ModelSerializer):
    """
    Serializer for diagnoses
    """
    duration_days = serializers.SerializerMethodField()

    class Meta:
        model = Diagnosis
        fields = [
            'id', 'medical_record', 'icd10_code', 'diagnosis_name', 'diagnosis_type', 'description',
            'severity', 'onset_date', 'is_chronic', 'is_resolved', 'resolution_date',
            'duration_days', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_duration_days(self, obj):
        if obj.onset_date:
            end_date = obj.resolution_date if obj.is_resolved else timezone.now().date()
            return (end_date - obj.onset_date).days
        return None


class PrescriptionSerializer(serializers.ModelSerializer):
    """
    Serializer for prescriptions
    """
    is_active = serializers.SerializerMethodField()
    days_remaining = serializers.SerializerMethodField()

    class Meta:
        model = Prescription
        fields = [
            'id', 'medical_record', 'medication_name', 'generic_name', 'dosage', 'frequency', 'route',
            'quantity', 'refills', 'start_date', 'end_date', 'instructions',
            'special_instructions', 'status', 'pharmacy_name', 'pharmacy_phone',
            'is_active', 'days_remaining', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_is_active(self, obj):
        if obj.status != 'active':
            return False
        if obj.end_date and obj.end_date < timezone.now().date():
            return False
        return True
    
    def get_days_remaining(self, obj):
        if obj.end_date and obj.status == 'active':
            remaining = (obj.end_date - timezone.now().date()).days
            return max(0, remaining)
        return None


class LabTestSerializer(serializers.ModelSerializer):
    """
    Serializer for lab tests
    """
    ordered_by_name = serializers.SerializerMethodField()
    collected_by_name = serializers.SerializerMethodField()
    reported_by_name = serializers.SerializerMethodField()
    days_since_ordered = serializers.SerializerMethodField()
    
    class Meta:
        model = LabTest
        fields = [
            'id', 'test_name', 'test_code', 'category', 'ordered_by', 'ordered_by_name',
            'ordered_date', 'priority', 'specimen_type', 'collection_date',
            'collected_by', 'collected_by_name', 'status', 'result_value',
            'reference_range', 'units', 'is_abnormal', 'result_date',
            'reported_by', 'reported_by_name', 'notes', 'days_since_ordered',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_ordered_by_name(self, obj):
        return obj.ordered_by.user.get_full_name() if obj.ordered_by else None
    
    def get_collected_by_name(self, obj):
        return obj.collected_by.get_full_name() if obj.collected_by else None
    
    def get_reported_by_name(self, obj):
        return obj.reported_by.get_full_name() if obj.reported_by else None
    
    def get_days_since_ordered(self, obj):
        return (timezone.now().date() - obj.ordered_date.date()).days


class MedicalDocumentSerializer(serializers.ModelSerializer):
    """
    Serializer for medical documents
    """
    uploaded_by_name = serializers.SerializerMethodField()
    file_url = serializers.SerializerMethodField()
    
    class Meta:
        model = MedicalDocument
        fields = [
            'id', 'title', 'document_type', 'description', 'file', 'file_url',
            'file_size', 'mime_type', 'uploaded_by', 'uploaded_by_name',
            'upload_date', 'is_confidential', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'file_size', 'mime_type', 'upload_date', 'created_at', 'updated_at']
    
    def get_uploaded_by_name(self, obj):
        return obj.uploaded_by.get_full_name() if obj.uploaded_by else None
    
    def get_file_url(self, obj):
        if obj.file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.file.url)
            return obj.file.url
        return None


class MedicalRecordListSerializer(serializers.ModelSerializer):
    """
    Serializer for medical record list view
    """
    patient_name = serializers.SerializerMethodField()
    doctor_name = serializers.SerializerMethodField()
    diagnoses_count = serializers.SerializerMethodField()
    prescriptions_count = serializers.SerializerMethodField()
    
    class Meta:
        model = MedicalRecord
        fields = [
            'id', 'record_number', 'patient', 'patient_name', 'doctor', 'doctor_name',
            'record_type', 'record_date', 'chief_complaint', 'is_finalized',
            'diagnoses_count', 'prescriptions_count', 'created_at'
        ]
        read_only_fields = ['id', 'record_number', 'created_at']
    
    def get_patient_name(self, obj):
        return obj.patient.user.get_full_name()
    
    def get_doctor_name(self, obj):
        return obj.doctor.user.get_full_name()
    
    def get_diagnoses_count(self, obj):
        return obj.diagnoses.count()
    
    def get_prescriptions_count(self, obj):
        return obj.prescriptions.count()


class MedicalRecordDetailSerializer(serializers.ModelSerializer):
    """
    Detailed serializer for medical records
    """
    patient_name = serializers.SerializerMethodField()
    doctor_name = serializers.SerializerMethodField()
    appointment_details = serializers.SerializerMethodField()
    vital_signs = VitalSignsSerializer(many=True, read_only=True)
    diagnoses = DiagnosisSerializer(many=True, read_only=True)
    prescriptions = PrescriptionSerializer(many=True, read_only=True)
    lab_tests = LabTestSerializer(many=True, read_only=True)
    documents = MedicalDocumentSerializer(many=True, read_only=True)
    
    class Meta:
        model = MedicalRecord
        fields = [
            'id', 'record_number', 'patient', 'patient_name', 'doctor', 'doctor_name',
            'appointment', 'appointment_details', 'record_type', 'record_date',
            'chief_complaint', 'history_of_present_illness', 'past_medical_history',
            'family_history', 'social_history', 'physical_examination',
            'assessment', 'treatment_plan', 'notes', 'is_finalized', 'finalized_at',
            'vital_signs', 'diagnoses', 'prescriptions', 'lab_tests', 'documents',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'record_number', 'created_at', 'updated_at']
    
    def get_patient_name(self, obj):
        return obj.patient.user.get_full_name()
    
    def get_doctor_name(self, obj):
        return obj.doctor.user.get_full_name()
    
    def get_appointment_details(self, obj):
        if obj.appointment:
            return {
                'id': obj.appointment.id,
                'appointment_number': obj.appointment.appointment_number,
                'appointment_date': obj.appointment.appointment_date,
                'appointment_time': obj.appointment.appointment_time,
                'status': obj.appointment.status
            }
        return None


class MedicalRecordCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating medical records
    """
    class Meta:
        model = MedicalRecord
        fields = [
            'patient', 'doctor', 'appointment', 'record_type', 'chief_complaint',
            'history_of_present_illness', 'past_medical_history', 'family_history',
            'social_history', 'physical_examination', 'assessment', 'treatment_plan',
            'notes'
        ]
    
    def create(self, validated_data):
        # Set the doctor from the request user if not provided
        request = self.context.get('request')
        if request and hasattr(request.user, 'doctor_profile') and not validated_data.get('doctor'):
            validated_data['doctor'] = request.user.doctor_profile
        
        return super().create(validated_data)


class MedicalHistoryTimelineSerializer(serializers.Serializer):
    """
    Serializer for medical history timeline view
    """
    date = serializers.DateTimeField()
    type = serializers.CharField()
    title = serializers.CharField()
    description = serializers.CharField()
    details = serializers.DictField()
    record_id = serializers.UUIDField()
    doctor_name = serializers.CharField()
    
    class Meta:
        fields = ['date', 'type', 'title', 'description', 'details', 'record_id', 'doctor_name']


class MedicalAlertSerializer(serializers.ModelSerializer):
    """
    Serializer for medical alerts
    """
    triggered_by_name = serializers.SerializerMethodField()
    acknowledged_by_name = serializers.SerializerMethodField()
    resolved_by_name = serializers.SerializerMethodField()
    patient_name = serializers.SerializerMethodField()

    class Meta:
        model = MedicalAlert
        fields = [
            'id', 'patient', 'patient_name', 'medical_record', 'alert_type', 'severity', 'status',
            'title', 'description', 'alert_data', 'triggered_by', 'triggered_by_name', 'triggered_at',
            'acknowledged_by', 'acknowledged_by_name', 'acknowledged_at',
            'resolved_by', 'resolved_by_name', 'resolved_at', 'resolution_notes',
            'auto_dismiss_after', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_triggered_by_name(self, obj):
        return obj.triggered_by.get_full_name() if obj.triggered_by else None

    def get_acknowledged_by_name(self, obj):
        return obj.acknowledged_by.get_full_name() if obj.acknowledged_by else None

    def get_resolved_by_name(self, obj):
        return obj.resolved_by.get_full_name() if obj.resolved_by else None

    def get_patient_name(self, obj):
        return obj.patient.user.get_full_name()


class PatientAllergySerializer(serializers.ModelSerializer):
    """
    Serializer for patient allergies
    """
    created_by_name = serializers.SerializerMethodField()
    patient_name = serializers.SerializerMethodField()

    class Meta:
        model = PatientAllergy
        fields = [
            'id', 'patient', 'patient_name', 'allergy_type', 'allergen', 'reaction_description',
            'severity', 'onset_date', 'last_reaction_date', 'is_active', 'verified_by_doctor',
            'notes', 'treatment_given', 'created_by', 'created_by_name', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_created_by_name(self, obj):
        return obj.created_by.get_full_name() if obj.created_by else None

    def get_patient_name(self, obj):
        return obj.patient.user.get_full_name()


class DrugInteractionSerializer(serializers.ModelSerializer):
    """
    Serializer for drug interactions
    """
    class Meta:
        model = DrugInteraction
        fields = [
            'id', 'drug1', 'drug2', 'interaction_type', 'description', 'clinical_effect',
            'mechanism', 'management_recommendation', 'severity_score', 'evidence_level',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class CriticalConditionSerializer(serializers.ModelSerializer):
    """
    Serializer for critical conditions
    """
    patient_name = serializers.SerializerMethodField()
    attending_physician_name = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = CriticalCondition
        fields = [
            'id', 'patient', 'patient_name', 'medical_record', 'condition_type', 'condition_name',
            'description', 'onset_time', 'severity_score', 'is_active', 'is_resolved', 'resolution_time',
            'response_team_notified', 'response_time', 'immediate_treatment', 'outcome',
            'attending_physician', 'attending_physician_name', 'created_by', 'created_by_name',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_patient_name(self, obj):
        return obj.patient.user.get_full_name()

    def get_attending_physician_name(self, obj):
        return obj.attending_physician.user.get_full_name() if obj.attending_physician else None

    def get_created_by_name(self, obj):
        return obj.created_by.get_full_name() if obj.created_by else None
