from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from django.db.models import Q, Prefetch, Count, Sum, Avg
from datetime import datetime, timedelta
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from .models import (
    MedicalRecord, VitalSigns, Diagnosis, Prescription,
    LabTest, MedicalDocument
)
from .alert_models import MedicalAlert, PatientAllergy, DrugInteraction, CriticalCondition
from .serializers import (
    MedicalRecordListSerializer, MedicalRecordDetailSerializer,
    MedicalRecordCreateSerializer, VitalSignsSerializer,
    DiagnosisSerializer, PrescriptionSerializer, LabTestSerializer,
    MedicalDocumentSerializer, MedicalHistoryTimelineSerializer,
    MedicalAlertSerializer, PatientAllergySerializer, DrugInteractionSerializer,
    CriticalConditionSerializer
)
from patients.models import Patient
from doctors.models import Doctor
from accounts.models import UserActivity
import logging

logger = logging.getLogger(__name__)


@extend_schema(tags=['Medical Records Management'])
class MedicalRecordViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing medical records
    """
    serializer_class = MedicalRecordListSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        Filter medical records based on user role
        """
        user = self.request.user

        if user.user_type == 'admin':
            # Admin can see all records
            return MedicalRecord.objects.select_related(
                'patient__user', 'doctor__user', 'appointment'
            ).prefetch_related(
                'vital_signs', 'diagnoses', 'prescriptions', 'lab_tests', 'documents'
            ).all()

        elif user.user_type == 'doctor':
            # Doctors can see records they created or are assigned to
            return MedicalRecord.objects.select_related(
                'patient__user', 'doctor__user', 'appointment'
            ).prefetch_related(
                'vital_signs', 'diagnoses', 'prescriptions', 'lab_tests', 'documents'
            ).filter(doctor=user.doctor_profile)

        elif user.user_type == 'patient':
            # Patients can only see their own records
            return MedicalRecord.objects.select_related(
                'patient__user', 'doctor__user', 'appointment'
            ).prefetch_related(
                'vital_signs', 'diagnoses', 'prescriptions', 'lab_tests', 'documents'
            ).filter(patient=user.patient_profile)

        else:
            # Staff can see all records (read-only)
            return MedicalRecord.objects.select_related(
                'patient__user', 'doctor__user', 'appointment'
            ).prefetch_related(
                'vital_signs', 'diagnoses', 'prescriptions', 'lab_tests', 'documents'
            ).all()

    def get_serializer_class(self):
        """
        Return appropriate serializer based on action
        """
        if self.action == 'create':
            return MedicalRecordCreateSerializer
        elif self.action in ['retrieve', 'update', 'partial_update']:
            return MedicalRecordDetailSerializer
        return MedicalRecordListSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        medical_record = serializer.save()

        # Log medical record creation
        UserActivity.objects.create(
            user=request.user,
            action='create',
            resource_type='medical_record',
            resource_id=str(medical_record.id),
            description=f'Created medical record {medical_record.record_number}',
            ip_address=request.META.get('REMOTE_ADDR', ''),
        )

        # Return detailed medical record data
        detail_serializer = MedicalRecordDetailSerializer(medical_record)
        return Response(detail_serializer.data, status=status.HTTP_201_CREATED)

    @extend_schema(
        parameters=[
            OpenApiParameter('patient_id', OpenApiTypes.STR, description='Filter by patient ID'),
            OpenApiParameter('doctor_id', OpenApiTypes.STR, description='Filter by doctor ID'),
            OpenApiParameter('record_type', OpenApiTypes.STR, description='Filter by record type'),
            OpenApiParameter('date_from', OpenApiTypes.DATE, description='Filter records from date'),
            OpenApiParameter('date_to', OpenApiTypes.DATE, description='Filter records to date'),
            OpenApiParameter('is_finalized', OpenApiTypes.BOOL, description='Filter by finalization status'),
        ]
    )
    def list(self, request, *args, **kwargs):
        """
        List medical records with filtering options
        """
        queryset = self.get_queryset()

        # Apply filters
        patient_id = request.query_params.get('patient_id')
        if patient_id:
            queryset = queryset.filter(patient__patient_id=patient_id)

        doctor_id = request.query_params.get('doctor_id')
        if doctor_id:
            queryset = queryset.filter(doctor__doctor_id=doctor_id)

        record_type = request.query_params.get('record_type')
        if record_type:
            queryset = queryset.filter(record_type=record_type)

        date_from = request.query_params.get('date_from')
        if date_from:
            try:
                date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
                queryset = queryset.filter(record_date__date__gte=date_from)
            except ValueError:
                pass

        date_to = request.query_params.get('date_to')
        if date_to:
            try:
                date_to = datetime.strptime(date_to, '%Y-%m-%d').date()
                queryset = queryset.filter(record_date__date__lte=date_to)
            except ValueError:
                pass

        is_finalized = request.query_params.get('is_finalized')
        if is_finalized is not None:
            queryset = queryset.filter(is_finalized=is_finalized.lower() == 'true')

        # Search functionality
        search = request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(record_number__icontains=search) |
                Q(chief_complaint__icontains=search) |
                Q(patient__user__first_name__icontains=search) |
                Q(patient__user__last_name__icontains=search) |
                Q(doctor__user__first_name__icontains=search) |
                Q(doctor__user__last_name__icontains=search)
            )

        # Pagination
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def patient_history(self, request):
        """
        Get complete medical history for a specific patient
        """
        patient_id = request.query_params.get('patient_id')
        if not patient_id:
            return Response(
                {'error': 'patient_id parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            patient = Patient.objects.get(patient_id=patient_id)
        except Patient.DoesNotExist:
            return Response(
                {'error': 'Patient not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Check permissions
        user = request.user
        if user.user_type == 'patient' and user.patient_profile != patient:
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Get all medical records for the patient
        records = MedicalRecord.objects.filter(patient=patient).select_related(
            'doctor__user', 'appointment'
        ).prefetch_related(
            'vital_signs', 'diagnoses', 'prescriptions', 'lab_tests', 'documents'
        ).order_by('-record_date')

        serializer = MedicalRecordDetailSerializer(records, many=True)
        return Response({
            'patient': {
                'id': patient.patient_id,
                'name': patient.user.get_full_name(),
                'date_of_birth': patient.user.date_of_birth,
                'gender': patient.user.gender,
            },
            'total_records': records.count(),
            'records': serializer.data
        })

    @action(detail=False, methods=['get'])
    def timeline(self, request):
        """
        Get medical history timeline for a patient
        """
        patient_id = request.query_params.get('patient_id')
        if not patient_id:
            return Response(
                {'error': 'patient_id parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            patient = Patient.objects.get(patient_id=patient_id)
        except Patient.DoesNotExist:
            return Response(
                {'error': 'Patient not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Check permissions
        user = request.user
        if user.user_type == 'patient' and user.patient_profile != patient:
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )

        timeline_events = []

        # Get medical records
        records = MedicalRecord.objects.filter(patient=patient).select_related('doctor__user')
        for record in records:
            timeline_events.append({
                'date': record.record_date,
                'type': 'medical_record',
                'title': f'{record.get_record_type_display()} - {record.chief_complaint}',
                'description': record.assessment or record.notes or 'No description available',
                'details': {
                    'record_number': record.record_number,
                    'record_type': record.record_type,
                    'is_finalized': record.is_finalized
                },
                'record_id': record.id,
                'doctor_name': record.doctor.user.get_full_name()
            })

        # Get diagnoses
        diagnoses = Diagnosis.objects.filter(
            medical_record__patient=patient
        ).select_related('medical_record__doctor__user')
        for diagnosis in diagnoses:
            timeline_events.append({
                'date': diagnosis.created_at,
                'type': 'diagnosis',
                'title': f'Diagnosis: {diagnosis.diagnosis_name}',
                'description': diagnosis.description or f'{diagnosis.get_diagnosis_type_display()} diagnosis',
                'details': {
                    'icd10_code': diagnosis.icd10_code,
                    'diagnosis_type': diagnosis.diagnosis_type,
                    'severity': diagnosis.severity,
                    'is_chronic': diagnosis.is_chronic,
                    'is_resolved': diagnosis.is_resolved
                },
                'record_id': diagnosis.medical_record.id,
                'doctor_name': diagnosis.medical_record.doctor.user.get_full_name()
            })

        # Get prescriptions
        prescriptions = Prescription.objects.filter(
            medical_record__patient=patient
        ).select_related('medical_record__doctor__user')
        for prescription in prescriptions:
            timeline_events.append({
                'date': prescription.created_at,
                'type': 'prescription',
                'title': f'Prescription: {prescription.medication_name}',
                'description': f'{prescription.dosage} - {prescription.get_frequency_display()}',
                'details': {
                    'medication_name': prescription.medication_name,
                    'dosage': prescription.dosage,
                    'frequency': prescription.frequency,
                    'status': prescription.status,
                    'instructions': prescription.instructions
                },
                'record_id': prescription.medical_record.id,
                'doctor_name': prescription.medical_record.doctor.user.get_full_name()
            })

        # Sort timeline by date (most recent first)
        timeline_events.sort(key=lambda x: x['date'], reverse=True)

        # Apply date filtering if provided
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')

        if date_from:
            try:
                date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
                timeline_events = [
                    event for event in timeline_events
                    if event['date'].date() >= date_from
                ]
            except ValueError:
                pass

        if date_to:
            try:
                date_to = datetime.strptime(date_to, '%Y-%m-%d').date()
                timeline_events = [
                    event for event in timeline_events
                    if event['date'].date() <= date_to
                ]
            except ValueError:
                pass

        # Limit results if requested
        limit = request.query_params.get('limit')
        if limit:
            try:
                limit = int(limit)
                timeline_events = timeline_events[:limit]
            except ValueError:
                pass

        return Response({
            'patient': {
                'id': patient.patient_id,
                'name': patient.user.get_full_name(),
            },
            'total_events': len(timeline_events),
            'timeline': timeline_events
        })

    @action(detail=True, methods=['post'])
    def finalize(self, request, pk=None):
        """
        Finalize a medical record
        """
        medical_record = self.get_object()

        # Check if user can finalize this record
        user = request.user
        if user.user_type not in ['admin', 'doctor'] or (
            user.user_type == 'doctor' and medical_record.doctor != user.doctor_profile
        ):
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )

        if medical_record.is_finalized:
            return Response(
                {'error': 'Medical record is already finalized'},
                status=status.HTTP_400_BAD_REQUEST
            )

        medical_record.is_finalized = True
        medical_record.finalized_at = timezone.now()
        medical_record.save()

        # Log finalization
        UserActivity.objects.create(
            user=request.user,
            action='finalize',
            resource_type='medical_record',
            resource_id=str(medical_record.id),
            description=f'Finalized medical record {medical_record.record_number}',
            ip_address=request.META.get('REMOTE_ADDR', ''),
        )

        serializer = MedicalRecordDetailSerializer(medical_record)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """
        Get medical records statistics
        """
        user = request.user

        # Base queryset based on user permissions
        if user.user_type == 'admin':
            queryset = MedicalRecord.objects.all()
        elif user.user_type == 'doctor':
            queryset = MedicalRecord.objects.filter(doctor=user.doctor_profile)
        elif user.user_type == 'patient':
            queryset = MedicalRecord.objects.filter(patient=user.patient_profile)
        else:
            queryset = MedicalRecord.objects.all()

        # Calculate statistics
        total_records = queryset.count()
        finalized_records = queryset.filter(is_finalized=True).count()
        recent_records = queryset.filter(
            record_date__gte=timezone.now() - timedelta(days=30)
        ).count()

        # Records by type
        record_types = {}
        for record_type, display_name in MedicalRecord.RECORD_TYPES:
            count = queryset.filter(record_type=record_type).count()
            record_types[record_type] = {
                'name': display_name,
                'count': count
            }

        # Recent activity (last 7 days)
        recent_activity = []
        for i in range(7):
            date = timezone.now().date() - timedelta(days=i)
            count = queryset.filter(record_date__date=date).count()
            recent_activity.append({
                'date': date,
                'count': count
            })

        return Response({
            'total_records': total_records,
            'finalized_records': finalized_records,
            'pending_records': total_records - finalized_records,
            'recent_records_30_days': recent_records,
            'finalization_rate': round((finalized_records / total_records * 100), 2) if total_records > 0 else 0,
            'record_types': record_types,
            'recent_activity': recent_activity
        })


@extend_schema(tags=['Medical Records Management'])
class DiagnosisViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing diagnoses
    """
    serializer_class = DiagnosisSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        Filter diagnoses based on user role and permissions
        """
        user = self.request.user

        if user.user_type == 'admin':
            # Admin can see all diagnoses
            return Diagnosis.objects.select_related(
                'medical_record__patient__user', 'medical_record__doctor__user'
            ).all()

        elif user.user_type == 'doctor':
            # Doctors can see diagnoses from their medical records
            return Diagnosis.objects.select_related(
                'medical_record__patient__user', 'medical_record__doctor__user'
            ).filter(medical_record__doctor=user.doctor_profile)

        elif user.user_type == 'patient':
            # Patients can only see their own diagnoses
            return Diagnosis.objects.select_related(
                'medical_record__patient__user', 'medical_record__doctor__user'
            ).filter(medical_record__patient=user.patient_profile)

        else:
            # Staff can see all diagnoses (read-only)
            return Diagnosis.objects.select_related(
                'medical_record__patient__user', 'medical_record__doctor__user'
            ).all()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        diagnosis = serializer.save()

        # Log diagnosis creation
        UserActivity.objects.create(
            user=request.user,
            action='create',
            resource_type='diagnosis',
            resource_id=str(diagnosis.id),
            description=f'Created diagnosis: {diagnosis.diagnosis_name}',
            ip_address=request.META.get('REMOTE_ADDR', ''),
        )

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'])
    def by_patient(self, request):
        """
        Get all diagnoses for a specific patient
        """
        patient_id = request.query_params.get('patient_id')
        if not patient_id:
            return Response(
                {'error': 'patient_id parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            patient = Patient.objects.get(patient_id=patient_id)
        except Patient.DoesNotExist:
            return Response(
                {'error': 'Patient not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Check permissions
        user = request.user
        if user.user_type == 'patient' and user.patient_profile != patient:
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )

        diagnoses = Diagnosis.objects.filter(
            medical_record__patient=patient
        ).select_related('medical_record__doctor__user').order_by('-created_at')

        # Group by status
        active_diagnoses = diagnoses.filter(is_resolved=False)
        resolved_diagnoses = diagnoses.filter(is_resolved=True)
        chronic_diagnoses = diagnoses.filter(is_chronic=True)

        return Response({
            'patient': {
                'id': patient.patient_id,
                'name': patient.user.get_full_name(),
            },
            'total_diagnoses': diagnoses.count(),
            'active_diagnoses': DiagnosisSerializer(active_diagnoses, many=True).data,
            'resolved_diagnoses': DiagnosisSerializer(resolved_diagnoses, many=True).data,
            'chronic_diagnoses': DiagnosisSerializer(chronic_diagnoses, many=True).data,
            'statistics': {
                'total': diagnoses.count(),
                'active': active_diagnoses.count(),
                'resolved': resolved_diagnoses.count(),
                'chronic': chronic_diagnoses.count()
            }
        })

    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        """
        Mark a diagnosis as resolved
        """
        diagnosis = self.get_object()

        # Check if user can resolve this diagnosis
        user = request.user
        if user.user_type not in ['admin', 'doctor'] or (
            user.user_type == 'doctor' and diagnosis.medical_record.doctor != user.doctor_profile
        ):
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )

        if diagnosis.is_resolved:
            return Response(
                {'error': 'Diagnosis is already resolved'},
                status=status.HTTP_400_BAD_REQUEST
            )

        diagnosis.is_resolved = True
        diagnosis.resolution_date = timezone.now().date()
        diagnosis.save()

        # Log resolution
        UserActivity.objects.create(
            user=request.user,
            action='resolve',
            resource_type='diagnosis',
            resource_id=str(diagnosis.id),
            description=f'Resolved diagnosis: {diagnosis.diagnosis_name}',
            ip_address=request.META.get('REMOTE_ADDR', ''),
        )

        serializer = DiagnosisSerializer(diagnosis)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """
        Get diagnosis statistics
        """
        user = request.user

        # Base queryset based on user permissions
        if user.user_type == 'admin':
            queryset = Diagnosis.objects.all()
        elif user.user_type == 'doctor':
            queryset = Diagnosis.objects.filter(medical_record__doctor=user.doctor_profile)
        elif user.user_type == 'patient':
            queryset = Diagnosis.objects.filter(medical_record__patient=user.patient_profile)
        else:
            queryset = Diagnosis.objects.all()

        # Calculate statistics
        total_diagnoses = queryset.count()
        active_diagnoses = queryset.filter(is_resolved=False).count()
        resolved_diagnoses = queryset.filter(is_resolved=True).count()
        chronic_diagnoses = queryset.filter(is_chronic=True).count()

        # Diagnoses by type
        diagnosis_types = {}
        for diagnosis_type, display_name in Diagnosis.DIAGNOSIS_TYPES:
            count = queryset.filter(diagnosis_type=diagnosis_type).count()
            diagnosis_types[diagnosis_type] = {
                'name': display_name,
                'count': count
            }

        # Most common diagnoses
        common_diagnoses = queryset.values('diagnosis_name').annotate(
            count=Count('diagnosis_name')
        ).order_by('-count')[:10]

        return Response({
            'total_diagnoses': total_diagnoses,
            'active_diagnoses': active_diagnoses,
            'resolved_diagnoses': resolved_diagnoses,
            'chronic_diagnoses': chronic_diagnoses,
            'resolution_rate': round((resolved_diagnoses / total_diagnoses * 100), 2) if total_diagnoses > 0 else 0,
            'diagnosis_types': diagnosis_types,
            'common_diagnoses': list(common_diagnoses)
        })


@extend_schema(tags=['Medical Records Management'])
class PrescriptionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing prescriptions and treatments
    """
    serializer_class = PrescriptionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        Filter prescriptions based on user role and permissions
        """
        user = self.request.user

        if user.user_type == 'admin':
            # Admin can see all prescriptions
            return Prescription.objects.select_related(
                'medical_record__patient__user', 'medical_record__doctor__user'
            ).all()

        elif user.user_type == 'doctor':
            # Doctors can see prescriptions from their medical records
            return Prescription.objects.select_related(
                'medical_record__patient__user', 'medical_record__doctor__user'
            ).filter(medical_record__doctor=user.doctor_profile)

        elif user.user_type == 'patient':
            # Patients can only see their own prescriptions
            return Prescription.objects.select_related(
                'medical_record__patient__user', 'medical_record__doctor__user'
            ).filter(medical_record__patient=user.patient_profile)

        else:
            # Staff can see all prescriptions (read-only)
            return Prescription.objects.select_related(
                'medical_record__patient__user', 'medical_record__doctor__user'
            ).all()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        prescription = serializer.save()

        # Log prescription creation
        UserActivity.objects.create(
            user=request.user,
            action='create',
            resource_type='prescription',
            resource_id=str(prescription.id),
            description=f'Created prescription: {prescription.medication_name}',
            ip_address=request.META.get('REMOTE_ADDR', ''),
        )

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'])
    def by_patient(self, request):
        """
        Get all prescriptions for a specific patient
        """
        patient_id = request.query_params.get('patient_id')
        if not patient_id:
            return Response(
                {'error': 'patient_id parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            patient = Patient.objects.get(patient_id=patient_id)
        except Patient.DoesNotExist:
            return Response(
                {'error': 'Patient not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Check permissions
        user = request.user
        if user.user_type == 'patient' and user.patient_profile != patient:
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )

        prescriptions = Prescription.objects.filter(
            medical_record__patient=patient
        ).select_related('medical_record__doctor__user').order_by('-created_at')

        # Group by status
        active_prescriptions = prescriptions.filter(status='active')
        completed_prescriptions = prescriptions.filter(status='completed')
        discontinued_prescriptions = prescriptions.filter(status='discontinued')

        return Response({
            'patient': {
                'id': patient.patient_id,
                'name': patient.user.get_full_name(),
            },
            'total_prescriptions': prescriptions.count(),
            'active_prescriptions': PrescriptionSerializer(active_prescriptions, many=True).data,
            'completed_prescriptions': PrescriptionSerializer(completed_prescriptions, many=True).data,
            'discontinued_prescriptions': PrescriptionSerializer(discontinued_prescriptions, many=True).data,
            'statistics': {
                'total': prescriptions.count(),
                'active': active_prescriptions.count(),
                'completed': completed_prescriptions.count(),
                'discontinued': discontinued_prescriptions.count()
            }
        })

    @action(detail=True, methods=['post'])
    def discontinue(self, request, pk=None):
        """
        Discontinue a prescription
        """
        prescription = self.get_object()

        # Check if user can discontinue this prescription
        user = request.user
        if user.user_type not in ['admin', 'doctor'] or (
            user.user_type == 'doctor' and prescription.medical_record.doctor != user.doctor_profile
        ):
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )

        if prescription.status == 'discontinued':
            return Response(
                {'error': 'Prescription is already discontinued'},
                status=status.HTTP_400_BAD_REQUEST
            )

        reason = request.data.get('reason', 'Discontinued by doctor')
        prescription.status = 'discontinued'
        prescription.save()

        # Log discontinuation
        UserActivity.objects.create(
            user=request.user,
            action='discontinue',
            resource_type='prescription',
            resource_id=str(prescription.id),
            description=f'Discontinued prescription: {prescription.medication_name} - {reason}',
            ip_address=request.META.get('REMOTE_ADDR', ''),
        )

        serializer = PrescriptionSerializer(prescription)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """
        Mark a prescription as completed
        """
        prescription = self.get_object()

        # Check if user can complete this prescription
        user = request.user
        if user.user_type not in ['admin', 'doctor'] or (
            user.user_type == 'doctor' and prescription.medical_record.doctor != user.doctor_profile
        ):
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )

        if prescription.status == 'completed':
            return Response(
                {'error': 'Prescription is already completed'},
                status=status.HTTP_400_BAD_REQUEST
            )

        prescription.status = 'completed'
        prescription.save()

        # Log completion
        UserActivity.objects.create(
            user=request.user,
            action='complete',
            resource_type='prescription',
            resource_id=str(prescription.id),
            description=f'Completed prescription: {prescription.medication_name}',
            ip_address=request.META.get('REMOTE_ADDR', ''),
        )

        serializer = PrescriptionSerializer(prescription)
        return Response(serializer.data)


@extend_schema(tags=['Medical Records Management'])
class MedicalDocumentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing medical documents and files
    """
    serializer_class = MedicalDocumentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        Filter medical documents based on user role and permissions
        """
        user = self.request.user

        if user.user_type == 'admin':
            # Admin can see all documents
            return MedicalDocument.objects.select_related(
                'medical_record__patient__user', 'medical_record__doctor__user', 'uploaded_by'
            ).all()

        elif user.user_type == 'doctor':
            # Doctors can see documents from their medical records
            return MedicalDocument.objects.select_related(
                'medical_record__patient__user', 'medical_record__doctor__user', 'uploaded_by'
            ).filter(medical_record__doctor=user.doctor_profile)

        elif user.user_type == 'patient':
            # Patients can only see their own documents
            return MedicalDocument.objects.select_related(
                'medical_record__patient__user', 'medical_record__doctor__user', 'uploaded_by'
            ).filter(medical_record__patient=user.patient_profile)

        else:
            # Staff can see all documents (read-only)
            return MedicalDocument.objects.select_related(
                'medical_record__patient__user', 'medical_record__doctor__user', 'uploaded_by'
            ).all()

    def create(self, request, *args, **kwargs):
        # Set the uploaded_by field to the current user
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Set file metadata
        uploaded_file = request.FILES.get('file')
        if uploaded_file:
            serializer.validated_data['file_size'] = uploaded_file.size
            serializer.validated_data['mime_type'] = uploaded_file.content_type

        serializer.validated_data['uploaded_by'] = request.user
        document = serializer.save()

        # Log document upload
        UserActivity.objects.create(
            user=request.user,
            action='upload',
            resource_type='medical_document',
            resource_id=str(document.id),
            description=f'Uploaded document: {document.title}',
            ip_address=request.META.get('REMOTE_ADDR', ''),
        )

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'])
    def by_patient(self, request):
        """
        Get all documents for a specific patient
        """
        patient_id = request.query_params.get('patient_id')
        if not patient_id:
            return Response(
                {'error': 'patient_id parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            patient = Patient.objects.get(patient_id=patient_id)
        except Patient.DoesNotExist:
            return Response(
                {'error': 'Patient not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Check permissions
        user = request.user
        if user.user_type == 'patient' and user.patient_profile != patient:
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )

        documents = MedicalDocument.objects.filter(
            medical_record__patient=patient
        ).select_related('medical_record__doctor__user', 'uploaded_by').order_by('-upload_date')

        # Group by document type
        document_groups = {}
        for doc_type, display_name in MedicalDocument.DOCUMENT_TYPES:
            docs = documents.filter(document_type=doc_type)
            document_groups[doc_type] = {
                'name': display_name,
                'count': docs.count(),
                'documents': MedicalDocumentSerializer(docs, many=True, context={'request': request}).data
            }

        return Response({
            'patient': {
                'id': patient.patient_id,
                'name': patient.user.get_full_name(),
            },
            'total_documents': documents.count(),
            'document_groups': document_groups,
            'statistics': {
                'total': documents.count(),
                'confidential': documents.filter(is_confidential=True).count(),
                'recent_uploads': documents.filter(
                    upload_date__gte=timezone.now() - timedelta(days=30)
                ).count()
            }
        })

    @action(detail=False, methods=['get'])
    def by_type(self, request):
        """
        Get documents filtered by type
        """
        document_type = request.query_params.get('type')
        if not document_type:
            return Response(
                {'error': 'type parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate document type
        valid_types = [choice[0] for choice in MedicalDocument.DOCUMENT_TYPES]
        if document_type not in valid_types:
            return Response(
                {'error': f'Invalid document type. Valid types: {valid_types}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        documents = self.get_queryset().filter(document_type=document_type)

        # Apply additional filters
        patient_id = request.query_params.get('patient_id')
        if patient_id:
            documents = documents.filter(medical_record__patient__patient_id=patient_id)

        date_from = request.query_params.get('date_from')
        if date_from:
            try:
                date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
                documents = documents.filter(upload_date__date__gte=date_from)
            except ValueError:
                pass

        date_to = request.query_params.get('date_to')
        if date_to:
            try:
                date_to = datetime.strptime(date_to, '%Y-%m-%d').date()
                documents = documents.filter(upload_date__date__lte=date_to)
            except ValueError:
                pass

        # Pagination
        page = self.paginate_queryset(documents)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(documents, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """
        Download a medical document
        """
        document = self.get_object()

        # Check permissions
        user = request.user
        if user.user_type == 'patient' and document.medical_record.patient != user.patient_profile:
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Log document access
        UserActivity.objects.create(
            user=request.user,
            action='download',
            resource_type='medical_document',
            resource_id=str(document.id),
            description=f'Downloaded document: {document.title}',
            ip_address=request.META.get('REMOTE_ADDR', ''),
        )

        # Return file URL for download
        if document.file:
            return Response({
                'download_url': request.build_absolute_uri(document.file.url),
                'filename': document.title,
                'file_size': document.file_size,
                'mime_type': document.mime_type
            })
        else:
            return Response(
                {'error': 'File not found'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """
        Get document statistics
        """
        user = request.user

        # Base queryset based on user permissions
        if user.user_type == 'admin':
            queryset = MedicalDocument.objects.all()
        elif user.user_type == 'doctor':
            queryset = MedicalDocument.objects.filter(medical_record__doctor=user.doctor_profile)
        elif user.user_type == 'patient':
            queryset = MedicalDocument.objects.filter(medical_record__patient=user.patient_profile)
        else:
            queryset = MedicalDocument.objects.all()

        # Calculate statistics
        total_documents = queryset.count()
        confidential_documents = queryset.filter(is_confidential=True).count()
        recent_documents = queryset.filter(
            upload_date__gte=timezone.now() - timedelta(days=30)
        ).count()

        # Documents by type
        document_types = {}
        for doc_type, display_name in MedicalDocument.DOCUMENT_TYPES:
            count = queryset.filter(document_type=doc_type).count()
            document_types[doc_type] = {
                'name': display_name,
                'count': count
            }

        # File size statistics
        total_size = queryset.aggregate(
            total_size=Sum('file_size')
        )['total_size'] or 0

        # Recent activity (last 7 days)
        recent_activity = []
        for i in range(7):
            date = timezone.now().date() - timedelta(days=i)
            count = queryset.filter(upload_date__date=date).count()
            recent_activity.append({
                'date': date,
                'count': count
            })

        return Response({
            'total_documents': total_documents,
            'confidential_documents': confidential_documents,
            'public_documents': total_documents - confidential_documents,
            'recent_documents_30_days': recent_documents,
            'total_file_size_mb': round(total_size / (1024 * 1024), 2) if total_size else 0,
            'document_types': document_types,
            'recent_activity': recent_activity
        })


@extend_schema(tags=['Medical Records Management'])
class VitalSignsViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing patient vital signs
    """
    serializer_class = VitalSignsSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        Filter vital signs based on user role and permissions
        """
        user = self.request.user

        if user.user_type == 'admin':
            # Admin can see all vital signs
            return VitalSigns.objects.select_related(
                'medical_record__patient__user', 'medical_record__doctor__user', 'recorded_by'
            ).all()

        elif user.user_type == 'doctor':
            # Doctors can see vital signs from their medical records
            return VitalSigns.objects.select_related(
                'medical_record__patient__user', 'medical_record__doctor__user', 'recorded_by'
            ).filter(medical_record__doctor=user.doctor_profile)

        elif user.user_type == 'patient':
            # Patients can only see their own vital signs
            return VitalSigns.objects.select_related(
                'medical_record__patient__user', 'medical_record__doctor__user', 'recorded_by'
            ).filter(medical_record__patient=user.patient_profile)

        else:
            # Staff can see all vital signs (read-only)
            return VitalSigns.objects.select_related(
                'medical_record__patient__user', 'medical_record__doctor__user', 'recorded_by'
            ).all()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Set the recorded_by field to the current user
        serializer.validated_data['recorded_by'] = request.user
        vital_signs = serializer.save()

        # Log vital signs recording
        UserActivity.objects.create(
            user=request.user,
            action='record',
            resource_type='vital_signs',
            resource_id=str(vital_signs.id),
            description=f'Recorded vital signs for patient',
            ip_address=request.META.get('REMOTE_ADDR', ''),
        )

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'])
    def by_patient(self, request):
        """
        Get all vital signs for a specific patient
        """
        patient_id = request.query_params.get('patient_id')
        if not patient_id:
            return Response(
                {'error': 'patient_id parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            patient = Patient.objects.get(patient_id=patient_id)
        except Patient.DoesNotExist:
            return Response(
                {'error': 'Patient not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Check permissions
        user = request.user
        if user.user_type == 'patient' and user.patient_profile != patient:
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )

        vital_signs = VitalSigns.objects.filter(
            medical_record__patient=patient
        ).select_related('medical_record__doctor__user', 'recorded_by').order_by('-recorded_at')

        # Apply date filtering if provided
        date_from = request.query_params.get('date_from')
        if date_from:
            try:
                date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
                vital_signs = vital_signs.filter(recorded_at__date__gte=date_from)
            except ValueError:
                pass

        date_to = request.query_params.get('date_to')
        if date_to:
            try:
                date_to = datetime.strptime(date_to, '%Y-%m-%d').date()
                vital_signs = vital_signs.filter(recorded_at__date__lte=date_to)
            except ValueError:
                pass

        # Get latest vital signs
        latest_vitals = vital_signs.first()

        # Calculate trends (last 7 days vs previous 7 days)
        recent_vitals = vital_signs.filter(
            recorded_at__gte=timezone.now() - timedelta(days=7)
        )

        return Response({
            'patient': {
                'id': patient.patient_id,
                'name': patient.user.get_full_name(),
            },
            'total_records': vital_signs.count(),
            'latest_vitals': VitalSignsSerializer(latest_vitals).data if latest_vitals else None,
            'recent_vitals': VitalSignsSerializer(recent_vitals, many=True).data,
            'all_vitals': VitalSignsSerializer(vital_signs, many=True).data,
            'statistics': self._calculate_vitals_statistics(vital_signs)
        })

    @action(detail=False, methods=['get'])
    def trends(self, request):
        """
        Get vital signs trends for a patient
        """
        patient_id = request.query_params.get('patient_id')
        if not patient_id:
            return Response(
                {'error': 'patient_id parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            patient = Patient.objects.get(patient_id=patient_id)
        except Patient.DoesNotExist:
            return Response(
                {'error': 'Patient not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Check permissions
        user = request.user
        if user.user_type == 'patient' and user.patient_profile != patient:
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Get vital signs for the last 30 days
        days = int(request.query_params.get('days', 30))
        start_date = timezone.now() - timedelta(days=days)

        vital_signs = VitalSigns.objects.filter(
            medical_record__patient=patient,
            recorded_at__gte=start_date
        ).order_by('recorded_at')

        # Group by date for trend analysis
        trends_data = {}
        for vital in vital_signs:
            date_key = vital.recorded_at.date().isoformat()
            if date_key not in trends_data:
                trends_data[date_key] = []

            trends_data[date_key].append({
                'temperature': vital.temperature,
                'blood_pressure_systolic': vital.blood_pressure_systolic,
                'blood_pressure_diastolic': vital.blood_pressure_diastolic,
                'heart_rate': vital.heart_rate,
                'respiratory_rate': vital.respiratory_rate,
                'oxygen_saturation': vital.oxygen_saturation,
                'weight': vital.weight,
                'bmi': vital.bmi,
                'recorded_at': vital.recorded_at
            })

        return Response({
            'patient': {
                'id': patient.patient_id,
                'name': patient.user.get_full_name(),
            },
            'period_days': days,
            'trends': trends_data,
            'summary': self._calculate_trends_summary(vital_signs)
        })

    @action(detail=False, methods=['get'])
    def alerts(self, request):
        """
        Get vital signs alerts for abnormal values
        """
        patient_id = request.query_params.get('patient_id')
        if not patient_id:
            return Response(
                {'error': 'patient_id parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            patient = Patient.objects.get(patient_id=patient_id)
        except Patient.DoesNotExist:
            return Response(
                {'error': 'Patient not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Check permissions
        user = request.user
        if user.user_type == 'patient' and user.patient_profile != patient:
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Get recent vital signs (last 7 days)
        recent_vitals = VitalSigns.objects.filter(
            medical_record__patient=patient,
            recorded_at__gte=timezone.now() - timedelta(days=7)
        ).order_by('-recorded_at')

        alerts = []
        for vital in recent_vitals:
            vital_alerts = self._check_vital_signs_alerts(vital)
            if vital_alerts:
                alerts.extend(vital_alerts)

        return Response({
            'patient': {
                'id': patient.patient_id,
                'name': patient.user.get_full_name(),
            },
            'total_alerts': len(alerts),
            'alerts': alerts,
            'alert_summary': self._summarize_alerts(alerts)
        })

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """
        Get vital signs statistics
        """
        user = request.user

        # Base queryset based on user permissions
        if user.user_type == 'admin':
            queryset = VitalSigns.objects.all()
        elif user.user_type == 'doctor':
            queryset = VitalSigns.objects.filter(medical_record__doctor=user.doctor_profile)
        elif user.user_type == 'patient':
            queryset = VitalSigns.objects.filter(medical_record__patient=user.patient_profile)
        else:
            queryset = VitalSigns.objects.all()

        # Calculate statistics
        total_records = queryset.count()
        recent_records = queryset.filter(
            recorded_at__gte=timezone.now() - timedelta(days=30)
        ).count()

        # Average values
        averages = queryset.aggregate(
            avg_temperature=Avg('temperature'),
            avg_systolic=Avg('blood_pressure_systolic'),
            avg_diastolic=Avg('blood_pressure_diastolic'),
            avg_heart_rate=Avg('heart_rate'),
            avg_respiratory_rate=Avg('respiratory_rate'),
            avg_oxygen_saturation=Avg('oxygen_saturation'),
            avg_weight=Avg('weight')
        )

        return Response({
            'total_records': total_records,
            'recent_records_30_days': recent_records,
            'averages': {
                'temperature': round(averages['avg_temperature'], 1) if averages['avg_temperature'] else None,
                'blood_pressure': f"{round(averages['avg_systolic'])}/{round(averages['avg_diastolic'])}" if averages['avg_systolic'] and averages['avg_diastolic'] else None,
                'heart_rate': round(averages['avg_heart_rate']) if averages['avg_heart_rate'] else None,
                'respiratory_rate': round(averages['avg_respiratory_rate']) if averages['avg_respiratory_rate'] else None,
                'oxygen_saturation': round(averages['avg_oxygen_saturation'], 1) if averages['avg_oxygen_saturation'] else None,
                'weight': round(averages['avg_weight'], 1) if averages['avg_weight'] else None
            }
        })

    def _calculate_vitals_statistics(self, vital_signs):
        """
        Calculate statistics for vital signs
        """
        if not vital_signs.exists():
            return {}

        # Get latest and oldest for comparison
        latest = vital_signs.first()
        oldest = vital_signs.last()

        # Calculate averages
        averages = vital_signs.aggregate(
            avg_temperature=Avg('temperature'),
            avg_systolic=Avg('blood_pressure_systolic'),
            avg_diastolic=Avg('blood_pressure_diastolic'),
            avg_heart_rate=Avg('heart_rate'),
            avg_respiratory_rate=Avg('respiratory_rate'),
            avg_oxygen_saturation=Avg('oxygen_saturation'),
            avg_weight=Avg('weight')
        )

        return {
            'total_records': vital_signs.count(),
            'date_range': {
                'from': oldest.recorded_at if oldest else None,
                'to': latest.recorded_at if latest else None
            },
            'averages': {
                'temperature': round(averages['avg_temperature'], 1) if averages['avg_temperature'] else None,
                'blood_pressure_systolic': round(averages['avg_systolic']) if averages['avg_systolic'] else None,
                'blood_pressure_diastolic': round(averages['avg_diastolic']) if averages['avg_diastolic'] else None,
                'heart_rate': round(averages['avg_heart_rate']) if averages['avg_heart_rate'] else None,
                'respiratory_rate': round(averages['avg_respiratory_rate']) if averages['avg_respiratory_rate'] else None,
                'oxygen_saturation': round(averages['avg_oxygen_saturation'], 1) if averages['avg_oxygen_saturation'] else None,
                'weight': round(averages['avg_weight'], 1) if averages['avg_weight'] else None
            }
        }

    def _calculate_trends_summary(self, vital_signs):
        """
        Calculate trends summary for vital signs
        """
        if vital_signs.count() < 2:
            return {'message': 'Insufficient data for trend analysis'}

        # Get first and last readings
        first = vital_signs.last()  # oldest
        last = vital_signs.first()  # newest

        trends = {}

        # Calculate trends for each vital sign
        if first.temperature and last.temperature:
            temp_change = last.temperature - first.temperature
            trends['temperature'] = {
                'change': round(temp_change, 1),
                'direction': 'increasing' if temp_change > 0 else 'decreasing' if temp_change < 0 else 'stable'
            }

        if first.blood_pressure_systolic and last.blood_pressure_systolic:
            bp_change = last.blood_pressure_systolic - first.blood_pressure_systolic
            trends['blood_pressure_systolic'] = {
                'change': round(bp_change),
                'direction': 'increasing' if bp_change > 0 else 'decreasing' if bp_change < 0 else 'stable'
            }

        if first.heart_rate and last.heart_rate:
            hr_change = last.heart_rate - first.heart_rate
            trends['heart_rate'] = {
                'change': round(hr_change),
                'direction': 'increasing' if hr_change > 0 else 'decreasing' if hr_change < 0 else 'stable'
            }

        if first.weight and last.weight:
            weight_change = last.weight - first.weight
            trends['weight'] = {
                'change': round(weight_change, 1),
                'direction': 'increasing' if weight_change > 0 else 'decreasing' if weight_change < 0 else 'stable'
            }

        return {
            'period': {
                'from': first.recorded_at,
                'to': last.recorded_at,
                'days': (last.recorded_at.date() - first.recorded_at.date()).days
            },
            'trends': trends
        }

    def _check_vital_signs_alerts(self, vital_signs):
        """
        Check for abnormal vital signs and generate alerts
        """
        alerts = []

        # Temperature alerts
        if vital_signs.temperature:
            if vital_signs.temperature > 38.0:  # Fever
                alerts.append({
                    'type': 'temperature',
                    'severity': 'high' if vital_signs.temperature > 39.0 else 'medium',
                    'message': f'High temperature: {vital_signs.temperature}°C',
                    'value': vital_signs.temperature,
                    'normal_range': '36.1-37.2°C',
                    'recorded_at': vital_signs.recorded_at
                })
            elif vital_signs.temperature < 36.0:  # Hypothermia
                alerts.append({
                    'type': 'temperature',
                    'severity': 'high',
                    'message': f'Low temperature: {vital_signs.temperature}°C',
                    'value': vital_signs.temperature,
                    'normal_range': '36.1-37.2°C',
                    'recorded_at': vital_signs.recorded_at
                })

        # Blood pressure alerts
        if vital_signs.blood_pressure_systolic and vital_signs.blood_pressure_diastolic:
            if vital_signs.blood_pressure_systolic > 140 or vital_signs.blood_pressure_diastolic > 90:
                alerts.append({
                    'type': 'blood_pressure',
                    'severity': 'high' if vital_signs.blood_pressure_systolic > 160 or vital_signs.blood_pressure_diastolic > 100 else 'medium',
                    'message': f'High blood pressure: {vital_signs.blood_pressure_systolic}/{vital_signs.blood_pressure_diastolic} mmHg',
                    'value': f'{vital_signs.blood_pressure_systolic}/{vital_signs.blood_pressure_diastolic}',
                    'normal_range': '<120/80 mmHg',
                    'recorded_at': vital_signs.recorded_at
                })
            elif vital_signs.blood_pressure_systolic < 90 or vital_signs.blood_pressure_diastolic < 60:
                alerts.append({
                    'type': 'blood_pressure',
                    'severity': 'medium',
                    'message': f'Low blood pressure: {vital_signs.blood_pressure_systolic}/{vital_signs.blood_pressure_diastolic} mmHg',
                    'value': f'{vital_signs.blood_pressure_systolic}/{vital_signs.blood_pressure_diastolic}',
                    'normal_range': '<120/80 mmHg',
                    'recorded_at': vital_signs.recorded_at
                })

        # Heart rate alerts
        if vital_signs.heart_rate:
            if vital_signs.heart_rate > 100:  # Tachycardia
                alerts.append({
                    'type': 'heart_rate',
                    'severity': 'high' if vital_signs.heart_rate > 120 else 'medium',
                    'message': f'High heart rate: {vital_signs.heart_rate} bpm',
                    'value': vital_signs.heart_rate,
                    'normal_range': '60-100 bpm',
                    'recorded_at': vital_signs.recorded_at
                })
            elif vital_signs.heart_rate < 60:  # Bradycardia
                alerts.append({
                    'type': 'heart_rate',
                    'severity': 'medium',
                    'message': f'Low heart rate: {vital_signs.heart_rate} bpm',
                    'value': vital_signs.heart_rate,
                    'normal_range': '60-100 bpm',
                    'recorded_at': vital_signs.recorded_at
                })

        # Oxygen saturation alerts
        if vital_signs.oxygen_saturation:
            if vital_signs.oxygen_saturation < 95:
                alerts.append({
                    'type': 'oxygen_saturation',
                    'severity': 'high' if vital_signs.oxygen_saturation < 90 else 'medium',
                    'message': f'Low oxygen saturation: {vital_signs.oxygen_saturation}%',
                    'value': vital_signs.oxygen_saturation,
                    'normal_range': '95-100%',
                    'recorded_at': vital_signs.recorded_at
                })

        return alerts

    def _summarize_alerts(self, alerts):
        """
        Summarize alerts by type and severity
        """
        summary = {
            'total': len(alerts),
            'by_severity': {'high': 0, 'medium': 0, 'low': 0},
            'by_type': {}
        }

        for alert in alerts:
            # Count by severity
            severity = alert.get('severity', 'low')
            summary['by_severity'][severity] += 1

            # Count by type
            alert_type = alert.get('type', 'unknown')
            if alert_type not in summary['by_type']:
                summary['by_type'][alert_type] = 0
            summary['by_type'][alert_type] += 1

        return summary


@extend_schema(tags=['Medical Records Management'])
class MedicalAlertViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing medical alerts
    """
    serializer_class = MedicalAlertSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        Filter medical alerts based on user role and permissions
        """
        user = self.request.user

        if user.user_type == 'admin':
            # Admin can see all alerts
            return MedicalAlert.objects.select_related(
                'patient__user', 'triggered_by', 'acknowledged_by', 'resolved_by'
            ).all()

        elif user.user_type == 'doctor':
            # Doctors can see alerts for their patients
            return MedicalAlert.objects.select_related(
                'patient__user', 'triggered_by', 'acknowledged_by', 'resolved_by'
            ).filter(
                Q(medical_record__doctor=user.doctor_profile) |
                Q(triggered_by=user)
            )

        elif user.user_type == 'patient':
            # Patients can only see their own alerts
            return MedicalAlert.objects.select_related(
                'patient__user', 'triggered_by', 'acknowledged_by', 'resolved_by'
            ).filter(patient=user.patient_profile)

        else:
            # Staff can see all alerts (read-only)
            return MedicalAlert.objects.select_related(
                'patient__user', 'triggered_by', 'acknowledged_by', 'resolved_by'
            ).all()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Set the triggered_by field to the current user
        serializer.validated_data['triggered_by'] = request.user
        alert = serializer.save()

        # Log alert creation
        UserActivity.objects.create(
            user=request.user,
            action='create',
            resource_type='medical_alert',
            resource_id=str(alert.id),
            description=f'Created medical alert: {alert.title}',
            ip_address=request.META.get('REMOTE_ADDR', ''),
        )

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def acknowledge(self, request, pk=None):
        """
        Acknowledge a medical alert
        """
        alert = self.get_object()

        if alert.status == 'acknowledged':
            return Response(
                {'error': 'Alert is already acknowledged'},
                status=status.HTTP_400_BAD_REQUEST
            )

        alert.status = 'acknowledged'
        alert.acknowledged_by = request.user
        alert.acknowledged_at = timezone.now()
        alert.save()

        # Log acknowledgment
        UserActivity.objects.create(
            user=request.user,
            action='acknowledge',
            resource_type='medical_alert',
            resource_id=str(alert.id),
            description=f'Acknowledged medical alert: {alert.title}',
            ip_address=request.META.get('REMOTE_ADDR', ''),
        )

        serializer = MedicalAlertSerializer(alert)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        """
        Resolve a medical alert
        """
        alert = self.get_object()

        if alert.status == 'resolved':
            return Response(
                {'error': 'Alert is already resolved'},
                status=status.HTTP_400_BAD_REQUEST
            )

        resolution_notes = request.data.get('resolution_notes', '')

        alert.status = 'resolved'
        alert.resolved_by = request.user
        alert.resolved_at = timezone.now()
        alert.resolution_notes = resolution_notes
        alert.save()

        # Log resolution
        UserActivity.objects.create(
            user=request.user,
            action='resolve',
            resource_type='medical_alert',
            resource_id=str(alert.id),
            description=f'Resolved medical alert: {alert.title}',
            ip_address=request.META.get('REMOTE_ADDR', ''),
        )

        serializer = MedicalAlertSerializer(alert)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def by_patient(self, request):
        """
        Get all alerts for a specific patient
        """
        patient_id = request.query_params.get('patient_id')
        if not patient_id:
            return Response(
                {'error': 'patient_id parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            patient = Patient.objects.get(patient_id=patient_id)
        except Patient.DoesNotExist:
            return Response(
                {'error': 'Patient not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Check permissions
        user = request.user
        if user.user_type == 'patient' and user.patient_profile != patient:
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )

        alerts = MedicalAlert.objects.filter(patient=patient).order_by('-triggered_at')

        # Apply status filtering if provided
        status_filter = request.query_params.get('status')
        if status_filter:
            alerts = alerts.filter(status=status_filter)

        # Apply severity filtering if provided
        severity_filter = request.query_params.get('severity')
        if severity_filter:
            alerts = alerts.filter(severity=severity_filter)

        # Apply alert type filtering if provided
        alert_type_filter = request.query_params.get('alert_type')
        if alert_type_filter:
            alerts = alerts.filter(alert_type=alert_type_filter)

        return Response({
            'patient': {
                'id': patient.patient_id,
                'name': patient.user.get_full_name(),
            },
            'total_alerts': alerts.count(),
            'alerts': MedicalAlertSerializer(alerts, many=True).data,
            'statistics': self._calculate_alert_statistics(alerts)
        })

    def _calculate_alert_statistics(self, alerts):
        """
        Calculate statistics for alerts
        """
        total = alerts.count()
        if total == 0:
            return {}

        # Count by status
        status_counts = {}
        for status_choice in MedicalAlert.STATUS_CHOICES:
            status = status_choice[0]
            count = alerts.filter(status=status).count()
            status_counts[status] = count

        # Count by severity
        severity_counts = {}
        for severity_choice in MedicalAlert.SEVERITY_LEVELS:
            severity = severity_choice[0]
            count = alerts.filter(severity=severity).count()
            severity_counts[severity] = count

        # Count by type
        type_counts = {}
        for type_choice in MedicalAlert.ALERT_TYPES:
            alert_type = type_choice[0]
            count = alerts.filter(alert_type=alert_type).count()
            type_counts[alert_type] = count

        return {
            'total': total,
            'by_status': status_counts,
            'by_severity': severity_counts,
            'by_type': type_counts,
            'active_alerts': alerts.filter(status='active').count(),
            'critical_alerts': alerts.filter(severity='critical').count()
        }
