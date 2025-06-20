from rest_framework import serializers
from django.utils import timezone
from decimal import Decimal
from .models import (
    ServiceCategory, Service, Invoice, InvoiceItem, Payment,
    InsuranceClaim, FinancialTransaction, FinancialReport, RevenueMetrics,
    BillingNotification, NotificationTemplate, NotificationSchedule
)


class ServiceCategorySerializer(serializers.ModelSerializer):
    """
    Serializer for service categories
    """
    services_count = serializers.SerializerMethodField()
    
    class Meta:
        model = ServiceCategory
        fields = [
            'id', 'name', 'description', 'is_active', 'services_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_services_count(self, obj):
        return obj.services.filter(is_active=True).count()


class ServiceSerializer(serializers.ModelSerializer):
    """
    Serializer for medical services
    """
    category_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Service
        fields = [
            'id', 'category', 'category_name', 'name', 'code', 'description',
            'base_price', 'insurance_price', 'duration_minutes', 'requires_authorization',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_category_name(self, obj):
        return obj.category.name


class InvoiceItemSerializer(serializers.ModelSerializer):
    """
    Serializer for invoice items
    """
    service_name = serializers.SerializerMethodField()
    service_code = serializers.SerializerMethodField()

    class Meta:
        model = InvoiceItem
        fields = [
            'id', 'service', 'service_name', 'service_code', 'description',
            'quantity', 'unit_price', 'discount_amount', 'total_price',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'service_name', 'service_code', 'total_price', 'created_at', 'updated_at']
    
    def get_service_name(self, obj):
        return obj.service.name if obj.service else None
    
    def get_service_code(self, obj):
        return obj.service.code if obj.service else None


class InvoiceListSerializer(serializers.ModelSerializer):
    """
    Serializer for invoice list view
    """
    patient_name = serializers.SerializerMethodField()
    balance_due = serializers.SerializerMethodField()
    is_overdue = serializers.SerializerMethodField()
    items_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Invoice
        fields = [
            'id', 'invoice_number', 'patient', 'patient_name', 'appointment',
            'invoice_date', 'due_date', 'status', 'subtotal', 'tax_amount',
            'discount_amount', 'total_amount', 'paid_amount', 'balance_due',
            'is_overdue', 'items_count', 'created_at'
        ]
        read_only_fields = ['id', 'invoice_number', 'balance_due', 'is_overdue', 'created_at']
    
    def get_patient_name(self, obj):
        return obj.patient.user.get_full_name()
    
    def get_balance_due(self, obj):
        return obj.balance_due
    
    def get_is_overdue(self, obj):
        return obj.is_overdue
    
    def get_items_count(self, obj):
        return obj.items.count()


class InvoiceDetailSerializer(serializers.ModelSerializer):
    """
    Detailed serializer for invoices
    """
    patient_name = serializers.SerializerMethodField()
    patient_details = serializers.SerializerMethodField()
    appointment_details = serializers.SerializerMethodField()
    items = InvoiceItemSerializer(many=True, read_only=True)
    payments = serializers.SerializerMethodField()
    balance_due = serializers.SerializerMethodField()
    is_overdue = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Invoice
        fields = [
            'id', 'invoice_number', 'patient', 'patient_name', 'patient_details',
            'appointment', 'appointment_details', 'invoice_date', 'due_date', 'status',
            'subtotal', 'tax_amount', 'discount_amount', 'total_amount', 'paid_amount',
            'balance_due', 'is_overdue', 'notes', 'terms_and_conditions',
            'created_by', 'created_by_name', 'sent_date', 'items', 'payments',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'invoice_number', 'balance_due', 'is_overdue', 'created_at', 'updated_at']
    
    def get_patient_name(self, obj):
        return obj.patient.user.get_full_name()
    
    def get_patient_details(self, obj):
        return {
            'id': obj.patient.patient_id,
            'name': obj.patient.user.get_full_name(),
            'email': obj.patient.user.email,
            'phone': obj.patient.user.phone_number,
            'address': obj.patient.user.address,
            'date_of_birth': obj.patient.user.date_of_birth,
        }
    
    def get_appointment_details(self, obj):
        if obj.appointment:
            return {
                'id': obj.appointment.id,
                'appointment_number': obj.appointment.appointment_number,
                'appointment_date': obj.appointment.appointment_date,
                'appointment_time': obj.appointment.appointment_time,
                'doctor_name': obj.appointment.doctor.user.get_full_name(),
                'status': obj.appointment.status
            }
        return None
    
    def get_payments(self, obj):
        # Avoid circular import by defining inline
        payments_data = []
        for payment in obj.payments.all():
            payments_data.append({
                'id': payment.id,
                'payment_number': payment.payment_number,
                'amount': payment.amount,
                'payment_method': payment.payment_method,
                'payment_date': payment.payment_date,
                'status': payment.status,
                'transaction_id': payment.transaction_id,
                'reference_number': payment.reference_number
            })
        return payments_data
    
    def get_balance_due(self, obj):
        return obj.balance_due
    
    def get_is_overdue(self, obj):
        return obj.is_overdue
    
    def get_created_by_name(self, obj):
        return obj.created_by.get_full_name() if obj.created_by else None


class InvoiceCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating invoices
    """
    items = InvoiceItemSerializer(many=True, write_only=True)
    
    class Meta:
        model = Invoice
        fields = [
            'patient', 'appointment', 'invoice_date', 'due_date',
            'tax_amount', 'discount_amount', 'notes', 'terms_and_conditions', 'items'
        ]
    
    def create(self, validated_data):
        items_data = validated_data.pop('items')
        
        # Set created_by from request user
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            validated_data['created_by'] = request.user
        
        # Create invoice
        invoice = Invoice.objects.create(**validated_data)
        
        # Create invoice items and calculate subtotal
        subtotal = Decimal('0.00')
        for item_data in items_data:
            item_data['invoice'] = invoice
            item = InvoiceItem.objects.create(**item_data)
            subtotal += item.total_price
        
        # Update invoice subtotal and total
        invoice.subtotal = subtotal
        invoice.save()
        
        return invoice


class PaymentSerializer(serializers.ModelSerializer):
    """
    Serializer for payments
    """
    invoice_number = serializers.SerializerMethodField()
    patient_name = serializers.SerializerMethodField()
    processed_by_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Payment
        fields = [
            'id', 'payment_number', 'invoice', 'invoice_number', 'patient_name',
            'amount', 'payment_method', 'payment_date', 'status',
            'transaction_id', 'reference_number', 'notes',
            'processed_by', 'processed_by_name', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'payment_number', 'created_at', 'updated_at']
    
    def get_invoice_number(self, obj):
        return obj.invoice.invoice_number
    
    def get_patient_name(self, obj):
        return obj.invoice.patient.user.get_full_name()
    
    def get_processed_by_name(self, obj):
        return obj.processed_by.get_full_name() if obj.processed_by else None


class FinancialTransactionSerializer(serializers.ModelSerializer):
    """
    Serializer for financial transactions
    """
    patient_name = serializers.SerializerMethodField()
    processed_by_name = serializers.SerializerMethodField()
    invoice_number = serializers.SerializerMethodField()
    payment_number = serializers.SerializerMethodField()
    
    class Meta:
        model = FinancialTransaction
        fields = [
            'id', 'transaction_number', 'transaction_type', 'amount', 'transaction_date',
            'patient', 'patient_name', 'invoice', 'invoice_number', 'payment', 'payment_number',
            'description', 'reference_number', 'processed_by', 'processed_by_name', 'created_at'
        ]
        read_only_fields = ['id', 'transaction_number', 'created_at']
    
    def get_patient_name(self, obj):
        return obj.patient.user.get_full_name()
    
    def get_processed_by_name(self, obj):
        return obj.processed_by.get_full_name() if obj.processed_by else None
    
    def get_invoice_number(self, obj):
        return obj.invoice.invoice_number if obj.invoice else None
    
    def get_payment_number(self, obj):
        return obj.payment.payment_number if obj.payment else None


class InsuranceClaimSerializer(serializers.ModelSerializer):
    """
    Serializer for insurance claims
    """
    patient_name = serializers.SerializerMethodField()
    insurance_company = serializers.SerializerMethodField()
    invoice_number = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()
    
    class Meta:
        model = InsuranceClaim
        fields = [
            'id', 'claim_number', 'patient', 'patient_name', 'insurance_info',
            'insurance_company', 'invoice', 'invoice_number', 'claim_date', 'service_date',
            'status', 'billed_amount', 'approved_amount', 'paid_amount', 'patient_responsibility',
            'submitted_date', 'processed_date', 'denial_reason', 'notes',
            'created_by', 'created_by_name', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'claim_number', 'created_at', 'updated_at']
    
    def get_patient_name(self, obj):
        return obj.patient.user.get_full_name()
    
    def get_insurance_company(self, obj):
        return obj.insurance_info.provider_name
    
    def get_invoice_number(self, obj):
        return obj.invoice.invoice_number
    
    def get_created_by_name(self, obj):
        return obj.created_by.get_full_name() if obj.created_by else None


class FinancialReportSerializer(serializers.ModelSerializer):
    """
    Serializer for financial reports
    """
    generated_by_name = serializers.CharField(source='generated_by.get_full_name', read_only=True)

    class Meta:
        model = FinancialReport
        fields = '__all__'
        read_only_fields = ('report_number', 'generated_at', 'created_at')


class RevenueMetricsSerializer(serializers.ModelSerializer):
    """
    Serializer for revenue metrics
    """

    class Meta:
        model = RevenueMetrics
        fields = '__all__'
        read_only_fields = ('calculated_at',)


class BillingNotificationSerializer(serializers.ModelSerializer):
    """
    Serializer for billing notifications
    """
    patient_name = serializers.CharField(source='patient.user.get_full_name', read_only=True)
    patient_id = serializers.CharField(source='patient.patient_id', read_only=True)
    invoice_number = serializers.CharField(source='invoice.invoice_number', read_only=True)
    payment_number = serializers.CharField(source='payment.payment_number', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)

    class Meta:
        model = BillingNotification
        fields = '__all__'
        read_only_fields = ('notification_number', 'sent_at', 'created_at', 'updated_at')


class NotificationTemplateSerializer(serializers.ModelSerializer):
    """
    Serializer for notification templates
    """

    class Meta:
        model = NotificationTemplate
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')


class NotificationScheduleSerializer(serializers.ModelSerializer):
    """
    Serializer for notification schedules
    """
    template_name = serializers.CharField(source='template.name', read_only=True)

    class Meta:
        model = NotificationSchedule
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')
