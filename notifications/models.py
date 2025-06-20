import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone
from decimal import Decimal


class EmailTemplate(models.Model):
    """
    Email templates for different notification types
    """
    TEMPLATE_TYPES = (
        ('appointment_confirmation', 'Appointment Confirmation'),
        ('appointment_reminder', 'Appointment Reminder'),
        ('appointment_cancellation', 'Appointment Cancellation'),
        ('appointment_rescheduled', 'Appointment Rescheduled'),
        ('test_results_ready', 'Test Results Ready'),
        ('prescription_ready', 'Prescription Ready'),
        ('payment_confirmation', 'Payment Confirmation'),
        ('payment_reminder', 'Payment Reminder'),
        ('invoice_generated', 'Invoice Generated'),
        ('insurance_claim_update', 'Insurance Claim Update'),
        ('welcome_patient', 'Welcome New Patient'),
        ('welcome_doctor', 'Welcome New Doctor'),
        ('password_reset', 'Password Reset'),
        ('account_activation', 'Account Activation'),
        ('system_maintenance', 'System Maintenance'),
        ('emergency_alert', 'Emergency Alert'),
        ('custom', 'Custom Template'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    template_type = models.CharField(max_length=50, choices=TEMPLATE_TYPES)
    description = models.TextField(blank=True)

    # Email content
    subject_template = models.CharField(max_length=500, help_text="Subject line with variable placeholders")
    html_template = models.TextField(help_text="HTML email template with variable placeholders")
    text_template = models.TextField(help_text="Plain text email template with variable placeholders")

    # Template variables
    available_variables = models.JSONField(
        default=list,
        help_text="List of available variables for this template"
    )

    # Settings
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False, help_text="Default template for this type")

    # Metadata
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['template_type', 'name']
        unique_together = ['template_type', 'is_default']

    def __str__(self):
        return f"{self.name} ({self.get_template_type_display()})"


class EmailNotification(models.Model):
    """
    Email notification records with delivery tracking
    """
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('sending', 'Sending'),
        ('sent', 'Sent'),
        ('delivered', 'Delivered'),
        ('opened', 'Opened'),
        ('clicked', 'Clicked'),
        ('failed', 'Failed'),
        ('bounced', 'Bounced'),
        ('spam', 'Marked as Spam'),
        ('unsubscribed', 'Unsubscribed'),
    )

    PRIORITY_CHOICES = (
        ('low', 'Low'),
        ('normal', 'Normal'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    notification_id = models.CharField(max_length=20, unique=True, help_text="Human-readable notification ID")

    # Recipients
    recipient_email = models.EmailField()
    recipient_name = models.CharField(max_length=200, blank=True)
    recipient_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='email_notifications'
    )

    # Email content
    template = models.ForeignKey(EmailTemplate, on_delete=models.SET_NULL, null=True, blank=True)
    subject = models.CharField(max_length=500)
    html_content = models.TextField()
    text_content = models.TextField()

    # Template variables used
    template_variables = models.JSONField(default=dict, help_text="Variables used to render the template")

    # Delivery settings
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='normal')
    scheduled_at = models.DateTimeField(null=True, blank=True, help_text="When to send the email")

    # Status tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    attempts = models.PositiveIntegerField(default=0)
    max_attempts = models.PositiveIntegerField(default=3)

    # Delivery tracking
    sent_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    opened_at = models.DateTimeField(null=True, blank=True)
    clicked_at = models.DateTimeField(null=True, blank=True)

    # Error handling
    error_message = models.TextField(blank=True)
    bounce_reason = models.TextField(blank=True)

    # Email service provider response
    provider_message_id = models.CharField(max_length=200, blank=True)
    provider_response = models.JSONField(default=dict, blank=True)

    # Related objects
    appointment = models.ForeignKey(
        'appointments.Appointment',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='email_notifications'
    )
    invoice = models.ForeignKey(
        'billing.Invoice',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='email_notifications'
    )

    # Metadata
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_email_notifications'
    )
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient_email', 'status']),
            models.Index(fields=['status', 'scheduled_at']),
            models.Index(fields=['template', 'status']),
        ]

    def __str__(self):
        return f"{self.notification_id} - {self.recipient_email} - {self.status}"

    def save(self, *args, **kwargs):
        if not self.notification_id:
            # Generate notification ID if not provided
            today = timezone.now().date()
            today_notifications = EmailNotification.objects.filter(
                created_at__date=today
            ).count()
            self.notification_id = f'EMAIL{today.strftime("%Y%m%d")}{today_notifications + 1:04d}'
        super().save(*args, **kwargs)


class EmailConfiguration(models.Model):
    """
    Email service provider configuration
    """
    PROVIDER_TYPES = (
        ('smtp', 'SMTP Server'),
        ('sendgrid', 'SendGrid'),
        ('mailgun', 'Mailgun'),
        ('ses', 'Amazon SES'),
        ('postmark', 'Postmark'),
        ('mandrill', 'Mandrill'),
        ('sparkpost', 'SparkPost'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    provider_type = models.CharField(max_length=20, choices=PROVIDER_TYPES)

    # Configuration settings (stored as JSON for flexibility)
    configuration = models.JSONField(default=dict, help_text="Provider-specific configuration")

    # Settings
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)

    # Rate limiting
    daily_limit = models.PositiveIntegerField(null=True, blank=True, help_text="Daily email limit")
    hourly_limit = models.PositiveIntegerField(null=True, blank=True, help_text="Hourly email limit")

    # Tracking
    emails_sent_today = models.PositiveIntegerField(default=0)
    emails_sent_this_hour = models.PositiveIntegerField(default=0)
    last_reset_date = models.DateField(default=timezone.now)
    last_reset_hour = models.DateTimeField(default=timezone.now)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.get_provider_type_display()})"


class EmailSubscription(models.Model):
    """
    Email subscription preferences for users
    """
    SUBSCRIPTION_TYPES = (
        ('appointment_reminders', 'Appointment Reminders'),
        ('test_results', 'Test Results'),
        ('payment_reminders', 'Payment Reminders'),
        ('promotional', 'Promotional Emails'),
        ('newsletters', 'Newsletters'),
        ('system_updates', 'System Updates'),
        ('emergency_alerts', 'Emergency Alerts'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='email_subscriptions')
    subscription_type = models.CharField(max_length=50, choices=SUBSCRIPTION_TYPES)

    # Subscription settings
    is_subscribed = models.BooleanField(default=True)
    frequency = models.CharField(max_length=20, choices=[
        ('immediate', 'Immediate'),
        ('daily', 'Daily Digest'),
        ('weekly', 'Weekly Digest'),
        ('monthly', 'Monthly Digest'),
    ], default='immediate')

    # Tracking
    subscribed_at = models.DateTimeField(default=timezone.now)
    unsubscribed_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['user', 'subscription_type']
        ordering = ['user', 'subscription_type']

    def __str__(self):
        status = "Subscribed" if self.is_subscribed else "Unsubscribed"
        return f"{self.user.get_full_name()} - {self.get_subscription_type_display()} - {status}"


class EmailAnalytics(models.Model):
    """
    Email analytics and reporting
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Date tracking
    date = models.DateField(default=timezone.now)

    # Email metrics
    emails_sent = models.PositiveIntegerField(default=0)
    emails_delivered = models.PositiveIntegerField(default=0)
    emails_opened = models.PositiveIntegerField(default=0)
    emails_clicked = models.PositiveIntegerField(default=0)
    emails_bounced = models.PositiveIntegerField(default=0)
    emails_failed = models.PositiveIntegerField(default=0)
    emails_spam = models.PositiveIntegerField(default=0)
    emails_unsubscribed = models.PositiveIntegerField(default=0)

    # Template breakdown (JSON for flexibility)
    template_metrics = models.JSONField(default=dict, help_text="Metrics broken down by template type")

    # Provider breakdown
    provider_metrics = models.JSONField(default=dict, help_text="Metrics broken down by email provider")

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['date']
        ordering = ['-date']

    def __str__(self):
        return f"Email Analytics - {self.date}"

    @property
    def delivery_rate(self):
        """Calculate delivery rate percentage"""
        if self.emails_sent > 0:
            return (self.emails_delivered / self.emails_sent) * 100
        return 0

    @property
    def open_rate(self):
        """Calculate open rate percentage"""
        if self.emails_delivered > 0:
            return (self.emails_opened / self.emails_delivered) * 100
        return 0

    @property
    def click_rate(self):
        """Calculate click rate percentage"""
        if self.emails_opened > 0:
            return (self.emails_clicked / self.emails_opened) * 100
        return 0

    @property
    def bounce_rate(self):
        """Calculate bounce rate percentage"""
        if self.emails_sent > 0:
            return (self.emails_bounced / self.emails_sent) * 100
        return 0


class SMSTemplate(models.Model):
    """
    SMS templates for different notification types
    """
    TEMPLATE_TYPES = (
        ('appointment_reminder', 'Appointment Reminder'),
        ('appointment_confirmation', 'Appointment Confirmation'),
        ('appointment_cancellation', 'Appointment Cancellation'),
        ('test_results_ready', 'Test Results Ready'),
        ('prescription_ready', 'Prescription Ready'),
        ('payment_reminder', 'Payment Reminder'),
        ('payment_confirmation', 'Payment Confirmation'),
        ('emergency_alert', 'Emergency Alert'),
        ('verification_code', 'Verification Code'),
        ('password_reset', 'Password Reset'),
        ('appointment_today', 'Appointment Today'),
        ('medication_reminder', 'Medication Reminder'),
        ('custom', 'Custom Template'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    template_type = models.CharField(max_length=50, choices=TEMPLATE_TYPES)
    description = models.TextField(blank=True)

    # SMS content (160 characters limit for single SMS)
    message_template = models.TextField(
        max_length=1600,
        help_text="SMS message template with variable placeholders (max 1600 chars for 10 SMS)"
    )

    # Template variables
    available_variables = models.JSONField(
        default=list,
        help_text="List of available variables for this template"
    )

    # Settings
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False, help_text="Default template for this type")
    max_length = models.PositiveIntegerField(default=160, help_text="Maximum message length")

    # Metadata
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['template_type', 'name']
        unique_together = ['template_type', 'is_default']

    def __str__(self):
        return f"{self.name} ({self.get_template_type_display()})"


class SMSNotification(models.Model):
    """
    SMS notification records with delivery tracking
    """
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('queued', 'Queued'),
        ('sending', 'Sending'),
        ('sent', 'Sent'),
        ('delivered', 'Delivered'),
        ('failed', 'Failed'),
        ('undelivered', 'Undelivered'),
        ('unknown', 'Unknown'),
    )

    PRIORITY_CHOICES = (
        ('low', 'Low'),
        ('normal', 'Normal'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    notification_id = models.CharField(max_length=20, unique=True, help_text="Human-readable notification ID")

    # Recipients
    recipient_phone = models.CharField(max_length=20, help_text="Phone number in E.164 format")
    recipient_name = models.CharField(max_length=200, blank=True)
    recipient_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sms_notifications'
    )

    # SMS content
    template = models.ForeignKey(SMSTemplate, on_delete=models.SET_NULL, null=True, blank=True)
    message = models.TextField(max_length=1600)

    # Template variables used
    template_variables = models.JSONField(default=dict, help_text="Variables used to render the template")

    # Delivery settings
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='normal')
    scheduled_at = models.DateTimeField(null=True, blank=True, help_text="When to send the SMS")

    # Status tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    attempts = models.PositiveIntegerField(default=0)
    max_attempts = models.PositiveIntegerField(default=3)

    # Delivery tracking
    sent_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)

    # Error handling
    error_message = models.TextField(blank=True)
    error_code = models.CharField(max_length=50, blank=True)

    # SMS service provider response
    provider_message_id = models.CharField(max_length=200, blank=True)
    provider_response = models.JSONField(default=dict, blank=True)

    # Cost tracking
    cost = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    currency = models.CharField(max_length=3, default='USD')

    # Related objects
    appointment = models.ForeignKey(
        'appointments.Appointment',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sms_notifications'
    )

    # Metadata
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_sms_notifications'
    )
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient_phone', 'status']),
            models.Index(fields=['status', 'scheduled_at']),
            models.Index(fields=['template', 'status']),
        ]

    def __str__(self):
        return f"{self.notification_id} - {self.recipient_phone} - {self.status}"

    def save(self, *args, **kwargs):
        if not self.notification_id:
            # Generate notification ID if not provided
            today = timezone.now().date()
            today_notifications = SMSNotification.objects.filter(
                created_at__date=today
            ).count()
            self.notification_id = f'SMS{today.strftime("%Y%m%d")}{today_notifications + 1:04d}'
        super().save(*args, **kwargs)


class SMSConfiguration(models.Model):
    """
    SMS service provider configuration
    """
    PROVIDER_TYPES = (
        ('twilio', 'Twilio'),
        ('aws_sns', 'Amazon SNS'),
        ('nexmo', 'Nexmo/Vonage'),
        ('messagebird', 'MessageBird'),
        ('clicksend', 'ClickSend'),
        ('textlocal', 'Textlocal'),
        ('plivo', 'Plivo'),
        ('mock', 'Mock Provider (Testing)'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    provider_type = models.CharField(max_length=20, choices=PROVIDER_TYPES)

    # Configuration settings (stored as JSON for flexibility)
    configuration = models.JSONField(default=dict, help_text="Provider-specific configuration")

    # Settings
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)

    # Rate limiting
    daily_limit = models.PositiveIntegerField(null=True, blank=True, help_text="Daily SMS limit")
    hourly_limit = models.PositiveIntegerField(null=True, blank=True, help_text="Hourly SMS limit")

    # Cost settings
    cost_per_sms = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    currency = models.CharField(max_length=3, default='USD')

    # Tracking
    sms_sent_today = models.PositiveIntegerField(default=0)
    sms_sent_this_hour = models.PositiveIntegerField(default=0)
    total_cost_today = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    last_reset_date = models.DateField(default=timezone.now)
    last_reset_hour = models.DateTimeField(default=timezone.now)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.get_provider_type_display()})"


class SMSAnalytics(models.Model):
    """
    SMS analytics and reporting
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Date tracking
    date = models.DateField(default=timezone.now)

    # SMS metrics
    sms_sent = models.PositiveIntegerField(default=0)
    sms_delivered = models.PositiveIntegerField(default=0)
    sms_failed = models.PositiveIntegerField(default=0)
    sms_undelivered = models.PositiveIntegerField(default=0)

    # Cost metrics
    total_cost = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    currency = models.CharField(max_length=3, default='USD')

    # Template breakdown (JSON for flexibility)
    template_metrics = models.JSONField(default=dict, help_text="Metrics broken down by template type")

    # Provider breakdown
    provider_metrics = models.JSONField(default=dict, help_text="Metrics broken down by SMS provider")

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['date']
        ordering = ['-date']

    def __str__(self):
        return f"SMS Analytics - {self.date}"

    @property
    def delivery_rate(self):
        """Calculate delivery rate percentage"""
        if self.sms_sent > 0:
            return (self.sms_delivered / self.sms_sent) * 100
        return 0

    @property
    def failure_rate(self):
        """Calculate failure rate percentage"""
        if self.sms_sent > 0:
            return (self.sms_failed / self.sms_sent) * 100
        return 0

    @property
    def average_cost_per_sms(self):
        """Calculate average cost per SMS"""
        if self.sms_sent > 0:
            return self.total_cost / self.sms_sent
        return Decimal('0.00')


class PushNotificationTemplate(models.Model):
    """
    Push notification templates for different notification types
    """
    TEMPLATE_TYPES = (
        ('appointment_reminder', 'Appointment Reminder'),
        ('appointment_confirmed', 'Appointment Confirmed'),
        ('test_results_ready', 'Test Results Ready'),
        ('prescription_ready', 'Prescription Ready'),
        ('payment_due', 'Payment Due'),
        ('payment_received', 'Payment Received'),
        ('emergency_alert', 'Emergency Alert'),
        ('system_update', 'System Update'),
        ('new_message', 'New Message'),
        ('lab_report_ready', 'Lab Report Ready'),
        ('medication_reminder', 'Medication Reminder'),
        ('custom', 'Custom Notification'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    template_type = models.CharField(max_length=50, choices=TEMPLATE_TYPES)
    description = models.TextField(blank=True)

    # Push notification content
    title_template = models.CharField(max_length=200, help_text="Notification title with variable placeholders")
    body_template = models.TextField(max_length=500, help_text="Notification body with variable placeholders")

    # Additional push notification data
    icon_url = models.URLField(blank=True, help_text="URL to notification icon")
    image_url = models.URLField(blank=True, help_text="URL to notification image")
    action_url = models.URLField(blank=True, help_text="URL to open when notification is clicked")

    # Template variables
    available_variables = models.JSONField(
        default=list,
        help_text="List of available variables for this template"
    )

    # Settings
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False, help_text="Default template for this type")
    requires_interaction = models.BooleanField(default=False, help_text="Notification requires user interaction")

    # Metadata
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['template_type', 'name']
        unique_together = ['template_type', 'is_default']

    def __str__(self):
        return f"{self.name} ({self.get_template_type_display()})"


class PushNotification(models.Model):
    """
    Push notification records with delivery tracking
    """
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('queued', 'Queued'),
        ('sending', 'Sending'),
        ('sent', 'Sent'),
        ('delivered', 'Delivered'),
        ('clicked', 'Clicked'),
        ('dismissed', 'Dismissed'),
        ('failed', 'Failed'),
        ('expired', 'Expired'),
    )

    PRIORITY_CHOICES = (
        ('low', 'Low'),
        ('normal', 'Normal'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    )

    DEVICE_TYPES = (
        ('web', 'Web Browser'),
        ('android', 'Android'),
        ('ios', 'iOS'),
        ('desktop', 'Desktop'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    notification_id = models.CharField(max_length=20, unique=True, help_text="Human-readable notification ID")

    # Recipients
    recipient_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='push_notifications'
    )
    device_token = models.CharField(max_length=500, blank=True, help_text="Device-specific push token")
    device_type = models.CharField(max_length=20, choices=DEVICE_TYPES, default='web')

    # Push notification content
    template = models.ForeignKey(PushNotificationTemplate, on_delete=models.SET_NULL, null=True, blank=True)
    title = models.CharField(max_length=200)
    body = models.TextField(max_length=500)
    icon_url = models.URLField(blank=True)
    image_url = models.URLField(blank=True)
    action_url = models.URLField(blank=True)

    # Template variables used
    template_variables = models.JSONField(default=dict, help_text="Variables used to render the template")

    # Additional data
    custom_data = models.JSONField(default=dict, help_text="Custom data to send with notification")

    # Delivery settings
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='normal')
    scheduled_at = models.DateTimeField(null=True, blank=True, help_text="When to send the notification")
    expires_at = models.DateTimeField(null=True, blank=True, help_text="When the notification expires")

    # Status tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    attempts = models.PositiveIntegerField(default=0)
    max_attempts = models.PositiveIntegerField(default=3)

    # Delivery tracking
    sent_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    clicked_at = models.DateTimeField(null=True, blank=True)
    dismissed_at = models.DateTimeField(null=True, blank=True)

    # Error handling
    error_message = models.TextField(blank=True)
    error_code = models.CharField(max_length=50, blank=True)

    # Push service provider response
    provider_message_id = models.CharField(max_length=200, blank=True)
    provider_response = models.JSONField(default=dict, blank=True)

    # Related objects
    appointment = models.ForeignKey(
        'appointments.Appointment',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='push_notifications'
    )

    # Metadata
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_push_notifications'
    )
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient_user', 'status']),
            models.Index(fields=['status', 'scheduled_at']),
            models.Index(fields=['device_type', 'status']),
        ]

    def __str__(self):
        return f"{self.notification_id} - {self.recipient_user.get_full_name()} - {self.status}"

    def save(self, *args, **kwargs):
        if not self.notification_id:
            # Generate notification ID if not provided
            today = timezone.now().date()
            today_notifications = PushNotification.objects.filter(
                created_at__date=today
            ).count()
            self.notification_id = f'PUSH{today.strftime("%Y%m%d")}{today_notifications + 1:04d}'
        super().save(*args, **kwargs)


class PushNotificationConfiguration(models.Model):
    """
    Push notification service configuration
    """
    PROVIDER_TYPES = (
        ('fcm', 'Firebase Cloud Messaging'),
        ('apns', 'Apple Push Notification Service'),
        ('web_push', 'Web Push Protocol'),
        ('websocket', 'WebSocket Real-time'),
        ('mock', 'Mock Provider (Testing)'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    provider_type = models.CharField(max_length=20, choices=PROVIDER_TYPES)

    # Configuration settings (stored as JSON for flexibility)
    configuration = models.JSONField(default=dict, help_text="Provider-specific configuration")

    # Settings
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)

    # Rate limiting
    daily_limit = models.PositiveIntegerField(null=True, blank=True, help_text="Daily push notification limit")
    hourly_limit = models.PositiveIntegerField(null=True, blank=True, help_text="Hourly push notification limit")

    # Tracking
    notifications_sent_today = models.PositiveIntegerField(default=0)
    notifications_sent_this_hour = models.PositiveIntegerField(default=0)
    last_reset_date = models.DateField(default=timezone.now)
    last_reset_hour = models.DateTimeField(default=timezone.now)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.get_provider_type_display()})"


class PushNotificationAnalytics(models.Model):
    """
    Push notification analytics and reporting
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Date tracking
    date = models.DateField(default=timezone.now)

    # Push notification metrics
    notifications_sent = models.PositiveIntegerField(default=0)
    notifications_delivered = models.PositiveIntegerField(default=0)
    notifications_clicked = models.PositiveIntegerField(default=0)
    notifications_dismissed = models.PositiveIntegerField(default=0)
    notifications_failed = models.PositiveIntegerField(default=0)
    notifications_expired = models.PositiveIntegerField(default=0)

    # Device breakdown (JSON for flexibility)
    device_metrics = models.JSONField(default=dict, help_text="Metrics broken down by device type")

    # Template breakdown
    template_metrics = models.JSONField(default=dict, help_text="Metrics broken down by template type")

    # Provider breakdown
    provider_metrics = models.JSONField(default=dict, help_text="Metrics broken down by push provider")

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['date']
        ordering = ['-date']

    def __str__(self):
        return f"Push Analytics - {self.date}"

    @property
    def delivery_rate(self):
        """Calculate delivery rate percentage"""
        if self.notifications_sent > 0:
            return (self.notifications_delivered / self.notifications_sent) * 100
        return 0

    @property
    def click_rate(self):
        """Calculate click rate percentage"""
        if self.notifications_delivered > 0:
            return (self.notifications_clicked / self.notifications_delivered) * 100
        return 0

    @property
    def dismissal_rate(self):
        """Calculate dismissal rate percentage"""
        if self.notifications_delivered > 0:
            return (self.notifications_dismissed / self.notifications_delivered) * 100
        return 0

    @property
    def failure_rate(self):
        """Calculate failure rate percentage"""
        if self.notifications_sent > 0:
            return (self.notifications_failed / self.notifications_sent) * 100
        return 0


class DeviceToken(models.Model):
    """
    Device tokens for push notifications
    """
    DEVICE_TYPES = (
        ('web', 'Web Browser'),
        ('android', 'Android'),
        ('ios', 'iOS'),
        ('desktop', 'Desktop'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='device_tokens')

    # Device information
    device_token = models.CharField(max_length=500, unique=True)
    device_type = models.CharField(max_length=20, choices=DEVICE_TYPES)
    device_name = models.CharField(max_length=200, blank=True, help_text="User-friendly device name")

    # Device details
    user_agent = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    # Settings
    is_active = models.BooleanField(default=True)
    notifications_enabled = models.BooleanField(default=True)

    # Tracking
    last_used_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-last_used_at']
        indexes = [
            models.Index(fields=['user', 'device_type']),
            models.Index(fields=['device_token']),
        ]

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.get_device_type_display()} - {self.device_name or 'Unknown Device'}"


class TemplateVariable(models.Model):
    """
    Template variables with validation and formatting rules
    """
    VARIABLE_TYPES = (
        ('string', 'String'),
        ('number', 'Number'),
        ('date', 'Date'),
        ('datetime', 'Date Time'),
        ('boolean', 'Boolean'),
        ('email', 'Email'),
        ('phone', 'Phone Number'),
        ('url', 'URL'),
        ('currency', 'Currency'),
    )

    FORMAT_TYPES = (
        ('none', 'No Formatting'),
        ('uppercase', 'Uppercase'),
        ('lowercase', 'Lowercase'),
        ('title_case', 'Title Case'),
        ('date_short', 'Short Date (MM/DD/YYYY)'),
        ('date_long', 'Long Date (Month DD, YYYY)'),
        ('time_12h', '12-hour Time'),
        ('time_24h', '24-hour Time'),
        ('currency_usd', 'US Dollar ($)'),
        ('phone_us', 'US Phone Format'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    display_name = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    # Variable properties
    variable_type = models.CharField(max_length=20, choices=VARIABLE_TYPES, default='string')
    format_type = models.CharField(max_length=20, choices=FORMAT_TYPES, default='none')

    # Validation rules
    is_required = models.BooleanField(default=False)
    default_value = models.TextField(blank=True)
    validation_regex = models.CharField(max_length=500, blank=True, help_text="Regex pattern for validation")

    # Usage tracking
    usage_count = models.PositiveIntegerField(default=0)

    # Metadata
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.get_variable_type_display()})"


class TemplateLanguage(models.Model):
    """
    Supported languages for multi-language templates
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=10, unique=True, help_text="Language code (e.g., en, es, fr)")
    name = models.CharField(max_length=100, help_text="Language name (e.g., English, Spanish)")
    native_name = models.CharField(max_length=100, help_text="Native language name (e.g., Español)")

    # Settings
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)

    # Text direction
    text_direction = models.CharField(max_length=3, choices=[
        ('ltr', 'Left to Right'),
        ('rtl', 'Right to Left'),
    ], default='ltr')

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.code})"


class UnifiedTemplate(models.Model):
    """
    Unified template that can be used across email, SMS, and push notifications
    """
    TEMPLATE_TYPES = (
        ('appointment_confirmation', 'Appointment Confirmation'),
        ('appointment_reminder', 'Appointment Reminder'),
        ('appointment_cancellation', 'Appointment Cancellation'),
        ('test_results_ready', 'Test Results Ready'),
        ('prescription_ready', 'Prescription Ready'),
        ('payment_confirmation', 'Payment Confirmation'),
        ('payment_reminder', 'Payment Reminder'),
        ('invoice_generated', 'Invoice Generated'),
        ('welcome_patient', 'Welcome New Patient'),
        ('welcome_doctor', 'Welcome New Doctor'),
        ('password_reset', 'Password Reset'),
        ('verification_code', 'Verification Code'),
        ('emergency_alert', 'Emergency Alert'),
        ('system_maintenance', 'System Maintenance'),
        ('custom', 'Custom Template'),
    )

    NOTIFICATION_CHANNELS = (
        ('email', 'Email'),
        ('sms', 'SMS'),
        ('push', 'Push Notification'),
        ('all', 'All Channels'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    template_type = models.CharField(max_length=50, choices=TEMPLATE_TYPES)
    description = models.TextField(blank=True)

    # Channel support
    supported_channels = models.JSONField(default=list, help_text="List of supported notification channels")

    # Template variables
    variables = models.ManyToManyField(TemplateVariable, related_name='templates')

    # Versioning
    version = models.CharField(max_length=20, default='1.0')
    parent_template = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True)

    # Settings
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)

    # Metadata
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['template_type', 'name']
        unique_together = ['template_type', 'is_default']

    def __str__(self):
        return f"{self.name} v{self.version} ({self.get_template_type_display()})"


class TemplateContent(models.Model):
    """
    Multi-language content for unified templates
    """
    CONTENT_TYPES = (
        ('email_subject', 'Email Subject'),
        ('email_html', 'Email HTML'),
        ('email_text', 'Email Text'),
        ('sms_message', 'SMS Message'),
        ('push_title', 'Push Title'),
        ('push_body', 'Push Body'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    template = models.ForeignKey(UnifiedTemplate, on_delete=models.CASCADE, related_name='content')
    language = models.ForeignKey(TemplateLanguage, on_delete=models.CASCADE)
    content_type = models.CharField(max_length=20, choices=CONTENT_TYPES)

    # Content
    content = models.TextField()

    # Additional properties for specific content types
    properties = models.JSONField(default=dict, help_text="Additional properties (e.g., icon_url for push)")

    # Metadata
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['template', 'language', 'content_type']
        ordering = ['template', 'language', 'content_type']

    def __str__(self):
        return f"{self.template.name} - {self.language.code} - {self.get_content_type_display()}"


class TemplateUsageLog(models.Model):
    """
    Log template usage for analytics and optimization
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    template = models.ForeignKey(UnifiedTemplate, on_delete=models.CASCADE, related_name='usage_logs')
    language = models.ForeignKey(TemplateLanguage, on_delete=models.SET_NULL, null=True)

    # Usage details
    channel = models.CharField(max_length=20)
    recipient_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    variables_used = models.JSONField(default=dict)

    # Performance metrics
    render_time_ms = models.PositiveIntegerField(null=True, blank=True)
    success = models.BooleanField(default=True)
    error_message = models.TextField(blank=True)

    # Metadata
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['template', 'channel']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.template.name} - {self.channel} - {self.created_at.date()}"


class NotificationPreference(models.Model):
    """
    User notification preferences for different channels and types
    """
    NOTIFICATION_TYPES = (
        ('appointment_confirmation', 'Appointment Confirmation'),
        ('appointment_reminder', 'Appointment Reminder'),
        ('appointment_cancellation', 'Appointment Cancellation'),
        ('test_results_ready', 'Test Results Ready'),
        ('prescription_ready', 'Prescription Ready'),
        ('payment_confirmation', 'Payment Confirmation'),
        ('payment_reminder', 'Payment Reminder'),
        ('invoice_generated', 'Invoice Generated'),
        ('welcome_message', 'Welcome Message'),
        ('password_reset', 'Password Reset'),
        ('verification_code', 'Verification Code'),
        ('emergency_alert', 'Emergency Alert'),
        ('system_maintenance', 'System Maintenance'),
        ('marketing', 'Marketing Communications'),
        ('newsletter', 'Newsletter'),
        ('survey', 'Survey Requests'),
    )

    CHANNELS = (
        ('email', 'Email'),
        ('sms', 'SMS'),
        ('push', 'Push Notification'),
        ('in_app', 'In-App Notification'),
    )

    FREQUENCY_CHOICES = (
        ('immediate', 'Immediate'),
        ('daily_digest', 'Daily Digest'),
        ('weekly_digest', 'Weekly Digest'),
        ('disabled', 'Disabled'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notification_preferences')

    # Preference settings
    notification_type = models.CharField(max_length=50, choices=NOTIFICATION_TYPES)
    channel = models.CharField(max_length=20, choices=CHANNELS)
    is_enabled = models.BooleanField(default=True)
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES, default='immediate')

    # Time preferences
    quiet_hours_start = models.TimeField(null=True, blank=True, help_text="Start of quiet hours (no notifications)")
    quiet_hours_end = models.TimeField(null=True, blank=True, help_text="End of quiet hours")

    # Language preference
    preferred_language = models.ForeignKey(
        TemplateLanguage,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Preferred language for this notification type"
    )

    # Advanced settings
    priority_threshold = models.CharField(
        max_length=10,
        choices=[
            ('low', 'Low and above'),
            ('normal', 'Normal and above'),
            ('high', 'High and above'),
            ('urgent', 'Urgent only'),
        ],
        default='low',
        help_text="Minimum priority level to receive notifications"
    )

    # Metadata
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['user', 'notification_type', 'channel']
        ordering = ['user', 'notification_type', 'channel']
        indexes = [
            models.Index(fields=['user', 'is_enabled']),
            models.Index(fields=['notification_type', 'channel']),
        ]

    def __str__(self):
        status = "Enabled" if self.is_enabled else "Disabled"
        return f"{self.user.get_full_name()} - {self.get_notification_type_display()} - {self.get_channel_display()} - {status}"


class NotificationSettings(models.Model):
    """
    Global notification settings for users
    """
    TIMEZONE_CHOICES = (
        ('UTC', 'UTC'),
        ('US/Eastern', 'Eastern Time'),
        ('US/Central', 'Central Time'),
        ('US/Mountain', 'Mountain Time'),
        ('US/Pacific', 'Pacific Time'),
        ('Europe/London', 'London'),
        ('Europe/Paris', 'Paris'),
        ('Asia/Tokyo', 'Tokyo'),
        ('Asia/Shanghai', 'Shanghai'),
        ('Australia/Sydney', 'Sydney'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notification_settings'
    )

    # Global settings
    notifications_enabled = models.BooleanField(default=True, help_text="Master notification toggle")
    email_notifications_enabled = models.BooleanField(default=True)
    sms_notifications_enabled = models.BooleanField(default=True)
    push_notifications_enabled = models.BooleanField(default=True)
    in_app_notifications_enabled = models.BooleanField(default=True)

    # Contact information
    primary_email = models.EmailField(blank=True, help_text="Primary email for notifications")
    secondary_email = models.EmailField(blank=True, help_text="Secondary email for important notifications")
    primary_phone = models.CharField(max_length=20, blank=True, help_text="Primary phone for SMS notifications")
    secondary_phone = models.CharField(max_length=20, blank=True, help_text="Secondary phone for emergency notifications")

    # Time and language preferences
    timezone = models.CharField(max_length=50, choices=TIMEZONE_CHOICES, default='UTC')
    default_language = models.ForeignKey(
        TemplateLanguage,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Default language for all notifications"
    )

    # Quiet hours (global)
    global_quiet_hours_enabled = models.BooleanField(default=False)
    global_quiet_hours_start = models.TimeField(null=True, blank=True)
    global_quiet_hours_end = models.TimeField(null=True, blank=True)

    # Weekend and holiday preferences
    weekend_notifications_enabled = models.BooleanField(default=True)
    holiday_notifications_enabled = models.BooleanField(default=True)

    # Digest settings
    daily_digest_enabled = models.BooleanField(default=False)
    daily_digest_time = models.TimeField(null=True, blank=True, help_text="Time to send daily digest")
    weekly_digest_enabled = models.BooleanField(default=False)
    weekly_digest_day = models.CharField(
        max_length=10,
        choices=[
            ('monday', 'Monday'),
            ('tuesday', 'Tuesday'),
            ('wednesday', 'Wednesday'),
            ('thursday', 'Thursday'),
            ('friday', 'Friday'),
            ('saturday', 'Saturday'),
            ('sunday', 'Sunday'),
        ],
        default='monday',
        blank=True
    )
    weekly_digest_time = models.TimeField(null=True, blank=True)

    # Marketing and promotional
    marketing_emails_enabled = models.BooleanField(default=False)
    newsletter_enabled = models.BooleanField(default=False)
    survey_requests_enabled = models.BooleanField(default=True)

    # Advanced settings
    notification_sound_enabled = models.BooleanField(default=True)
    notification_vibration_enabled = models.BooleanField(default=True)
    notification_preview_enabled = models.BooleanField(default=True, help_text="Show notification content in previews")

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Notification Settings"
        verbose_name_plural = "Notification Settings"

    def __str__(self):
        return f"Notification Settings - {self.user.get_full_name()}"


class NotificationBlacklist(models.Model):
    """
    Blacklisted contacts or patterns for notifications
    """
    BLACKLIST_TYPES = (
        ('email', 'Email Address'),
        ('phone', 'Phone Number'),
        ('domain', 'Email Domain'),
        ('keyword', 'Content Keyword'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notification_blacklist'
    )

    # Blacklist details
    blacklist_type = models.CharField(max_length=20, choices=BLACKLIST_TYPES)
    value = models.CharField(max_length=500, help_text="Email, phone, domain, or keyword to blacklist")
    reason = models.TextField(blank=True, help_text="Reason for blacklisting")

    # Settings
    is_active = models.BooleanField(default=True)
    expires_at = models.DateTimeField(null=True, blank=True, help_text="When this blacklist entry expires")

    # Metadata
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['user', 'blacklist_type', 'value']
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['blacklist_type', 'value']),
        ]

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.get_blacklist_type_display()}: {self.value}"


class NotificationSchedule(models.Model):
    """
    Custom notification schedules for users
    """
    SCHEDULE_TYPES = (
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('custom', 'Custom'),
    )

    DAYS_OF_WEEK = (
        ('monday', 'Monday'),
        ('tuesday', 'Tuesday'),
        ('wednesday', 'Wednesday'),
        ('thursday', 'Thursday'),
        ('friday', 'Friday'),
        ('saturday', 'Saturday'),
        ('sunday', 'Sunday'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notification_schedules'
    )

    # Schedule details
    name = models.CharField(max_length=200, help_text="Name for this schedule")
    description = models.TextField(blank=True)
    schedule_type = models.CharField(max_length=20, choices=SCHEDULE_TYPES)

    # Time settings
    start_time = models.TimeField(help_text="Start time for notifications")
    end_time = models.TimeField(help_text="End time for notifications")

    # Day settings
    days_of_week = models.JSONField(
        default=list,
        help_text="List of days when this schedule is active"
    )

    # Date range
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)

    # Notification types this schedule applies to
    notification_types = models.JSONField(
        default=list,
        help_text="List of notification types this schedule applies to"
    )

    # Settings
    is_active = models.BooleanField(default=True)
    priority = models.PositiveIntegerField(default=1, help_text="Schedule priority (higher number = higher priority)")

    # Metadata
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-priority', 'name']
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['schedule_type', 'is_active']),
        ]

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.name} ({self.get_schedule_type_display()})"


class NotificationJob(models.Model):
    """
    Scheduled notification jobs for automated sending
    """
    JOB_TYPES = (
        ('immediate', 'Immediate'),
        ('scheduled', 'Scheduled'),
        ('recurring', 'Recurring'),
        ('delayed', 'Delayed'),
        ('batch', 'Batch'),
    )

    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('queued', 'Queued'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
        ('paused', 'Paused'),
    )

    PRIORITY_CHOICES = (
        ('low', 'Low'),
        ('normal', 'Normal'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job_id = models.CharField(max_length=20, unique=True, help_text="Human-readable job ID")

    # Job details
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    job_type = models.CharField(max_length=20, choices=JOB_TYPES)

    # Notification details
    notification_type = models.CharField(max_length=50)
    channel = models.CharField(max_length=20)
    template_id = models.UUIDField(null=True, blank=True, help_text="Template to use for notifications")

    # Recipients
    recipient_users = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='scheduled_notifications',
        blank=True
    )
    recipient_filter = models.JSONField(
        default=dict,
        help_text="Filter criteria for dynamic recipient selection"
    )

    # Scheduling
    scheduled_at = models.DateTimeField(null=True, blank=True)
    execute_after = models.DateTimeField(null=True, blank=True, help_text="Earliest execution time")
    execute_before = models.DateTimeField(null=True, blank=True, help_text="Latest execution time")

    # Recurring settings
    is_recurring = models.BooleanField(default=False)
    recurrence_pattern = models.JSONField(
        default=dict,
        help_text="Recurrence pattern (daily, weekly, monthly, etc.)"
    )
    next_run_at = models.DateTimeField(null=True, blank=True)
    last_run_at = models.DateTimeField(null=True, blank=True)

    # Batch settings
    batch_size = models.PositiveIntegerField(default=100, help_text="Number of notifications per batch")
    batch_delay = models.PositiveIntegerField(default=60, help_text="Delay between batches in seconds")

    # Job status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='normal')

    # Execution tracking
    attempts = models.PositiveIntegerField(default=0)
    max_attempts = models.PositiveIntegerField(default=3)

    # Results
    total_recipients = models.PositiveIntegerField(default=0)
    successful_sends = models.PositiveIntegerField(default=0)
    failed_sends = models.PositiveIntegerField(default=0)

    # Error handling
    error_message = models.TextField(blank=True)
    error_details = models.JSONField(default=dict, blank=True)

    # Template variables
    template_variables = models.JSONField(default=dict, help_text="Variables to use in template rendering")

    # Metadata
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_notification_jobs'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-priority', 'scheduled_at', 'created_at']
        indexes = [
            models.Index(fields=['status', 'scheduled_at']),
            models.Index(fields=['job_type', 'status']),
            models.Index(fields=['next_run_at']),
        ]

    def __str__(self):
        return f"{self.job_id} - {self.name} ({self.get_status_display()})"

    def save(self, *args, **kwargs):
        if not self.job_id:
            # Generate job ID if not provided
            today = timezone.now().date()
            today_jobs = NotificationJob.objects.filter(
                created_at__date=today
            ).count()
            self.job_id = f'JOB{today.strftime("%Y%m%d")}{today_jobs + 1:04d}'
        super().save(*args, **kwargs)


class NotificationQueue(models.Model):
    """
    Queue for managing notification delivery
    """
    QUEUE_STATUS = (
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('retrying', 'Retrying'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job = models.ForeignKey(NotificationJob, on_delete=models.CASCADE, related_name='queue_items')

    # Recipient details
    recipient_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    recipient_email = models.EmailField(blank=True)
    recipient_phone = models.CharField(max_length=20, blank=True)

    # Notification content
    channel = models.CharField(max_length=20)
    subject = models.CharField(max_length=500, blank=True)
    content = models.TextField()

    # Additional data
    template_variables = models.JSONField(default=dict)
    custom_data = models.JSONField(default=dict)

    # Scheduling
    scheduled_at = models.DateTimeField()
    priority = models.CharField(max_length=10, default='normal')

    # Status tracking
    status = models.CharField(max_length=20, choices=QUEUE_STATUS, default='pending')
    attempts = models.PositiveIntegerField(default=0)
    max_attempts = models.PositiveIntegerField(default=3)

    # Execution tracking
    processed_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)

    # Error handling
    error_message = models.TextField(blank=True)
    retry_after = models.DateTimeField(null=True, blank=True)

    # Provider response
    provider_message_id = models.CharField(max_length=200, blank=True)
    provider_response = models.JSONField(default=dict, blank=True)

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['priority', 'scheduled_at']
        indexes = [
            models.Index(fields=['status', 'scheduled_at']),
            models.Index(fields=['job', 'status']),
            models.Index(fields=['retry_after']),
        ]

    def __str__(self):
        return f"{self.job.job_id} - {self.recipient_user.get_full_name()} - {self.channel}"


class CronJob(models.Model):
    """
    Cron job definitions for recurring notification tasks
    """
    CRON_TYPES = (
        ('notification_reminders', 'Notification Reminders'),
        ('digest_emails', 'Digest Emails'),
        ('cleanup_tasks', 'Cleanup Tasks'),
        ('analytics_reports', 'Analytics Reports'),
        ('system_alerts', 'System Alerts'),
        ('custom', 'Custom Task'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    cron_type = models.CharField(max_length=50, choices=CRON_TYPES)

    # Cron expression
    cron_expression = models.CharField(
        max_length=100,
        help_text="Cron expression (e.g., '0 9 * * *' for daily at 9 AM)"
    )

    # Task configuration
    task_function = models.CharField(max_length=200, help_text="Python function to execute")
    task_parameters = models.JSONField(default=dict, help_text="Parameters to pass to the task")

    # Status
    is_active = models.BooleanField(default=True)
    is_running = models.BooleanField(default=False)

    # Execution tracking
    last_run_at = models.DateTimeField(null=True, blank=True)
    next_run_at = models.DateTimeField(null=True, blank=True)
    run_count = models.PositiveIntegerField(default=0)
    success_count = models.PositiveIntegerField(default=0)
    failure_count = models.PositiveIntegerField(default=0)

    # Error handling
    last_error = models.TextField(blank=True)
    max_failures = models.PositiveIntegerField(default=5, help_text="Max consecutive failures before disabling")
    consecutive_failures = models.PositiveIntegerField(default=0)

    # Timeout settings
    timeout_seconds = models.PositiveIntegerField(default=300, help_text="Task timeout in seconds")

    # Metadata
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['is_active', 'next_run_at']),
            models.Index(fields=['cron_type', 'is_active']),
        ]

    def __str__(self):
        return f"{self.name} ({self.cron_expression})"


class NotificationAnalytics(models.Model):
    """
    Comprehensive notification analytics and reporting
    """
    ANALYTICS_TYPES = (
        ('daily', 'Daily Report'),
        ('weekly', 'Weekly Report'),
        ('monthly', 'Monthly Report'),
        ('custom', 'Custom Period'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Report details
    report_type = models.CharField(max_length=20, choices=ANALYTICS_TYPES)
    start_date = models.DateField()
    end_date = models.DateField()

    # Overall metrics
    total_notifications = models.PositiveIntegerField(default=0)
    total_sent = models.PositiveIntegerField(default=0)
    total_delivered = models.PositiveIntegerField(default=0)
    total_opened = models.PositiveIntegerField(default=0)
    total_clicked = models.PositiveIntegerField(default=0)
    total_failed = models.PositiveIntegerField(default=0)
    total_bounced = models.PositiveIntegerField(default=0)
    total_unsubscribed = models.PositiveIntegerField(default=0)

    # Channel breakdown
    email_metrics = models.JSONField(default=dict, help_text="Email-specific metrics")
    sms_metrics = models.JSONField(default=dict, help_text="SMS-specific metrics")
    push_metrics = models.JSONField(default=dict, help_text="Push notification metrics")

    # Template performance
    template_performance = models.JSONField(default=dict, help_text="Performance by template type")

    # User engagement
    user_engagement = models.JSONField(default=dict, help_text="User engagement metrics")

    # Time-based analytics
    hourly_distribution = models.JSONField(default=dict, help_text="Notifications by hour")
    daily_distribution = models.JSONField(default=dict, help_text="Notifications by day of week")

    # Cost analytics
    total_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    cost_breakdown = models.JSONField(default=dict, help_text="Cost breakdown by channel/provider")

    # Performance metrics
    average_delivery_time = models.FloatField(default=0, help_text="Average delivery time in seconds")
    average_open_time = models.FloatField(default=0, help_text="Average time to open in seconds")

    # Metadata
    generated_at = models.DateTimeField(auto_now_add=True)
    generated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    class Meta:
        ordering = ['-generated_at']
        unique_together = ['report_type', 'start_date', 'end_date']
        indexes = [
            models.Index(fields=['report_type', 'start_date']),
            models.Index(fields=['generated_at']),
        ]

    def __str__(self):
        return f"{self.get_report_type_display()} - {self.start_date} to {self.end_date}"

    @property
    def delivery_rate(self):
        """Calculate delivery rate percentage"""
        if self.total_sent > 0:
            return (self.total_delivered / self.total_sent) * 100
        return 0

    @property
    def open_rate(self):
        """Calculate open rate percentage"""
        if self.total_delivered > 0:
            return (self.total_opened / self.total_delivered) * 100
        return 0

    @property
    def click_rate(self):
        """Calculate click rate percentage"""
        if self.total_opened > 0:
            return (self.total_clicked / self.total_opened) * 100
        return 0

    @property
    def bounce_rate(self):
        """Calculate bounce rate percentage"""
        if self.total_sent > 0:
            return (self.total_bounced / self.total_sent) * 100
        return 0

    @property
    def unsubscribe_rate(self):
        """Calculate unsubscribe rate percentage"""
        if self.total_delivered > 0:
            return (self.total_unsubscribed / self.total_delivered) * 100
        return 0


class NotificationEvent(models.Model):
    """
    Individual notification events for detailed tracking
    """
    EVENT_TYPES = (
        ('created', 'Created'),
        ('queued', 'Queued'),
        ('sent', 'Sent'),
        ('delivered', 'Delivered'),
        ('opened', 'Opened'),
        ('clicked', 'Clicked'),
        ('bounced', 'Bounced'),
        ('failed', 'Failed'),
        ('unsubscribed', 'Unsubscribed'),
        ('complained', 'Complained'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Event details
    event_type = models.CharField(max_length=20, choices=EVENT_TYPES)
    event_timestamp = models.DateTimeField(default=timezone.now)

    # Notification reference
    notification_type = models.CharField(max_length=50)
    notification_channel = models.CharField(max_length=20)
    notification_id = models.UUIDField(help_text="Reference to the actual notification")

    # Recipient details
    recipient_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    recipient_email = models.EmailField(blank=True)
    recipient_phone = models.CharField(max_length=20, blank=True)

    # Event metadata
    user_agent = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    device_type = models.CharField(max_length=50, blank=True)
    location = models.JSONField(default=dict, blank=True, help_text="Geographic location data")

    # Provider details
    provider_name = models.CharField(max_length=100, blank=True)
    provider_message_id = models.CharField(max_length=200, blank=True)
    provider_response = models.JSONField(default=dict, blank=True)

    # Additional data
    event_data = models.JSONField(default=dict, help_text="Additional event-specific data")

    class Meta:
        ordering = ['-event_timestamp']
        indexes = [
            models.Index(fields=['event_type', 'event_timestamp']),
            models.Index(fields=['notification_channel', 'event_type']),
            models.Index(fields=['recipient_user', 'event_type']),
            models.Index(fields=['notification_id']),
        ]

    def __str__(self):
        return f"{self.get_event_type_display()} - {self.notification_channel} - {self.event_timestamp}"


class NotificationCampaign(models.Model):
    """
    Notification campaigns for grouping related notifications
    """
    CAMPAIGN_TYPES = (
        ('promotional', 'Promotional'),
        ('transactional', 'Transactional'),
        ('reminder', 'Reminder'),
        ('announcement', 'Announcement'),
        ('survey', 'Survey'),
        ('newsletter', 'Newsletter'),
        ('emergency', 'Emergency'),
    )

    STATUS_CHOICES = (
        ('draft', 'Draft'),
        ('scheduled', 'Scheduled'),
        ('running', 'Running'),
        ('paused', 'Paused'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campaign_id = models.CharField(max_length=20, unique=True)

    # Campaign details
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    campaign_type = models.CharField(max_length=20, choices=CAMPAIGN_TYPES)

    # Targeting
    target_audience = models.JSONField(default=dict, help_text="Audience targeting criteria")
    estimated_recipients = models.PositiveIntegerField(default=0)

    # Scheduling
    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)

    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')

    # Performance tracking
    total_sent = models.PositiveIntegerField(default=0)
    total_delivered = models.PositiveIntegerField(default=0)
    total_opened = models.PositiveIntegerField(default=0)
    total_clicked = models.PositiveIntegerField(default=0)
    total_conversions = models.PositiveIntegerField(default=0)

    # Cost tracking
    budget = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    actual_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # Metadata
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['campaign_type', 'status']),
            models.Index(fields=['start_date', 'end_date']),
        ]

    def __str__(self):
        return f"{self.campaign_id} - {self.name}"

    def save(self, *args, **kwargs):
        if not self.campaign_id:
            # Generate campaign ID if not provided
            today = timezone.now().date()
            today_campaigns = NotificationCampaign.objects.filter(
                created_at__date=today
            ).count()
            self.campaign_id = f'CAMP{today.strftime("%Y%m%d")}{today_campaigns + 1:04d}'
        super().save(*args, **kwargs)

    @property
    def delivery_rate(self):
        """Calculate delivery rate percentage"""
        if self.total_sent > 0:
            return (self.total_delivered / self.total_sent) * 100
        return 0

    @property
    def open_rate(self):
        """Calculate open rate percentage"""
        if self.total_delivered > 0:
            return (self.total_opened / self.total_delivered) * 100
        return 0

    @property
    def click_rate(self):
        """Calculate click rate percentage"""
        if self.total_opened > 0:
            return (self.total_clicked / self.total_opened) * 100
        return 0

    @property
    def conversion_rate(self):
        """Calculate conversion rate percentage"""
        if self.total_clicked > 0:
            return (self.total_conversions / self.total_clicked) * 100
        return 0

    @property
    def roi(self):
        """Calculate return on investment"""
        if self.actual_cost > 0:
            # This would need to be calculated based on actual business metrics
            return 0  # Placeholder
        return 0
