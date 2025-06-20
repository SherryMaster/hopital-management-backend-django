import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import Dict, List, Optional, Any
from decimal import Decimal
from django.conf import settings
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template import Template, Context
from django.utils import timezone
from django.db import models
from .models import (
    EmailTemplate, EmailNotification, EmailConfiguration, EmailAnalytics,
    SMSTemplate, SMSNotification, SMSConfiguration, SMSAnalytics,
    PushNotificationTemplate, PushNotification, PushNotificationConfiguration,
    PushNotificationAnalytics, DeviceToken,
    TemplateVariable, TemplateLanguage, UnifiedTemplate, TemplateContent, TemplateUsageLog,
    NotificationPreference, NotificationSettings, NotificationBlacklist, NotificationSchedule,
    NotificationJob, NotificationQueue, CronJob,
    NotificationAnalytics, NotificationEvent, NotificationCampaign
)

logger = logging.getLogger(__name__)


class EmailTemplateService:
    """
    Service for managing email templates
    """
    
    @staticmethod
    def render_template(template: EmailTemplate, variables: Dict[str, Any]) -> Dict[str, str]:
        """
        Render email template with provided variables
        """
        try:
            # Create Django template objects
            subject_template = Template(template.subject_template)
            html_template = Template(template.html_template)
            text_template = Template(template.text_template)
            
            # Create context
            context = Context(variables)
            
            # Render templates
            rendered_subject = subject_template.render(context)
            rendered_html = html_template.render(context)
            rendered_text = text_template.render(context)
            
            return {
                'subject': rendered_subject,
                'html_content': rendered_html,
                'text_content': rendered_text
            }
        except Exception as e:
            logger.error(f"Error rendering template {template.id}: {str(e)}")
            raise
    
    @staticmethod
    def get_default_template(template_type: str) -> Optional[EmailTemplate]:
        """
        Get default template for a specific type
        """
        try:
            return EmailTemplate.objects.filter(
                template_type=template_type,
                is_default=True,
                is_active=True
            ).first()
        except EmailTemplate.DoesNotExist:
            return None
    
    @staticmethod
    def validate_variables(template: EmailTemplate, variables: Dict[str, Any]) -> List[str]:
        """
        Validate that all required variables are provided
        """
        missing_variables = []
        for required_var in template.available_variables:
            if required_var not in variables:
                missing_variables.append(required_var)
        return missing_variables


class EmailDeliveryService:
    """
    Service for delivering emails through various providers
    """
    
    def __init__(self, configuration: Optional[EmailConfiguration] = None):
        self.configuration = configuration or self._get_default_configuration()
    
    def _get_default_configuration(self) -> Optional[EmailConfiguration]:
        """Get default email configuration"""
        return EmailConfiguration.objects.filter(
            is_default=True,
            is_active=True
        ).first()
    
    def send_email(self, notification: EmailNotification) -> bool:
        """
        Send email notification
        """
        try:
            # Check rate limits
            if not self._check_rate_limits():
                logger.warning("Rate limit exceeded for email sending")
                return False
            
            # Update notification status
            notification.status = 'sending'
            notification.attempts += 1
            notification.save()
            
            # Send email based on provider type
            success = False
            if self.configuration.provider_type == 'smtp':
                success = self._send_via_smtp(notification)
            elif self.configuration.provider_type == 'sendgrid':
                success = self._send_via_sendgrid(notification)
            elif self.configuration.provider_type == 'ses':
                success = self._send_via_ses(notification)
            else:
                # Fallback to Django's default email backend
                success = self._send_via_django(notification)
            
            # Update notification status
            if success:
                notification.status = 'sent'
                notification.sent_at = timezone.now()
                self._update_rate_limits()
            else:
                notification.status = 'failed'
                notification.error_message = "Failed to send email"
            
            notification.save()
            return success
            
        except Exception as e:
            logger.error(f"Error sending email {notification.id}: {str(e)}")
            notification.status = 'failed'
            notification.error_message = str(e)
            notification.save()
            return False
    
    def _check_rate_limits(self) -> bool:
        """Check if rate limits allow sending"""
        if not self.configuration:
            return True
        
        # Check daily limit
        if self.configuration.daily_limit:
            if self.configuration.emails_sent_today >= self.configuration.daily_limit:
                return False
        
        # Check hourly limit
        if self.configuration.hourly_limit:
            if self.configuration.emails_sent_this_hour >= self.configuration.hourly_limit:
                return False
        
        return True
    
    def _update_rate_limits(self):
        """Update rate limit counters"""
        if not self.configuration:
            return
        
        now = timezone.now()
        today = now.date()
        
        # Reset daily counter if new day
        if self.configuration.last_reset_date < today:
            self.configuration.emails_sent_today = 0
            self.configuration.last_reset_date = today
        
        # Reset hourly counter if new hour
        if self.configuration.last_reset_hour.hour != now.hour:
            self.configuration.emails_sent_this_hour = 0
            self.configuration.last_reset_hour = now
        
        # Increment counters
        self.configuration.emails_sent_today += 1
        self.configuration.emails_sent_this_hour += 1
        self.configuration.save()
    
    def _send_via_django(self, notification: EmailNotification) -> bool:
        """Send email using Django's default email backend"""
        try:
            msg = EmailMultiAlternatives(
                subject=notification.subject,
                body=notification.text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[notification.recipient_email]
            )
            
            if notification.html_content:
                msg.attach_alternative(notification.html_content, "text/html")
            
            msg.send()
            return True
        except Exception as e:
            logger.error(f"Django email send failed: {str(e)}")
            return False
    
    def _send_via_smtp(self, notification: EmailNotification) -> bool:
        """Send email via SMTP"""
        try:
            config = self.configuration.configuration
            
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = notification.subject
            msg['From'] = config.get('from_email', settings.DEFAULT_FROM_EMAIL)
            msg['To'] = notification.recipient_email
            
            # Add text and HTML parts
            text_part = MIMEText(notification.text_content, 'plain')
            html_part = MIMEText(notification.html_content, 'html')
            
            msg.attach(text_part)
            msg.attach(html_part)
            
            # Send email
            server = smtplib.SMTP(config['host'], config['port'])
            if config.get('use_tls', True):
                server.starttls()
            if config.get('username') and config.get('password'):
                server.login(config['username'], config['password'])
            
            server.send_message(msg)
            server.quit()
            
            return True
        except Exception as e:
            logger.error(f"SMTP email send failed: {str(e)}")
            return False
    
    def _send_via_sendgrid(self, notification: EmailNotification) -> bool:
        """Send email via SendGrid API"""
        try:
            # This would integrate with SendGrid's Python SDK
            # For now, return True as placeholder
            logger.info(f"SendGrid email send for {notification.recipient_email}")
            return True
        except Exception as e:
            logger.error(f"SendGrid email send failed: {str(e)}")
            return False
    
    def _send_via_ses(self, notification: EmailNotification) -> bool:
        """Send email via Amazon SES"""
        try:
            # This would integrate with boto3 for SES
            # For now, return True as placeholder
            logger.info(f"SES email send for {notification.recipient_email}")
            return True
        except Exception as e:
            logger.error(f"SES email send failed: {str(e)}")
            return False


class EmailNotificationService:
    """
    High-level service for creating and sending email notifications
    """
    
    def __init__(self):
        self.template_service = EmailTemplateService()
        self.delivery_service = EmailDeliveryService()
    
    def send_notification(
        self,
        template_type: str,
        recipient_email: str,
        variables: Dict[str, Any],
        recipient_user=None,
        priority='normal',
        scheduled_at=None
    ) -> EmailNotification:
        """
        Create and send email notification
        """
        # Get template
        template = self.template_service.get_default_template(template_type)
        if not template:
            raise ValueError(f"No default template found for type: {template_type}")
        
        # Validate variables
        missing_vars = self.template_service.validate_variables(template, variables)
        if missing_vars:
            raise ValueError(f"Missing required variables: {missing_vars}")
        
        # Render template
        rendered_content = self.template_service.render_template(template, variables)
        
        # Create notification
        notification = EmailNotification.objects.create(
            template=template,
            recipient_email=recipient_email,
            recipient_user=recipient_user,
            subject=rendered_content['subject'],
            html_content=rendered_content['html_content'],
            text_content=rendered_content['text_content'],
            template_variables=variables,
            priority=priority,
            scheduled_at=scheduled_at
        )
        
        # Send immediately if not scheduled
        if not scheduled_at:
            self.delivery_service.send_email(notification)
        
        return notification
    
    def send_appointment_confirmation(self, appointment, recipient_email: str):
        """Send appointment confirmation email"""
        variables = {
            'patient_name': appointment.patient.user.get_full_name(),
            'doctor_name': appointment.doctor.user.get_full_name(),
            'appointment_date': appointment.appointment_date.strftime('%B %d, %Y'),
            'appointment_time': appointment.appointment_time.strftime('%I:%M %p'),
            'department': appointment.doctor.department.name if appointment.doctor.department else 'General',
            'hospital_name': 'Hospital Management System',
            'appointment_id': str(appointment.id)
        }
        
        return self.send_notification(
            template_type='appointment_confirmation',
            recipient_email=recipient_email,
            variables=variables,
            recipient_user=appointment.patient.user
        )
    
    def send_payment_confirmation(self, payment, recipient_email: str):
        """Send payment confirmation email"""
        variables = {
            'patient_name': payment.invoice.patient.user.get_full_name(),
            'payment_amount': str(payment.amount),
            'payment_date': payment.payment_date.strftime('%B %d, %Y'),
            'payment_method': payment.get_payment_method_display(),
            'invoice_number': payment.invoice.invoice_number,
            'transaction_id': payment.transaction_id,
            'hospital_name': 'Hospital Management System'
        }
        
        return self.send_notification(
            template_type='payment_confirmation',
            recipient_email=recipient_email,
            variables=variables,
            recipient_user=payment.invoice.patient.user
        )


class SMSTemplateService:
    """
    Service for managing SMS templates
    """

    @staticmethod
    def render_template(template: SMSTemplate, variables: Dict[str, Any]) -> str:
        """
        Render SMS template with provided variables
        """
        try:
            # Create Django template object
            message_template = Template(template.message_template)

            # Create context
            context = Context(variables)

            # Render template
            rendered_message = message_template.render(context)

            # Check length limit
            if len(rendered_message) > template.max_length:
                logger.warning(f"SMS message exceeds max length: {len(rendered_message)} > {template.max_length}")

            return rendered_message
        except Exception as e:
            logger.error(f"Error rendering SMS template {template.id}: {str(e)}")
            raise

    @staticmethod
    def get_default_template(template_type: str) -> Optional[SMSTemplate]:
        """
        Get default SMS template for a specific type
        """
        try:
            return SMSTemplate.objects.filter(
                template_type=template_type,
                is_default=True,
                is_active=True
            ).first()
        except SMSTemplate.DoesNotExist:
            return None

    @staticmethod
    def validate_variables(template: SMSTemplate, variables: Dict[str, Any]) -> List[str]:
        """
        Validate that all required variables are provided
        """
        missing_variables = []
        for required_var in template.available_variables:
            if required_var not in variables:
                missing_variables.append(required_var)
        return missing_variables


class SMSDeliveryService:
    """
    Service for delivering SMS through various providers
    """

    def __init__(self, configuration: Optional[SMSConfiguration] = None):
        self.configuration = configuration or self._get_default_configuration()

    def _get_default_configuration(self) -> Optional[SMSConfiguration]:
        """Get default SMS configuration"""
        return SMSConfiguration.objects.filter(
            is_default=True,
            is_active=True
        ).first()

    def send_sms(self, notification: SMSNotification) -> bool:
        """
        Send SMS notification
        """
        try:
            # Check rate limits
            if not self._check_rate_limits():
                logger.warning("Rate limit exceeded for SMS sending")
                return False

            # Update notification status
            notification.status = 'sending'
            notification.attempts += 1
            notification.save()

            # Send SMS based on provider type
            success = False
            if self.configuration and self.configuration.provider_type == 'twilio':
                success = self._send_via_twilio(notification)
            elif self.configuration and self.configuration.provider_type == 'aws_sns':
                success = self._send_via_aws_sns(notification)
            elif self.configuration and self.configuration.provider_type == 'nexmo':
                success = self._send_via_nexmo(notification)
            else:
                # Mock provider for testing
                success = self._send_via_mock(notification)

            # Update notification status
            if success:
                notification.status = 'sent'
                notification.sent_at = timezone.now()
                self._update_rate_limits()
                self._update_cost_tracking(notification)
            else:
                notification.status = 'failed'
                notification.error_message = "Failed to send SMS"

            notification.save()
            return success

        except Exception as e:
            logger.error(f"Error sending SMS {notification.id}: {str(e)}")
            notification.status = 'failed'
            notification.error_message = str(e)
            notification.save()
            return False

    def _check_rate_limits(self) -> bool:
        """Check if rate limits allow sending"""
        if not self.configuration:
            return True

        # Check daily limit
        if self.configuration.daily_limit:
            if self.configuration.sms_sent_today >= self.configuration.daily_limit:
                return False

        # Check hourly limit
        if self.configuration.hourly_limit:
            if self.configuration.sms_sent_this_hour >= self.configuration.hourly_limit:
                return False

        return True

    def _update_rate_limits(self):
        """Update rate limit counters"""
        if not self.configuration:
            return

        now = timezone.now()
        today = now.date()

        # Reset daily counter if new day
        if self.configuration.last_reset_date < today:
            self.configuration.sms_sent_today = 0
            self.configuration.total_cost_today = Decimal('0.00')
            self.configuration.last_reset_date = today

        # Reset hourly counter if new hour
        if self.configuration.last_reset_hour.hour != now.hour:
            self.configuration.sms_sent_this_hour = 0
            self.configuration.last_reset_hour = now

        # Increment counters
        self.configuration.sms_sent_today += 1
        self.configuration.sms_sent_this_hour += 1
        self.configuration.save()

    def _update_cost_tracking(self, notification: SMSNotification):
        """Update cost tracking"""
        if self.configuration and self.configuration.cost_per_sms:
            cost = self.configuration.cost_per_sms
            notification.cost = cost
            notification.currency = self.configuration.currency

            # Update daily cost
            self.configuration.total_cost_today += cost
            self.configuration.save()

    def _send_via_twilio(self, notification: SMSNotification) -> bool:
        """Send SMS via Twilio"""
        try:
            # This would integrate with Twilio's Python SDK
            config = self.configuration.configuration

            # Mock Twilio integration
            logger.info(f"Twilio SMS send to {notification.recipient_phone}: {notification.message[:50]}...")

            # Simulate provider response
            notification.provider_message_id = f"twilio_{timezone.now().timestamp()}"
            notification.provider_response = {
                'status': 'sent',
                'provider': 'twilio',
                'message_id': notification.provider_message_id
            }

            return True
        except Exception as e:
            logger.error(f"Twilio SMS send failed: {str(e)}")
            return False

    def _send_via_aws_sns(self, notification: SMSNotification) -> bool:
        """Send SMS via Amazon SNS"""
        try:
            # This would integrate with boto3 for SNS
            logger.info(f"AWS SNS SMS send to {notification.recipient_phone}: {notification.message[:50]}...")

            # Simulate provider response
            notification.provider_message_id = f"sns_{timezone.now().timestamp()}"
            notification.provider_response = {
                'status': 'sent',
                'provider': 'aws_sns',
                'message_id': notification.provider_message_id
            }

            return True
        except Exception as e:
            logger.error(f"AWS SNS SMS send failed: {str(e)}")
            return False

    def _send_via_nexmo(self, notification: SMSNotification) -> bool:
        """Send SMS via Nexmo/Vonage"""
        try:
            # This would integrate with Nexmo's Python SDK
            logger.info(f"Nexmo SMS send to {notification.recipient_phone}: {notification.message[:50]}...")

            # Simulate provider response
            notification.provider_message_id = f"nexmo_{timezone.now().timestamp()}"
            notification.provider_response = {
                'status': 'sent',
                'provider': 'nexmo',
                'message_id': notification.provider_message_id
            }

            return True
        except Exception as e:
            logger.error(f"Nexmo SMS send failed: {str(e)}")
            return False

    def _send_via_mock(self, notification: SMSNotification) -> bool:
        """Send SMS via mock provider (for testing)"""
        try:
            logger.info(f"Mock SMS send to {notification.recipient_phone}: {notification.message}")

            # Simulate provider response
            notification.provider_message_id = f"mock_{timezone.now().timestamp()}"
            notification.provider_response = {
                'status': 'sent',
                'provider': 'mock',
                'message_id': notification.provider_message_id,
                'message': notification.message
            }

            return True
        except Exception as e:
            logger.error(f"Mock SMS send failed: {str(e)}")
            return False


class SMSNotificationService:
    """
    High-level service for creating and sending SMS notifications
    """

    def __init__(self):
        self.template_service = SMSTemplateService()
        self.delivery_service = SMSDeliveryService()

    def send_notification(
        self,
        template_type: str,
        recipient_phone: str,
        variables: Dict[str, Any],
        recipient_user=None,
        priority='normal',
        scheduled_at=None
    ) -> SMSNotification:
        """
        Create and send SMS notification
        """
        # Get template
        template = self.template_service.get_default_template(template_type)
        if not template:
            raise ValueError(f"No default template found for type: {template_type}")

        # Validate variables
        missing_vars = self.template_service.validate_variables(template, variables)
        if missing_vars:
            raise ValueError(f"Missing required variables: {missing_vars}")

        # Render template
        rendered_message = self.template_service.render_template(template, variables)

        # Create notification
        notification = SMSNotification.objects.create(
            template=template,
            recipient_phone=recipient_phone,
            recipient_user=recipient_user,
            message=rendered_message,
            template_variables=variables,
            priority=priority,
            scheduled_at=scheduled_at
        )

        # Send immediately if not scheduled
        if not scheduled_at:
            self.delivery_service.send_sms(notification)

        return notification

    def send_appointment_reminder(self, appointment, recipient_phone: str):
        """Send appointment reminder SMS"""
        variables = {
            'patient_name': appointment.patient.user.first_name,
            'doctor_name': appointment.doctor.user.get_full_name(),
            'appointment_date': appointment.appointment_date.strftime('%m/%d/%Y'),
            'appointment_time': appointment.appointment_time.strftime('%I:%M %p'),
            'hospital_name': 'City Hospital'
        }

        return self.send_notification(
            template_type='appointment_reminder',
            recipient_phone=recipient_phone,
            variables=variables,
            recipient_user=appointment.patient.user
        )

    def send_verification_code(self, user, phone_number: str, code: str):
        """Send verification code SMS"""
        variables = {
            'user_name': user.first_name,
            'verification_code': code,
            'hospital_name': 'City Hospital'
        }

        return self.send_notification(
            template_type='verification_code',
            recipient_phone=phone_number,
            variables=variables,
            recipient_user=user,
            priority='high'
        )


class PushNotificationTemplateService:
    """
    Service for managing push notification templates
    """

    @staticmethod
    def render_template(template: PushNotificationTemplate, variables: Dict[str, Any]) -> Dict[str, str]:
        """
        Render push notification template with provided variables
        """
        try:
            # Create Django template objects
            title_template = Template(template.title_template)
            body_template = Template(template.body_template)

            # Create context
            context = Context(variables)

            # Render templates
            rendered_title = title_template.render(context)
            rendered_body = body_template.render(context)

            return {
                'title': rendered_title,
                'body': rendered_body,
                'icon_url': template.icon_url,
                'image_url': template.image_url,
                'action_url': template.action_url
            }
        except Exception as e:
            logger.error(f"Error rendering push template {template.id}: {str(e)}")
            raise

    @staticmethod
    def get_default_template(template_type: str) -> Optional[PushNotificationTemplate]:
        """
        Get default push notification template for a specific type
        """
        try:
            return PushNotificationTemplate.objects.filter(
                template_type=template_type,
                is_default=True,
                is_active=True
            ).first()
        except PushNotificationTemplate.DoesNotExist:
            return None

    @staticmethod
    def validate_variables(template: PushNotificationTemplate, variables: Dict[str, Any]) -> List[str]:
        """
        Validate that all required variables are provided
        """
        missing_variables = []
        for required_var in template.available_variables:
            if required_var not in variables:
                missing_variables.append(required_var)
        return missing_variables


class PushNotificationDeliveryService:
    """
    Service for delivering push notifications through various providers
    """

    def __init__(self, configuration: Optional[PushNotificationConfiguration] = None):
        self.configuration = configuration or self._get_default_configuration()

    def _get_default_configuration(self) -> Optional[PushNotificationConfiguration]:
        """Get default push notification configuration"""
        return PushNotificationConfiguration.objects.filter(
            is_default=True,
            is_active=True
        ).first()

    def send_push_notification(self, notification: PushNotification) -> bool:
        """
        Send push notification
        """
        try:
            # Check rate limits
            if not self._check_rate_limits():
                logger.warning("Rate limit exceeded for push notification sending")
                return False

            # Update notification status
            notification.status = 'sending'
            notification.attempts += 1
            notification.save()

            # Send push notification based on provider type
            success = False
            if self.configuration and self.configuration.provider_type == 'fcm':
                success = self._send_via_fcm(notification)
            elif self.configuration and self.configuration.provider_type == 'apns':
                success = self._send_via_apns(notification)
            elif self.configuration and self.configuration.provider_type == 'web_push':
                success = self._send_via_web_push(notification)
            elif self.configuration and self.configuration.provider_type == 'websocket':
                success = self._send_via_websocket(notification)
            else:
                # Mock provider for testing
                success = self._send_via_mock(notification)

            # Update notification status
            if success:
                notification.status = 'sent'
                notification.sent_at = timezone.now()
                self._update_rate_limits()
            else:
                notification.status = 'failed'
                notification.error_message = "Failed to send push notification"

            notification.save()
            return success

        except Exception as e:
            logger.error(f"Error sending push notification {notification.id}: {str(e)}")
            notification.status = 'failed'
            notification.error_message = str(e)
            notification.save()
            return False

    def _check_rate_limits(self) -> bool:
        """Check if rate limits allow sending"""
        if not self.configuration:
            return True

        # Check daily limit
        if self.configuration.daily_limit:
            if self.configuration.notifications_sent_today >= self.configuration.daily_limit:
                return False

        # Check hourly limit
        if self.configuration.hourly_limit:
            if self.configuration.notifications_sent_this_hour >= self.configuration.hourly_limit:
                return False

        return True

    def _update_rate_limits(self):
        """Update rate limit counters"""
        if not self.configuration:
            return

        now = timezone.now()
        today = now.date()

        # Reset daily counter if new day
        if self.configuration.last_reset_date < today:
            self.configuration.notifications_sent_today = 0
            self.configuration.last_reset_date = today

        # Reset hourly counter if new hour
        if self.configuration.last_reset_hour.hour != now.hour:
            self.configuration.notifications_sent_this_hour = 0
            self.configuration.last_reset_hour = now

        # Increment counters
        self.configuration.notifications_sent_today += 1
        self.configuration.notifications_sent_this_hour += 1
        self.configuration.save()

    def _send_via_fcm(self, notification: PushNotification) -> bool:
        """Send push notification via Firebase Cloud Messaging"""
        try:
            # This would integrate with Firebase Admin SDK
            logger.info(f"FCM push notification to {notification.recipient_user.get_full_name()}: {notification.title}")

            # Simulate provider response
            notification.provider_message_id = f"fcm_{timezone.now().timestamp()}"
            notification.provider_response = {
                'status': 'sent',
                'provider': 'fcm',
                'message_id': notification.provider_message_id
            }

            return True
        except Exception as e:
            logger.error(f"FCM push notification send failed: {str(e)}")
            return False

    def _send_via_apns(self, notification: PushNotification) -> bool:
        """Send push notification via Apple Push Notification Service"""
        try:
            # This would integrate with APNs
            logger.info(f"APNS push notification to {notification.recipient_user.get_full_name()}: {notification.title}")

            # Simulate provider response
            notification.provider_message_id = f"apns_{timezone.now().timestamp()}"
            notification.provider_response = {
                'status': 'sent',
                'provider': 'apns',
                'message_id': notification.provider_message_id
            }

            return True
        except Exception as e:
            logger.error(f"APNS push notification send failed: {str(e)}")
            return False

    def _send_via_web_push(self, notification: PushNotification) -> bool:
        """Send push notification via Web Push Protocol"""
        try:
            # This would integrate with Web Push libraries
            logger.info(f"Web Push notification to {notification.recipient_user.get_full_name()}: {notification.title}")

            # Simulate provider response
            notification.provider_message_id = f"webpush_{timezone.now().timestamp()}"
            notification.provider_response = {
                'status': 'sent',
                'provider': 'web_push',
                'message_id': notification.provider_message_id
            }

            return True
        except Exception as e:
            logger.error(f"Web Push notification send failed: {str(e)}")
            return False

    def _send_via_websocket(self, notification: PushNotification) -> bool:
        """Send real-time notification via WebSocket"""
        try:
            # This would integrate with Django Channels or similar WebSocket framework
            logger.info(f"WebSocket notification to {notification.recipient_user.get_full_name()}: {notification.title}")

            # Simulate provider response
            notification.provider_message_id = f"websocket_{timezone.now().timestamp()}"
            notification.provider_response = {
                'status': 'sent',
                'provider': 'websocket',
                'message_id': notification.provider_message_id,
                'real_time': True
            }

            return True
        except Exception as e:
            logger.error(f"WebSocket notification send failed: {str(e)}")
            return False

    def _send_via_mock(self, notification: PushNotification) -> bool:
        """Send push notification via mock provider (for testing)"""
        try:
            logger.info(f"Mock push notification to {notification.recipient_user.get_full_name()}: {notification.title} - {notification.body}")

            # Simulate provider response
            notification.provider_message_id = f"mock_{timezone.now().timestamp()}"
            notification.provider_response = {
                'status': 'sent',
                'provider': 'mock',
                'message_id': notification.provider_message_id,
                'title': notification.title,
                'body': notification.body
            }

            return True
        except Exception as e:
            logger.error(f"Mock push notification send failed: {str(e)}")
            return False


class PushNotificationService:
    """
    High-level service for creating and sending push notifications
    """

    def __init__(self):
        self.template_service = PushNotificationTemplateService()
        self.delivery_service = PushNotificationDeliveryService()

    def send_notification(
        self,
        template_type: str,
        recipient_user,
        variables: Dict[str, Any],
        device_type='web',
        priority='normal',
        scheduled_at=None,
        custom_data=None
    ) -> PushNotification:
        """
        Create and send push notification
        """
        # Get template
        template = self.template_service.get_default_template(template_type)
        if not template:
            raise ValueError(f"No default template found for type: {template_type}")

        # Validate variables
        missing_vars = self.template_service.validate_variables(template, variables)
        if missing_vars:
            raise ValueError(f"Missing required variables: {missing_vars}")

        # Render template
        rendered_content = self.template_service.render_template(template, variables)

        # Get device token for user (if available)
        device_token = self._get_device_token(recipient_user, device_type)

        # Create notification
        notification = PushNotification.objects.create(
            template=template,
            recipient_user=recipient_user,
            device_token=device_token,
            device_type=device_type,
            title=rendered_content['title'],
            body=rendered_content['body'],
            icon_url=rendered_content.get('icon_url', ''),
            image_url=rendered_content.get('image_url', ''),
            action_url=rendered_content.get('action_url', ''),
            template_variables=variables,
            custom_data=custom_data or {},
            priority=priority,
            scheduled_at=scheduled_at
        )

        # Send immediately if not scheduled
        if not scheduled_at:
            self.delivery_service.send_push_notification(notification)

        return notification

    def _get_device_token(self, user, device_type: str) -> str:
        """Get device token for user and device type"""
        try:
            device = DeviceToken.objects.filter(
                user=user,
                device_type=device_type,
                is_active=True,
                notifications_enabled=True
            ).first()
            return device.device_token if device else ''
        except DeviceToken.DoesNotExist:
            return ''

    def send_appointment_reminder(self, appointment, device_type='web'):
        """Send appointment reminder push notification"""
        variables = {
            'patient_name': appointment.patient.user.first_name,
            'doctor_name': appointment.doctor.user.get_full_name(),
            'appointment_date': appointment.appointment_date.strftime('%B %d, %Y'),
            'appointment_time': appointment.appointment_time.strftime('%I:%M %p'),
            'hospital_name': 'City Hospital'
        }

        return self.send_notification(
            template_type='appointment_reminder',
            recipient_user=appointment.patient.user,
            variables=variables,
            device_type=device_type,
            priority='normal'
        )

    def send_test_results_ready(self, patient_user, test_name: str, device_type='web'):
        """Send test results ready push notification"""
        variables = {
            'patient_name': patient_user.first_name,
            'test_name': test_name,
            'hospital_name': 'City Hospital'
        }

        return self.send_notification(
            template_type='test_results_ready',
            recipient_user=patient_user,
            variables=variables,
            device_type=device_type,
            priority='high'
        )

    def send_emergency_alert(self, user, alert_message: str, device_type='web'):
        """Send emergency alert push notification"""
        variables = {
            'patient_name': user.get_full_name(),
            'alert_message': alert_message,
            'hospital_name': 'City Hospital'
        }

        return self.send_notification(
            template_type='emergency_alert',
            recipient_user=user,
            variables=variables,
            device_type=device_type,
            priority='urgent'
        )

    def register_device_token(self, user, device_token: str, device_type: str, device_name: str = '', user_agent: str = '', ip_address: str = ''):
        """Register or update device token for push notifications"""
        device, created = DeviceToken.objects.get_or_create(
            user=user,
            device_token=device_token,
            defaults={
                'device_type': device_type,
                'device_name': device_name,
                'user_agent': user_agent,
                'ip_address': ip_address,
                'is_active': True,
                'notifications_enabled': True
            }
        )

        if not created:
            # Update existing device
            device.device_type = device_type
            device.device_name = device_name or device.device_name
            device.user_agent = user_agent or device.user_agent
            device.ip_address = ip_address or device.ip_address
            device.is_active = True
            device.last_used_at = timezone.now()
            device.save()

        return device


class TemplateVariableService:
    """
    Service for managing template variables with validation and formatting
    """

    @staticmethod
    def validate_variable_value(variable: TemplateVariable, value: Any) -> bool:
        """
        Validate variable value against its type and validation rules
        """
        try:
            # Type validation
            if variable.variable_type == 'string':
                if not isinstance(value, str):
                    return False
            elif variable.variable_type == 'number':
                try:
                    float(value)
                except (ValueError, TypeError):
                    return False
            elif variable.variable_type == 'date':
                if isinstance(value, str):
                    from datetime import datetime
                    try:
                        datetime.strptime(value, '%Y-%m-%d')
                    except ValueError:
                        return False
            elif variable.variable_type == 'email':
                import re
                email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
                if not re.match(email_pattern, str(value)):
                    return False
            elif variable.variable_type == 'phone':
                import re
                phone_pattern = r'^\+?1?\d{9,15}$'
                if not re.match(phone_pattern, str(value).replace(' ', '').replace('-', '')):
                    return False

            # Regex validation
            if variable.validation_regex:
                import re
                if not re.match(variable.validation_regex, str(value)):
                    return False

            return True
        except Exception as e:
            logger.error(f"Error validating variable {variable.name}: {str(e)}")
            return False

    @staticmethod
    def format_variable_value(variable: TemplateVariable, value: Any) -> str:
        """
        Format variable value according to its format type
        """
        try:
            str_value = str(value)

            if variable.format_type == 'uppercase':
                return str_value.upper()
            elif variable.format_type == 'lowercase':
                return str_value.lower()
            elif variable.format_type == 'title_case':
                return str_value.title()
            elif variable.format_type == 'date_short':
                from datetime import datetime
                if isinstance(value, str):
                    date_obj = datetime.strptime(value, '%Y-%m-%d')
                    return date_obj.strftime('%m/%d/%Y')
                return str_value
            elif variable.format_type == 'date_long':
                from datetime import datetime
                if isinstance(value, str):
                    date_obj = datetime.strptime(value, '%Y-%m-%d')
                    return date_obj.strftime('%B %d, %Y')
                return str_value
            elif variable.format_type == 'currency_usd':
                try:
                    amount = float(value)
                    return f"${amount:,.2f}"
                except (ValueError, TypeError):
                    return str_value
            elif variable.format_type == 'phone_us':
                import re
                digits = re.sub(r'\D', '', str_value)
                if len(digits) == 10:
                    return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
                elif len(digits) == 11 and digits[0] == '1':
                    return f"+1 ({digits[1:4]}) {digits[4:7]}-{digits[7:]}"
                return str_value
            else:
                return str_value
        except Exception as e:
            logger.error(f"Error formatting variable {variable.name}: {str(e)}")
            return str(value)

    @staticmethod
    def get_variable_suggestions(template_type: str) -> List[TemplateVariable]:
        """
        Get suggested variables for a template type
        """
        # Common variables for different template types
        suggestions_map = {
            'appointment_confirmation': ['patient_name', 'doctor_name', 'appointment_date', 'appointment_time'],
            'appointment_reminder': ['patient_name', 'doctor_name', 'appointment_date', 'appointment_time'],
            'payment_confirmation': ['patient_name', 'payment_amount', 'payment_date', 'invoice_number'],
            'test_results_ready': ['patient_name', 'test_name', 'result_date'],
            'welcome_patient': ['patient_name', 'hospital_name'],
        }

        suggested_names = suggestions_map.get(template_type, [])
        return TemplateVariable.objects.filter(name__in=suggested_names)


class UnifiedTemplateService:
    """
    Service for managing unified templates across all notification channels
    """

    def __init__(self):
        self.variable_service = TemplateVariableService()

    def create_template(
        self,
        name: str,
        template_type: str,
        supported_channels: List[str],
        content_data: Dict[str, Dict[str, str]],
        variables: List[str],
        created_by=None
    ) -> UnifiedTemplate:
        """
        Create a unified template with multi-language content
        """
        # Create the template
        template = UnifiedTemplate.objects.create(
            name=name,
            template_type=template_type,
            supported_channels=supported_channels,
            created_by=created_by
        )

        # Add variables
        for variable_name in variables:
            variable, created = TemplateVariable.objects.get_or_create(
                name=variable_name,
                defaults={
                    'display_name': variable_name.replace('_', ' ').title(),
                    'variable_type': 'string'
                }
            )
            template.variables.add(variable)

        # Create content for each language and content type
        for lang_code, content_dict in content_data.items():
            try:
                language = TemplateLanguage.objects.get(code=lang_code)
                for content_type, content in content_dict.items():
                    TemplateContent.objects.create(
                        template=template,
                        language=language,
                        content_type=content_type,
                        content=content
                    )
            except TemplateLanguage.DoesNotExist:
                logger.warning(f"Language {lang_code} not found, skipping content creation")

        return template

    def render_template(
        self,
        template: UnifiedTemplate,
        channel: str,
        language_code: str,
        variables: Dict[str, Any]
    ) -> Dict[str, str]:
        """
        Render template for specific channel and language
        """
        start_time = timezone.now()

        try:
            # Get language
            language = TemplateLanguage.objects.get(code=language_code)

            # Validate and format variables
            formatted_variables = {}
            for template_var in template.variables.all():
                if template_var.name in variables:
                    value = variables[template_var.name]

                    # Validate
                    if not self.variable_service.validate_variable_value(template_var, value):
                        if template_var.is_required:
                            raise ValueError(f"Invalid value for required variable: {template_var.name}")
                        value = template_var.default_value or ''

                    # Format
                    formatted_value = self.variable_service.format_variable_value(template_var, value)
                    formatted_variables[template_var.name] = formatted_value
                elif template_var.is_required:
                    if template_var.default_value:
                        formatted_variables[template_var.name] = template_var.default_value
                    else:
                        raise ValueError(f"Missing required variable: {template_var.name}")

            # Get content for channel
            content_types = self._get_content_types_for_channel(channel)
            rendered_content = {}

            for content_type in content_types:
                try:
                    template_content = TemplateContent.objects.get(
                        template=template,
                        language=language,
                        content_type=content_type
                    )

                    # Render content
                    django_template = Template(template_content.content)
                    context = Context(formatted_variables)
                    rendered_content[content_type] = django_template.render(context)

                except TemplateContent.DoesNotExist:
                    logger.warning(f"Content not found for {template.name} - {language_code} - {content_type}")

            # Log usage
            render_time = (timezone.now() - start_time).total_seconds() * 1000
            TemplateUsageLog.objects.create(
                template=template,
                language=language,
                channel=channel,
                variables_used=variables,
                render_time_ms=int(render_time),
                success=True
            )

            return rendered_content

        except Exception as e:
            # Log failed usage
            render_time = (timezone.now() - start_time).total_seconds() * 1000
            TemplateUsageLog.objects.create(
                template=template,
                language=language if 'language' in locals() else None,
                channel=channel,
                variables_used=variables,
                render_time_ms=int(render_time),
                success=False,
                error_message=str(e)
            )
            raise

    def _get_content_types_for_channel(self, channel: str) -> List[str]:
        """
        Get required content types for a notification channel
        """
        content_map = {
            'email': ['email_subject', 'email_html', 'email_text'],
            'sms': ['sms_message'],
            'push': ['push_title', 'push_body']
        }
        return content_map.get(channel, [])

    def get_template_analytics(self, template: UnifiedTemplate, days: int = 30) -> Dict[str, Any]:
        """
        Get analytics for a template
        """
        from datetime import timedelta
        from django.db import models

        start_date = timezone.now() - timedelta(days=days)
        usage_logs = TemplateUsageLog.objects.filter(
            template=template,
            created_at__gte=start_date
        )

        total_usage = usage_logs.count()
        successful_usage = usage_logs.filter(success=True).count()
        failed_usage = usage_logs.filter(success=False).count()

        # Channel breakdown
        channel_usage = {}
        for log in usage_logs:
            channel = log.channel
            if channel not in channel_usage:
                channel_usage[channel] = {'total': 0, 'success': 0, 'failed': 0}
            channel_usage[channel]['total'] += 1
            if log.success:
                channel_usage[channel]['success'] += 1
            else:
                channel_usage[channel]['failed'] += 1

        # Language breakdown
        language_usage = {}
        for log in usage_logs.filter(language__isnull=False):
            lang_code = log.language.code
            if lang_code not in language_usage:
                language_usage[lang_code] = 0
            language_usage[lang_code] += 1

        # Performance metrics
        successful_logs = usage_logs.filter(success=True, render_time_ms__isnull=False)
        avg_render_time = 0
        if successful_logs.exists():
            avg_render_time = successful_logs.aggregate(
                avg_time=models.Avg('render_time_ms')
            )['avg_time'] or 0

        return {
            'total_usage': total_usage,
            'successful_usage': successful_usage,
            'failed_usage': failed_usage,
            'success_rate': (successful_usage / total_usage * 100) if total_usage > 0 else 0,
            'channel_usage': channel_usage,
            'language_usage': language_usage,
            'avg_render_time_ms': round(avg_render_time, 2),
            'period_days': days
        }


class NotificationPreferenceService:
    """
    Service for managing user notification preferences
    """

    @staticmethod
    def create_default_preferences(user) -> List[NotificationPreference]:
        """
        Create default notification preferences for a new user
        """
        default_preferences = []

        # Default preferences configuration
        default_config = {
            'appointment_confirmation': {'email': True, 'sms': True, 'push': True, 'in_app': True},
            'appointment_reminder': {'email': True, 'sms': True, 'push': True, 'in_app': True},
            'appointment_cancellation': {'email': True, 'sms': True, 'push': True, 'in_app': True},
            'test_results_ready': {'email': True, 'sms': False, 'push': True, 'in_app': True},
            'prescription_ready': {'email': True, 'sms': False, 'push': True, 'in_app': True},
            'payment_confirmation': {'email': True, 'sms': False, 'push': False, 'in_app': True},
            'payment_reminder': {'email': True, 'sms': True, 'push': True, 'in_app': True},
            'invoice_generated': {'email': True, 'sms': False, 'push': False, 'in_app': True},
            'welcome_message': {'email': True, 'sms': False, 'push': True, 'in_app': True},
            'password_reset': {'email': True, 'sms': True, 'push': False, 'in_app': False},
            'verification_code': {'email': True, 'sms': True, 'push': False, 'in_app': False},
            'emergency_alert': {'email': True, 'sms': True, 'push': True, 'in_app': True},
            'system_maintenance': {'email': True, 'sms': False, 'push': False, 'in_app': True},
            'marketing': {'email': False, 'sms': False, 'push': False, 'in_app': False},
            'newsletter': {'email': False, 'sms': False, 'push': False, 'in_app': False},
            'survey': {'email': False, 'sms': False, 'push': False, 'in_app': True},
        }

        # Create preferences for each notification type and channel
        for notification_type, channels in default_config.items():
            for channel, is_enabled in channels.items():
                preference = NotificationPreference.objects.create(
                    user=user,
                    notification_type=notification_type,
                    channel=channel,
                    is_enabled=is_enabled,
                    frequency='immediate' if is_enabled else 'disabled',
                    priority_threshold='low'
                )
                default_preferences.append(preference)

        return default_preferences

    @staticmethod
    def create_default_settings(user) -> NotificationSettings:
        """
        Create default notification settings for a new user
        """
        # Get default language
        default_language = TemplateLanguage.objects.filter(is_default=True).first()

        settings = NotificationSettings.objects.create(
            user=user,
            notifications_enabled=True,
            email_notifications_enabled=True,
            sms_notifications_enabled=True,
            push_notifications_enabled=True,
            in_app_notifications_enabled=True,
            primary_email=user.email,
            timezone='UTC',
            default_language=default_language,
            global_quiet_hours_enabled=False,
            weekend_notifications_enabled=True,
            holiday_notifications_enabled=True,
            daily_digest_enabled=False,
            weekly_digest_enabled=False,
            marketing_emails_enabled=False,
            newsletter_enabled=False,
            survey_requests_enabled=True,
            notification_sound_enabled=True,
            notification_vibration_enabled=True,
            notification_preview_enabled=True
        )

        return settings

    @staticmethod
    def check_user_preference(
        user,
        notification_type: str,
        channel: str,
        priority: str = 'normal'
    ) -> bool:
        """
        Check if user wants to receive a specific notification
        """
        try:
            # Check global settings first
            settings = NotificationSettings.objects.get(user=user)

            # Master toggle
            if not settings.notifications_enabled:
                return False

            # Channel-specific toggles
            if channel == 'email' and not settings.email_notifications_enabled:
                return False
            elif channel == 'sms' and not settings.sms_notifications_enabled:
                return False
            elif channel == 'push' and not settings.push_notifications_enabled:
                return False
            elif channel == 'in_app' and not settings.in_app_notifications_enabled:
                return False

            # Check specific preference
            try:
                preference = NotificationPreference.objects.get(
                    user=user,
                    notification_type=notification_type,
                    channel=channel
                )

                # Check if preference is enabled
                if not preference.is_enabled:
                    return False

                # Check priority threshold
                priority_levels = {'low': 1, 'normal': 2, 'high': 3, 'urgent': 4}
                user_threshold = priority_levels.get(preference.priority_threshold, 1)
                notification_priority = priority_levels.get(priority, 2)

                if notification_priority < user_threshold:
                    return False

                # Check quiet hours
                if preference.quiet_hours_start and preference.quiet_hours_end:
                    current_time = timezone.now().time()
                    if preference.quiet_hours_start <= current_time <= preference.quiet_hours_end:
                        # Allow urgent notifications during quiet hours
                        if priority != 'urgent':
                            return False

                return True

            except NotificationPreference.DoesNotExist:
                # If no specific preference, use default based on notification type
                return notification_type in [
                    'appointment_confirmation', 'appointment_reminder', 'emergency_alert'
                ]

        except NotificationSettings.DoesNotExist:
            # If no settings, create defaults and allow important notifications
            NotificationPreferenceService.create_default_settings(user)
            return notification_type in [
                'appointment_confirmation', 'appointment_reminder', 'emergency_alert'
            ]

    @staticmethod
    def is_blacklisted(user, contact_info: str, blacklist_type: str) -> bool:
        """
        Check if a contact is blacklisted
        """
        try:
            blacklist_entries = NotificationBlacklist.objects.filter(
                user=user,
                blacklist_type=blacklist_type,
                is_active=True
            )

            for entry in blacklist_entries:
                # Check if entry has expired
                if entry.expires_at and entry.expires_at < timezone.now():
                    entry.is_active = False
                    entry.save()
                    continue

                # Check for exact match or pattern match
                if blacklist_type == 'domain' and '@' in contact_info:
                    domain = contact_info.split('@')[1]
                    if domain.lower() == entry.value.lower():
                        return True
                elif blacklist_type in ['email', 'phone']:
                    if contact_info.lower() == entry.value.lower():
                        return True
                elif blacklist_type == 'keyword':
                    if entry.value.lower() in contact_info.lower():
                        return True

            return False

        except Exception as e:
            logger.error(f"Error checking blacklist for {user.id}: {str(e)}")
            return False

    @staticmethod
    def get_user_language(user, notification_type: str = None) -> str:
        """
        Get user's preferred language for notifications
        """
        try:
            # Check for type-specific language preference
            if notification_type:
                preference = NotificationPreference.objects.filter(
                    user=user,
                    notification_type=notification_type,
                    preferred_language__isnull=False
                ).first()

                if preference and preference.preferred_language:
                    return preference.preferred_language.code

            # Check global language setting
            settings = NotificationSettings.objects.get(user=user)
            if settings.default_language:
                return settings.default_language.code

            # Fallback to default system language
            default_language = TemplateLanguage.objects.filter(is_default=True).first()
            return default_language.code if default_language else 'en'

        except (NotificationSettings.DoesNotExist, AttributeError):
            return 'en'

    @staticmethod
    def should_send_during_schedule(user, notification_type: str) -> bool:
        """
        Check if notification should be sent based on user's schedule preferences
        """
        try:
            current_time = timezone.now()
            current_day = current_time.strftime('%A').lower()

            # Check global quiet hours
            settings = NotificationSettings.objects.get(user=user)
            if settings.global_quiet_hours_enabled:
                if (settings.global_quiet_hours_start and
                    settings.global_quiet_hours_end and
                    settings.global_quiet_hours_start <= current_time.time() <= settings.global_quiet_hours_end):
                    return False

            # Check weekend settings
            if current_day in ['saturday', 'sunday'] and not settings.weekend_notifications_enabled:
                return False

            # Check custom schedules
            active_schedules = NotificationSchedule.objects.filter(
                user=user,
                is_active=True,
                notification_types__contains=[notification_type]
            ).order_by('-priority')

            for schedule in active_schedules:
                # Check date range
                if schedule.start_date and current_time.date() < schedule.start_date:
                    continue
                if schedule.end_date and current_time.date() > schedule.end_date:
                    continue

                # Check day of week
                if schedule.days_of_week and current_day not in schedule.days_of_week:
                    continue

                # Check time range
                if (schedule.start_time <= current_time.time() <= schedule.end_time):
                    return True

            # If no specific schedule found, allow during normal hours (8 AM - 10 PM)
            return 8 <= current_time.hour <= 22

        except NotificationSettings.DoesNotExist:
            return True  # Allow if no settings found


class NotificationSchedulingService:
    """
    Service for managing notification scheduling and automation
    """

    def __init__(self):
        self.preference_service = NotificationPreferenceService()
        self.email_service = EmailNotificationService()
        self.sms_service = SMSNotificationService()
        self.push_service = PushNotificationService()

    def create_scheduled_job(
        self,
        name: str,
        notification_type: str,
        channel: str,
        recipients=None,
        recipient_filter=None,
        template_variables=None,
        scheduled_at=None,
        job_type='scheduled',
        priority='normal',
        created_by=None
    ) -> NotificationJob:
        """
        Create a scheduled notification job
        """
        job = NotificationJob.objects.create(
            name=name,
            job_type=job_type,
            notification_type=notification_type,
            channel=channel,
            scheduled_at=scheduled_at or timezone.now(),
            priority=priority,
            template_variables=template_variables or {},
            recipient_filter=recipient_filter or {},
            created_by=created_by
        )

        # Add recipients if provided
        if recipients:
            job.recipient_users.set(recipients)

        # Queue the job for processing
        self._queue_job(job)

        return job

    def create_recurring_job(
        self,
        name: str,
        notification_type: str,
        channel: str,
        recurrence_pattern: Dict[str, Any],
        recipients=None,
        recipient_filter=None,
        template_variables=None,
        start_date=None,
        created_by=None
    ) -> NotificationJob:
        """
        Create a recurring notification job
        """
        next_run = self._calculate_next_run(recurrence_pattern, start_date)

        job = NotificationJob.objects.create(
            name=name,
            job_type='recurring',
            notification_type=notification_type,
            channel=channel,
            is_recurring=True,
            recurrence_pattern=recurrence_pattern,
            next_run_at=next_run,
            template_variables=template_variables or {},
            recipient_filter=recipient_filter or {},
            created_by=created_by
        )

        # Add recipients if provided
        if recipients:
            job.recipient_users.set(recipients)

        return job

    def create_batch_job(
        self,
        name: str,
        notification_type: str,
        channel: str,
        recipients,
        template_variables=None,
        batch_size=100,
        batch_delay=60,
        scheduled_at=None,
        created_by=None
    ) -> NotificationJob:
        """
        Create a batch notification job for large recipient lists
        """
        job = NotificationJob.objects.create(
            name=name,
            job_type='batch',
            notification_type=notification_type,
            channel=channel,
            scheduled_at=scheduled_at or timezone.now(),
            batch_size=batch_size,
            batch_delay=batch_delay,
            template_variables=template_variables or {},
            total_recipients=len(recipients),
            created_by=created_by
        )

        # Add recipients
        job.recipient_users.set(recipients)

        # Queue the job for processing
        self._queue_job(job)

        return job

    def _queue_job(self, job: NotificationJob):
        """
        Queue a job for processing by creating queue items
        """
        recipients = self._get_job_recipients(job)

        for recipient in recipients:
            # Check user preferences
            if not self.preference_service.check_user_preference(
                user=recipient,
                notification_type=job.notification_type,
                channel=job.channel
            ):
                continue

            # Get recipient contact info
            contact_info = self._get_recipient_contact(recipient, job.channel)
            if not contact_info:
                continue

            # Create queue item
            NotificationQueue.objects.create(
                job=job,
                recipient_user=recipient,
                recipient_email=contact_info.get('email', ''),
                recipient_phone=contact_info.get('phone', ''),
                channel=job.channel,
                scheduled_at=job.scheduled_at,
                priority=job.priority,
                template_variables=job.template_variables
            )

        # Update job status
        job.status = 'queued'
        job.save()

    def _get_job_recipients(self, job: NotificationJob):
        """
        Get recipients for a job based on explicit recipients or filters
        """
        if job.recipient_users.exists():
            return job.recipient_users.all()

        # Apply recipient filter
        from django.contrib.auth import get_user_model
        User = get_user_model()

        queryset = User.objects.all()

        # Apply filters
        if job.recipient_filter:
            if 'user_type' in job.recipient_filter:
                queryset = queryset.filter(user_type=job.recipient_filter['user_type'])
            if 'is_active' in job.recipient_filter:
                queryset = queryset.filter(is_active=job.recipient_filter['is_active'])
            # Add more filter conditions as needed

        return queryset

    def _get_recipient_contact(self, user, channel: str) -> Dict[str, str]:
        """
        Get contact information for a recipient based on channel
        """
        contact_info = {}

        if channel == 'email':
            contact_info['email'] = user.email
        elif channel == 'sms':
            # Get phone from user profile or settings
            try:
                settings = NotificationSettings.objects.get(user=user)
                contact_info['phone'] = settings.primary_phone
            except NotificationSettings.DoesNotExist:
                contact_info['phone'] = ''

        return contact_info

    def process_scheduled_jobs(self):
        """
        Process jobs that are ready to be executed
        """
        current_time = timezone.now()

        # Get jobs ready for execution
        ready_jobs = NotificationJob.objects.filter(
            status__in=['pending', 'queued'],
            scheduled_at__lte=current_time
        ).exclude(
            execute_after__gt=current_time
        ).exclude(
            execute_before__lt=current_time
        )

        for job in ready_jobs:
            try:
                self._execute_job(job)
            except Exception as e:
                logger.error(f"Error executing job {job.job_id}: {str(e)}")
                job.status = 'failed'
                job.error_message = str(e)
                job.attempts += 1
                job.save()

    def _execute_job(self, job: NotificationJob):
        """
        Execute a notification job
        """
        job.status = 'processing'
        job.started_at = timezone.now()
        job.attempts += 1
        job.save()

        try:
            if job.job_type == 'batch':
                self._execute_batch_job(job)
            else:
                self._execute_regular_job(job)

            # Handle recurring jobs
            if job.is_recurring:
                self._schedule_next_recurrence(job)
            else:
                job.status = 'completed'
                job.completed_at = timezone.now()
                job.save()

        except Exception as e:
            job.status = 'failed'
            job.error_message = str(e)
            job.save()
            raise

    def _execute_regular_job(self, job: NotificationJob):
        """
        Execute a regular notification job
        """
        queue_items = NotificationQueue.objects.filter(
            job=job,
            status='pending'
        )

        successful_sends = 0
        failed_sends = 0

        for item in queue_items:
            try:
                success = self._send_queued_notification(item)
                if success:
                    successful_sends += 1
                    item.status = 'completed'
                    item.sent_at = timezone.now()
                else:
                    failed_sends += 1
                    item.status = 'failed'

                item.processed_at = timezone.now()
                item.save()

            except Exception as e:
                failed_sends += 1
                item.status = 'failed'
                item.error_message = str(e)
                item.processed_at = timezone.now()
                item.save()

        # Update job statistics
        job.successful_sends = successful_sends
        job.failed_sends = failed_sends
        job.save()

    def _execute_batch_job(self, job: NotificationJob):
        """
        Execute a batch notification job with rate limiting
        """
        import time

        queue_items = NotificationQueue.objects.filter(
            job=job,
            status='pending'
        )

        successful_sends = 0
        failed_sends = 0
        batch_count = 0

        for i, item in enumerate(queue_items):
            try:
                success = self._send_queued_notification(item)
                if success:
                    successful_sends += 1
                    item.status = 'completed'
                    item.sent_at = timezone.now()
                else:
                    failed_sends += 1
                    item.status = 'failed'

                item.processed_at = timezone.now()
                item.save()

                # Check if we need to pause for batch delay
                if (i + 1) % job.batch_size == 0:
                    batch_count += 1
                    if batch_count * job.batch_size < queue_items.count():
                        time.sleep(job.batch_delay)

            except Exception as e:
                failed_sends += 1
                item.status = 'failed'
                item.error_message = str(e)
                item.processed_at = timezone.now()
                item.save()

        # Update job statistics
        job.successful_sends = successful_sends
        job.failed_sends = failed_sends
        job.save()

    def _send_queued_notification(self, queue_item: NotificationQueue) -> bool:
        """
        Send a queued notification
        """
        try:
            if queue_item.channel == 'email':
                return self._send_email_notification(queue_item)
            elif queue_item.channel == 'sms':
                return self._send_sms_notification(queue_item)
            elif queue_item.channel == 'push':
                return self._send_push_notification(queue_item)
            else:
                logger.warning(f"Unknown channel: {queue_item.channel}")
                return False
        except Exception as e:
            logger.error(f"Error sending notification: {str(e)}")
            return False

    def _send_email_notification(self, queue_item: NotificationQueue) -> bool:
        """
        Send email notification from queue item
        """
        try:
            notification = self.email_service.send_notification(
                template_type=queue_item.job.notification_type,
                recipient_email=queue_item.recipient_email,
                recipient_user=queue_item.recipient_user,
                variables=queue_item.template_variables,
                priority=queue_item.priority
            )

            # Update queue item with provider response
            queue_item.provider_message_id = notification.message_id
            queue_item.provider_response = {
                'notification_id': str(notification.id),
                'status': notification.status
            }

            return notification.status in ['sent', 'delivered']
        except Exception as e:
            queue_item.error_message = str(e)
            return False

    def _send_sms_notification(self, queue_item: NotificationQueue) -> bool:
        """
        Send SMS notification from queue item
        """
        try:
            notification = self.sms_service.send_notification(
                template_type=queue_item.job.notification_type,
                recipient_phone=queue_item.recipient_phone,
                recipient_user=queue_item.recipient_user,
                variables=queue_item.template_variables,
                priority=queue_item.priority
            )

            # Update queue item with provider response
            queue_item.provider_message_id = notification.message_id
            queue_item.provider_response = {
                'notification_id': str(notification.id),
                'status': notification.status
            }

            return notification.status in ['sent', 'delivered']
        except Exception as e:
            queue_item.error_message = str(e)
            return False

    def _send_push_notification(self, queue_item: NotificationQueue) -> bool:
        """
        Send push notification from queue item
        """
        try:
            notification = self.push_service.send_notification(
                template_type=queue_item.job.notification_type,
                recipient_user=queue_item.recipient_user,
                variables=queue_item.template_variables,
                priority=queue_item.priority
            )

            # Update queue item with provider response
            queue_item.provider_message_id = notification.provider_message_id
            queue_item.provider_response = notification.provider_response

            return notification.status in ['sent', 'delivered']
        except Exception as e:
            queue_item.error_message = str(e)
            return False

    def _calculate_next_run(self, recurrence_pattern: Dict[str, Any], start_date=None) -> timezone.datetime:
        """
        Calculate next run time based on recurrence pattern
        """
        from datetime import timedelta

        base_time = start_date or timezone.now()

        pattern_type = recurrence_pattern.get('type', 'daily')
        interval = recurrence_pattern.get('interval', 1)

        if pattern_type == 'daily':
            return base_time + timedelta(days=interval)
        elif pattern_type == 'weekly':
            return base_time + timedelta(weeks=interval)
        elif pattern_type == 'monthly':
            # Approximate monthly calculation
            return base_time + timedelta(days=30 * interval)
        elif pattern_type == 'hourly':
            return base_time + timedelta(hours=interval)
        else:
            # Default to daily
            return base_time + timedelta(days=1)

    def _schedule_next_recurrence(self, job: NotificationJob):
        """
        Schedule the next occurrence of a recurring job
        """
        next_run = self._calculate_next_run(job.recurrence_pattern, job.last_run_at or timezone.now())

        job.last_run_at = timezone.now()
        job.next_run_at = next_run
        job.status = 'pending'  # Reset status for next run
        job.save()

        # Create new queue items for next run
        self._queue_job(job)

    def process_recurring_jobs(self):
        """
        Process recurring jobs that are due
        """
        current_time = timezone.now()

        due_jobs = NotificationJob.objects.filter(
            is_recurring=True,
            status='pending',
            next_run_at__lte=current_time
        )

        for job in due_jobs:
            try:
                self._execute_job(job)
            except Exception as e:
                logger.error(f"Error executing recurring job {job.job_id}: {str(e)}")

    def retry_failed_notifications(self):
        """
        Retry failed notifications that are eligible for retry
        """
        current_time = timezone.now()

        # Get failed queue items that can be retried
        retry_items = NotificationQueue.objects.filter(
            status='failed',
            attempts__lt=models.F('max_attempts'),
            retry_after__lte=current_time
        )

        for item in retry_items:
            try:
                item.status = 'retrying'
                item.attempts += 1
                item.save()

                success = self._send_queued_notification(item)

                if success:
                    item.status = 'completed'
                    item.sent_at = timezone.now()
                else:
                    item.status = 'failed'
                    # Set retry time (exponential backoff)
                    retry_delay = min(300 * (2 ** item.attempts), 3600)  # Max 1 hour
                    item.retry_after = timezone.now() + timezone.timedelta(seconds=retry_delay)

                item.save()

            except Exception as e:
                item.status = 'failed'
                item.error_message = str(e)
                item.save()

    def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a scheduled job
        """
        try:
            job = NotificationJob.objects.get(job_id=job_id)

            if job.status in ['pending', 'queued']:
                job.status = 'cancelled'
                job.save()

                # Cancel pending queue items
                NotificationQueue.objects.filter(
                    job=job,
                    status='pending'
                ).update(status='cancelled')

                return True
            else:
                return False
        except NotificationJob.DoesNotExist:
            return False

    def pause_job(self, job_id: str) -> bool:
        """
        Pause a scheduled job
        """
        try:
            job = NotificationJob.objects.get(job_id=job_id)

            if job.status in ['pending', 'queued']:
                job.status = 'paused'
                job.save()
                return True
            else:
                return False
        except NotificationJob.DoesNotExist:
            return False

    def resume_job(self, job_id: str) -> bool:
        """
        Resume a paused job
        """
        try:
            job = NotificationJob.objects.get(job_id=job_id)

            if job.status == 'paused':
                job.status = 'pending'
                job.save()
                return True
            else:
                return False
        except NotificationJob.DoesNotExist:
            return False


class CronJobService:
    """
    Service for managing cron jobs and scheduled tasks
    """

    @staticmethod
    def create_cron_job(
        name: str,
        cron_expression: str,
        task_function: str,
        cron_type: str = 'custom',
        task_parameters=None,
        created_by=None
    ) -> CronJob:
        """
        Create a new cron job
        """
        cron_job = CronJob.objects.create(
            name=name,
            cron_expression=cron_expression,
            task_function=task_function,
            cron_type=cron_type,
            task_parameters=task_parameters or {},
            created_by=created_by
        )

        # Calculate next run time
        next_run = CronJobService._calculate_next_run_from_cron(cron_expression)
        cron_job.next_run_at = next_run
        cron_job.save()

        return cron_job

    @staticmethod
    def _calculate_next_run_from_cron(cron_expression: str) -> timezone.datetime:
        """
        Calculate next run time from cron expression
        This is a simplified implementation - in production, use a library like croniter
        """
        from datetime import timedelta

        # For now, return next hour as a simple implementation
        # In production, you would use croniter or similar library
        return timezone.now() + timedelta(hours=1)

    @staticmethod
    def execute_due_cron_jobs():
        """
        Execute cron jobs that are due
        """
        current_time = timezone.now()

        due_jobs = CronJob.objects.filter(
            is_active=True,
            is_running=False,
            next_run_at__lte=current_time
        )

        for job in due_jobs:
            try:
                CronJobService._execute_cron_job(job)
            except Exception as e:
                logger.error(f"Error executing cron job {job.name}: {str(e)}")
                job.last_error = str(e)
                job.consecutive_failures += 1

                # Disable job if too many failures
                if job.consecutive_failures >= job.max_failures:
                    job.is_active = False
                    logger.warning(f"Disabled cron job {job.name} due to consecutive failures")

                job.save()

    @staticmethod
    def _execute_cron_job(job: CronJob):
        """
        Execute a specific cron job
        """
        job.is_running = True
        job.run_count += 1
        job.save()

        try:
            # Execute the task function
            if job.task_function == 'send_appointment_reminders':
                CronJobService._send_appointment_reminders(job.task_parameters)
            elif job.task_function == 'send_daily_digest':
                CronJobService._send_daily_digest(job.task_parameters)
            elif job.task_function == 'cleanup_old_notifications':
                CronJobService._cleanup_old_notifications(job.task_parameters)
            elif job.task_function == 'generate_analytics_report':
                CronJobService._generate_analytics_report(job.task_parameters)
            else:
                logger.warning(f"Unknown task function: {job.task_function}")

            # Mark as successful
            job.success_count += 1
            job.consecutive_failures = 0
            job.last_run_at = timezone.now()

            # Calculate next run time
            job.next_run_at = CronJobService._calculate_next_run_from_cron(job.cron_expression)

        except Exception as e:
            job.failure_count += 1
            job.consecutive_failures += 1
            job.last_error = str(e)
            raise
        finally:
            job.is_running = False
            job.save()

    @staticmethod
    def _send_appointment_reminders(parameters: Dict[str, Any]):
        """
        Send appointment reminders for upcoming appointments
        """
        from datetime import timedelta
        from appointments.models import Appointment

        # Get appointments for tomorrow
        tomorrow = timezone.now().date() + timedelta(days=1)
        upcoming_appointments = Appointment.objects.filter(
            appointment_date=tomorrow,
            status='confirmed'
        )

        scheduling_service = NotificationSchedulingService()

        for appointment in upcoming_appointments:
            try:
                # Create reminder job
                scheduling_service.create_scheduled_job(
                    name=f'Appointment Reminder - {appointment.id}',
                    notification_type='appointment_reminder',
                    channel='email',
                    recipients=[appointment.patient.user],
                    template_variables={
                        'patient_name': appointment.patient.user.get_full_name(),
                        'doctor_name': appointment.doctor.user.get_full_name(),
                        'appointment_date': appointment.appointment_date.strftime('%B %d, %Y'),
                        'appointment_time': appointment.appointment_time.strftime('%I:%M %p'),
                    },
                    scheduled_at=timezone.now(),
                    job_type='immediate'
                )
            except Exception as e:
                logger.error(f"Error creating reminder for appointment {appointment.id}: {str(e)}")

    @staticmethod
    def _send_daily_digest(parameters: Dict[str, Any]):
        """
        Send daily digest emails to users who have opted in
        """
        # Get users with daily digest enabled
        digest_users = NotificationSettings.objects.filter(
            daily_digest_enabled=True,
            notifications_enabled=True,
            email_notifications_enabled=True
        )

        scheduling_service = NotificationSchedulingService()

        for settings in digest_users:
            try:
                # Create digest job
                scheduling_service.create_scheduled_job(
                    name=f'Daily Digest - {settings.user.get_full_name()}',
                    notification_type='daily_digest',
                    channel='email',
                    recipients=[settings.user],
                    template_variables={
                        'user_name': settings.user.get_full_name(),
                        'digest_date': timezone.now().strftime('%B %d, %Y'),
                    },
                    scheduled_at=timezone.now(),
                    job_type='immediate'
                )
            except Exception as e:
                logger.error(f"Error creating digest for user {settings.user.id}: {str(e)}")

    @staticmethod
    def _cleanup_old_notifications(parameters: Dict[str, Any]):
        """
        Clean up old notification records
        """
        from datetime import timedelta

        # Default to 90 days if not specified
        days_to_keep = parameters.get('days_to_keep', 90)
        cutoff_date = timezone.now() - timedelta(days=days_to_keep)

        # Clean up old email notifications
        old_emails = EmailNotification.objects.filter(created_at__lt=cutoff_date)
        email_count = old_emails.count()
        old_emails.delete()

        # Clean up old SMS notifications
        old_sms = SMSNotification.objects.filter(created_at__lt=cutoff_date)
        sms_count = old_sms.count()
        old_sms.delete()

        # Clean up old push notifications
        old_push = PushNotification.objects.filter(created_at__lt=cutoff_date)
        push_count = old_push.count()
        old_push.delete()

        # Clean up old notification jobs
        old_jobs = NotificationJob.objects.filter(
            created_at__lt=cutoff_date,
            status__in=['completed', 'failed', 'cancelled']
        )
        job_count = old_jobs.count()
        old_jobs.delete()

        logger.info(f"Cleaned up {email_count} emails, {sms_count} SMS, {push_count} push notifications, {job_count} jobs")

    @staticmethod
    def _generate_analytics_report(parameters: Dict[str, Any]):
        """
        Generate and send analytics reports
        """
        # This would generate comprehensive analytics reports
        # For now, just log that the task ran
        logger.info("Analytics report generation completed")


class NotificationAnalyticsService:
    """
    Service for generating comprehensive notification analytics
    """

    @staticmethod
    def generate_analytics_report(
        start_date,
        end_date,
        report_type='custom',
        generated_by=None
    ) -> NotificationAnalytics:
        """
        Generate comprehensive analytics report for a date range
        """
        # Get all notifications in the date range
        email_notifications = EmailNotification.objects.filter(
            created_at__date__gte=start_date,
            created_at__date__lte=end_date
        )

        sms_notifications = SMSNotification.objects.filter(
            created_at__date__gte=start_date,
            created_at__date__lte=end_date
        )

        push_notifications = PushNotification.objects.filter(
            created_at__date__gte=start_date,
            created_at__date__lte=end_date
        )

        # Calculate overall metrics
        total_notifications = (
            email_notifications.count() +
            sms_notifications.count() +
            push_notifications.count()
        )

        total_sent = (
            email_notifications.filter(status__in=['sent', 'delivered']).count() +
            sms_notifications.filter(status__in=['sent', 'delivered']).count() +
            push_notifications.filter(status__in=['sent', 'delivered']).count()
        )

        total_delivered = (
            email_notifications.filter(status='delivered').count() +
            sms_notifications.filter(status='delivered').count() +
            push_notifications.filter(status='delivered').count()
        )

        total_opened = email_notifications.filter(opened_at__isnull=False).count()
        total_clicked = email_notifications.filter(clicked_at__isnull=False).count()

        total_failed = (
            email_notifications.filter(status='failed').count() +
            sms_notifications.filter(status='failed').count() +
            push_notifications.filter(status='failed').count()
        )

        total_bounced = email_notifications.filter(bounce_reason__isnull=False).count()

        # Calculate channel-specific metrics
        email_metrics = NotificationAnalyticsService._calculate_email_metrics(email_notifications)
        sms_metrics = NotificationAnalyticsService._calculate_sms_metrics(sms_notifications)
        push_metrics = NotificationAnalyticsService._calculate_push_metrics(push_notifications)

        # Calculate template performance
        template_performance = NotificationAnalyticsService._calculate_template_performance(
            email_notifications, sms_notifications, push_notifications
        )

        # Calculate time-based distribution
        hourly_distribution = NotificationAnalyticsService._calculate_hourly_distribution(
            email_notifications, sms_notifications, push_notifications
        )

        daily_distribution = NotificationAnalyticsService._calculate_daily_distribution(
            email_notifications, sms_notifications, push_notifications
        )

        # Calculate costs
        total_cost, cost_breakdown = NotificationAnalyticsService._calculate_costs(
            email_notifications, sms_notifications, push_notifications
        )

        # Create or update analytics record
        analytics, created = NotificationAnalytics.objects.get_or_create(
            report_type=report_type,
            start_date=start_date,
            end_date=end_date,
            defaults={
                'total_notifications': total_notifications,
                'total_sent': total_sent,
                'total_delivered': total_delivered,
                'total_opened': total_opened,
                'total_clicked': total_clicked,
                'total_failed': total_failed,
                'total_bounced': total_bounced,
                'email_metrics': email_metrics,
                'sms_metrics': sms_metrics,
                'push_metrics': push_metrics,
                'template_performance': template_performance,
                'hourly_distribution': hourly_distribution,
                'daily_distribution': daily_distribution,
                'total_cost': total_cost,
                'cost_breakdown': cost_breakdown,
                'generated_by': generated_by
            }
        )

        # If not created, update the existing record
        if not created:
            analytics.total_notifications = total_notifications
            analytics.total_sent = total_sent
            analytics.total_delivered = total_delivered
            analytics.total_opened = total_opened
            analytics.total_clicked = total_clicked
            analytics.total_failed = total_failed
            analytics.total_bounced = total_bounced
            analytics.email_metrics = email_metrics
            analytics.sms_metrics = sms_metrics
            analytics.push_metrics = push_metrics
            analytics.template_performance = template_performance
            analytics.hourly_distribution = hourly_distribution
            analytics.daily_distribution = daily_distribution
            analytics.total_cost = total_cost
            analytics.cost_breakdown = cost_breakdown
            analytics.save()

        return analytics

    @staticmethod
    def _calculate_email_metrics(email_notifications):
        """Calculate email-specific metrics"""
        total_emails = email_notifications.count()
        sent_emails = email_notifications.filter(status__in=['sent', 'delivered']).count()
        delivered_emails = email_notifications.filter(status='delivered').count()
        opened_emails = email_notifications.filter(opened_at__isnull=False).count()
        clicked_emails = email_notifications.filter(clicked_at__isnull=False).count()
        bounced_emails = email_notifications.filter(bounce_reason__isnull=False).count()
        failed_emails = email_notifications.filter(status='failed').count()

        return {
            'total': total_emails,
            'sent': sent_emails,
            'delivered': delivered_emails,
            'opened': opened_emails,
            'clicked': clicked_emails,
            'bounced': bounced_emails,
            'failed': failed_emails,
            'delivery_rate': (delivered_emails / sent_emails * 100) if sent_emails > 0 else 0,
            'open_rate': (opened_emails / delivered_emails * 100) if delivered_emails > 0 else 0,
            'click_rate': (clicked_emails / opened_emails * 100) if opened_emails > 0 else 0,
            'bounce_rate': (bounced_emails / sent_emails * 100) if sent_emails > 0 else 0,
        }

    @staticmethod
    def _calculate_sms_metrics(sms_notifications):
        """Calculate SMS-specific metrics"""
        total_sms = sms_notifications.count()
        sent_sms = sms_notifications.filter(status__in=['sent', 'delivered']).count()
        delivered_sms = sms_notifications.filter(status='delivered').count()
        failed_sms = sms_notifications.filter(status='failed').count()

        # Calculate total cost
        total_cost = sum(
            notification.cost for notification in sms_notifications
            if notification.cost
        )

        return {
            'total': total_sms,
            'sent': sent_sms,
            'delivered': delivered_sms,
            'failed': failed_sms,
            'delivery_rate': (delivered_sms / sent_sms * 100) if sent_sms > 0 else 0,
            'failure_rate': (failed_sms / total_sms * 100) if total_sms > 0 else 0,
            'total_cost': float(total_cost),
            'average_cost': float(total_cost / total_sms) if total_sms > 0 else 0,
        }

    @staticmethod
    def _calculate_push_metrics(push_notifications):
        """Calculate push notification metrics"""
        total_push = push_notifications.count()
        sent_push = push_notifications.filter(status__in=['sent', 'delivered']).count()
        delivered_push = push_notifications.filter(status='delivered').count()
        clicked_push = push_notifications.filter(clicked_at__isnull=False).count()
        dismissed_push = push_notifications.filter(dismissed_at__isnull=False).count()
        failed_push = push_notifications.filter(status='failed').count()

        return {
            'total': total_push,
            'sent': sent_push,
            'delivered': delivered_push,
            'clicked': clicked_push,
            'dismissed': dismissed_push,
            'failed': failed_push,
            'delivery_rate': (delivered_push / sent_push * 100) if sent_push > 0 else 0,
            'click_rate': (clicked_push / delivered_push * 100) if delivered_push > 0 else 0,
            'dismissal_rate': (dismissed_push / delivered_push * 100) if delivered_push > 0 else 0,
            'failure_rate': (failed_push / total_push * 100) if total_push > 0 else 0,
        }

    @staticmethod
    def _calculate_template_performance(email_notifications, sms_notifications, push_notifications):
        """Calculate performance metrics by template type"""
        template_performance = {}

        # Email template performance
        for notification in email_notifications:
            if notification.template:
                template_type = notification.template.template_type
                if template_type not in template_performance:
                    template_performance[template_type] = {
                        'total': 0, 'sent': 0, 'delivered': 0, 'opened': 0, 'clicked': 0
                    }

                template_performance[template_type]['total'] += 1
                if notification.status in ['sent', 'delivered']:
                    template_performance[template_type]['sent'] += 1
                if notification.status == 'delivered':
                    template_performance[template_type]['delivered'] += 1
                if notification.opened_at:
                    template_performance[template_type]['opened'] += 1
                if notification.clicked_at:
                    template_performance[template_type]['clicked'] += 1

        # SMS template performance
        for notification in sms_notifications:
            if notification.template:
                template_type = notification.template.template_type
                if template_type not in template_performance:
                    template_performance[template_type] = {
                        'total': 0, 'sent': 0, 'delivered': 0
                    }

                template_performance[template_type]['total'] += 1
                if notification.status in ['sent', 'delivered']:
                    template_performance[template_type]['sent'] += 1
                if notification.status == 'delivered':
                    template_performance[template_type]['delivered'] += 1

        # Push template performance
        for notification in push_notifications:
            if notification.template:
                template_type = notification.template.template_type
                if template_type not in template_performance:
                    template_performance[template_type] = {
                        'total': 0, 'sent': 0, 'delivered': 0, 'clicked': 0
                    }

                template_performance[template_type]['total'] += 1
                if notification.status in ['sent', 'delivered']:
                    template_performance[template_type]['sent'] += 1
                if notification.status == 'delivered':
                    template_performance[template_type]['delivered'] += 1
                if notification.clicked_at:
                    template_performance[template_type]['clicked'] += 1

        return template_performance

    @staticmethod
    def _calculate_hourly_distribution(email_notifications, sms_notifications, push_notifications):
        """Calculate notification distribution by hour of day"""
        hourly_distribution = {str(hour): 0 for hour in range(24)}

        # Count notifications by hour
        for notification in email_notifications:
            hour = notification.created_at.hour
            hourly_distribution[str(hour)] += 1

        for notification in sms_notifications:
            hour = notification.created_at.hour
            hourly_distribution[str(hour)] += 1

        for notification in push_notifications:
            hour = notification.created_at.hour
            hourly_distribution[str(hour)] += 1

        return hourly_distribution

    @staticmethod
    def _calculate_daily_distribution(email_notifications, sms_notifications, push_notifications):
        """Calculate notification distribution by day of week"""
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        daily_distribution = {day: 0 for day in days}

        # Count notifications by day of week
        for notification in email_notifications:
            day_name = days[notification.created_at.weekday()]
            daily_distribution[day_name] += 1

        for notification in sms_notifications:
            day_name = days[notification.created_at.weekday()]
            daily_distribution[day_name] += 1

        for notification in push_notifications:
            day_name = days[notification.created_at.weekday()]
            daily_distribution[day_name] += 1

        return daily_distribution

    @staticmethod
    def _calculate_costs(email_notifications, sms_notifications, push_notifications):
        """Calculate total costs and breakdown by channel"""
        from decimal import Decimal

        # Email costs (usually free or very low cost)
        email_cost = Decimal('0.00')
        email_count = email_notifications.count()

        # SMS costs
        sms_cost = sum(
            notification.cost for notification in sms_notifications
            if notification.cost
        )

        # Push notification costs (usually free)
        push_cost = Decimal('0.00')
        push_count = push_notifications.count()

        total_cost = email_cost + sms_cost + push_cost

        cost_breakdown = {
            'email': {
                'total_cost': float(email_cost),
                'count': email_count,
                'average_cost': float(email_cost / email_count) if email_count > 0 else 0
            },
            'sms': {
                'total_cost': float(sms_cost),
                'count': sms_notifications.count(),
                'average_cost': float(sms_cost / sms_notifications.count()) if sms_notifications.count() > 0 else 0
            },
            'push': {
                'total_cost': float(push_cost),
                'count': push_count,
                'average_cost': float(push_cost / push_count) if push_count > 0 else 0
            }
        }

        return total_cost, cost_breakdown

    @staticmethod
    def track_notification_event(
        event_type: str,
        notification_type: str,
        notification_channel: str,
        notification_id,
        recipient_user=None,
        recipient_email='',
        recipient_phone='',
        user_agent='',
        ip_address=None,
        device_type='',
        provider_name='',
        provider_message_id='',
        event_data=None
    ) -> NotificationEvent:
        """
        Track a notification event for analytics
        """
        event = NotificationEvent.objects.create(
            event_type=event_type,
            notification_type=notification_type,
            notification_channel=notification_channel,
            notification_id=notification_id,
            recipient_user=recipient_user,
            recipient_email=recipient_email,
            recipient_phone=recipient_phone,
            user_agent=user_agent,
            ip_address=ip_address,
            device_type=device_type,
            provider_name=provider_name,
            provider_message_id=provider_message_id,
            event_data=event_data or {}
        )

        return event

    @staticmethod
    def get_user_engagement_metrics(user, days=30):
        """
        Get engagement metrics for a specific user
        """
        from datetime import timedelta

        start_date = timezone.now() - timedelta(days=days)

        # Get user's notification events
        events = NotificationEvent.objects.filter(
            recipient_user=user,
            event_timestamp__gte=start_date
        )

        total_sent = events.filter(event_type='sent').count()
        total_delivered = events.filter(event_type='delivered').count()
        total_opened = events.filter(event_type='opened').count()
        total_clicked = events.filter(event_type='clicked').count()

        # Calculate engagement rates
        delivery_rate = (total_delivered / total_sent * 100) if total_sent > 0 else 0
        open_rate = (total_opened / total_delivered * 100) if total_delivered > 0 else 0
        click_rate = (total_clicked / total_opened * 100) if total_opened > 0 else 0

        # Channel breakdown
        channel_breakdown = {}
        for event in events:
            channel = event.notification_channel
            if channel not in channel_breakdown:
                channel_breakdown[channel] = {'sent': 0, 'opened': 0, 'clicked': 0}

            if event.event_type == 'sent':
                channel_breakdown[channel]['sent'] += 1
            elif event.event_type == 'opened':
                channel_breakdown[channel]['opened'] += 1
            elif event.event_type == 'clicked':
                channel_breakdown[channel]['clicked'] += 1

        return {
            'user_id': user.id,
            'user_name': user.get_full_name(),
            'period_days': days,
            'total_sent': total_sent,
            'total_delivered': total_delivered,
            'total_opened': total_opened,
            'total_clicked': total_clicked,
            'delivery_rate': delivery_rate,
            'open_rate': open_rate,
            'click_rate': click_rate,
            'channel_breakdown': channel_breakdown
        }


class NotificationCampaignService:
    """
    Service for managing notification campaigns
    """

    @staticmethod
    def create_campaign(
        name: str,
        campaign_type: str,
        target_audience: Dict[str, Any],
        description='',
        budget=None,
        start_date=None,
        end_date=None,
        created_by=None
    ) -> NotificationCampaign:
        """
        Create a new notification campaign
        """
        # Estimate recipients based on target audience
        estimated_recipients = NotificationCampaignService._estimate_recipients(target_audience)

        campaign = NotificationCampaign.objects.create(
            name=name,
            description=description,
            campaign_type=campaign_type,
            target_audience=target_audience,
            estimated_recipients=estimated_recipients,
            budget=budget,
            start_date=start_date,
            end_date=end_date,
            created_by=created_by
        )

        return campaign

    @staticmethod
    def _estimate_recipients(target_audience: Dict[str, Any]) -> int:
        """
        Estimate number of recipients based on targeting criteria
        """
        from django.contrib.auth import get_user_model
        User = get_user_model()

        queryset = User.objects.all()

        # Apply targeting filters
        if 'user_type' in target_audience:
            queryset = queryset.filter(user_type=target_audience['user_type'])

        if 'is_active' in target_audience:
            queryset = queryset.filter(is_active=target_audience['is_active'])

        if 'age_range' in target_audience:
            # This would require a birth_date field or age calculation
            pass

        if 'location' in target_audience:
            # This would require location data
            pass

        return queryset.count()

    @staticmethod
    def launch_campaign(campaign_id: str) -> bool:
        """
        Launch a campaign
        """
        try:
            campaign = NotificationCampaign.objects.get(campaign_id=campaign_id)

            if campaign.status == 'draft':
                campaign.status = 'running'
                campaign.start_date = timezone.now()
                campaign.save()

                # Create notification jobs for the campaign
                NotificationCampaignService._create_campaign_jobs(campaign)

                return True
            else:
                return False
        except NotificationCampaign.DoesNotExist:
            return False

    @staticmethod
    def _create_campaign_jobs(campaign: NotificationCampaign):
        """
        Create notification jobs for a campaign
        """
        # This would create the actual notification jobs based on campaign settings
        # For now, just log that jobs would be created
        logger.info(f"Creating notification jobs for campaign {campaign.campaign_id}")

    @staticmethod
    def pause_campaign(campaign_id: str) -> bool:
        """
        Pause a running campaign
        """
        try:
            campaign = NotificationCampaign.objects.get(campaign_id=campaign_id)

            if campaign.status == 'running':
                campaign.status = 'paused'
                campaign.save()
                return True
            else:
                return False
        except NotificationCampaign.DoesNotExist:
            return False

    @staticmethod
    def resume_campaign(campaign_id: str) -> bool:
        """
        Resume a paused campaign
        """
        try:
            campaign = NotificationCampaign.objects.get(campaign_id=campaign_id)

            if campaign.status == 'paused':
                campaign.status = 'running'
                campaign.save()
                return True
            else:
                return False
        except NotificationCampaign.DoesNotExist:
            return False

    @staticmethod
    def complete_campaign(campaign_id: str) -> bool:
        """
        Mark a campaign as completed
        """
        try:
            campaign = NotificationCampaign.objects.get(campaign_id=campaign_id)

            if campaign.status in ['running', 'paused']:
                campaign.status = 'completed'
                campaign.end_date = timezone.now()
                campaign.save()
                return True
            else:
                return False
        except NotificationCampaign.DoesNotExist:
            return False

    @staticmethod
    def get_campaign_analytics(campaign_id: str) -> Dict[str, Any]:
        """
        Get analytics for a specific campaign
        """
        try:
            campaign = NotificationCampaign.objects.get(campaign_id=campaign_id)

            # Calculate performance metrics
            analytics = {
                'campaign_id': campaign.campaign_id,
                'campaign_name': campaign.name,
                'campaign_type': campaign.campaign_type,
                'status': campaign.status,
                'estimated_recipients': campaign.estimated_recipients,
                'total_sent': campaign.total_sent,
                'total_delivered': campaign.total_delivered,
                'total_opened': campaign.total_opened,
                'total_clicked': campaign.total_clicked,
                'total_conversions': campaign.total_conversions,
                'delivery_rate': campaign.delivery_rate,
                'open_rate': campaign.open_rate,
                'click_rate': campaign.click_rate,
                'conversion_rate': campaign.conversion_rate,
                'budget': float(campaign.budget) if campaign.budget else None,
                'actual_cost': float(campaign.actual_cost),
                'roi': campaign.roi,
                'start_date': campaign.start_date,
                'end_date': campaign.end_date,
                'duration_days': (campaign.end_date - campaign.start_date).days if campaign.end_date and campaign.start_date else None
            }

            return analytics

        except NotificationCampaign.DoesNotExist:
            return {}

    @staticmethod
    def update_campaign_metrics(
        campaign_id: str,
        sent=0,
        delivered=0,
        opened=0,
        clicked=0,
        conversions=0,
        cost=0
    ):
        """
        Update campaign performance metrics
        """
        try:
            campaign = NotificationCampaign.objects.get(campaign_id=campaign_id)

            campaign.total_sent += sent
            campaign.total_delivered += delivered
            campaign.total_opened += opened
            campaign.total_clicked += clicked
            campaign.total_conversions += conversions
            from decimal import Decimal
            campaign.actual_cost += Decimal(str(cost))

            campaign.save()

        except NotificationCampaign.DoesNotExist:
            logger.error(f"Campaign {campaign_id} not found for metrics update")
