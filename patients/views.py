from rest_framework import generics, permissions, status, viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import PermissionDenied
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, OpenApiParameter
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone
from .models import Patient, EmergencyContact, InsuranceInformation
from .serializers import (
    PatientRegistrationSerializer, PatientProfileSerializer, PatientListSerializer,
    PatientUpdateSerializer, EmergencyContactSerializer, InsuranceInformationSerializer
)
from accounts.models import UserActivity
import logging

logger = logging.getLogger(__name__)
User = get_user_model()


class PatientRegistrationView(generics.CreateAPIView):
    """
    Patient registration endpoint
    """
    serializer_class = PatientRegistrationSerializer
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        tags=['Patient Management'],
        summary="Register new patient",
        description="Register a new patient with user account creation",
        responses={201: PatientProfileSerializer}
    )
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            patient = serializer.save()

            # Log patient registration
            UserActivity.objects.create(
                user=patient.user,
                action='create',
                resource_type='patient_registration',
                description='Patient registered successfully',
                ip_address=request.META.get('REMOTE_ADDR', ''),
            )

            # Return detailed patient profile
            profile_serializer = PatientProfileSerializer(patient)
            return Response(
                {
                    'message': 'Patient registered successfully',
                    'patient': profile_serializer.data
                },
                status=status.HTTP_201_CREATED
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(tags=['Patient Management'])
class PatientViewSet(viewsets.ModelViewSet):
    """
    ViewSet for patient management
    """
    queryset = Patient.objects.select_related('user').prefetch_related(
        'emergency_contacts', 'insurance_info'
    ).filter(is_active=True)
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['blood_type', 'marital_status', 'is_active']
    search_fields = ['patient_id', 'user__first_name', 'user__last_name', 'user__email']
    ordering_fields = ['patient_id', 'registration_date', 'user__first_name', 'user__last_name']
    ordering = ['patient_id']

    def get_serializer_class(self):
        if self.action == 'list':
            return PatientListSerializer
        elif self.action in ['update', 'partial_update']:
            return PatientUpdateSerializer
        return PatientProfileSerializer

    def get_queryset(self):
        queryset = super().get_queryset()

        # Role-based filtering
        user = self.request.user
        if user.user_type == 'patient':
            # Patients can only see their own profile
            return queryset.filter(user=user)
        elif user.user_type in ['doctor', 'nurse']:
            # Medical staff can see all active patients
            return queryset
        elif user.user_type == 'admin':
            # Admins can see all patients including inactive
            return Patient.objects.select_related('user').prefetch_related(
                'emergency_contacts', 'insurance_info'
            )
        else:
            # Other roles have no access
            return queryset.none()

    @extend_schema(
        tags=['Patient Management'],
        summary="List patients",
        description="Get list of patients with filtering and search",
        parameters=[
            OpenApiParameter('search', str, description='Search by patient ID, name, or email'),
            OpenApiParameter('blood_type', str, description='Filter by blood type'),
            OpenApiParameter('marital_status', str, description='Filter by marital status'),
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        tags=['Patient Management'],
        summary="Get patient details",
        description="Get detailed patient information including emergency contacts and insurance"
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(
        tags=['Patient Management'],
        summary="Update patient information",
        description="Update patient medical and personal information"
    )
    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)

        if response.status_code == 200:
            # Log patient update
            UserActivity.objects.create(
                user=request.user,
                action='update',
                resource_type='patient_profile',
                description=f'Patient {self.get_object().patient_id} updated',
                ip_address=request.META.get('REMOTE_ADDR', ''),
            )

        return response

    @action(detail=True, methods=['get'])
    def medical_summary(self, request, pk=None):
        """
        Get patient medical summary
        """
        patient = self.get_object()

        summary = {
            'patient_id': patient.patient_id,
            'full_name': patient.user.get_full_name(),
            'age': self._calculate_age(patient.user.date_of_birth),
            'blood_type': patient.blood_type,
            'bmi': patient.bmi,
            'allergies': patient.allergies,
            'chronic_conditions': patient.chronic_conditions,
            'current_medications': patient.current_medications,
            'emergency_contact': {
                'name': patient.emergency_contact_name,
                'phone': patient.emergency_contact_phone,
                'relationship': patient.emergency_contact_relationship
            },
            'insurance_active': patient.insurance_info.filter(is_active=True).exists(),
            'registration_date': patient.registration_date,
            'last_updated': patient.updated_at
        }

        return Response(summary)

    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        """
        Deactivate patient account
        """
        patient = self.get_object()

        # Only admins can deactivate patients
        if request.user.user_type != 'admin':
            return Response(
                {'error': 'Only administrators can deactivate patient accounts'},
                status=status.HTTP_403_FORBIDDEN
            )

        patient.is_active = False
        patient.save()

        # Log deactivation
        UserActivity.objects.create(
            user=request.user,
            action='update',
            resource_type='patient_account',
            description=f'Patient {patient.patient_id} deactivated',
            ip_address=request.META.get('REMOTE_ADDR', ''),
        )

        return Response({'message': 'Patient account deactivated successfully'})

    @action(detail=True, methods=['post'])
    def reactivate(self, request, pk=None):
        """
        Reactivate patient account
        """
        patient = self.get_object()

        # Only admins can reactivate patients
        if request.user.user_type != 'admin':
            return Response(
                {'error': 'Only administrators can reactivate patient accounts'},
                status=status.HTTP_403_FORBIDDEN
            )

        patient.is_active = True
        patient.save()

        # Log reactivation
        UserActivity.objects.create(
            user=request.user,
            action='update',
            resource_type='patient_account',
            description=f'Patient {patient.patient_id} reactivated',
            ip_address=request.META.get('REMOTE_ADDR', ''),
        )

        return Response({'message': 'Patient account reactivated successfully'})

    def _calculate_age(self, date_of_birth):
        """Calculate age from date of birth"""
        if date_of_birth:
            today = timezone.now().date()
            return today.year - date_of_birth.year - (
                (today.month, today.day) < (date_of_birth.month, date_of_birth.day)
            )
        return None


class PatientProfileView(generics.RetrieveUpdateAPIView):
    """
    Patient profile view for authenticated patients
    """
    serializer_class = PatientProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        # Patients can only access their own profile
        if self.request.user.user_type == 'patient':
            try:
                return Patient.objects.select_related('user').prefetch_related(
                    'emergency_contacts', 'insurance_info'
                ).get(user=self.request.user)
            except Patient.DoesNotExist:
                return None
        else:
            # Other user types should use PatientViewSet
            return None

    @extend_schema(
        tags=['Patient Management'],
        summary="Get my patient profile",
        description="Get authenticated patient's own profile information"
    )
    def get(self, request, *args, **kwargs):
        patient = self.get_object()
        if not patient:
            return Response(
                {'error': 'Patient profile not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = self.get_serializer(patient)
        return Response(serializer.data)

    @extend_schema(
        tags=['Patient Management'],
        summary="Update my patient profile",
        description="Update authenticated patient's own profile information"
    )
    def patch(self, request, *args, **kwargs):
        patient = self.get_object()
        if not patient:
            return Response(
                {'error': 'Patient profile not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = PatientUpdateSerializer(patient, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()

            # Log profile update
            UserActivity.objects.create(
                user=request.user,
                action='update',
                resource_type='patient_profile',
                description='Patient updated own profile',
                ip_address=request.META.get('REMOTE_ADDR', ''),
            )

            # Return updated profile
            profile_serializer = PatientProfileSerializer(patient)
            return Response(profile_serializer.data)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        tags=['Patient Management'],
        summary="Update my patient profile",
        description="Update authenticated patient's own profile information"
    )
    def put(self, request, *args, **kwargs):
        patient = self.get_object()
        if not patient:
            return Response(
                {'error': 'Patient profile not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = PatientUpdateSerializer(patient, data=request.data)
        if serializer.is_valid():
            serializer.save()

            # Log profile update
            UserActivity.objects.create(
                user=request.user,
                action='update',
                resource_type='patient_profile',
                description='Patient updated own profile',
                ip_address=request.META.get('REMOTE_ADDR', ''),
            )

            # Return updated profile
            profile_serializer = PatientProfileSerializer(patient)
            return Response(profile_serializer.data)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(tags=['Patient Management'])
class EmergencyContactViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing patient emergency contacts
    """
    serializer_class = EmergencyContactSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        patient_id = self.kwargs.get('patient_pk')
        if patient_id:
            return EmergencyContact.objects.filter(patient_id=patient_id)
        return EmergencyContact.objects.none()

    def perform_create(self, serializer):
        patient_id = self.kwargs.get('patient_pk')
        patient = Patient.objects.get(id=patient_id)

        # Check permissions
        if (self.request.user.user_type == 'patient' and
            patient.user != self.request.user):
            raise PermissionDenied("You can only manage your own emergency contacts")

        serializer.save(patient=patient)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        patient_id = self.kwargs.get('patient_pk')
        if patient_id:
            context['patient'] = Patient.objects.get(id=patient_id)
        return context


@extend_schema(tags=['Patient Management'])
class InsuranceInformationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing patient insurance information
    """
    serializer_class = InsuranceInformationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        patient_id = self.kwargs.get('patient_pk')
        if patient_id:
            return InsuranceInformation.objects.filter(patient_id=patient_id)
        return InsuranceInformation.objects.none()

    def perform_create(self, serializer):
        patient_id = self.kwargs.get('patient_pk')
        patient = Patient.objects.get(id=patient_id)

        # Check permissions
        if (self.request.user.user_type == 'patient' and
            patient.user != self.request.user):
            raise PermissionDenied("You can only manage your own insurance information")

        serializer.save(patient=patient)
