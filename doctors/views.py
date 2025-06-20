from rest_framework import generics, viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import PermissionDenied
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from drf_spectacular.utils import extend_schema, OpenApiParameter
from django.contrib.auth import get_user_model
from django.db.models import Q, Count
from django.utils import timezone
from .models import Doctor, Specialization, Department, DoctorQualification, DoctorAvailability, DoctorAvailability
from .serializers import (
    DoctorListSerializer,
    DoctorDetailSerializer,
    DoctorRegistrationSerializer,
    DoctorUpdateSerializer,
    SpecializationSerializer,
    DepartmentSerializer,
    DoctorQualificationSerializer,
    DoctorAvailabilitySerializer,
    DoctorAvailabilityCreateSerializer,
    DoctorWeeklyAvailabilitySerializer
)
from accounts.models import UserActivity

User = get_user_model()


@extend_schema(tags=['Doctor Management'])
class DoctorRegistrationView(generics.CreateAPIView):
    """
    Doctor registration view for creating new doctor accounts
    """
    queryset = Doctor.objects.all()
    serializer_class = DoctorRegistrationSerializer
    permission_classes = [permissions.AllowAny]  # Will be restricted to admin in production

    @extend_schema(
        tags=['Doctor Management'],
        summary="Register new doctor",
        description="Register a new doctor with user account creation",
        responses={201: DoctorDetailSerializer}
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        doctor = serializer.save()

        # Log doctor registration
        UserActivity.objects.create(
            user=request.user if request.user.is_authenticated else doctor.user,
            action='create',
            resource_type='doctor_account',
            resource_id=str(doctor.id),
            description=f'Doctor {doctor.doctor_id} registered',
            ip_address=request.META.get('REMOTE_ADDR', ''),
        )

        # Return detailed doctor information
        response_serializer = DoctorDetailSerializer(doctor)
        return Response(
            {
                'message': 'Doctor registered successfully',
                'doctor': response_serializer.data
            },
            status=status.HTTP_201_CREATED
        )


@extend_schema(tags=['Doctor Management'])
class DoctorViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing doctors
    """
    queryset = Doctor.objects.select_related('user', 'department').prefetch_related(
        'specializations', 'qualifications', 'availability_schedule'
    )
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['employment_status', 'department', 'specializations', 'is_available_for_consultation']
    search_fields = ['doctor_id', 'user__first_name', 'user__last_name', 'user__email', 'specializations__name']
    ordering_fields = ['doctor_id', 'hire_date', 'consultation_fee', 'years_of_experience']
    ordering = ['doctor_id']

    def get_serializer_class(self):
        if self.action == 'list':
            return DoctorListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return DoctorUpdateSerializer
        return DoctorDetailSerializer

    def get_queryset(self):
        user = self.request.user
        queryset = self.queryset

        if user.user_type == 'patient':
            # Patients can only see active doctors
            return queryset.filter(employment_status='active')
        elif user.user_type in ['doctor', 'nurse']:
            # Medical staff can see all active doctors
            return queryset.filter(employment_status__in=['active', 'on_leave'])
        elif user.user_type == 'admin':
            # Admins can see all doctors
            return queryset
        else:
            # Other roles have no access
            return queryset.none()

    @extend_schema(
        tags=['Doctor Management'],
        summary="List doctors",
        description="Get list of doctors with filtering and search",
        parameters=[
            OpenApiParameter('search', str, description='Search by doctor ID, name, email, or specialization'),
            OpenApiParameter('employment_status', str, description='Filter by employment status'),
            OpenApiParameter('department', str, description='Filter by department'),
            OpenApiParameter('specializations', str, description='Filter by specialization'),
            OpenApiParameter('is_available_for_consultation', bool, description='Filter by availability'),
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        tags=['Doctor Management'],
        summary="Get doctor details",
        description="Get detailed doctor information including qualifications and availability"
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(
        tags=['Doctor Management'],
        summary="Update doctor information",
        description="Update doctor profile and professional information"
    )
    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)

        if response.status_code == 200:
            # Log doctor update
            UserActivity.objects.create(
                user=request.user,
                action='update',
                resource_type='doctor_profile',
                resource_id=str(self.get_object().id),
                description=f'Doctor {self.get_object().doctor_id} updated',
                ip_address=request.META.get('REMOTE_ADDR', ''),
            )

        return response

    @action(detail=True, methods=['get'])
    @extend_schema(
        tags=['Doctor Management'],
        summary="Get doctor availability",
        description="Get doctor's weekly availability schedule"
    )
    def availability(self, request, pk=None):
        """
        Get doctor's availability schedule
        """
        doctor = self.get_object()
        availability = doctor.availability_schedule.all()
        serializer = DoctorAvailabilitySerializer(availability, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    @extend_schema(
        tags=['Doctor Management'],
        summary="Set doctor availability",
        description="Set or update doctor's availability schedule",
        request=DoctorAvailabilitySerializer
    )
    def set_availability(self, request, pk=None):
        """
        Set doctor's availability schedule
        """
        doctor = self.get_object()

        # Check permissions - only the doctor themselves or admin can set availability
        if request.user.user_type not in ['admin'] and request.user != doctor.user:
            return Response(
                {'error': 'You can only manage your own availability'},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = DoctorAvailabilitySerializer(data=request.data)
        if serializer.is_valid():
            # Delete existing availability for this day
            DoctorAvailability.objects.filter(
                doctor=doctor,
                day_of_week=serializer.validated_data['day_of_week']
            ).delete()

            # Create new availability
            serializer.save(doctor=doctor)

            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    @extend_schema(
        tags=['Doctor Management'],
        summary="Get doctor statistics",
        description="Get doctor's performance statistics and metrics"
    )
    def statistics(self, request, pk=None):
        """
        Get doctor statistics
        """
        doctor = self.get_object()

        # Basic statistics (will be enhanced when appointments are implemented)
        stats = {
            'doctor_id': doctor.doctor_id,
            'full_name': doctor.user.get_full_name(),
            'years_of_experience': doctor.years_of_experience,
            'total_qualifications': doctor.qualifications.count(),
            'specializations_count': doctor.specializations.count(),
            'consultation_fee': doctor.consultation_fee,
            'max_patients_per_day': doctor.max_patients_per_day,
            'employment_status': doctor.employment_status,
            'is_available': doctor.is_available_for_consultation,
            'license_expiry_date': doctor.license_expiry_date,
            'hire_date': doctor.hire_date,
        }

        return Response(stats)


class DoctorProfileView(generics.RetrieveUpdateAPIView):
    """
    Doctor profile view for authenticated doctors
    """
    serializer_class = DoctorDetailSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        # Doctors can only access their own profile
        if self.request.user.user_type == 'doctor':
            try:
                return Doctor.objects.select_related('user', 'department').prefetch_related(
                    'specializations', 'qualifications', 'availability_schedule'
                ).get(user=self.request.user)
            except Doctor.DoesNotExist:
                return None
        else:
            # Other user types should use DoctorViewSet
            return None

    @extend_schema(
        tags=['Doctor Management'],
        summary="Get my doctor profile",
        description="Get authenticated doctor's own profile information"
    )
    def get(self, request, *args, **kwargs):
        doctor = self.get_object()
        if not doctor:
            return Response(
                {'error': 'Doctor profile not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = self.get_serializer(doctor)
        return Response(serializer.data)

    @extend_schema(
        tags=['Doctor Management'],
        summary="Update my doctor profile",
        description="Update authenticated doctor's own profile information"
    )
    def patch(self, request, *args, **kwargs):
        doctor = self.get_object()
        if not doctor:
            return Response(
                {'error': 'Doctor profile not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = DoctorUpdateSerializer(doctor, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()

            # Log profile update
            UserActivity.objects.create(
                user=request.user,
                action='update',
                resource_type='doctor_profile',
                description='Doctor updated own profile',
                ip_address=request.META.get('REMOTE_ADDR', ''),
            )

            # Return updated profile
            profile_serializer = DoctorDetailSerializer(doctor)
            return Response(profile_serializer.data)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        tags=['Doctor Management'],
        summary="Update my doctor profile",
        description="Update authenticated doctor's own profile information"
    )
    def put(self, request, *args, **kwargs):
        doctor = self.get_object()
        if not doctor:
            return Response(
                {'error': 'Doctor profile not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = DoctorUpdateSerializer(doctor, data=request.data)
        if serializer.is_valid():
            serializer.save()

            # Log profile update
            UserActivity.objects.create(
                user=request.user,
                action='update',
                resource_type='doctor_profile',
                description='Doctor updated own profile',
                ip_address=request.META.get('REMOTE_ADDR', ''),
            )

            # Return updated profile
            profile_serializer = DoctorDetailSerializer(doctor)
            return Response(profile_serializer.data)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(tags=['Doctor Management'])
class SpecializationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing medical specializations
    """
    queryset = Specialization.objects.all()
    serializer_class = SpecializationSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']

    @extend_schema(
        tags=['Doctor Management'],
        summary="List specializations",
        description="Get list of medical specializations"
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        tags=['Doctor Management'],
        summary="Create specialization",
        description="Create a new medical specialization (Admin only)"
    )
    def create(self, request, *args, **kwargs):
        # Only admins can create specializations
        if request.user.user_type != 'admin':
            return Response(
                {'error': 'Only administrators can create specializations'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().create(request, *args, **kwargs)


@extend_schema(tags=['Doctor Management'])
class DepartmentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing hospital departments
    """
    queryset = Department.objects.all()
    serializer_class = DepartmentSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['name', 'description', 'location']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']

    @extend_schema(
        tags=['Doctor Management'],
        summary="List departments",
        description="Get list of hospital departments"
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        tags=['Doctor Management'],
        summary="Create department",
        description="Create a new hospital department (Admin only)"
    )
    def create(self, request, *args, **kwargs):
        # Only admins can create departments
        if request.user.user_type != 'admin':
            return Response(
                {'error': 'Only administrators can create departments'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().create(request, *args, **kwargs)


@extend_schema(tags=['Doctor Management'])
class DoctorQualificationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing doctor qualifications
    """
    serializer_class = DoctorQualificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        doctor_id = self.kwargs.get('doctor_pk')
        if doctor_id:
            return DoctorQualification.objects.filter(doctor_id=doctor_id)
        return DoctorQualification.objects.none()

    def perform_create(self, serializer):
        doctor_id = self.kwargs.get('doctor_pk')
        doctor = Doctor.objects.get(id=doctor_id)

        # Check permissions
        if (self.request.user.user_type == 'doctor' and
            doctor.user != self.request.user):
            raise PermissionDenied("You can only manage your own qualifications")

        serializer.save(doctor=doctor)

    @extend_schema(
        tags=['Doctor Management'],
        summary="List doctor qualifications",
        description="Get list of qualifications for a specific doctor"
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        tags=['Doctor Management'],
        summary="Add doctor qualification",
        description="Add a new qualification for a doctor"
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)


@extend_schema(tags=['Doctor Management'])
class DoctorAvailabilityViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing doctor availability schedules
    """
    serializer_class = DoctorAvailabilitySerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['day_of_week', 'is_available']
    ordering_fields = ['day_of_week', 'start_time']
    ordering = ['day_of_week', 'start_time']

    def get_queryset(self):
        """Filter availability based on user permissions"""
        user = self.request.user

        if hasattr(user, 'user_type'):
            if user.user_type == 'doctor':
                # Doctors can only see their own availability
                return DoctorAvailability.objects.filter(doctor__user=user)
            elif user.user_type == 'admin':
                # Admins can see all availability
                return DoctorAvailability.objects.all()
            else:
                # Other users can see all active doctors' availability
                return DoctorAvailability.objects.filter(
                    doctor__employment_status='active',
                    is_available=True
                )
        else:
            return DoctorAvailability.objects.none()

    def get_serializer_class(self):
        if self.action == 'create':
            return DoctorAvailabilityCreateSerializer
        return DoctorAvailabilitySerializer

    @extend_schema(
        tags=['Doctor Management'],
        summary="List doctor availability",
        description="Get list of doctor availability schedules"
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        tags=['Doctor Management'],
        summary="Create availability schedule",
        description="Create a new availability schedule for authenticated doctor"
    )
    def create(self, request, *args, **kwargs):
        # Only doctors can create their own availability
        if not hasattr(request.user, 'user_type') or request.user.user_type != 'doctor':
            return Response(
                {'error': 'Only doctors can create availability schedules'},
                status=status.HTTP_403_FORBIDDEN
            )

        return super().create(request, *args, **kwargs)

    @extend_schema(
        tags=['Doctor Management'],
        summary="Update availability schedule",
        description="Update an existing availability schedule"
    )
    def update(self, request, *args, **kwargs):
        availability = self.get_object()

        # Check permissions
        if (hasattr(request.user, 'user_type') and
            request.user.user_type == 'doctor' and
            availability.doctor.user != request.user):
            return Response(
                {'error': 'You can only update your own availability'},
                status=status.HTTP_403_FORBIDDEN
            )

        return super().update(request, *args, **kwargs)

    @extend_schema(
        tags=['Doctor Management'],
        summary="Delete availability schedule",
        description="Delete an availability schedule"
    )
    def destroy(self, request, *args, **kwargs):
        availability = self.get_object()

        # Check permissions
        if (hasattr(request.user, 'user_type') and
            request.user.user_type == 'doctor' and
            availability.doctor.user != request.user):
            return Response(
                {'error': 'You can only delete your own availability'},
                status=status.HTTP_403_FORBIDDEN
            )

        return super().destroy(request, *args, **kwargs)

    @action(detail=False, methods=['post'])
    @extend_schema(
        tags=['Doctor Management'],
        summary="Set weekly availability",
        description="Set complete weekly availability schedule for authenticated doctor",
        request=DoctorWeeklyAvailabilitySerializer
    )
    def set_weekly_schedule(self, request):
        """
        Set weekly availability schedule for the authenticated doctor
        """
        if not hasattr(request.user, 'user_type') or request.user.user_type != 'doctor':
            return Response(
                {'error': 'Only doctors can set weekly schedules'},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            # Try to get doctor profile
            try:
                doctor = request.user.doctor_profile
            except AttributeError:
                # Fallback: try direct lookup
                from .models import Doctor
                doctor = Doctor.objects.get(user=request.user)
        except (AttributeError, Doctor.DoesNotExist):
            return Response(
                {'error': 'Doctor profile not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = DoctorWeeklyAvailabilitySerializer(
            data=request.data,
            context={'request': request}
        )

        if serializer.is_valid():
            # Clear existing availability
            DoctorAvailability.objects.filter(doctor=doctor).delete()

            # Create new weekly schedule
            created_availabilities = serializer.save()

            # Return the created schedules
            response_serializer = DoctorAvailabilitySerializer(
                created_availabilities,
                many=True
            )

            return Response(
                {
                    'message': 'Weekly schedule set successfully',
                    'schedules': response_serializer.data
                },
                status=status.HTTP_201_CREATED
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    @extend_schema(
        tags=['Doctor Management'],
        summary="Get my availability",
        description="Get authenticated doctor's availability schedule"
    )
    def my_availability(self, request):
        """
        Get the authenticated doctor's availability schedule
        """
        if not hasattr(request.user, 'user_type') or request.user.user_type != 'doctor':
            return Response(
                {'error': 'Only doctors can access this endpoint'},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            # Try to get doctor profile
            try:
                doctor = request.user.doctor_profile
            except AttributeError:
                # Fallback: try direct lookup
                from .models import Doctor
                doctor = Doctor.objects.get(user=request.user)

            availability = DoctorAvailability.objects.filter(doctor=doctor).order_by('day_of_week', 'start_time')
            serializer = DoctorAvailabilitySerializer(availability, many=True)

            return Response({
                'doctor_id': doctor.doctor_id,
                'doctor_name': doctor.user.get_full_name(),
                'availability': serializer.data
            })
        except (AttributeError, Doctor.DoesNotExist):
            return Response(
                {'error': 'Doctor profile not found'},
                status=status.HTTP_404_NOT_FOUND
            )
