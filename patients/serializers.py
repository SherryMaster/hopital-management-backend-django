from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import Patient, EmergencyContact, InsuranceInformation
from accounts.models import UserProfile

User = get_user_model()


class EmergencyContactSerializer(serializers.ModelSerializer):
    """
    Serializer for emergency contact information
    """
    class Meta:
        model = EmergencyContact
        fields = [
            'id', 'name', 'relationship', 'primary_phone', 'secondary_phone',
            'email', 'address', 'is_primary', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate(self, attrs):
        # Ensure only one primary emergency contact per patient
        if attrs.get('is_primary', False):
            patient = self.context.get('patient')
            if patient:
                existing_primary = EmergencyContact.objects.filter(
                    patient=patient, is_primary=True
                ).exclude(id=self.instance.id if self.instance else None)
                
                if existing_primary.exists():
                    raise serializers.ValidationError(
                        "Only one primary emergency contact is allowed per patient"
                    )
        return attrs


class InsuranceInformationSerializer(serializers.ModelSerializer):
    """
    Serializer for insurance information
    """
    class Meta:
        model = InsuranceInformation
        fields = [
            'id', 'insurance_type', 'provider_name', 'policy_number', 'group_number',
            'subscriber_name', 'subscriber_id', 'relationship_to_subscriber',
            'effective_date', 'expiration_date', 'copay_amount', 'deductible_amount',
            'provider_phone', 'provider_address', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_effective_date(self, value):
        if value > timezone.now().date():
            raise serializers.ValidationError("Effective date cannot be in the future")
        return value

    def validate_expiration_date(self, value):
        if value and value <= timezone.now().date():
            raise serializers.ValidationError("Expiration date must be in the future")
        return value

    def validate(self, attrs):
        effective_date = attrs.get('effective_date')
        expiration_date = attrs.get('expiration_date')
        
        if effective_date and expiration_date and effective_date >= expiration_date:
            raise serializers.ValidationError(
                "Effective date must be before expiration date"
            )
        return attrs


class PatientProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for patient profile information
    """
    # User information
    email = serializers.EmailField(source='user.email', read_only=True)
    first_name = serializers.CharField(source='user.first_name', read_only=True)
    last_name = serializers.CharField(source='user.last_name', read_only=True)
    phone_number = serializers.CharField(source='user.phone_number', read_only=True)
    date_of_birth = serializers.DateField(source='user.date_of_birth', read_only=True)
    gender = serializers.CharField(source='user.gender', read_only=True)
    address = serializers.CharField(source='user.address', read_only=True)
    
    # Related data
    emergency_contacts = EmergencyContactSerializer(many=True, read_only=True)
    insurance_info = InsuranceInformationSerializer(many=True, read_only=True)
    
    # Computed fields
    bmi = serializers.ReadOnlyField()
    age = serializers.SerializerMethodField()
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = Patient
        fields = [
            'id', 'patient_id', 'email', 'first_name', 'last_name', 'full_name',
            'phone_number', 'date_of_birth', 'age', 'gender', 'address',
            'blood_type', 'height', 'weight', 'bmi', 'allergies', 'chronic_conditions',
            'current_medications', 'marital_status', 'occupation',
            'registration_date', 'is_active', 'notes',
            'emergency_contacts', 'insurance_info', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'patient_id', 'registration_date', 'created_at', 'updated_at',
            'email', 'first_name', 'last_name', 'phone_number', 'date_of_birth',
            'gender', 'address', 'bmi', 'age', 'full_name'
        ]

    def get_age(self, obj):
        """Calculate patient age"""
        if obj.user.date_of_birth:
            today = timezone.now().date()
            return today.year - obj.user.date_of_birth.year - (
                (today.month, today.day) < (obj.user.date_of_birth.month, obj.user.date_of_birth.day)
            )
        return None

    def get_full_name(self, obj):
        """Get patient full name"""
        return obj.user.get_full_name()


class PatientRegistrationSerializer(serializers.ModelSerializer):
    """
    Serializer for patient registration
    """
    # User fields
    email = serializers.EmailField(source='user.email')
    first_name = serializers.CharField(source='user.first_name')
    last_name = serializers.CharField(source='user.last_name')
    phone_number = serializers.CharField(source='user.phone_number')
    date_of_birth = serializers.DateField(source='user.date_of_birth')
    gender = serializers.CharField(source='user.gender')
    address = serializers.CharField(source='user.address')
    password = serializers.CharField(source='user.password', write_only=True, min_length=8)
    
    # Emergency contact (optional during registration)
    emergency_contacts = EmergencyContactSerializer(many=True, required=False)
    insurance_info = InsuranceInformationSerializer(many=True, required=False)

    class Meta:
        model = Patient
        fields = [
            'email', 'first_name', 'last_name', 'phone_number', 'date_of_birth',
            'gender', 'address', 'password', 'blood_type', 'height', 'weight',
            'allergies', 'chronic_conditions', 'current_medications', 'marital_status',
            'occupation', 'emergency_contacts', 'insurance_info'
        ]

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists")
        return value

    def validate_date_of_birth(self, value):
        if value >= timezone.now().date():
            raise serializers.ValidationError("Date of birth must be in the past")
        return value

    def create(self, validated_data):
        # Extract user data
        user_data = validated_data.pop('user')
        emergency_contacts_data = validated_data.pop('emergency_contacts', [])
        insurance_info_data = validated_data.pop('insurance_info', [])
        
        # Create user
        password = user_data.pop('password')
        user = User.objects.create_user(
            username=user_data['email'],  # Use email as username
            user_type='patient',
            **user_data
        )
        user.set_password(password)
        user.save()
        
        # Create patient profile
        patient = Patient.objects.create(user=user, **validated_data)
        
        # Create emergency contacts
        for contact_data in emergency_contacts_data:
            EmergencyContact.objects.create(patient=patient, **contact_data)
        
        # Create insurance information
        for insurance_data in insurance_info_data:
            InsuranceInformation.objects.create(patient=patient, **insurance_data)
        
        return patient


class PatientListSerializer(serializers.ModelSerializer):
    """
    Simplified serializer for patient list views
    """
    full_name = serializers.SerializerMethodField()
    age = serializers.SerializerMethodField()
    gender = serializers.CharField(source='user.gender', read_only=True)
    primary_phone = serializers.CharField(source='user.phone_number', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)

    class Meta:
        model = Patient
        fields = [
            'id', 'patient_id', 'full_name', 'age', 'gender', 'primary_phone',
            'email', 'blood_type', 'registration_date', 'is_active'
        ]

    def get_full_name(self, obj):
        return obj.user.get_full_name()

    def get_age(self, obj):
        if obj.user.date_of_birth:
            today = timezone.now().date()
            return today.year - obj.user.date_of_birth.year - (
                (today.month, today.day) < (obj.user.date_of_birth.month, obj.user.date_of_birth.day)
            )
        return None


class PatientUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating patient information
    """
    class Meta:
        model = Patient
        fields = [
            'blood_type', 'height', 'weight', 'allergies', 'chronic_conditions',
            'current_medications', 'marital_status', 'occupation', 'notes'
        ]

    def validate_height(self, value):
        if value and (value < 30 or value > 300):
            raise serializers.ValidationError("Height must be between 30 and 300 cm")
        return value

    def validate_weight(self, value):
        if value and (value < 1 or value > 500):
            raise serializers.ValidationError("Weight must be between 1 and 500 kg")
        return value
