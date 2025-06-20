from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from drf_spectacular.utils import extend_schema, OpenApiParameter
from django.utils import timezone
from datetime import datetime, timedelta, time
from django.db.models import Q
from .models import Appointment, AppointmentType, AppointmentHistory, AppointmentReminder
from .serializers import (
    AppointmentListSerializer, AppointmentDetailSerializer,
    AppointmentCreateSerializer, AppointmentUpdateSerializer,
    AppointmentTypeSerializer, AppointmentHistorySerializer,
    AppointmentReminderSerializer
)
from doctors.models import Doctor
from patients.models import Patient
from accounts.models import UserActivity
from .services import NotificationService
import logging

logger = logging.getLogger(__name__)


@extend_schema(tags=['Appointment Management'])
class AppointmentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing appointments
    """
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'priority', 'appointment_date', 'doctor', 'patient']
    search_fields = ['appointment_number', 'patient__user__first_name', 'patient__user__last_name',
                    'doctor__user__first_name', 'doctor__user__last_name', 'reason_for_visit']
    ordering_fields = ['appointment_date', 'appointment_time', 'created_at', 'priority']
    ordering = ['appointment_date', 'appointment_time']

    def get_queryset(self):
        """Filter appointments based on user role"""
        # Handle swagger schema generation
        if getattr(self, 'swagger_fake_view', False):
            return Appointment.objects.none()

        user = self.request.user
        if not user.is_authenticated:
            return Appointment.objects.none()

        queryset = Appointment.objects.select_related(
            'patient__user', 'doctor__user', 'appointment_type', 'created_by'
        ).prefetch_related('history', 'reminders')

        if hasattr(user, 'patient_profile'):
            # Patients can only see their own appointments
            return queryset.filter(patient=user.patient_profile)
        elif hasattr(user, 'doctor_profile'):
            # Doctors can see their own appointments
            return queryset.filter(doctor=user.doctor_profile)
        elif getattr(user, 'user_type', None) in ['admin', 'staff']:
            # Admin and staff can see all appointments
            return queryset
        else:
            # Other users have no access
            return queryset.none()

    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'list':
            return AppointmentListSerializer
        elif self.action == 'create':
            return AppointmentCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return AppointmentUpdateSerializer
        else:
            return AppointmentDetailSerializer

    @extend_schema(
        summary="List appointments",
        description="Get list of appointments with advanced filtering and search capabilities",
        parameters=[
            OpenApiParameter('status', str, description='Filter by appointment status'),
            OpenApiParameter('priority', str, description='Filter by priority'),
            OpenApiParameter('appointment_date', str, description='Filter by appointment date (YYYY-MM-DD)'),
            OpenApiParameter('date_from', str, description='Filter appointments from date (YYYY-MM-DD)'),
            OpenApiParameter('date_to', str, description='Filter appointments to date (YYYY-MM-DD)'),
            OpenApiParameter('doctor', str, description='Filter by doctor ID'),
            OpenApiParameter('doctor_name', str, description='Filter by doctor name'),
            OpenApiParameter('patient', str, description='Filter by patient ID'),
            OpenApiParameter('patient_name', str, description='Filter by patient name'),
            OpenApiParameter('department', str, description='Filter by doctor department'),
            OpenApiParameter('appointment_type', str, description='Filter by appointment type'),
            OpenApiParameter('time_from', str, description='Filter by time from (HH:MM)'),
            OpenApiParameter('time_to', str, description='Filter by time to (HH:MM)'),
            OpenApiParameter('duration_min', int, description='Filter by minimum duration'),
            OpenApiParameter('duration_max', int, description='Filter by maximum duration'),
            OpenApiParameter('is_recurring', bool, description='Filter recurring appointments'),
            OpenApiParameter('has_reminders', bool, description='Filter appointments with reminders'),
            OpenApiParameter('search', str, description='Search in appointment number, patient/doctor names, reason'),
            OpenApiParameter('ordering', str, description='Order by: appointment_date, appointment_time, created_at, priority'),
        ]
    )
    def list(self, request, *args, **kwargs):
        """
        Enhanced list view with advanced filtering
        """
        queryset = self.get_queryset()

        # Apply additional custom filters
        queryset = self._apply_advanced_filters(queryset, request)

        # Apply search
        search_query = request.query_params.get('search')
        if search_query:
            queryset = self._apply_search(queryset, search_query)

        # Apply ordering
        ordering = request.query_params.get('ordering')
        if ordering:
            queryset = self._apply_ordering(queryset, ordering)

        # Pagination
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def _apply_advanced_filters(self, queryset, request):
        """
        Apply advanced filtering options
        """
        # Date range filtering
        date_from = request.query_params.get('date_from')
        if date_from:
            try:
                date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
                queryset = queryset.filter(appointment_date__gte=date_from)
            except ValueError:
                pass

        date_to = request.query_params.get('date_to')
        if date_to:
            try:
                date_to = datetime.strptime(date_to, '%Y-%m-%d').date()
                queryset = queryset.filter(appointment_date__lte=date_to)
            except ValueError:
                pass

        # Doctor name filtering
        doctor_name = request.query_params.get('doctor_name')
        if doctor_name:
            queryset = queryset.filter(
                Q(doctor__user__first_name__icontains=doctor_name) |
                Q(doctor__user__last_name__icontains=doctor_name)
            )

        # Patient name filtering
        patient_name = request.query_params.get('patient_name')
        if patient_name:
            queryset = queryset.filter(
                Q(patient__user__first_name__icontains=patient_name) |
                Q(patient__user__last_name__icontains=patient_name)
            )

        # Department filtering
        department = request.query_params.get('department')
        if department:
            queryset = queryset.filter(doctor__department__name__icontains=department)

        # Appointment type filtering
        appointment_type = request.query_params.get('appointment_type')
        if appointment_type:
            queryset = queryset.filter(appointment_type__name__icontains=appointment_type)

        # Time range filtering
        time_from = request.query_params.get('time_from')
        if time_from:
            try:
                time_from = datetime.strptime(time_from, '%H:%M').time()
                queryset = queryset.filter(appointment_time__gte=time_from)
            except ValueError:
                pass

        time_to = request.query_params.get('time_to')
        if time_to:
            try:
                time_to = datetime.strptime(time_to, '%H:%M').time()
                queryset = queryset.filter(appointment_time__lte=time_to)
            except ValueError:
                pass

        # Duration filtering
        duration_min = request.query_params.get('duration_min')
        if duration_min:
            try:
                duration_min = int(duration_min)
                queryset = queryset.filter(duration_minutes__gte=duration_min)
            except ValueError:
                pass

        duration_max = request.query_params.get('duration_max')
        if duration_max:
            try:
                duration_max = int(duration_max)
                queryset = queryset.filter(duration_minutes__lte=duration_max)
            except ValueError:
                pass

        # Recurring appointments filtering
        is_recurring = request.query_params.get('is_recurring')
        if is_recurring is not None:
            queryset = queryset.filter(is_recurring=is_recurring.lower() == 'true')

        # Reminders filtering
        has_reminders = request.query_params.get('has_reminders')
        if has_reminders is not None:
            if has_reminders.lower() == 'true':
                queryset = queryset.filter(reminders__isnull=False).distinct()
            else:
                queryset = queryset.filter(reminders__isnull=True)

        return queryset

    def _apply_search(self, queryset, search_query):
        """
        Apply advanced search functionality
        """
        return queryset.filter(
            Q(appointment_number__icontains=search_query) |
            Q(patient__user__first_name__icontains=search_query) |
            Q(patient__user__last_name__icontains=search_query) |
            Q(patient__patient_id__icontains=search_query) |
            Q(doctor__user__first_name__icontains=search_query) |
            Q(doctor__user__last_name__icontains=search_query) |
            Q(doctor__doctor_id__icontains=search_query) |
            Q(reason_for_visit__icontains=search_query) |
            Q(notes__icontains=search_query) |
            Q(appointment_type__name__icontains=search_query) |
            Q(doctor__department__name__icontains=search_query)
        )

    def _apply_ordering(self, queryset, ordering):
        """
        Apply custom ordering
        """
        valid_orderings = [
            'appointment_date', '-appointment_date',
            'appointment_time', '-appointment_time',
            'created_at', '-created_at',
            'priority', '-priority',
            'status', '-status',
            'patient__user__last_name', '-patient__user__last_name',
            'doctor__user__last_name', '-doctor__user__last_name'
        ]

        if ordering in valid_orderings:
            return queryset.order_by(ordering)

        return queryset

    @action(detail=False, methods=['get'])
    def advanced_search(self, request):
        """
        Advanced search with multiple criteria
        """
        queryset = self.get_queryset()

        # Apply all filters
        queryset = self._apply_advanced_filters(queryset, request)

        # Apply search
        search_query = request.query_params.get('search')
        if search_query:
            queryset = self._apply_search(queryset, search_query)

        # Apply ordering
        ordering = request.query_params.get('ordering', '-appointment_date')
        queryset = self._apply_ordering(queryset, ordering)

        # Get statistics
        total_count = queryset.count()
        status_counts = {}
        for status_choice in Appointment.STATUS_CHOICES:
            status = status_choice[0]
            count = queryset.filter(status=status).count()
            status_counts[status] = count

        # Pagination
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response({
                'results': serializer.data,
                'statistics': {
                    'total_count': total_count,
                    'status_counts': status_counts
                }
            })

        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'results': serializer.data,
            'statistics': {
                'total_count': total_count,
                'status_counts': status_counts
            }
        })

    @action(detail=False, methods=['get'])
    def search_suggestions(self, request):
        """
        Get search suggestions for autocomplete
        """
        query = request.query_params.get('q', '').strip()
        if len(query) < 2:
            return Response({'suggestions': []})

        suggestions = []

        # Patient suggestions
        patients = self.get_queryset().filter(
            Q(patient__user__first_name__icontains=query) |
            Q(patient__user__last_name__icontains=query) |
            Q(patient__patient_id__icontains=query)
        ).values(
            'patient__user__first_name',
            'patient__user__last_name',
            'patient__patient_id'
        ).distinct()[:5]

        for patient in patients:
            suggestions.append({
                'type': 'patient',
                'value': f"{patient['patient__user__first_name']} {patient['patient__user__last_name']}",
                'id': patient['patient__patient_id']
            })

        # Doctor suggestions
        doctors = self.get_queryset().filter(
            Q(doctor__user__first_name__icontains=query) |
            Q(doctor__user__last_name__icontains=query) |
            Q(doctor__doctor_id__icontains=query)
        ).values(
            'doctor__user__first_name',
            'doctor__user__last_name',
            'doctor__doctor_id'
        ).distinct()[:5]

        for doctor in doctors:
            suggestions.append({
                'type': 'doctor',
                'value': f"Dr. {doctor['doctor__user__first_name']} {doctor['doctor__user__last_name']}",
                'id': doctor['doctor__doctor_id']
            })

        # Appointment number suggestions
        appointments = self.get_queryset().filter(
            appointment_number__icontains=query
        ).values('appointment_number').distinct()[:5]

        for appointment in appointments:
            suggestions.append({
                'type': 'appointment',
                'value': appointment['appointment_number'],
                'id': appointment['appointment_number']
            })

        return Response({'suggestions': suggestions[:15]})

    @extend_schema(
        summary="Create appointment",
        description="Book a new appointment with availability checking and conflict resolution"
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        appointment = serializer.save()

        # Log appointment creation
        UserActivity.objects.create(
            user=request.user,
            action='create',
            resource_type='appointment',
            resource_id=str(appointment.id),
            description=f'Created appointment {appointment.appointment_number}',
            ip_address=request.META.get('REMOTE_ADDR', ''),
        )

        # Send confirmation notification
        try:
            NotificationService.send_appointment_confirmation(appointment)
            # Schedule automatic reminders
            NotificationService.schedule_appointment_reminders(appointment)
        except Exception as e:
            logger.error(f"Failed to send notifications for appointment {appointment.appointment_number}: {str(e)}")

        # Return detailed appointment data
        detail_serializer = AppointmentDetailSerializer(appointment)
        return Response(detail_serializer.data, status=status.HTTP_201_CREATED)

    @extend_schema(
        summary="Get appointment details",
        description="Get detailed appointment information including history and reminders"
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(
        summary="Update appointment",
        description="Update appointment details with status validation and history tracking"
    )
    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)

        if response.status_code == 200:
            appointment = self.get_object()
            # Log appointment update
            UserActivity.objects.create(
                user=request.user,
                action='update',
                resource_type='appointment',
                resource_id=str(appointment.id),
                description=f'Updated appointment {appointment.appointment_number}',
                ip_address=request.META.get('REMOTE_ADDR', ''),
            )

        return response

    @extend_schema(
        summary="Partially update appointment",
        description="Partially update appointment details"
    )
    def partial_update(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)

    @action(detail=True, methods=['post'])
    @extend_schema(
        summary="Check in patient",
        description="Mark patient as checked in for the appointment"
    )
    def check_in(self, request, pk=None):
        """Check in patient for appointment"""
        appointment = self.get_object()

        if appointment.status not in ['scheduled', 'confirmed']:
            return Response(
                {'error': 'Can only check in scheduled or confirmed appointments'},
                status=status.HTTP_400_BAD_REQUEST
            )

        appointment.checked_in_at = timezone.now()
        appointment.status = 'confirmed'
        appointment.save()

        # Create history record
        AppointmentHistory.objects.create(
            appointment=appointment,
            action='updated',
            new_values={'status': 'confirmed', 'checked_in_at': str(appointment.checked_in_at)},
            reason='Patient checked in',
            performed_by=request.user
        )

        # Log activity
        UserActivity.objects.create(
            user=request.user,
            action='update',
            resource_type='appointment',
            resource_id=str(appointment.id),
            description=f'Checked in patient for appointment {appointment.appointment_number}',
            ip_address=request.META.get('REMOTE_ADDR', ''),
        )

        serializer = AppointmentDetailSerializer(appointment)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    @extend_schema(
        summary="Start appointment",
        description="Mark appointment as in progress"
    )
    def start(self, request, pk=None):
        """Start the appointment"""
        appointment = self.get_object()

        if appointment.status != 'confirmed':
            return Response(
                {'error': 'Can only start confirmed appointments'},
                status=status.HTTP_400_BAD_REQUEST
            )

        appointment.started_at = timezone.now()
        appointment.status = 'in_progress'
        appointment.save()

        # Create history record
        AppointmentHistory.objects.create(
            appointment=appointment,
            action='updated',
            new_values={'status': 'in_progress', 'started_at': str(appointment.started_at)},
            reason='Appointment started',
            performed_by=request.user
        )

        serializer = AppointmentDetailSerializer(appointment)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    @extend_schema(
        summary="Complete appointment",
        description="Mark appointment as completed"
    )
    def complete(self, request, pk=None):
        """Complete the appointment"""
        appointment = self.get_object()

        if appointment.status != 'in_progress':
            return Response(
                {'error': 'Can only complete appointments that are in progress'},
                status=status.HTTP_400_BAD_REQUEST
            )

        appointment.completed_at = timezone.now()
        appointment.status = 'completed'
        appointment.save()

        # Create history record
        AppointmentHistory.objects.create(
            appointment=appointment,
            action='completed',
            new_values={'status': 'completed', 'completed_at': str(appointment.completed_at)},
            reason='Appointment completed',
            performed_by=request.user
        )

        serializer = AppointmentDetailSerializer(appointment)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    @extend_schema(
        summary="Cancel appointment",
        description="Cancel an appointment with reason",
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'reason': {'type': 'string', 'description': 'Reason for cancellation'}
                },
                'required': ['reason']
            }
        }
    )
    def cancel(self, request, pk=None):
        """Cancel the appointment"""
        appointment = self.get_object()
        reason = request.data.get('reason', '')

        if appointment.status in ['completed', 'cancelled']:
            return Response(
                {'error': 'Cannot cancel completed or already cancelled appointments'},
                status=status.HTTP_400_BAD_REQUEST
            )

        old_status = appointment.status
        appointment.status = 'cancelled'
        appointment.cancelled_at = timezone.now()
        appointment.cancellation_reason = reason
        appointment.cancelled_by = request.data.get('cancelled_by', 'staff')
        appointment.save()

        # Create history record
        AppointmentHistory.objects.create(
            appointment=appointment,
            action='cancelled',
            old_values={'status': old_status},
            new_values={'status': 'cancelled'},
            reason=reason,
            performed_by=request.user
        )

        # Send cancellation notification
        try:
            NotificationService.send_appointment_cancellation(appointment, reason)
            # Cancel any pending reminders
            appointment.reminders.filter(status='pending').update(status='cancelled')
        except Exception as e:
            logger.error(f"Failed to send cancellation notification for appointment {appointment.appointment_number}: {str(e)}")

        serializer = AppointmentDetailSerializer(appointment)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    @extend_schema(
        summary="Mark as no-show",
        description="Mark appointment as no-show when patient doesn't arrive"
    )
    def no_show(self, request, pk=None):
        """Mark appointment as no-show"""
        appointment = self.get_object()

        if appointment.status not in ['scheduled', 'confirmed']:
            return Response(
                {'error': 'Can only mark scheduled or confirmed appointments as no-show'},
                status=status.HTTP_400_BAD_REQUEST
            )

        appointment.status = 'no_show'
        appointment.no_show_at = timezone.now()
        appointment.save()

        # Create history record
        AppointmentHistory.objects.create(
            appointment=appointment,
            action='no_show',
            new_values={'status': 'no_show'},
            reason='Patient did not show up',
            performed_by=request.user
        )

        # Cancel any pending reminders
        try:
            appointment.reminders.filter(status='pending').update(status='cancelled')
        except Exception as e:
            logger.error(f"Failed to cancel reminders for no-show appointment {appointment.appointment_number}: {str(e)}")

        serializer = AppointmentDetailSerializer(appointment)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    @extend_schema(
        summary="Check doctor availability",
        description="Check doctor availability for a specific date and time range",
        parameters=[
            OpenApiParameter('doctor_id', str, description='Doctor ID', required=True),
            OpenApiParameter('date', str, description='Date (YYYY-MM-DD)', required=True),
            OpenApiParameter('start_time', str, description='Start time (HH:MM)', required=False),
            OpenApiParameter('end_time', str, description='End time (HH:MM)', required=False),
        ]
    )
    def check_availability(self, request):
        """Check doctor availability for booking"""
        doctor_id = request.query_params.get('doctor_id')
        date_str = request.query_params.get('date')
        start_time_str = request.query_params.get('start_time', '08:00')
        end_time_str = request.query_params.get('end_time', '18:00')

        if not doctor_id or not date_str:
            return Response(
                {'error': 'doctor_id and date parameters are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            doctor = Doctor.objects.get(doctor_id=doctor_id)
            appointment_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            start_time = datetime.strptime(start_time_str, '%H:%M').time()
            end_time = datetime.strptime(end_time_str, '%H:%M').time()
        except (Doctor.DoesNotExist, ValueError) as e:
            return Response(
                {'error': f'Invalid parameters: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get existing appointments for the doctor on that date
        existing_appointments = Appointment.objects.filter(
            doctor=doctor,
            appointment_date=appointment_date,
            status__in=['scheduled', 'confirmed', 'in_progress']
        ).order_by('appointment_time')

        # Generate available time slots (30-minute intervals)
        available_slots = []
        current_time = datetime.combine(appointment_date, start_time)
        end_datetime = datetime.combine(appointment_date, end_time)

        while current_time < end_datetime:
            slot_end = current_time + timedelta(minutes=30)

            # Check if this slot conflicts with any existing appointment
            is_available = True
            for apt in existing_appointments:
                apt_start = datetime.combine(apt.appointment_date, apt.appointment_time)
                apt_end = apt_start + timedelta(minutes=apt.duration_minutes)

                if (current_time < apt_end and slot_end > apt_start):
                    is_available = False
                    break

            if is_available:
                available_slots.append({
                    'time': current_time.time().strftime('%H:%M'),
                    'datetime': current_time.isoformat(),
                })

            current_time += timedelta(minutes=30)

        return Response({
            'doctor_id': doctor_id,
            'doctor_name': doctor.user.get_full_name(),
            'date': date_str,
            'available_slots': available_slots,
            'existing_appointments': [
                {
                    'time': apt.appointment_time.strftime('%H:%M'),
                    'duration': apt.duration_minutes,
                    'patient': apt.patient.user.get_full_name(),
                    'status': apt.status
                }
                for apt in existing_appointments
            ]
        })


@extend_schema(tags=['Appointment Management'])
class AppointmentTypeViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing appointment types
    """
    queryset = AppointmentType.objects.filter(is_active=True)
    serializer_class = AppointmentTypeSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'duration_minutes', 'created_at']
    ordering = ['name']

    @extend_schema(
        summary="List appointment types",
        description="Get list of available appointment types"
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary="Create appointment type",
        description="Create a new appointment type (Admin only)"
    )
    def create(self, request, *args, **kwargs):
        # Only admins can create appointment types
        if request.user.user_type != 'admin':
            return Response(
                {'error': 'Only administrators can create appointment types'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().create(request, *args, **kwargs)

    @extend_schema(
        summary="Get appointment type details",
        description="Get detailed information about an appointment type"
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(
        summary="Update appointment type",
        description="Update appointment type details (Admin only)"
    )
    def update(self, request, *args, **kwargs):
        if request.user.user_type != 'admin':
            return Response(
                {'error': 'Only administrators can update appointment types'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().update(request, *args, **kwargs)

    @extend_schema(
        summary="Delete appointment type",
        description="Deactivate appointment type (Admin only)"
    )
    def destroy(self, request, *args, **kwargs):
        if request.user.user_type != 'admin':
            return Response(
                {'error': 'Only administrators can delete appointment types'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Soft delete by setting is_active to False
        appointment_type = self.get_object()
        appointment_type.is_active = False
        appointment_type.save()

        return Response(status=status.HTTP_204_NO_CONTENT)
