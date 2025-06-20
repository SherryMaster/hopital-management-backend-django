from rest_framework import serializers
from django.utils import timezone
from django.core.exceptions import ValidationError
from datetime import datetime, timedelta
from .models import Appointment, AppointmentType, AppointmentHistory, AppointmentReminder
from patients.models import Patient
from doctors.models import Doctor
from accounts.models import User


class AppointmentTypeSerializer(serializers.ModelSerializer):
    """
    Serializer for appointment types
    """
    class Meta:
        model = AppointmentType
        fields = [
            'id', 'name', 'description', 'duration_minutes', 
            'color_code', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class AppointmentHistorySerializer(serializers.ModelSerializer):
    """
    Serializer for appointment history
    """
    performed_by_name = serializers.CharField(source='performed_by.get_full_name', read_only=True)
    
    class Meta:
        model = AppointmentHistory
        fields = [
            'id', 'action', 'old_values', 'new_values', 'reason',
            'performed_by', 'performed_by_name', 'timestamp'
        ]
        read_only_fields = ['id', 'timestamp', 'performed_by_name']


class AppointmentReminderSerializer(serializers.ModelSerializer):
    """
    Serializer for appointment reminders
    """
    class Meta:
        model = AppointmentReminder
        fields = [
            'id', 'reminder_type', 'scheduled_time', 'status',
            'sent_at', 'error_message', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'sent_at', 'created_at', 'updated_at']


class AppointmentListSerializer(serializers.ModelSerializer):
    """
    Serializer for appointment list view (optimized for performance)
    """
    patient_name = serializers.CharField(source='patient.user.get_full_name', read_only=True)
    patient_id = serializers.CharField(source='patient.patient_id', read_only=True)
    doctor_name = serializers.CharField(source='doctor.user.get_full_name', read_only=True)
    doctor_id = serializers.CharField(source='doctor.doctor_id', read_only=True)
    appointment_type_name = serializers.CharField(source='appointment_type.name', read_only=True)
    appointment_datetime = serializers.SerializerMethodField()
    
    class Meta:
        model = Appointment
        fields = [
            'id', 'appointment_number', 'patient_name', 'patient_id',
            'doctor_name', 'doctor_id', 'appointment_type_name',
            'appointment_date', 'appointment_time', 'appointment_datetime',
            'duration_minutes', 'status', 'priority', 'reason_for_visit',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'appointment_number', 'created_at', 'updated_at']
    
    def get_appointment_datetime(self, obj):
        """Combine date and time for easier frontend handling"""
        if obj.appointment_date and obj.appointment_time:
            return timezone.datetime.combine(obj.appointment_date, obj.appointment_time)
        return None


class AppointmentDetailSerializer(serializers.ModelSerializer):
    """
    Detailed serializer for appointment with all related information
    """
    patient = serializers.SerializerMethodField()
    doctor = serializers.SerializerMethodField()
    appointment_type = AppointmentTypeSerializer(read_only=True)
    history = AppointmentHistorySerializer(many=True, read_only=True)
    reminders = AppointmentReminderSerializer(many=True, read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    appointment_datetime = serializers.SerializerMethodField()
    
    class Meta:
        model = Appointment
        fields = [
            'id', 'appointment_number', 'patient', 'doctor', 'appointment_type',
            'appointment_date', 'appointment_time', 'appointment_datetime',
            'duration_minutes', 'status', 'priority', 'reason_for_visit',
            'symptoms', 'notes', 'created_by', 'created_by_name',
            'checked_in_at', 'started_at', 'completed_at',
            'follow_up_required', 'follow_up_date', 'follow_up_notes',
            'history', 'reminders', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'appointment_number', 'created_by', 'created_by_name',
            'history', 'reminders', 'created_at', 'updated_at'
        ]
    
    def get_patient(self, obj):
        """Get patient information"""
        return {
            'id': obj.patient.id,
            'patient_id': obj.patient.patient_id,
            'name': obj.patient.user.get_full_name(),
            'email': obj.patient.user.email,
            'phone': obj.patient.user.phone_number,
            'date_of_birth': obj.patient.user.date_of_birth,
            'blood_type': obj.patient.blood_type,
        }
    
    def get_doctor(self, obj):
        """Get doctor information"""
        return {
            'id': obj.doctor.id,
            'doctor_id': obj.doctor.doctor_id,
            'name': obj.doctor.user.get_full_name(),
            'email': obj.doctor.user.email,
            'phone': obj.doctor.user.phone_number,
            'specializations': [spec.name for spec in obj.doctor.specializations.all()],
            'department': obj.doctor.department.name if obj.doctor.department else None,
        }
    
    def get_appointment_datetime(self, obj):
        """Combine date and time for easier frontend handling"""
        if obj.appointment_date and obj.appointment_time:
            return timezone.datetime.combine(obj.appointment_date, obj.appointment_time)
        return None


class AppointmentCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating new appointments
    """
    patient_id = serializers.CharField(write_only=True)
    doctor_id = serializers.CharField(write_only=True)
    appointment_type_id = serializers.UUIDField(write_only=True, required=False)
    
    class Meta:
        model = Appointment
        fields = [
            'patient_id', 'doctor_id', 'appointment_type_id',
            'appointment_date', 'appointment_time', 'duration_minutes',
            'priority', 'reason_for_visit', 'symptoms', 'notes',
            'follow_up_required', 'follow_up_date', 'follow_up_notes'
        ]
    
    def validate_patient_id(self, value):
        """Validate patient exists and is active"""
        try:
            patient = Patient.objects.get(patient_id=value, is_active=True)
            return value  # Return the original value, not the object
        except Patient.DoesNotExist:
            raise serializers.ValidationError("Patient not found or inactive")

    def validate_doctor_id(self, value):
        """Validate doctor exists and is available"""
        try:
            doctor = Doctor.objects.get(doctor_id=value, employment_status='active')
            return value  # Return the original value, not the object
        except Doctor.DoesNotExist:
            raise serializers.ValidationError("Doctor not found or not available")
    
    def validate_appointment_type_id(self, value):
        """Validate appointment type exists and is active"""
        if value:
            try:
                appointment_type = AppointmentType.objects.get(id=value, is_active=True)
                return appointment_type
            except AppointmentType.DoesNotExist:
                raise serializers.ValidationError("Appointment type not found or inactive")
        return None
    
    def validate_appointment_date(self, value):
        """Validate appointment date is not in the past"""
        if value < timezone.now().date():
            raise serializers.ValidationError("Appointment date cannot be in the past")
        return value
    
    def validate(self, attrs):
        """Cross-field validation"""
        appointment_date = attrs.get('appointment_date')
        appointment_time = attrs.get('appointment_time')
        doctor_id = attrs.get('doctor_id')
        duration_minutes = attrs.get('duration_minutes', 30)

        if appointment_date and appointment_time and doctor_id:
            # Check if appointment is during business hours (8 AM to 6 PM)
            if appointment_time.hour < 8 or appointment_time.hour >= 18:
                raise serializers.ValidationError(
                    "Appointments can only be scheduled between 8:00 AM and 6:00 PM"
                )

            # Get the doctor object for validation
            try:
                doctor = Doctor.objects.get(doctor_id=doctor_id)
            except Doctor.DoesNotExist:
                raise serializers.ValidationError("Doctor not found")

            # Check for doctor availability and conflicts
            appointment_datetime = timezone.datetime.combine(appointment_date, appointment_time)
            appointment_end = appointment_datetime + timedelta(minutes=duration_minutes)

            # Check for overlapping appointments
            overlapping = Appointment.objects.filter(
                doctor=doctor,
                appointment_date=appointment_date,
                status__in=['scheduled', 'confirmed', 'in_progress']
            )
            
            for apt in overlapping:
                existing_start = timezone.datetime.combine(apt.appointment_date, apt.appointment_time)
                existing_end = existing_start + timedelta(minutes=apt.duration_minutes)
                
                if (appointment_datetime < existing_end and appointment_end > existing_start):
                    raise serializers.ValidationError(
                        f"Doctor is not available at this time. Conflicting appointment from "
                        f"{existing_start.time()} to {existing_end.time()}"
                    )
        
        return attrs
    
    def create(self, validated_data):
        """Create appointment with proper relationships"""
        # Extract related objects
        patient_id = validated_data.pop('patient_id')
        doctor_id = validated_data.pop('doctor_id')
        appointment_type_id = validated_data.pop('appointment_type_id', None)

        # Get the actual objects
        patient = Patient.objects.get(patient_id=patient_id)
        doctor = Doctor.objects.get(doctor_id=doctor_id)
        appointment_type = None
        if appointment_type_id:
            appointment_type = AppointmentType.objects.get(id=appointment_type_id)
        
        # Set duration from appointment type if not provided
        if appointment_type and not validated_data.get('duration_minutes'):
            validated_data['duration_minutes'] = appointment_type.duration_minutes
        
        # Create appointment
        appointment = Appointment.objects.create(
            patient=patient,
            doctor=doctor,
            appointment_type=appointment_type,
            **validated_data
        )
        
        # Skip history creation for now to debug
        # TODO: Add history creation back after debugging
        
        return appointment


class AppointmentUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating appointments
    """
    class Meta:
        model = Appointment
        fields = [
            'appointment_date', 'appointment_time', 'duration_minutes',
            'status', 'priority', 'reason_for_visit', 'symptoms', 'notes',
            'checked_in_at', 'started_at', 'completed_at',
            'follow_up_required', 'follow_up_date', 'follow_up_notes'
        ]
    
    def validate_appointment_date(self, value):
        """Validate appointment date"""
        if value < timezone.now().date():
            raise serializers.ValidationError("Appointment date cannot be in the past")
        return value
    
    def validate_status(self, value):
        """Validate status transitions"""
        if self.instance:
            current_status = self.instance.status
            
            # Define valid status transitions
            valid_transitions = {
                'scheduled': ['confirmed', 'cancelled', 'rescheduled'],
                'confirmed': ['in_progress', 'cancelled', 'no_show', 'rescheduled'],
                'in_progress': ['completed', 'cancelled'],
                'completed': [],  # Completed appointments cannot be changed
                'cancelled': ['scheduled'],  # Can reschedule cancelled appointments
                'no_show': ['scheduled'],  # Can reschedule no-show appointments
                'rescheduled': ['scheduled', 'confirmed'],
            }
            
            if current_status in valid_transitions and value not in valid_transitions[current_status]:
                raise serializers.ValidationError(
                    f"Cannot change status from '{current_status}' to '{value}'"
                )
        
        return value
    
    def update(self, instance, validated_data):
        """Update appointment with history tracking"""
        # Store old values for history
        old_values = {
            'appointment_date': str(instance.appointment_date),
            'appointment_time': str(instance.appointment_time),
            'status': instance.status,
            'priority': instance.priority,
        }
        
        # Update the instance
        updated_instance = super().update(instance, validated_data)
        
        # Create history record
        new_values = {
            'appointment_date': str(updated_instance.appointment_date),
            'appointment_time': str(updated_instance.appointment_time),
            'status': updated_instance.status,
            'priority': updated_instance.priority,
        }
        
        AppointmentHistory.objects.create(
            appointment=updated_instance,
            action='updated',
            old_values=old_values,
            new_values=new_values,
            reason='Appointment updated',
            performed_by=self.context['request'].user
        )
        
        return updated_instance
