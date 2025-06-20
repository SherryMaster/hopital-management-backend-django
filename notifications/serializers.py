from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import (
    EmailTemplate, EmailNotification, EmailConfiguration,
    EmailSubscription, EmailAnalytics,
    SMSTemplate, SMSNotification, SMSConfiguration, SMSAnalytics,
    PushNotificationTemplate, PushNotification, PushNotificationConfiguration,
    PushNotificationAnalytics, DeviceToken,
    TemplateVariable, TemplateLanguage, UnifiedTemplate, TemplateContent, TemplateUsageLog,
    NotificationPreference, NotificationSettings, NotificationBlacklist, NotificationSchedule,
    NotificationJob, NotificationQueue, CronJob
)

User = get_user_model()


class EmailTemplateSerializer(serializers.ModelSerializer):
    """
    Serializer for email templates
    """
    template_type_display = serializers.CharField(source='get_template_type_display', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    
    class Meta:
        model = EmailTemplate
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')


class EmailTemplateListSerializer(serializers.ModelSerializer):
    """
    Simplified serializer for email template lists
    """
    template_type_display = serializers.CharField(source='get_template_type_display', read_only=True)
    
    class Meta:
        model = EmailTemplate
        fields = [
            'id', 'name', 'template_type', 'template_type_display', 
            'description', 'is_active', 'is_default', 'created_at'
        ]


class EmailNotificationSerializer(serializers.ModelSerializer):
    """
    Serializer for email notifications
    """
    template_name = serializers.CharField(source='template.name', read_only=True)
    template_type = serializers.CharField(source='template.template_type', read_only=True)
    recipient_name_display = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    
    class Meta:
        model = EmailNotification
        fields = '__all__'
        read_only_fields = (
            'notification_id', 'sent_at', 'delivered_at', 'opened_at', 
            'clicked_at', 'provider_message_id', 'created_at', 'updated_at'
        )
    
    def get_recipient_name_display(self, obj):
        """Get display name for recipient"""
        if obj.recipient_name:
            return obj.recipient_name
        elif obj.recipient_user:
            return obj.recipient_user.get_full_name()
        else:
            return obj.recipient_email


class EmailNotificationListSerializer(serializers.ModelSerializer):
    """
    Simplified serializer for email notification lists
    """
    template_name = serializers.CharField(source='template.name', read_only=True)
    recipient_name_display = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = EmailNotification
        fields = [
            'id', 'notification_id', 'recipient_email', 'recipient_name_display',
            'template_name', 'subject', 'status', 'status_display', 'priority',
            'scheduled_at', 'sent_at', 'created_at'
        ]
    
    def get_recipient_name_display(self, obj):
        """Get display name for recipient"""
        if obj.recipient_name:
            return obj.recipient_name
        elif obj.recipient_user:
            return obj.recipient_user.get_full_name()
        else:
            return obj.recipient_email


class EmailConfigurationSerializer(serializers.ModelSerializer):
    """
    Serializer for email configurations
    """
    provider_type_display = serializers.CharField(source='get_provider_type_display', read_only=True)
    
    class Meta:
        model = EmailConfiguration
        fields = '__all__'
        read_only_fields = (
            'emails_sent_today', 'emails_sent_this_hour', 
            'last_reset_date', 'last_reset_hour', 'created_at', 'updated_at'
        )


class EmailSubscriptionSerializer(serializers.ModelSerializer):
    """
    Serializer for email subscriptions
    """
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    subscription_type_display = serializers.CharField(source='get_subscription_type_display', read_only=True)
    frequency_display = serializers.CharField(source='get_frequency_display', read_only=True)
    
    class Meta:
        model = EmailSubscription
        fields = '__all__'
        read_only_fields = ('subscribed_at', 'unsubscribed_at', 'created_at', 'updated_at')


class EmailAnalyticsSerializer(serializers.ModelSerializer):
    """
    Serializer for email analytics
    """
    delivery_rate = serializers.ReadOnlyField()
    open_rate = serializers.ReadOnlyField()
    click_rate = serializers.ReadOnlyField()
    bounce_rate = serializers.ReadOnlyField()
    
    class Meta:
        model = EmailAnalytics
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')


class SendEmailSerializer(serializers.Serializer):
    """
    Serializer for sending custom emails
    """
    template_type = serializers.ChoiceField(choices=EmailTemplate.TEMPLATE_TYPES)
    recipient_email = serializers.EmailField()
    recipient_name = serializers.CharField(max_length=200, required=False)
    variables = serializers.JSONField()
    priority = serializers.ChoiceField(
        choices=EmailNotification.PRIORITY_CHOICES,
        default='normal'
    )
    scheduled_at = serializers.DateTimeField(required=False)
    
    def validate_variables(self, value):
        """Validate that variables is a dictionary"""
        if not isinstance(value, dict):
            raise serializers.ValidationError("Variables must be a dictionary")
        return value


class BulkEmailSerializer(serializers.Serializer):
    """
    Serializer for sending bulk emails
    """
    template_type = serializers.ChoiceField(choices=EmailTemplate.TEMPLATE_TYPES)
    recipients = serializers.ListField(
        child=serializers.DictField(),
        min_length=1,
        max_length=1000
    )
    priority = serializers.ChoiceField(
        choices=EmailNotification.PRIORITY_CHOICES,
        default='normal'
    )
    scheduled_at = serializers.DateTimeField(required=False)
    
    def validate_recipients(self, value):
        """Validate recipients list"""
        for recipient in value:
            if 'email' not in recipient:
                raise serializers.ValidationError("Each recipient must have an 'email' field")
            if 'variables' not in recipient:
                raise serializers.ValidationError("Each recipient must have a 'variables' field")
            if not isinstance(recipient['variables'], dict):
                raise serializers.ValidationError("Variables must be a dictionary")
        return value


class EmailStatsSerializer(serializers.Serializer):
    """
    Serializer for email statistics
    """
    total_sent = serializers.IntegerField()
    total_delivered = serializers.IntegerField()
    total_opened = serializers.IntegerField()
    total_clicked = serializers.IntegerField()
    total_bounced = serializers.IntegerField()
    total_failed = serializers.IntegerField()
    delivery_rate = serializers.FloatField()
    open_rate = serializers.FloatField()
    click_rate = serializers.FloatField()
    bounce_rate = serializers.FloatField()
    
    # Template breakdown
    template_stats = serializers.DictField()
    
    # Recent activity
    recent_notifications = EmailNotificationListSerializer(many=True)
    
    # Date range
    date_from = serializers.DateField()
    date_to = serializers.DateField()


class EmailTemplatePreviewSerializer(serializers.Serializer):
    """
    Serializer for previewing email templates
    """
    template_id = serializers.UUIDField()
    variables = serializers.JSONField()
    
    def validate_variables(self, value):
        """Validate that variables is a dictionary"""
        if not isinstance(value, dict):
            raise serializers.ValidationError("Variables must be a dictionary")
        return value


class EmailDeliveryStatusSerializer(serializers.Serializer):
    """
    Serializer for email delivery status updates
    """
    notification_id = serializers.CharField()
    status = serializers.ChoiceField(choices=EmailNotification.STATUS_CHOICES)
    provider_message_id = serializers.CharField(required=False)
    provider_response = serializers.JSONField(required=False)
    error_message = serializers.CharField(required=False)
    bounce_reason = serializers.CharField(required=False)
    
    def validate_provider_response(self, value):
        """Validate provider response"""
        if value is not None and not isinstance(value, dict):
            raise serializers.ValidationError("Provider response must be a dictionary")
        return value


# SMS Serializers

class SMSTemplateSerializer(serializers.ModelSerializer):
    """
    Serializer for SMS templates
    """
    template_type_display = serializers.CharField(source='get_template_type_display', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    message_length = serializers.SerializerMethodField()

    class Meta:
        model = SMSTemplate
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')

    def get_message_length(self, obj):
        """Get message template length"""
        return len(obj.message_template)


class SMSNotificationSerializer(serializers.ModelSerializer):
    """
    Serializer for SMS notifications
    """
    template_name = serializers.CharField(source='template.name', read_only=True)
    template_type = serializers.CharField(source='template.template_type', read_only=True)
    recipient_name_display = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    message_length = serializers.SerializerMethodField()

    class Meta:
        model = SMSNotification
        fields = '__all__'
        read_only_fields = (
            'notification_id', 'sent_at', 'delivered_at',
            'provider_message_id', 'cost', 'created_at', 'updated_at'
        )

    def get_recipient_name_display(self, obj):
        """Get display name for recipient"""
        if obj.recipient_name:
            return obj.recipient_name
        elif obj.recipient_user:
            return obj.recipient_user.get_full_name()
        else:
            return obj.recipient_phone

    def get_message_length(self, obj):
        """Get message length"""
        return len(obj.message)


class SendSMSSerializer(serializers.Serializer):
    """
    Serializer for sending custom SMS
    """
    template_type = serializers.ChoiceField(choices=SMSTemplate.TEMPLATE_TYPES)
    recipient_phone = serializers.CharField(max_length=20)
    recipient_name = serializers.CharField(max_length=200, required=False)
    variables = serializers.JSONField()
    priority = serializers.ChoiceField(
        choices=SMSNotification.PRIORITY_CHOICES,
        default='normal'
    )
    scheduled_at = serializers.DateTimeField(required=False)

    def validate_variables(self, value):
        """Validate that variables is a dictionary"""
        if not isinstance(value, dict):
            raise serializers.ValidationError("Variables must be a dictionary")
        return value

    def validate_recipient_phone(self, value):
        """Validate phone number format"""
        # Basic phone number validation
        import re
        phone_pattern = r'^\+?1?\d{9,15}$'
        if not re.match(phone_pattern, value.replace(' ', '').replace('-', '')):
            raise serializers.ValidationError("Invalid phone number format")
        return value


# Push Notification Serializers

class PushNotificationTemplateSerializer(serializers.ModelSerializer):
    """
    Serializer for push notification templates
    """
    template_type_display = serializers.CharField(source='get_template_type_display', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    title_length = serializers.SerializerMethodField()
    body_length = serializers.SerializerMethodField()

    class Meta:
        model = PushNotificationTemplate
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')

    def get_title_length(self, obj):
        """Get title template length"""
        return len(obj.title_template)

    def get_body_length(self, obj):
        """Get body template length"""
        return len(obj.body_template)


class PushNotificationSerializer(serializers.ModelSerializer):
    """
    Serializer for push notifications
    """
    template_name = serializers.CharField(source='template.name', read_only=True)
    template_type = serializers.CharField(source='template.template_type', read_only=True)
    recipient_name = serializers.CharField(source='recipient_user.get_full_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    device_type_display = serializers.CharField(source='get_device_type_display', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)

    class Meta:
        model = PushNotification
        fields = '__all__'
        read_only_fields = (
            'notification_id', 'sent_at', 'delivered_at', 'clicked_at', 'dismissed_at',
            'provider_message_id', 'created_at', 'updated_at'
        )


class SendPushNotificationSerializer(serializers.Serializer):
    """
    Serializer for sending custom push notifications
    """
    template_type = serializers.ChoiceField(choices=PushNotificationTemplate.TEMPLATE_TYPES)
    recipient_user_id = serializers.IntegerField()
    variables = serializers.JSONField()
    device_type = serializers.ChoiceField(
        choices=PushNotification.DEVICE_TYPES,
        default='web'
    )
    priority = serializers.ChoiceField(
        choices=PushNotification.PRIORITY_CHOICES,
        default='normal'
    )
    scheduled_at = serializers.DateTimeField(required=False)
    custom_data = serializers.JSONField(required=False)

    def validate_variables(self, value):
        """Validate that variables is a dictionary"""
        if not isinstance(value, dict):
            raise serializers.ValidationError("Variables must be a dictionary")
        return value

    def validate_custom_data(self, value):
        """Validate custom data"""
        if value is not None and not isinstance(value, dict):
            raise serializers.ValidationError("Custom data must be a dictionary")
        return value


class RegisterDeviceTokenSerializer(serializers.Serializer):
    """
    Serializer for registering device tokens
    """
    device_token = serializers.CharField(max_length=500)
    device_type = serializers.ChoiceField(choices=DeviceToken.DEVICE_TYPES)
    device_name = serializers.CharField(max_length=200, required=False)
    user_agent = serializers.CharField(required=False)

    def validate_device_token(self, value):
        """Validate device token format"""
        if len(value) < 10:
            raise serializers.ValidationError("Device token too short")
        return value


# Template Management Serializers

class TemplateVariableSerializer(serializers.ModelSerializer):
    """
    Serializer for template variables
    """
    variable_type_display = serializers.CharField(source='get_variable_type_display', read_only=True)
    format_type_display = serializers.CharField(source='get_format_type_display', read_only=True)

    class Meta:
        model = TemplateVariable
        fields = '__all__'
        read_only_fields = ('usage_count', 'created_at', 'updated_at')


class TemplateLanguageSerializer(serializers.ModelSerializer):
    """
    Serializer for template languages
    """
    text_direction_display = serializers.CharField(source='get_text_direction_display', read_only=True)

    class Meta:
        model = TemplateLanguage
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')


class UnifiedTemplateSerializer(serializers.ModelSerializer):
    """
    Serializer for unified templates
    """
    template_type_display = serializers.CharField(source='get_template_type_display', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    variable_count = serializers.SerializerMethodField()
    content_count = serializers.SerializerMethodField()

    class Meta:
        model = UnifiedTemplate
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')

    def get_variable_count(self, obj):
        """Get number of variables"""
        return obj.variables.count()

    def get_content_count(self, obj):
        """Get number of content items"""
        return obj.content.count()


class CreateUnifiedTemplateSerializer(serializers.Serializer):
    """
    Serializer for creating unified templates
    """
    name = serializers.CharField(max_length=200)
    template_type = serializers.ChoiceField(choices=UnifiedTemplate.TEMPLATE_TYPES)
    description = serializers.CharField(required=False)
    supported_channels = serializers.ListField(
        child=serializers.CharField(),
        min_length=1
    )
    variables = serializers.ListField(
        child=serializers.CharField(),
        required=False
    )
    content_data = serializers.JSONField()

    def validate_supported_channels(self, value):
        """Validate supported channels"""
        valid_channels = ['email', 'sms', 'push']
        for channel in value:
            if channel not in valid_channels:
                raise serializers.ValidationError(f"Invalid channel: {channel}")
        return value

    def validate_content_data(self, value):
        """Validate content data structure"""
        if not isinstance(value, dict):
            raise serializers.ValidationError("Content data must be a dictionary")

        # Check that each language has proper content types
        for lang_code, content_dict in value.items():
            if not isinstance(content_dict, dict):
                raise serializers.ValidationError(f"Content for {lang_code} must be a dictionary")

        return value


class RenderTemplateSerializer(serializers.Serializer):
    """
    Serializer for rendering templates
    """
    template_id = serializers.UUIDField()
    channel = serializers.ChoiceField(choices=['email', 'sms', 'push'])
    language_code = serializers.CharField(max_length=10, default='en')
    variables = serializers.JSONField()

    def validate_variables(self, value):
        """Validate variables"""
        if not isinstance(value, dict):
            raise serializers.ValidationError("Variables must be a dictionary")
        return value


# Notification Preferences Serializers

class NotificationPreferenceSerializer(serializers.ModelSerializer):
    """
    Serializer for notification preferences
    """
    notification_type_display = serializers.CharField(source='get_notification_type_display', read_only=True)
    channel_display = serializers.CharField(source='get_channel_display', read_only=True)
    frequency_display = serializers.CharField(source='get_frequency_display', read_only=True)
    priority_threshold_display = serializers.CharField(source='get_priority_threshold_display', read_only=True)
    language_name = serializers.CharField(source='preferred_language.name', read_only=True)

    class Meta:
        model = NotificationPreference
        fields = '__all__'
        read_only_fields = ('user', 'created_at', 'updated_at')


class NotificationSettingsSerializer(serializers.ModelSerializer):
    """
    Serializer for notification settings
    """
    timezone_display = serializers.CharField(source='get_timezone_display', read_only=True)
    default_language_name = serializers.CharField(source='default_language.name', read_only=True)
    weekly_digest_day_display = serializers.CharField(source='get_weekly_digest_day_display', read_only=True)

    class Meta:
        model = NotificationSettings
        fields = '__all__'
        read_only_fields = ('user', 'created_at', 'updated_at')


class UpdatePreferencesSerializer(serializers.Serializer):
    """
    Serializer for bulk updating notification preferences
    """
    preferences = serializers.ListField(
        child=serializers.DictField(),
        min_length=1
    )

    def validate_preferences(self, value):
        """Validate preferences data"""
        for pref in value:
            required_fields = ['notification_type', 'channel', 'is_enabled']
            for field in required_fields:
                if field not in pref:
                    raise serializers.ValidationError(f"Missing required field: {field}")
        return value


class PreferenceCheckSerializer(serializers.Serializer):
    """
    Serializer for checking notification preferences
    """
    notification_type = serializers.ChoiceField(choices=NotificationPreference.NOTIFICATION_TYPES)
    channel = serializers.ChoiceField(choices=NotificationPreference.CHANNELS)
    priority = serializers.ChoiceField(
        choices=[('low', 'Low'), ('normal', 'Normal'), ('high', 'High'), ('urgent', 'Urgent')],
        default='normal'
    )
    contact_info = serializers.CharField(required=False, help_text="Email or phone to check against blacklist")


# Notification Scheduling Serializers

class NotificationJobSerializer(serializers.ModelSerializer):
    """
    Serializer for notification jobs
    """
    job_type_display = serializers.CharField(source='get_job_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    recipient_count = serializers.SerializerMethodField()
    success_rate = serializers.SerializerMethodField()

    class Meta:
        model = NotificationJob
        fields = '__all__'
        read_only_fields = (
            'job_id', 'total_recipients', 'successful_sends', 'failed_sends',
            'started_at', 'completed_at', 'created_at', 'updated_at'
        )

    def get_recipient_count(self, obj):
        """Get number of recipients"""
        return obj.recipient_users.count()

    def get_success_rate(self, obj):
        """Calculate success rate"""
        if obj.total_recipients > 0:
            return (obj.successful_sends / obj.total_recipients) * 100
        return 0


class NotificationQueueSerializer(serializers.ModelSerializer):
    """
    Serializer for notification queue items
    """
    job_name = serializers.CharField(source='job.name', read_only=True)
    recipient_name = serializers.CharField(source='recipient_user.get_full_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = NotificationQueue
        fields = '__all__'
        read_only_fields = (
            'processed_at', 'sent_at', 'delivered_at', 'provider_message_id',
            'created_at', 'updated_at'
        )


class CronJobSerializer(serializers.ModelSerializer):
    """
    Serializer for cron jobs
    """
    cron_type_display = serializers.CharField(source='get_cron_type_display', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    success_rate = serializers.SerializerMethodField()
    is_overdue = serializers.SerializerMethodField()

    class Meta:
        model = CronJob
        fields = '__all__'
        read_only_fields = (
            'last_run_at', 'next_run_at', 'run_count', 'success_count',
            'failure_count', 'consecutive_failures', 'created_at', 'updated_at'
        )

    def get_success_rate(self, obj):
        """Calculate success rate"""
        if obj.run_count > 0:
            return (obj.success_count / obj.run_count) * 100
        return 0

    def get_is_overdue(self, obj):
        """Check if cron job is overdue"""
        if obj.next_run_at:
            from django.utils import timezone
            return obj.next_run_at < timezone.now()
        return False


class CreateScheduledJobSerializer(serializers.Serializer):
    """
    Serializer for creating scheduled notification jobs
    """
    name = serializers.CharField(max_length=200)
    notification_type = serializers.CharField(max_length=50)
    channel = serializers.ChoiceField(choices=[
        ('email', 'Email'),
        ('sms', 'SMS'),
        ('push', 'Push Notification'),
    ])
    recipient_user_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False
    )
    recipient_filter = serializers.JSONField(required=False)
    template_variables = serializers.JSONField(required=False)
    scheduled_at = serializers.DateTimeField(required=False)
    job_type = serializers.ChoiceField(
        choices=NotificationJob.JOB_TYPES,
        default='scheduled'
    )
    priority = serializers.ChoiceField(
        choices=NotificationJob.PRIORITY_CHOICES,
        default='normal'
    )

    def validate(self, data):
        """Validate that either recipient_user_ids or recipient_filter is provided"""
        if not data.get('recipient_user_ids') and not data.get('recipient_filter'):
            raise serializers.ValidationError(
                "Either recipient_user_ids or recipient_filter must be provided"
            )
        return data


class CreateRecurringJobSerializer(serializers.Serializer):
    """
    Serializer for creating recurring notification jobs
    """
    name = serializers.CharField(max_length=200)
    notification_type = serializers.CharField(max_length=50)
    channel = serializers.ChoiceField(choices=[
        ('email', 'Email'),
        ('sms', 'SMS'),
        ('push', 'Push Notification'),
    ])
    recurrence_pattern = serializers.JSONField()
    recipient_user_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False
    )
    recipient_filter = serializers.JSONField(required=False)
    template_variables = serializers.JSONField(required=False)
    start_date = serializers.DateTimeField(required=False)

    def validate_recurrence_pattern(self, value):
        """Validate recurrence pattern"""
        required_fields = ['type']
        for field in required_fields:
            if field not in value:
                raise serializers.ValidationError(f"Missing required field in recurrence_pattern: {field}")

        valid_types = ['daily', 'weekly', 'monthly', 'hourly']
        if value['type'] not in valid_types:
            raise serializers.ValidationError(f"Invalid recurrence type. Must be one of: {valid_types}")

        return value


class CreateBatchJobSerializer(serializers.Serializer):
    """
    Serializer for creating batch notification jobs
    """
    name = serializers.CharField(max_length=200)
    notification_type = serializers.CharField(max_length=50)
    channel = serializers.ChoiceField(choices=[
        ('email', 'Email'),
        ('sms', 'SMS'),
        ('push', 'Push Notification'),
    ])
    recipient_user_ids = serializers.ListField(
        child=serializers.IntegerField(),
        min_length=1
    )
    template_variables = serializers.JSONField(required=False)
    batch_size = serializers.IntegerField(min_value=1, max_value=1000, default=100)
    batch_delay = serializers.IntegerField(min_value=1, max_value=3600, default=60)
    scheduled_at = serializers.DateTimeField(required=False)


class JobControlSerializer(serializers.Serializer):
    """
    Serializer for job control operations (cancel, pause, resume)
    """
    job_id = serializers.CharField(max_length=20)
    action = serializers.ChoiceField(choices=[
        ('cancel', 'Cancel'),
        ('pause', 'Pause'),
        ('resume', 'Resume'),
    ])
