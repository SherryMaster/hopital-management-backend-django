from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import Doctor, Specialization, Department, DoctorQualification, DoctorAvailability, DoctorAvailability
from accounts.serializers import UserSerializer

User = get_user_model()


class SpecializationSerializer(serializers.ModelSerializer):
    """
    Serializer for medical specializations
    """
    class Meta:
        model = Specialization
        fields = ['id', 'name', 'description', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class DepartmentSerializer(serializers.ModelSerializer):
    """
    Serializer for hospital departments
    """
    head_of_department_name = serializers.CharField(source='head_of_department.user.get_full_name', read_only=True)
    doctor_count = serializers.SerializerMethodField()

    class Meta:
        model = Department
        fields = [
            'id', 'name', 'description', 'head_of_department', 'head_of_department_name',
            'location', 'phone_number', 'email', 'is_active', 'doctor_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_doctor_count(self, obj):
        return obj.doctors.filter(employment_status='active').count()


class DoctorQualificationSerializer(serializers.ModelSerializer):
    """
    Serializer for doctor qualifications
    """
    class Meta:
        model = DoctorQualification
        fields = [
            'id', 'qualification_type', 'degree_name', 'institution',
            'year_obtained', 'grade_or_score', 'certificate_file',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class DoctorAvailabilitySerializer(serializers.ModelSerializer):
    """
    Serializer for doctor availability schedule
    """
    day_name = serializers.CharField(source='get_day_of_week_display', read_only=True)

    class Meta:
        model = DoctorAvailability
        fields = [
            'id', 'day_of_week', 'day_name', 'start_time', 'end_time',
            'is_available', 'break_start_time', 'break_end_time',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate(self, data):
        """
        Validate time constraints
        """
        start_time = data.get('start_time')
        end_time = data.get('end_time')
        break_start = data.get('break_start_time')
        break_end = data.get('break_end_time')

        if start_time and end_time and start_time >= end_time:
            raise serializers.ValidationError("End time must be after start time")

        if break_start and break_end:
            if break_start >= break_end:
                raise serializers.ValidationError("Break end time must be after break start time")
            
            if start_time and end_time:
                if break_start < start_time or break_end > end_time:
                    raise serializers.ValidationError("Break time must be within working hours")

        return data


class DoctorListSerializer(serializers.ModelSerializer):
    """
    Simplified serializer for doctor list views
    """
    full_name = serializers.CharField(source='user.get_full_name', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    phone_number = serializers.CharField(source='user.phone_number', read_only=True)
    specializations = SpecializationSerializer(many=True, read_only=True)
    department_name = serializers.CharField(source='department.name', read_only=True)

    class Meta:
        model = Doctor
        fields = [
            'id', 'doctor_id', 'full_name', 'email', 'phone_number',
            'specializations', 'department_name', 'employment_status',
            'consultation_fee', 'years_of_experience', 'is_available_for_consultation'
        ]


class DoctorDetailSerializer(serializers.ModelSerializer):
    """
    Detailed serializer for doctor profile
    """
    user = UserSerializer(read_only=True)
    specializations = SpecializationSerializer(many=True, read_only=True)
    department = DepartmentSerializer(read_only=True)
    qualifications = DoctorQualificationSerializer(many=True, read_only=True)
    availability_schedule = DoctorAvailabilitySerializer(many=True, read_only=True)
    
    # Computed fields
    full_name = serializers.CharField(source='user.get_full_name', read_only=True)
    age = serializers.SerializerMethodField()
    total_qualifications = serializers.SerializerMethodField()

    class Meta:
        model = Doctor
        fields = [
            'id', 'doctor_id', 'user', 'full_name', 'age',
            'medical_license_number', 'license_expiry_date',
            'specializations', 'department', 'hire_date', 'employment_status',
            'consultation_fee', 'years_of_experience', 'bio', 'languages_spoken',
            'is_available_for_consultation', 'max_patients_per_day',
            'qualifications', 'total_qualifications', 'availability_schedule',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'doctor_id', 'created_at', 'updated_at']

    def get_age(self, obj):
        if obj.user.date_of_birth:
            today = timezone.now().date()
            return today.year - obj.user.date_of_birth.year - (
                (today.month, today.day) < (obj.user.date_of_birth.month, obj.user.date_of_birth.day)
            )
        return None

    def get_total_qualifications(self, obj):
        return obj.qualifications.count()


class DoctorRegistrationSerializer(serializers.ModelSerializer):
    """
    Serializer for doctor registration
    """
    # User fields
    email = serializers.EmailField()
    first_name = serializers.CharField(max_length=30)
    last_name = serializers.CharField(max_length=30)
    phone_number = serializers.CharField(max_length=17)
    date_of_birth = serializers.DateField()
    gender = serializers.ChoiceField(choices=[('M', 'Male'), ('F', 'Female'), ('O', 'Other')])
    address = serializers.CharField()
    password = serializers.CharField(write_only=True, min_length=8)

    # Doctor fields
    specialization_ids = serializers.ListField(
        child=serializers.UUIDField(),
        write_only=True,
        required=False
    )

    class Meta:
        model = Doctor
        fields = [
            'email', 'first_name', 'last_name', 'phone_number', 'date_of_birth',
            'gender', 'address', 'password', 'medical_license_number',
            'license_expiry_date', 'specialization_ids', 'department',
            'hire_date', 'consultation_fee', 'years_of_experience', 'bio',
            'languages_spoken', 'max_patients_per_day'
        ]

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def validate_medical_license_number(self, value):
        if Doctor.objects.filter(medical_license_number=value).exists():
            raise serializers.ValidationError("A doctor with this license number already exists.")
        return value

    def create(self, validated_data):
        # Extract user data
        user_data = {
            'email': validated_data.pop('email'),
            'first_name': validated_data.pop('first_name'),
            'last_name': validated_data.pop('last_name'),
            'phone_number': validated_data.pop('phone_number'),
            'date_of_birth': validated_data.pop('date_of_birth'),
            'gender': validated_data.pop('gender'),
            'address': validated_data.pop('address'),
            'user_type': 'doctor',
            'is_active': True,
        }
        password = validated_data.pop('password')
        specialization_ids = validated_data.pop('specialization_ids', [])

        # Create user
        user = User.objects.create_user(
            username=user_data['email'],
            password=password,
            **user_data
        )

        # Create doctor profile
        doctor = Doctor.objects.create(user=user, **validated_data)

        # Add specializations
        if specialization_ids:
            specializations = Specialization.objects.filter(id__in=specialization_ids)
            doctor.specializations.set(specializations)

        return doctor


class DoctorAvailabilityCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating doctor availability
    """
    class Meta:
        model = DoctorAvailability
        fields = [
            'day_of_week', 'start_time', 'end_time', 'is_available',
            'break_start_time', 'break_end_time'
        ]

    def validate(self, attrs):
        """Cross-field validation for availability"""
        start_time = attrs.get('start_time')
        end_time = attrs.get('end_time')
        break_start_time = attrs.get('break_start_time')
        break_end_time = attrs.get('break_end_time')

        # Validate start and end times
        if start_time and end_time and start_time >= end_time:
            raise serializers.ValidationError("Start time must be before end time")

        # Validate break times
        if break_start_time and break_end_time:
            if break_start_time >= break_end_time:
                raise serializers.ValidationError("Break start time must be before break end time")

            if start_time and end_time:
                if break_start_time < start_time or break_end_time > end_time:
                    raise serializers.ValidationError("Break times must be within working hours")

        # Additional validation can be added here if needed

        return attrs

    def create(self, validated_data):
        """Create availability for the authenticated doctor"""
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            try:
                doctor = request.user.doctor_profile
                return DoctorAvailability.objects.create(doctor=doctor, **validated_data)
            except AttributeError:
                # Fallback: try to get doctor profile directly
                from doctors.models import Doctor
                doctor = Doctor.objects.get(user=request.user)
                return DoctorAvailability.objects.create(doctor=doctor, **validated_data)
        else:
            raise serializers.ValidationError("Authentication required")


class DoctorWeeklyAvailabilityItemSerializer(serializers.Serializer):
    """
    Serializer for individual day availability in weekly schedule
    """
    start_time = serializers.TimeField()
    end_time = serializers.TimeField()
    is_available = serializers.BooleanField(default=True)
    break_start_time = serializers.TimeField(required=False, allow_null=True)
    break_end_time = serializers.TimeField(required=False, allow_null=True)

    def validate(self, attrs):
        """Cross-field validation for availability"""
        start_time = attrs.get('start_time')
        end_time = attrs.get('end_time')
        break_start_time = attrs.get('break_start_time')
        break_end_time = attrs.get('break_end_time')

        # Validate start and end times
        if start_time and end_time and start_time >= end_time:
            raise serializers.ValidationError("Start time must be before end time")

        # Validate break times
        if break_start_time and break_end_time:
            if break_start_time >= break_end_time:
                raise serializers.ValidationError("Break start time must be before break end time")

            if start_time and end_time:
                if break_start_time < start_time or break_end_time > end_time:
                    raise serializers.ValidationError("Break times must be within working hours")

        return attrs


class DoctorWeeklyAvailabilitySerializer(serializers.Serializer):
    """
    Serializer for setting weekly availability for a doctor
    """
    monday = DoctorWeeklyAvailabilityItemSerializer(required=False)
    tuesday = DoctorWeeklyAvailabilityItemSerializer(required=False)
    wednesday = DoctorWeeklyAvailabilityItemSerializer(required=False)
    thursday = DoctorWeeklyAvailabilityItemSerializer(required=False)
    friday = DoctorWeeklyAvailabilityItemSerializer(required=False)
    saturday = DoctorWeeklyAvailabilityItemSerializer(required=False)
    sunday = DoctorWeeklyAvailabilityItemSerializer(required=False)

    def create(self, validated_data):
        """Create weekly availability for the authenticated doctor"""
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            try:
                doctor = request.user.doctor_profile
            except AttributeError:
                # Fallback: try to get doctor profile directly
                from doctors.models import Doctor
                doctor = Doctor.objects.get(user=request.user)
        else:
            raise serializers.ValidationError("Authentication required")

        created_availabilities = []

        day_mapping = {
            'monday': 1,
            'tuesday': 2,
            'wednesday': 3,
            'thursday': 4,
            'friday': 5,
            'saturday': 6,
            'sunday': 0,
        }

        for day_name, day_data in validated_data.items():
            if day_data:
                day_data['day_of_week'] = day_mapping[day_name]
                availability = DoctorAvailability.objects.create(doctor=doctor, **day_data)
                created_availabilities.append(availability)

        return created_availabilities


class DoctorUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating doctor information
    """
    specialization_ids = serializers.ListField(
        child=serializers.UUIDField(),
        write_only=True,
        required=False
    )

    class Meta:
        model = Doctor
        fields = [
            'medical_license_number', 'license_expiry_date', 'specialization_ids',
            'department', 'employment_status', 'consultation_fee',
            'years_of_experience', 'bio', 'languages_spoken',
            'is_available_for_consultation', 'max_patients_per_day'
        ]

    def update(self, instance, validated_data):
        specialization_ids = validated_data.pop('specialization_ids', None)

        # Update doctor fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Update specializations if provided
        if specialization_ids is not None:
            specializations = Specialization.objects.filter(id__in=specialization_ids)
            instance.specializations.set(specializations)

        return instance
