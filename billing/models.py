from django.db import models
from django.conf import settings
from django.utils import timezone
from decimal import Decimal
import uuid


class ServiceCategory(models.Model):
    """
    Categories for medical services
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'Service Categories'

    def __str__(self):
        return self.name


class Service(models.Model):
    """
    Medical services and procedures
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    category = models.ForeignKey(ServiceCategory, on_delete=models.CASCADE, related_name='services')

    # Service details
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=50, unique=True)  # CPT code or internal code
    description = models.TextField(blank=True)

    # Pricing
    base_price = models.DecimalField(max_digits=10, decimal_places=2)
    insurance_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    # Service details
    duration_minutes = models.PositiveIntegerField(null=True, blank=True)
    requires_authorization = models.BooleanField(default=False)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['category', 'name']

    def __str__(self):
        return f"{self.code} - {self.name}"


class Invoice(models.Model):
    """
    Patient invoices
    """
    STATUS_CHOICES = (
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('paid', 'Paid'),
        ('partially_paid', 'Partially Paid'),
        ('overdue', 'Overdue'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    invoice_number = models.CharField(max_length=20, unique=True)
    patient = models.ForeignKey('patients.Patient', on_delete=models.CASCADE, related_name='invoices')
    appointment = models.ForeignKey('appointments.Appointment', on_delete=models.SET_NULL, null=True, blank=True)

    # Invoice details
    invoice_date = models.DateField(default=timezone.now)
    due_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')

    # Amounts
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))

    # Additional information
    notes = models.TextField(blank=True)
    terms_and_conditions = models.TextField(blank=True)

    # Tracking
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    sent_date = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-invoice_date']
        indexes = [
            models.Index(fields=['patient', 'invoice_date']),
            models.Index(fields=['status']),
            models.Index(fields=['due_date']),
        ]

    def __str__(self):
        return f"{self.invoice_number} - {self.patient.user.get_full_name()}"

    @property
    def balance_due(self):
        return self.total_amount - self.paid_amount

    @property
    def is_overdue(self):
        return self.due_date < timezone.now().date() and self.balance_due > 0

    def save(self, *args, **kwargs):
        if not self.invoice_number:
            # Generate invoice number if not provided
            today = timezone.now().date()
            today_invoices = Invoice.objects.filter(
                invoice_date=today
            ).count()
            self.invoice_number = f'INV{today.strftime("%Y%m%d")}{today_invoices + 1:04d}'

        # Calculate total amount
        self.total_amount = self.subtotal + self.tax_amount - self.discount_amount

        # Update status based on payment
        if self.paid_amount >= self.total_amount:
            self.status = 'paid'
        elif self.paid_amount > 0:
            self.status = 'partially_paid'
        elif self.is_overdue:
            self.status = 'overdue'

        super().save(*args, **kwargs)


class InvoiceItem(models.Model):
    """
    Individual items on an invoice
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='items')
    service = models.ForeignKey(Service, on_delete=models.CASCADE)

    # Item details
    description = models.CharField(max_length=200)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)

    # Discounts
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f"{self.description} - {self.quantity} x ${self.unit_price}"

    def save(self, *args, **kwargs):
        # Calculate total price
        self.total_price = (self.unit_price * self.quantity) - self.discount_amount
        super().save(*args, **kwargs)


class Payment(models.Model):
    """
    Payment records
    """
    PAYMENT_METHODS = (
        ('cash', 'Cash'),
        ('credit_card', 'Credit Card'),
        ('debit_card', 'Debit Card'),
        ('check', 'Check'),
        ('bank_transfer', 'Bank Transfer'),
        ('insurance', 'Insurance'),
        ('online', 'Online Payment'),
    )

    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payment_number = models.CharField(max_length=20, unique=True)
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='payments')

    # Payment details
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS)
    payment_date = models.DateTimeField(default=timezone.now)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    # Transaction details
    transaction_id = models.CharField(max_length=100, blank=True)
    reference_number = models.CharField(max_length=100, blank=True)

    # Additional information
    notes = models.TextField(blank=True)
    processed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-payment_date']

    def __str__(self):
        return f"{self.payment_number} - ${self.amount}"

    def save(self, *args, **kwargs):
        if not self.payment_number:
            # Generate payment number if not provided
            today = timezone.now().date()
            today_payments = Payment.objects.filter(
                payment_date__date=today
            ).count()
            self.payment_number = f'PAY{today.strftime("%Y%m%d")}{today_payments + 1:04d}'
        super().save(*args, **kwargs)


class InsuranceClaim(models.Model):
    """
    Insurance claims
    """
    STATUS_CHOICES = (
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('under_review', 'Under Review'),
        ('approved', 'Approved'),
        ('denied', 'Denied'),
        ('paid', 'Paid'),
        ('appealed', 'Appealed'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    claim_number = models.CharField(max_length=20, unique=True)
    patient = models.ForeignKey('patients.Patient', on_delete=models.CASCADE, related_name='insurance_claims')
    insurance_info = models.ForeignKey('patients.InsuranceInformation', on_delete=models.CASCADE)
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='insurance_claims')

    # Claim details
    claim_date = models.DateField(default=timezone.now)
    service_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')

    # Amounts
    billed_amount = models.DecimalField(max_digits=10, decimal_places=2)
    approved_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    patient_responsibility = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))

    # Processing information
    submitted_date = models.DateTimeField(null=True, blank=True)
    processed_date = models.DateTimeField(null=True, blank=True)
    denial_reason = models.TextField(blank=True)

    # Additional information
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-claim_date']

    def __str__(self):
        return f"{self.claim_number} - {self.patient.user.get_full_name()}"

    def save(self, *args, **kwargs):
        if not self.claim_number:
            # Generate claim number if not provided
            today = timezone.now().date()
            today_claims = InsuranceClaim.objects.filter(
                claim_date=today
            ).count()
            self.claim_number = f'CLM{today.strftime("%Y%m%d")}{today_claims + 1:04d}'
        super().save(*args, **kwargs)


class ClaimDocument(models.Model):
    """
    Documents attached to insurance claims
    """
    DOCUMENT_TYPES = (
        ('medical_record', 'Medical Record'),
        ('lab_result', 'Lab Result'),
        ('imaging', 'Imaging/X-Ray'),
        ('prescription', 'Prescription'),
        ('referral', 'Referral Letter'),
        ('prior_authorization', 'Prior Authorization'),
        ('appeal_letter', 'Appeal Letter'),
        ('other', 'Other'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    claim = models.ForeignKey(InsuranceClaim, on_delete=models.CASCADE, related_name='documents')

    # Document details
    document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPES)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    # File information
    file = models.FileField(upload_to='claim_documents/%Y/%m/')
    file_size = models.PositiveIntegerField(help_text="File size in bytes")
    file_type = models.CharField(max_length=50)

    # Metadata
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    uploaded_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"{self.claim.claim_number} - {self.title}"


class ClaimAuditLog(models.Model):
    """
    Audit log for insurance claim changes
    """
    ACTION_TYPES = (
        ('created', 'Created'),
        ('submitted', 'Submitted'),
        ('reviewed', 'Reviewed'),
        ('approved', 'Approved'),
        ('denied', 'Denied'),
        ('paid', 'Paid'),
        ('appealed', 'Appealed'),
        ('document_added', 'Document Added'),
        ('note_added', 'Note Added'),
        ('amount_adjusted', 'Amount Adjusted'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    claim = models.ForeignKey(InsuranceClaim, on_delete=models.CASCADE, related_name='audit_logs')

    # Action details
    action = models.CharField(max_length=20, choices=ACTION_TYPES)
    description = models.TextField()

    # Previous and new values (JSON for flexibility)
    previous_values = models.JSONField(default=dict, blank=True)
    new_values = models.JSONField(default=dict, blank=True)

    # User and timing
    performed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    performed_at = models.DateTimeField(default=timezone.now)

    # Additional context
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)

    class Meta:
        ordering = ['-performed_at']

    def __str__(self):
        return f"{self.claim.claim_number} - {self.action} - {self.performed_at}"


class InsurancePreAuthorization(models.Model):
    """
    Pre-authorization requests for insurance coverage
    """
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('denied', 'Denied'),
        ('expired', 'Expired'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    authorization_number = models.CharField(max_length=20, unique=True)

    # Related objects
    patient = models.ForeignKey('patients.Patient', on_delete=models.CASCADE, related_name='pre_authorizations')
    insurance_info = models.ForeignKey('patients.InsuranceInformation', on_delete=models.CASCADE)

    # Authorization details
    service_description = models.TextField()
    procedure_codes = models.JSONField(default=list, help_text="List of CPT/procedure codes")
    diagnosis_codes = models.JSONField(default=list, help_text="List of ICD-10 diagnosis codes")

    # Amounts and coverage
    requested_amount = models.DecimalField(max_digits=10, decimal_places=2)
    authorized_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    # Dates
    request_date = models.DateField(default=timezone.now)
    service_date_from = models.DateField()
    service_date_to = models.DateField()
    authorization_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)

    # Status and notes
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    notes = models.TextField(blank=True)
    denial_reason = models.TextField(blank=True)

    # Tracking
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-request_date']

    def __str__(self):
        return f"{self.authorization_number} - {self.patient.user.get_full_name()}"

    def save(self, *args, **kwargs):
        if not self.authorization_number:
            # Generate authorization number if not provided
            today = timezone.now().date()
            today_auths = InsurancePreAuthorization.objects.filter(
                request_date=today
            ).count()
            self.authorization_number = f'AUTH{today.strftime("%Y%m%d")}{today_auths + 1:04d}'
        super().save(*args, **kwargs)


class FinancialTransaction(models.Model):
    """
    All financial transactions for audit and reporting
    """
    TRANSACTION_TYPES = (
        ('invoice_created', 'Invoice Created'),
        ('payment_received', 'Payment Received'),
        ('refund_issued', 'Refund Issued'),
        ('adjustment', 'Adjustment'),
        ('write_off', 'Write Off'),
        ('insurance_payment', 'Insurance Payment'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    transaction_number = models.CharField(max_length=20, unique=True)

    # Transaction details
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_date = models.DateTimeField(default=timezone.now)

    # Related objects
    patient = models.ForeignKey('patients.Patient', on_delete=models.CASCADE, related_name='financial_transactions')
    invoice = models.ForeignKey(Invoice, on_delete=models.SET_NULL, null=True, blank=True)
    payment = models.ForeignKey(Payment, on_delete=models.SET_NULL, null=True, blank=True)

    # Additional information
    description = models.TextField()
    reference_number = models.CharField(max_length=100, blank=True)
    processed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)

    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-transaction_date']
        indexes = [
            models.Index(fields=['patient', 'transaction_date']),
            models.Index(fields=['transaction_type']),
        ]

    def __str__(self):
        return f"{self.transaction_number} - {self.transaction_type} - ${self.amount}"

    def save(self, *args, **kwargs):
        if not self.transaction_number:
            # Generate transaction number if not provided
            today = timezone.now().date()
            today_transactions = FinancialTransaction.objects.filter(
                transaction_date__date=today
            ).count()
            self.transaction_number = f'TXN{today.strftime("%Y%m%d")}{today_transactions + 1:04d}'
        super().save(*args, **kwargs)


class PaymentGateway(models.Model):
    """
    Payment gateway configuration
    """
    GATEWAY_TYPES = (
        ('stripe', 'Stripe'),
        ('paypal', 'PayPal'),
        ('square', 'Square'),
        ('authorize_net', 'Authorize.Net'),
        ('braintree', 'Braintree'),
        ('mock', 'Mock Gateway (Testing)'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    gateway_type = models.CharField(max_length=20, choices=GATEWAY_TYPES)

    # Configuration
    is_active = models.BooleanField(default=True)
    is_test_mode = models.BooleanField(default=True)

    # API Configuration (stored as JSON for flexibility)
    api_configuration = models.JSONField(default=dict, help_text="Gateway-specific API configuration")

    # Supported features
    supports_credit_cards = models.BooleanField(default=True)
    supports_debit_cards = models.BooleanField(default=True)
    supports_bank_transfers = models.BooleanField(default=False)
    supports_digital_wallets = models.BooleanField(default=False)

    # Fee structure
    transaction_fee_percentage = models.DecimalField(max_digits=5, decimal_places=4, default=Decimal('0.0290'))
    transaction_fee_fixed = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.30'))

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.gateway_type})"


class PaymentMethod(models.Model):
    """
    Stored payment methods for patients
    """
    PAYMENT_TYPE_CHOICES = (
        ('credit_card', 'Credit Card'),
        ('debit_card', 'Debit Card'),
        ('bank_account', 'Bank Account'),
        ('digital_wallet', 'Digital Wallet'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey('patients.Patient', on_delete=models.CASCADE, related_name='payment_methods')
    gateway = models.ForeignKey(PaymentGateway, on_delete=models.CASCADE)

    # Payment method details
    payment_type = models.CharField(max_length=20, choices=PAYMENT_TYPE_CHOICES)
    gateway_payment_method_id = models.CharField(max_length=200, help_text="Gateway-specific payment method ID")

    # Display information (masked/tokenized)
    display_name = models.CharField(max_length=100, help_text="e.g., 'Visa ending in 1234'")
    last_four_digits = models.CharField(max_length=4, blank=True)
    expiry_month = models.IntegerField(null=True, blank=True)
    expiry_year = models.IntegerField(null=True, blank=True)

    # Status
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_default', '-created_at']
        unique_together = ['patient', 'gateway_payment_method_id']

    def __str__(self):
        return f"{self.patient.patient_id} - {self.display_name}"


class PaymentAttempt(models.Model):
    """
    Track payment attempts and their results
    """
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('succeeded', 'Succeeded'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
        ('requires_action', 'Requires Action'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name='attempts')
    gateway = models.ForeignKey(PaymentGateway, on_delete=models.CASCADE)
    payment_method = models.ForeignKey(PaymentMethod, on_delete=models.SET_NULL, null=True, blank=True)

    # Attempt details
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='USD')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    # Gateway response
    gateway_transaction_id = models.CharField(max_length=200, blank=True)
    gateway_response = models.JSONField(default=dict, help_text="Full gateway response")

    # Error handling
    error_code = models.CharField(max_length=100, blank=True)
    error_message = models.TextField(blank=True)

    # Timing
    attempted_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-attempted_at']

    def __str__(self):
        return f"Attempt {self.id} - {self.status} - ${self.amount}"


class FinancialReport(models.Model):
    """
    Generated financial reports
    """
    REPORT_TYPES = (
        ('revenue_summary', 'Revenue Summary'),
        ('payment_analysis', 'Payment Analysis'),
        ('insurance_claims', 'Insurance Claims Report'),
        ('patient_aging', 'Patient Aging Report'),
        ('service_performance', 'Service Performance'),
        ('doctor_revenue', 'Doctor Revenue Report'),
        ('monthly_summary', 'Monthly Financial Summary'),
        ('yearly_summary', 'Yearly Financial Summary'),
        ('custom', 'Custom Report'),
    )

    STATUS_CHOICES = (
        ('generating', 'Generating'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    report_number = models.CharField(max_length=20, unique=True)

    # Report details
    report_type = models.CharField(max_length=20, choices=REPORT_TYPES)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    # Date range
    date_from = models.DateField()
    date_to = models.DateField()

    # Report data (stored as JSON for flexibility)
    report_data = models.JSONField(default=dict)

    # Status and metadata
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='generating')
    generated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    generated_at = models.DateTimeField(default=timezone.now)

    # File export (optional)
    export_file = models.FileField(upload_to='financial_reports/%Y/%m/', null=True, blank=True)
    export_format = models.CharField(max_length=10, blank=True, help_text="pdf, xlsx, csv")

    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-generated_at']

    def __str__(self):
        return f"{self.report_number} - {self.title}"

    def save(self, *args, **kwargs):
        if not self.report_number:
            # Generate report number if not provided
            today = timezone.now().date()
            today_reports = FinancialReport.objects.filter(
                generated_at__date=today
            ).count()
            self.report_number = f'RPT{today.strftime("%Y%m%d")}{today_reports + 1:04d}'
        super().save(*args, **kwargs)


class RevenueMetrics(models.Model):
    """
    Daily/Monthly revenue metrics for analytics
    """
    PERIOD_TYPES = (
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('yearly', 'Yearly'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Period information
    period_type = models.CharField(max_length=20, choices=PERIOD_TYPES)
    period_start = models.DateField()
    period_end = models.DateField()

    # Revenue metrics
    total_revenue = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    cash_revenue = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    insurance_revenue = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))

    # Invoice metrics
    total_invoices = models.IntegerField(default=0)
    paid_invoices = models.IntegerField(default=0)
    pending_invoices = models.IntegerField(default=0)
    overdue_invoices = models.IntegerField(default=0)

    # Payment metrics
    total_payments = models.IntegerField(default=0)
    total_refunds = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))

    # Outstanding amounts
    total_outstanding = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))

    # Service metrics
    top_services = models.JSONField(default=list, help_text="Top performing services")
    service_revenue_breakdown = models.JSONField(default=dict, help_text="Revenue by service category")

    # Doctor metrics
    doctor_revenue_breakdown = models.JSONField(default=dict, help_text="Revenue by doctor")

    # Calculated at
    calculated_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-period_start']
        unique_together = ['period_type', 'period_start', 'period_end']

    def __str__(self):
        return f"{self.period_type.title()} - {self.period_start} to {self.period_end} - ${self.total_revenue}"


class BillingNotification(models.Model):
    """
    Billing notifications and alerts
    """
    NOTIFICATION_TYPES = (
        ('invoice_created', 'Invoice Created'),
        ('invoice_sent', 'Invoice Sent'),
        ('payment_received', 'Payment Received'),
        ('payment_reminder', 'Payment Reminder'),
        ('overdue_notice', 'Overdue Notice'),
        ('final_notice', 'Final Notice'),
        ('payment_failed', 'Payment Failed'),
        ('refund_processed', 'Refund Processed'),
        ('insurance_claim_update', 'Insurance Claim Update'),
        ('billing_statement', 'Billing Statement'),
    )

    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    )

    DELIVERY_METHODS = (
        ('email', 'Email'),
        ('sms', 'SMS'),
        ('push', 'Push Notification'),
        ('mail', 'Physical Mail'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    notification_number = models.CharField(max_length=20, unique=True)

    # Related objects
    patient = models.ForeignKey('patients.Patient', on_delete=models.CASCADE, related_name='billing_notifications')
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, null=True, blank=True, related_name='notifications')
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, null=True, blank=True, related_name='notifications')
    insurance_claim = models.ForeignKey(InsuranceClaim, on_delete=models.CASCADE, null=True, blank=True, related_name='notifications')

    # Notification details
    notification_type = models.CharField(max_length=30, choices=NOTIFICATION_TYPES)
    delivery_method = models.CharField(max_length=20, choices=DELIVERY_METHODS)

    # Content
    subject = models.CharField(max_length=200)
    message = models.TextField()

    # Recipient information
    recipient_email = models.EmailField(blank=True)
    recipient_phone = models.CharField(max_length=20, blank=True)
    recipient_address = models.TextField(blank=True)

    # Scheduling
    scheduled_at = models.DateTimeField(default=timezone.now)
    sent_at = models.DateTimeField(null=True, blank=True)

    # Status and tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    attempts = models.IntegerField(default=0)
    max_attempts = models.IntegerField(default=3)

    # Response tracking
    delivery_response = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True)

    # Metadata
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-scheduled_at']
        indexes = [
            models.Index(fields=['patient', 'notification_type']),
            models.Index(fields=['status', 'scheduled_at']),
            models.Index(fields=['invoice', 'notification_type']),
        ]

    def __str__(self):
        return f"{self.notification_number} - {self.notification_type} - {self.patient.patient_id}"

    def save(self, *args, **kwargs):
        if not self.notification_number:
            # Generate notification number if not provided
            today = timezone.now().date()
            today_notifications = BillingNotification.objects.filter(
                created_at__date=today
            ).count()
            self.notification_number = f'NOT{today.strftime("%Y%m%d")}{today_notifications + 1:04d}'
        super().save(*args, **kwargs)


class NotificationTemplate(models.Model):
    """
    Templates for billing notifications
    """
    TEMPLATE_TYPES = (
        ('invoice_created', 'Invoice Created'),
        ('invoice_sent', 'Invoice Sent'),
        ('payment_received', 'Payment Received'),
        ('payment_reminder', 'Payment Reminder'),
        ('overdue_notice', 'Overdue Notice'),
        ('final_notice', 'Final Notice'),
        ('payment_failed', 'Payment Failed'),
        ('refund_processed', 'Refund Processed'),
        ('insurance_claim_update', 'Insurance Claim Update'),
        ('billing_statement', 'Billing Statement'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    template_type = models.CharField(max_length=30, choices=TEMPLATE_TYPES)

    # Template content
    subject_template = models.CharField(max_length=200)
    email_template = models.TextField()
    sms_template = models.TextField(blank=True)

    # Template variables (JSON list of available variables)
    available_variables = models.JSONField(default=list, help_text="List of available template variables")

    # Settings
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)

    # Timing settings
    send_immediately = models.BooleanField(default=True)
    delay_hours = models.IntegerField(default=0, help_text="Hours to delay sending")

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['template_type', 'name']
        unique_together = ['template_type', 'is_default']

    def __str__(self):
        return f"{self.name} ({self.template_type})"


class NotificationSchedule(models.Model):
    """
    Scheduled notification rules
    """
    SCHEDULE_TYPES = (
        ('payment_reminder', 'Payment Reminder'),
        ('overdue_notice', 'Overdue Notice'),
        ('final_notice', 'Final Notice'),
        ('follow_up', 'Follow-up'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    schedule_type = models.CharField(max_length=20, choices=SCHEDULE_TYPES)

    # Trigger conditions
    days_after_due = models.IntegerField(help_text="Days after due date to trigger")
    minimum_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))

    # Template to use
    template = models.ForeignKey(NotificationTemplate, on_delete=models.CASCADE)

    # Delivery settings
    delivery_method = models.CharField(max_length=20, choices=BillingNotification.DELIVERY_METHODS)

    # Settings
    is_active = models.BooleanField(default=True)
    max_notifications = models.IntegerField(default=3, help_text="Maximum notifications per invoice")

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['days_after_due']

    def __str__(self):
        return f"{self.name} - {self.days_after_due} days after due"


class PricingTier(models.Model):
    """
    Pricing tiers for different patient categories
    """
    TIER_TYPES = (
        ('standard', 'Standard'),
        ('premium', 'Premium'),
        ('vip', 'VIP'),
        ('insurance', 'Insurance'),
        ('self_pay', 'Self Pay'),
        ('employee', 'Employee'),
        ('senior', 'Senior Citizen'),
        ('student', 'Student'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    tier_type = models.CharField(max_length=20, choices=TIER_TYPES)
    description = models.TextField(blank=True)

    # Pricing modifiers
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    markup_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))

    # Eligibility criteria
    minimum_age = models.IntegerField(null=True, blank=True)
    maximum_age = models.IntegerField(null=True, blank=True)
    requires_verification = models.BooleanField(default=False)

    # Settings
    is_active = models.BooleanField(default=True)
    priority = models.IntegerField(default=0, help_text="Higher priority tiers are applied first")

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-priority', 'name']

    def __str__(self):
        return f"{self.name} ({self.tier_type})"


class ServicePricing(models.Model):
    """
    Service-specific pricing with tier support
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='pricing_tiers')
    pricing_tier = models.ForeignKey(PricingTier, on_delete=models.CASCADE, related_name='service_pricing')

    # Pricing details
    price = models.DecimalField(max_digits=10, decimal_places=2)
    minimum_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    maximum_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    # Effective dates
    effective_from = models.DateField(default=timezone.now)
    effective_to = models.DateField(null=True, blank=True)

    # Settings
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-effective_from']
        unique_together = ['service', 'pricing_tier', 'effective_from']

    def __str__(self):
        return f"{self.service.name} - {self.pricing_tier.name} - ${self.price}"


class DynamicPricingRule(models.Model):
    """
    Dynamic pricing rules based on various factors
    """
    RULE_TYPES = (
        ('time_based', 'Time Based'),
        ('demand_based', 'Demand Based'),
        ('seasonal', 'Seasonal'),
        ('volume_based', 'Volume Based'),
        ('loyalty_based', 'Loyalty Based'),
        ('emergency', 'Emergency'),
    )

    CONDITION_TYPES = (
        ('time_of_day', 'Time of Day'),
        ('day_of_week', 'Day of Week'),
        ('month', 'Month'),
        ('appointment_count', 'Appointment Count'),
        ('patient_visits', 'Patient Visits'),
        ('service_demand', 'Service Demand'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    rule_type = models.CharField(max_length=20, choices=RULE_TYPES)
    description = models.TextField(blank=True)

    # Applicable services
    services = models.ManyToManyField(Service, related_name='pricing_rules')
    service_categories = models.ManyToManyField(ServiceCategory, related_name='pricing_rules', blank=True)

    # Rule conditions (JSON for flexibility)
    conditions = models.JSONField(default=dict, help_text="Rule conditions and parameters")

    # Pricing adjustments
    adjustment_type = models.CharField(max_length=20, choices=[
        ('percentage', 'Percentage'),
        ('fixed_amount', 'Fixed Amount'),
        ('multiplier', 'Multiplier'),
    ], default='percentage')
    adjustment_value = models.DecimalField(max_digits=10, decimal_places=2)

    # Limits
    minimum_adjustment = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    maximum_adjustment = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    # Effective period
    effective_from = models.DateTimeField(default=timezone.now)
    effective_to = models.DateTimeField(null=True, blank=True)

    # Settings
    is_active = models.BooleanField(default=True)
    priority = models.IntegerField(default=0)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-priority', '-effective_from']

    def __str__(self):
        return f"{self.name} ({self.rule_type})"


class ServiceBundle(models.Model):
    """
    Service bundles with package pricing
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    description = models.TextField()

    # Bundle services
    services = models.ManyToManyField(Service, through='BundleService', related_name='bundles')

    # Pricing
    bundle_price = models.DecimalField(max_digits=10, decimal_places=2)
    individual_total = models.DecimalField(max_digits=10, decimal_places=2, help_text="Sum of individual service prices")
    savings_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    savings_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))

    # Validity
    valid_from = models.DateField(default=timezone.now)
    valid_to = models.DateField(null=True, blank=True)

    # Settings
    is_active = models.BooleanField(default=True)
    requires_approval = models.BooleanField(default=False)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} - ${self.bundle_price}"

    def calculate_savings(self):
        """Calculate savings amount and percentage"""
        if self.individual_total > 0:
            self.savings_amount = self.individual_total - self.bundle_price
            self.savings_percentage = (self.savings_amount / self.individual_total) * 100
        else:
            self.savings_amount = Decimal('0.00')
            self.savings_percentage = Decimal('0.00')


class BundleService(models.Model):
    """
    Through model for service bundles
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    bundle = models.ForeignKey(ServiceBundle, on_delete=models.CASCADE)
    service = models.ForeignKey(Service, on_delete=models.CASCADE)

    # Service details in bundle
    quantity = models.IntegerField(default=1)
    individual_price = models.DecimalField(max_digits=10, decimal_places=2)
    is_required = models.BooleanField(default=True)

    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ['bundle', 'service']

    def __str__(self):
        return f"{self.bundle.name} - {self.service.name} (x{self.quantity})"
