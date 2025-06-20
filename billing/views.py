from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from django.db.models import Q, Sum, Count, Avg
from datetime import datetime, timedelta
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
from decimal import Decimal

from .models import (
    ServiceCategory, Service, Invoice, InvoiceItem, Payment,
    InsuranceClaim, FinancialTransaction, PaymentGateway, PaymentMethod, PaymentAttempt,
    ClaimDocument, ClaimAuditLog, InsurancePreAuthorization, FinancialReport, RevenueMetrics,
    BillingNotification, NotificationTemplate, NotificationSchedule,
    PricingTier, ServicePricing, DynamicPricingRule, ServiceBundle, BundleService
)
from .serializers import (
    ServiceCategorySerializer, ServiceSerializer, InvoiceListSerializer,
    InvoiceDetailSerializer, InvoiceCreateSerializer, InvoiceItemSerializer,
    PaymentSerializer, FinancialTransactionSerializer, InsuranceClaimSerializer,
    FinancialReportSerializer, RevenueMetricsSerializer, BillingNotificationSerializer,
    NotificationTemplateSerializer, NotificationScheduleSerializer
)
from accounts.models import UserActivity
from patients.models import Patient


@extend_schema(tags=['Billing & Financial Management'])
class ServiceCategoryViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing service categories
    """
    queryset = ServiceCategory.objects.all()
    serializer_class = ServiceCategorySerializer
    permission_classes = [permissions.IsAuthenticated]


@extend_schema(tags=['Billing & Financial Management'])
class ServiceViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing medical services
    """
    queryset = Service.objects.select_related('category').all()
    serializer_class = ServiceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()

        # Filter by category if provided
        category_id = self.request.query_params.get('category')
        if category_id:
            queryset = queryset.filter(category_id=category_id)

        # Filter by active status
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')

        return queryset

    @action(detail=False, methods=['get'])
    def search(self, request):
        """
        Search services by name or code
        """
        query = request.query_params.get('q', '')
        if not query:
            return Response({'error': 'Query parameter "q" is required'}, status=status.HTTP_400_BAD_REQUEST)

        services = Service.objects.filter(
            Q(name__icontains=query) | Q(code__icontains=query),
            is_active=True
        ).select_related('category')

        serializer = ServiceSerializer(services, many=True)
        return Response(serializer.data)


@extend_schema(tags=['Billing & Financial Management'])
class InvoiceViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing invoices
    """
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        Filter invoices based on user role and permissions
        """
        user = self.request.user

        if user.user_type == 'admin':
            # Admin can see all invoices
            return Invoice.objects.select_related(
                'patient__user', 'appointment__doctor__user', 'created_by'
            ).prefetch_related('items__service', 'payments').all()

        elif user.user_type == 'doctor':
            # Doctors can see invoices for their appointments
            return Invoice.objects.select_related(
                'patient__user', 'appointment__doctor__user', 'created_by'
            ).prefetch_related('items__service', 'payments').filter(
                Q(appointment__doctor=user.doctor_profile) |
                Q(created_by=user)
            )

        elif user.user_type == 'patient':
            # Patients can only see their own invoices
            return Invoice.objects.select_related(
                'patient__user', 'appointment__doctor__user', 'created_by'
            ).prefetch_related('items__service', 'payments').filter(
                patient=user.patient_profile
            )

        else:
            # Staff can see all invoices (read-only)
            return Invoice.objects.select_related(
                'patient__user', 'appointment__doctor__user', 'created_by'
            ).prefetch_related('items__service', 'payments').all()

    def get_serializer_class(self):
        if self.action == 'list':
            return InvoiceListSerializer
        elif self.action == 'create':
            return InvoiceCreateSerializer
        else:
            return InvoiceDetailSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        invoice = serializer.save()

        # Create financial transaction
        FinancialTransaction.objects.create(
            transaction_type='invoice_created',
            amount=invoice.total_amount,
            patient=invoice.patient,
            invoice=invoice,
            description=f'Invoice {invoice.invoice_number} created',
            processed_by=request.user
        )

        # Log invoice creation
        UserActivity.objects.create(
            user=request.user,
            action='create',
            resource_type='invoice',
            resource_id=str(invoice.id),
            description=f'Created invoice {invoice.invoice_number}',
            ip_address=request.META.get('REMOTE_ADDR', ''),
        )

        return Response(
            InvoiceDetailSerializer(invoice, context={'request': request}).data,
            status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=['post'])
    def send(self, request, pk=None):
        """
        Send invoice to patient
        """
        invoice = self.get_object()

        if invoice.status == 'sent':
            return Response(
                {'error': 'Invoice has already been sent'},
                status=status.HTTP_400_BAD_REQUEST
            )

        invoice.status = 'sent'
        invoice.sent_date = timezone.now()
        invoice.save()

        # Log invoice sending
        UserActivity.objects.create(
            user=request.user,
            action='send',
            resource_type='invoice',
            resource_id=str(invoice.id),
            description=f'Sent invoice {invoice.invoice_number} to patient',
            ip_address=request.META.get('REMOTE_ADDR', ''),
        )

        serializer = InvoiceDetailSerializer(invoice, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """
        Cancel an invoice
        """
        invoice = self.get_object()

        if invoice.status in ['paid', 'cancelled']:
            return Response(
                {'error': f'Cannot cancel invoice with status: {invoice.status}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        invoice.status = 'cancelled'
        invoice.save()

        # Create financial transaction for cancellation
        FinancialTransaction.objects.create(
            transaction_type='adjustment',
            amount=-invoice.total_amount,
            patient=invoice.patient,
            invoice=invoice,
            description=f'Invoice {invoice.invoice_number} cancelled',
            processed_by=request.user
        )

        # Log invoice cancellation
        UserActivity.objects.create(
            user=request.user,
            action='cancel',
            resource_type='invoice',
            resource_id=str(invoice.id),
            description=f'Cancelled invoice {invoice.invoice_number}',
            ip_address=request.META.get('REMOTE_ADDR', ''),
        )

        serializer = InvoiceDetailSerializer(invoice, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def by_patient(self, request):
        """
        Get all invoices for a specific patient
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

        invoices = Invoice.objects.filter(patient=patient).order_by('-invoice_date')

        # Apply status filtering if provided
        status_filter = request.query_params.get('status')
        if status_filter:
            invoices = invoices.filter(status=status_filter)

        # Apply date filtering if provided
        date_from = request.query_params.get('date_from')
        if date_from:
            try:
                date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
                invoices = invoices.filter(invoice_date__gte=date_from)
            except ValueError:
                pass

        date_to = request.query_params.get('date_to')
        if date_to:
            try:
                date_to = datetime.strptime(date_to, '%Y-%m-%d').date()
                invoices = invoices.filter(invoice_date__lte=date_to)
            except ValueError:
                pass

        return Response({
            'patient': {
                'id': patient.patient_id,
                'name': patient.user.get_full_name(),
            },
            'total_invoices': invoices.count(),
            'invoices': InvoiceListSerializer(invoices, many=True).data,
            'summary': self._calculate_patient_invoice_summary(invoices)
        })

    @action(detail=False, methods=['get'])
    def overdue(self, request):
        """
        Get all overdue invoices
        """
        user = request.user

        # Get base queryset based on permissions
        if user.user_type == 'admin':
            queryset = Invoice.objects.all()
        elif user.user_type == 'doctor':
            queryset = Invoice.objects.filter(
                Q(appointment__doctor=user.doctor_profile) |
                Q(created_by=user)
            )
        elif user.user_type == 'patient':
            queryset = Invoice.objects.filter(patient=user.patient_profile)
        else:
            queryset = Invoice.objects.all()

        # Filter for overdue invoices
        overdue_invoices = queryset.filter(
            due_date__lt=timezone.now().date(),
            status__in=['sent', 'partially_paid']
        ).order_by('due_date')

        return Response({
            'total_overdue': overdue_invoices.count(),
            'invoices': InvoiceListSerializer(overdue_invoices, many=True).data,
            'total_overdue_amount': sum(invoice.balance_due for invoice in overdue_invoices)
        })

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """
        Get invoice statistics
        """
        user = request.user

        # Get base queryset based on permissions
        if user.user_type == 'admin':
            queryset = Invoice.objects.all()
        elif user.user_type == 'doctor':
            queryset = Invoice.objects.filter(
                Q(appointment__doctor=user.doctor_profile) |
                Q(created_by=user)
            )
        elif user.user_type == 'patient':
            queryset = Invoice.objects.filter(patient=user.patient_profile)
        else:
            queryset = Invoice.objects.all()

        # Calculate statistics
        total_invoices = queryset.count()
        total_amount = sum(invoice.total_amount for invoice in queryset)
        total_paid = sum(invoice.paid_amount for invoice in queryset)
        total_outstanding = total_amount - total_paid

        # Status breakdown
        status_counts = {}
        for status_choice in Invoice.STATUS_CHOICES:
            status = status_choice[0]
            count = queryset.filter(status=status).count()
            status_counts[status] = count

        # Recent invoices (last 30 days)
        recent_invoices = queryset.filter(
            invoice_date__gte=timezone.now().date() - timedelta(days=30)
        ).count()

        return Response({
            'total_invoices': total_invoices,
            'total_amount': total_amount,
            'total_paid': total_paid,
            'total_outstanding': total_outstanding,
            'recent_invoices_30_days': recent_invoices,
            'status_breakdown': status_counts,
            'average_invoice_amount': total_amount / total_invoices if total_invoices > 0 else 0
        })

    def _calculate_patient_invoice_summary(self, invoices):
        """
        Calculate summary statistics for patient invoices
        """
        if not invoices.exists():
            return {}

        total_amount = sum(invoice.total_amount for invoice in invoices)
        total_paid = sum(invoice.paid_amount for invoice in invoices)
        total_outstanding = total_amount - total_paid

        # Count by status
        status_counts = {}
        for status_choice in Invoice.STATUS_CHOICES:
            status = status_choice[0]
            count = invoices.filter(status=status).count()
            status_counts[status] = count

        # Overdue invoices
        overdue_count = invoices.filter(
            due_date__lt=timezone.now().date(),
            status__in=['sent', 'partially_paid']
        ).count()

        return {
            'total_amount': total_amount,
            'total_paid': total_paid,
            'total_outstanding': total_outstanding,
            'status_counts': status_counts,
            'overdue_count': overdue_count,
            'average_amount': total_amount / invoices.count() if invoices.count() > 0 else 0
        }


@extend_schema(tags=['Billing & Financial Management'])
class PaymentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing payments
    """
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        Filter payments based on user role and permissions
        """
        user = self.request.user

        if user.user_type == 'admin':
            # Admin can see all payments
            return Payment.objects.select_related(
                'invoice__patient__user', 'processed_by'
            ).all()

        elif user.user_type == 'doctor':
            # Doctors can see payments for their patients' invoices
            return Payment.objects.select_related(
                'invoice__patient__user', 'processed_by'
            ).filter(
                Q(invoice__appointment__doctor=user.doctor_profile) |
                Q(processed_by=user)
            )

        elif user.user_type == 'patient':
            # Patients can only see their own payments
            return Payment.objects.select_related(
                'invoice__patient__user', 'processed_by'
            ).filter(invoice__patient=user.patient_profile)

        else:
            # Staff can see all payments (read-only)
            return Payment.objects.select_related(
                'invoice__patient__user', 'processed_by'
            ).all()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Set the processed_by field to the current user
        serializer.validated_data['processed_by'] = request.user
        payment = serializer.save()

        # Update invoice payment status
        invoice = payment.invoice
        invoice.paid_amount += payment.amount
        if invoice.paid_amount >= invoice.total_amount:
            invoice.status = 'paid'
        elif invoice.paid_amount > 0:
            invoice.status = 'partially_paid'
        invoice.save()

        # Create financial transaction
        FinancialTransaction.objects.create(
            transaction_type='payment_received',
            amount=payment.amount,
            patient=invoice.patient,
            invoice=invoice,
            payment=payment,
            description=f'Payment {payment.payment_number} received for invoice {invoice.invoice_number}',
            processed_by=request.user
        )

        # Log payment creation
        UserActivity.objects.create(
            user=request.user,
            action='create',
            resource_type='payment',
            resource_id=str(payment.id),
            description=f'Processed payment {payment.payment_number} for ${payment.amount}',
            ip_address=request.META.get('REMOTE_ADDR', ''),
        )

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def refund(self, request, pk=None):
        """
        Process a refund for a payment
        """
        payment = self.get_object()

        if payment.status != 'completed':
            return Response(
                {'error': 'Can only refund completed payments'},
                status=status.HTTP_400_BAD_REQUEST
            )

        refund_amount = request.data.get('amount', payment.amount)
        refund_reason = request.data.get('reason', '')

        try:
            refund_amount = Decimal(str(refund_amount))
            if refund_amount <= 0 or refund_amount > payment.amount:
                return Response(
                    {'error': 'Invalid refund amount'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except (ValueError, TypeError):
            return Response(
                {'error': 'Invalid refund amount format'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Create refund payment record
        refund_payment = Payment.objects.create(
            invoice=payment.invoice,
            amount=-refund_amount,  # Negative amount for refund
            payment_method=payment.payment_method,
            status='completed',
            transaction_id=f'REFUND-{payment.transaction_id}',
            reference_number=f'REFUND-{payment.payment_number}',
            notes=f'Refund for payment {payment.payment_number}. Reason: {refund_reason}',
            processed_by=request.user
        )

        # Update original payment status if full refund
        if refund_amount == payment.amount:
            payment.status = 'refunded'
            payment.save()

        # Update invoice payment status
        invoice = payment.invoice
        invoice.paid_amount -= refund_amount
        if invoice.paid_amount <= 0:
            invoice.status = 'sent'  # Back to sent status
        elif invoice.paid_amount < invoice.total_amount:
            invoice.status = 'partially_paid'
        invoice.save()

        # Create financial transaction
        FinancialTransaction.objects.create(
            transaction_type='refund_issued',
            amount=refund_amount,
            patient=invoice.patient,
            invoice=invoice,
            payment=refund_payment,
            description=f'Refund {refund_payment.payment_number} issued for payment {payment.payment_number}',
            processed_by=request.user
        )

        # Log refund
        UserActivity.objects.create(
            user=request.user,
            action='refund',
            resource_type='payment',
            resource_id=str(payment.id),
            description=f'Processed refund of ${refund_amount} for payment {payment.payment_number}',
            ip_address=request.META.get('REMOTE_ADDR', ''),
        )

        return Response({
            'message': 'Refund processed successfully',
            'refund_payment': PaymentSerializer(refund_payment).data,
            'original_payment': PaymentSerializer(payment).data
        })

    @action(detail=False, methods=['get'])
    def by_invoice(self, request):
        """
        Get all payments for a specific invoice
        """
        invoice_id = request.query_params.get('invoice_id')
        if not invoice_id:
            return Response(
                {'error': 'invoice_id parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            invoice = Invoice.objects.get(id=invoice_id)
        except Invoice.DoesNotExist:
            return Response(
                {'error': 'Invoice not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Check permissions
        user = request.user
        if user.user_type == 'patient' and invoice.patient != user.patient_profile:
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )

        payments = Payment.objects.filter(invoice=invoice).order_by('-payment_date')

        return Response({
            'invoice': {
                'id': invoice.id,
                'invoice_number': invoice.invoice_number,
                'total_amount': invoice.total_amount,
                'paid_amount': invoice.paid_amount,
                'balance_due': invoice.balance_due
            },
            'total_payments': payments.count(),
            'payments': PaymentSerializer(payments, many=True).data,
            'payment_summary': self._calculate_payment_summary(payments)
        })

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """
        Get payment statistics
        """
        user = request.user

        # Get base queryset based on permissions
        if user.user_type == 'admin':
            queryset = Payment.objects.all()
        elif user.user_type == 'doctor':
            queryset = Payment.objects.filter(
                Q(invoice__appointment__doctor=user.doctor_profile) |
                Q(processed_by=user)
            )
        elif user.user_type == 'patient':
            queryset = Payment.objects.filter(invoice__patient=user.patient_profile)
        else:
            queryset = Payment.objects.all()

        # Calculate statistics
        total_payments = queryset.count()
        total_amount = sum(payment.amount for payment in queryset if payment.amount > 0)
        total_refunds = sum(abs(payment.amount) for payment in queryset if payment.amount < 0)

        # Status breakdown
        status_counts = {}
        for status_choice in Payment.STATUS_CHOICES:
            status = status_choice[0]
            count = queryset.filter(status=status).count()
            status_counts[status] = count

        # Payment method breakdown
        method_counts = {}
        for method_choice in Payment.PAYMENT_METHODS:
            method = method_choice[0]
            count = queryset.filter(payment_method=method).count()
            method_counts[method] = count

        # Recent payments (last 30 days)
        recent_payments = queryset.filter(
            payment_date__gte=timezone.now() - timedelta(days=30)
        ).count()

        return Response({
            'total_payments': total_payments,
            'total_amount': total_amount,
            'total_refunds': total_refunds,
            'net_amount': total_amount - total_refunds,
            'recent_payments_30_days': recent_payments,
            'status_breakdown': status_counts,
            'payment_method_breakdown': method_counts,
            'average_payment_amount': total_amount / total_payments if total_payments > 0 else 0
        })

    def _calculate_payment_summary(self, payments):
        """
        Calculate summary statistics for payments
        """
        if not payments.exists():
            return {}

        total_amount = sum(payment.amount for payment in payments if payment.amount > 0)
        total_refunds = sum(abs(payment.amount) for payment in payments if payment.amount < 0)

        # Count by status
        status_counts = {}
        for status_choice in Payment.STATUS_CHOICES:
            status = status_choice[0]
            count = payments.filter(status=status).count()
            status_counts[status] = count

        # Count by payment method
        method_counts = {}
        for method_choice in Payment.PAYMENT_METHODS:
            method = method_choice[0]
            count = payments.filter(payment_method=method).count()
            method_counts[method] = count

        return {
            'total_amount': total_amount,
            'total_refunds': total_refunds,
            'net_amount': total_amount - total_refunds,
            'status_counts': status_counts,
            'method_counts': method_counts,
            'average_amount': total_amount / payments.count() if payments.count() > 0 else 0
        }


@extend_schema(tags=['Billing & Financial Management'])
class InsuranceClaimViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing insurance claims
    """
    serializer_class = InsuranceClaimSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        Filter insurance claims based on user role and permissions
        """
        user = self.request.user

        if user.user_type == 'admin':
            # Admin can see all claims
            return InsuranceClaim.objects.select_related(
                'patient__user', 'insurance_info', 'invoice', 'created_by'
            ).all()

        elif user.user_type == 'doctor':
            # Doctors can see claims for their patients' invoices
            return InsuranceClaim.objects.select_related(
                'patient__user', 'insurance_info', 'invoice', 'created_by'
            ).filter(
                Q(invoice__appointment__doctor=user.doctor_profile) |
                Q(created_by=user)
            )

        elif user.user_type == 'patient':
            # Patients can only see their own claims
            return InsuranceClaim.objects.select_related(
                'patient__user', 'insurance_info', 'invoice', 'created_by'
            ).filter(patient=user.patient_profile)

        else:
            # Staff can see all claims (read-only)
            return InsuranceClaim.objects.select_related(
                'patient__user', 'insurance_info', 'invoice', 'created_by'
            ).all()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Set the created_by field to the current user
        serializer.validated_data['created_by'] = request.user
        claim = serializer.save()

        # Create audit log entry
        ClaimAuditLog.objects.create(
            claim=claim,
            action='created',
            description=f'Insurance claim {claim.claim_number} created',
            new_values={
                'status': claim.status,
                'billed_amount': str(claim.billed_amount),
                'patient': claim.patient.patient_id
            },
            performed_by=request.user,
            ip_address=request.META.get('REMOTE_ADDR', ''),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )

        # Log claim creation
        UserActivity.objects.create(
            user=request.user,
            action='create',
            resource_type='insurance_claim',
            resource_id=str(claim.id),
            description=f'Created insurance claim {claim.claim_number}',
            ip_address=request.META.get('REMOTE_ADDR', ''),
        )

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        """
        Submit an insurance claim
        """
        claim = self.get_object()

        if claim.status != 'draft':
            return Response(
                {'error': 'Only draft claims can be submitted'},
                status=status.HTTP_400_BAD_REQUEST
            )

        claim.status = 'submitted'
        claim.submitted_date = timezone.now()
        claim.save()

        # Create audit log entry
        ClaimAuditLog.objects.create(
            claim=claim,
            action='submitted',
            description=f'Insurance claim {claim.claim_number} submitted to insurance company',
            previous_values={'status': 'draft'},
            new_values={'status': 'submitted', 'submitted_date': claim.submitted_date.isoformat()},
            performed_by=request.user,
            ip_address=request.META.get('REMOTE_ADDR', ''),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )

        # Log claim submission
        UserActivity.objects.create(
            user=request.user,
            action='submit',
            resource_type='insurance_claim',
            resource_id=str(claim.id),
            description=f'Submitted insurance claim {claim.claim_number}',
            ip_address=request.META.get('REMOTE_ADDR', ''),
        )

        serializer = InsuranceClaimSerializer(claim)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """
        Approve an insurance claim
        """
        claim = self.get_object()

        if claim.status not in ['submitted', 'under_review']:
            return Response(
                {'error': 'Only submitted or under review claims can be approved'},
                status=status.HTTP_400_BAD_REQUEST
            )

        approved_amount = request.data.get('approved_amount')
        patient_responsibility = request.data.get('patient_responsibility', 0)
        notes = request.data.get('notes', '')

        try:
            approved_amount = Decimal(str(approved_amount))
            patient_responsibility = Decimal(str(patient_responsibility))
        except (ValueError, TypeError):
            return Response(
                {'error': 'Invalid amount format'},
                status=status.HTTP_400_BAD_REQUEST
            )

        previous_status = claim.status
        claim.status = 'approved'
        claim.approved_amount = approved_amount
        claim.patient_responsibility = patient_responsibility
        claim.processed_date = timezone.now()
        if notes:
            claim.notes = notes
        claim.save()

        # Create audit log entry
        ClaimAuditLog.objects.create(
            claim=claim,
            action='approved',
            description=f'Insurance claim {claim.claim_number} approved for ${approved_amount}',
            previous_values={
                'status': previous_status,
                'approved_amount': None,
                'patient_responsibility': str(claim.patient_responsibility)
            },
            new_values={
                'status': 'approved',
                'approved_amount': str(approved_amount),
                'patient_responsibility': str(patient_responsibility),
                'processed_date': claim.processed_date.isoformat()
            },
            performed_by=request.user,
            ip_address=request.META.get('REMOTE_ADDR', ''),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )

        # Log claim approval
        UserActivity.objects.create(
            user=request.user,
            action='approve',
            resource_type='insurance_claim',
            resource_id=str(claim.id),
            description=f'Approved insurance claim {claim.claim_number} for ${approved_amount}',
            ip_address=request.META.get('REMOTE_ADDR', ''),
        )

        serializer = InsuranceClaimSerializer(claim)
        return Response(serializer.data)


@extend_schema(tags=['Billing & Financial Management'])
class FinancialReportViewSet(viewsets.ModelViewSet):
    """
    ViewSet for generating and managing financial reports
    """
    serializer_class = FinancialReportSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        Filter financial reports based on user role and permissions
        """
        user = self.request.user

        if user.user_type in ['admin', 'staff']:
            # Admin and staff can see all reports
            return FinancialReport.objects.all()

        elif user.user_type == 'doctor':
            # Doctors can see reports they generated
            return FinancialReport.objects.filter(generated_by=user)

        else:
            # Patients cannot access financial reports
            return FinancialReport.objects.none()

    @action(detail=False, methods=['post'])
    def generate_revenue_summary(self, request):
        """
        Generate a comprehensive revenue summary report
        """
        date_from = request.data.get('date_from')
        date_to = request.data.get('date_to')

        if not date_from or not date_to:
            return Response(
                {'error': 'date_from and date_to are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
            date_to = datetime.strptime(date_to, '%Y-%m-%d').date()
        except ValueError:
            return Response(
                {'error': 'Invalid date format. Use YYYY-MM-DD'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Generate revenue summary data
        report_data = self._generate_revenue_summary_data(date_from, date_to)

        # Create report record
        report = FinancialReport.objects.create(
            report_type='revenue_summary',
            title=f'Revenue Summary Report - {date_from} to {date_to}',
            description=f'Comprehensive revenue analysis for the period {date_from} to {date_to}',
            date_from=date_from,
            date_to=date_to,
            report_data=report_data,
            status='completed',
            generated_by=request.user
        )

        # Log report generation
        UserActivity.objects.create(
            user=request.user,
            action='generate',
            resource_type='financial_report',
            resource_id=str(report.id),
            description=f'Generated revenue summary report {report.report_number}',
            ip_address=request.META.get('REMOTE_ADDR', ''),
        )

        serializer = FinancialReportSerializer(report)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def generate_payment_analysis(self, request):
        """
        Generate payment analysis report
        """
        date_from = request.data.get('date_from')
        date_to = request.data.get('date_to')

        if not date_from or not date_to:
            return Response(
                {'error': 'date_from and date_to are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
            date_to = datetime.strptime(date_to, '%Y-%m-%d').date()
        except ValueError:
            return Response(
                {'error': 'Invalid date format. Use YYYY-MM-DD'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Generate payment analysis data
        report_data = self._generate_payment_analysis_data(date_from, date_to)

        # Create report record
        report = FinancialReport.objects.create(
            report_type='payment_analysis',
            title=f'Payment Analysis Report - {date_from} to {date_to}',
            description=f'Detailed payment analysis for the period {date_from} to {date_to}',
            date_from=date_from,
            date_to=date_to,
            report_data=report_data,
            status='completed',
            generated_by=request.user
        )

        serializer = FinancialReportSerializer(report)
        return Response(serializer.data)

    def _generate_revenue_summary_data(self, date_from, date_to):
        """
        Generate comprehensive revenue summary data
        """
        # Get invoices in date range
        invoices = Invoice.objects.filter(
            invoice_date__range=[date_from, date_to]
        ).select_related('patient__user').prefetch_related('items__service', 'payments')

        # Get payments in date range
        payments = Payment.objects.filter(
            payment_date__range=[date_from, date_to]
        ).select_related('invoice__patient__user')

        # Calculate basic metrics
        total_invoices = invoices.count()
        total_billed = sum(invoice.total_amount for invoice in invoices)
        total_paid = sum(payment.amount for payment in payments if payment.amount > 0)
        total_refunds = sum(abs(payment.amount) for payment in payments if payment.amount < 0)
        total_outstanding = sum(invoice.balance_due for invoice in invoices)

        # Invoice status breakdown
        status_breakdown = {}
        for status_choice in Invoice.STATUS_CHOICES:
            status = status_choice[0]
            count = invoices.filter(status=status).count()
            amount = sum(inv.total_amount for inv in invoices.filter(status=status))
            status_breakdown[status] = {'count': count, 'amount': float(amount)}

        # Payment method breakdown
        payment_method_breakdown = {}
        for method_choice in Payment.PAYMENT_METHODS:
            method = method_choice[0]
            method_payments = payments.filter(payment_method=method, amount__gt=0)
            count = method_payments.count()
            amount = sum(p.amount for p in method_payments)
            payment_method_breakdown[method] = {'count': count, 'amount': float(amount)}

        # Service performance
        service_performance = {}
        for invoice in invoices:
            for item in invoice.items.all():
                service_name = item.service.name
                if service_name not in service_performance:
                    service_performance[service_name] = {'count': 0, 'revenue': 0}
                service_performance[service_name]['count'] += item.quantity
                service_performance[service_name]['revenue'] += float(item.total_amount)

        # Top services by revenue
        top_services = sorted(
            service_performance.items(),
            key=lambda x: x[1]['revenue'],
            reverse=True
        )[:10]

        return {
            'period': {
                'date_from': date_from.isoformat(),
                'date_to': date_to.isoformat(),
                'days': (date_to - date_from).days + 1
            },
            'summary': {
                'total_invoices': total_invoices,
                'total_billed': float(total_billed),
                'total_paid': float(total_paid),
                'total_refunds': float(total_refunds),
                'total_outstanding': float(total_outstanding),
                'collection_rate': float(total_paid / total_billed * 100) if total_billed > 0 else 0,
                'average_invoice_amount': float(total_billed / total_invoices) if total_invoices > 0 else 0
            },
            'invoice_status_breakdown': status_breakdown,
            'payment_method_breakdown': payment_method_breakdown,
            'service_performance': dict(service_performance),
            'top_services': top_services,
            'generated_at': timezone.now().isoformat()
        }

    def _generate_payment_analysis_data(self, date_from, date_to):
        """
        Generate detailed payment analysis data
        """
        # Get payments in date range
        payments = Payment.objects.filter(
            payment_date__range=[date_from, date_to]
        ).select_related('invoice__patient__user', 'processed_by')

        # Basic payment metrics
        total_payments = payments.filter(amount__gt=0).count()
        total_refunds = payments.filter(amount__lt=0).count()
        total_amount = sum(p.amount for p in payments if p.amount > 0)
        total_refund_amount = sum(abs(p.amount) for p in payments if p.amount < 0)

        # Payment status breakdown
        status_breakdown = {}
        for status_choice in Payment.STATUS_CHOICES:
            status = status_choice[0]
            status_payments = payments.filter(status=status)
            count = status_payments.count()
            amount = sum(p.amount for p in status_payments if p.amount > 0)
            status_breakdown[status] = {'count': count, 'amount': float(amount)}

        # Daily payment trends
        daily_trends = {}
        current_date = date_from
        while current_date <= date_to:
            day_payments = payments.filter(payment_date__date=current_date, amount__gt=0)
            daily_trends[current_date.isoformat()] = {
                'count': day_payments.count(),
                'amount': float(sum(p.amount for p in day_payments))
            }
            current_date += timedelta(days=1)

        return {
            'period': {
                'date_from': date_from.isoformat(),
                'date_to': date_to.isoformat()
            },
            'summary': {
                'total_payments': total_payments,
                'total_refunds': total_refunds,
                'total_amount': float(total_amount),
                'total_refund_amount': float(total_refund_amount),
                'net_amount': float(total_amount - total_refund_amount),
                'average_payment': float(total_amount / total_payments) if total_payments > 0 else 0
            },
            'status_breakdown': status_breakdown,
            'daily_trends': daily_trends,
            'generated_at': timezone.now().isoformat()
        }


@extend_schema(tags=['Billing & Financial Management'])
class BillingNotificationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing billing notifications
    """
    serializer_class = BillingNotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        Filter billing notifications based on user role and permissions
        """
        user = self.request.user

        if user.user_type == 'admin':
            # Admin can see all notifications
            return BillingNotification.objects.select_related(
                'patient__user', 'invoice', 'payment', 'insurance_claim', 'created_by'
            ).all()

        elif user.user_type == 'doctor':
            # Doctors can see notifications for their patients
            return BillingNotification.objects.select_related(
                'patient__user', 'invoice', 'payment', 'insurance_claim', 'created_by'
            ).filter(
                Q(invoice__appointment__doctor=user.doctor_profile) |
                Q(created_by=user)
            )

        elif user.user_type == 'patient':
            # Patients can only see their own notifications
            return BillingNotification.objects.select_related(
                'patient__user', 'invoice', 'payment', 'insurance_claim', 'created_by'
            ).filter(patient=user.patient_profile)

        else:
            # Staff can see all notifications (read-only)
            return BillingNotification.objects.select_related(
                'patient__user', 'invoice', 'payment', 'insurance_claim', 'created_by'
            ).all()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Set the created_by field to the current user
        serializer.validated_data['created_by'] = request.user
        notification = serializer.save()

        # Log notification creation
        UserActivity.objects.create(
            user=request.user,
            action='create',
            resource_type='billing_notification',
            resource_id=str(notification.id),
            description=f'Created billing notification {notification.notification_number}',
            ip_address=request.META.get('REMOTE_ADDR', ''),
        )

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'])
    def pricing_analytics(self, request):
        """
        Get pricing and service analytics
        """
        user = self.request.user

        if user.user_type not in ['admin', 'staff']:
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Service pricing analytics
        services = Service.objects.filter(is_active=True)
        service_categories = ServiceCategory.objects.filter(is_active=True)

        # Calculate pricing statistics
        total_services = services.count()
        total_categories = service_categories.count()

        # Price range analysis
        if services.exists():
            min_price = min(service.base_price for service in services)
            max_price = max(service.base_price for service in services)
            avg_price = sum(service.base_price for service in services) / total_services
        else:
            min_price = max_price = avg_price = 0

        # Category breakdown
        category_breakdown = {}
        for category in service_categories:
            category_services = services.filter(category=category)
            if category_services.exists():
                category_breakdown[category.name] = {
                    'service_count': category_services.count(),
                    'avg_price': float(sum(s.base_price for s in category_services) / category_services.count()),
                    'min_price': float(min(s.base_price for s in category_services)),
                    'max_price': float(max(s.base_price for s in category_services))
                }

        # Service utilization (based on invoice items)
        popular_services = []
        for service in services[:10]:  # Top 10 services
            usage_count = InvoiceItem.objects.filter(service=service).count()
            total_revenue = sum(
                item.total_price for item in InvoiceItem.objects.filter(service=service)
            )
            popular_services.append({
                'service_name': service.name,
                'service_code': service.code,
                'base_price': float(service.base_price),
                'usage_count': usage_count,
                'total_revenue': float(total_revenue)
            })

        # Sort by usage count
        popular_services.sort(key=lambda x: x['usage_count'], reverse=True)

        return Response({
            'summary': {
                'total_services': total_services,
                'total_categories': total_categories,
                'price_range': {
                    'minimum': float(min_price),
                    'maximum': float(max_price),
                    'average': float(avg_price)
                }
            },
            'category_breakdown': category_breakdown,
            'popular_services': popular_services[:10],
            'generated_at': timezone.now().isoformat()
        })
