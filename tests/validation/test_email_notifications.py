import os
import django
from datetime import datetime, timedelta

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hospital_backend.settings')
django.setup()

from django.utils import timezone
from notifications.models import (
    EmailTemplate, EmailNotification, EmailConfiguration,
    EmailSubscription, EmailAnalytics
)
from notifications.services import EmailNotificationService, EmailTemplateService
from accounts.models import User
from patients.models import Patient
from appointments.models import Appointment

def test_email_notification_system():
    print("=== Testing Email Notification System ===")
    
    # Get required objects
    user = User.objects.filter(user_type='admin').first()
    patient = Patient.objects.first()
    appointment = Appointment.objects.first()
    
    print(f'User: {user.get_full_name() if user else "No admin user"}')
    print(f'Patient: {patient.patient_id if patient else "No patient"}')
    print(f'Appointment: {appointment.id if appointment else "No appointment"}')
    
    # Test 1: Create email templates
    print('\n1. Creating email templates...')
    
    # Appointment confirmation template
    appointment_template = EmailTemplate.objects.create(
        name='Appointment Confirmation Template',
        template_type='appointment_confirmation',
        description='Template for confirming patient appointments',
        subject_template='Appointment Confirmed - {{appointment_date}} at {{appointment_time}}',
        html_template='''
        <html>
        <body>
            <h2>Appointment Confirmation</h2>
            <p>Dear {{patient_name}},</p>
            
            <p>Your appointment has been confirmed with the following details:</p>
            
            <div style="background-color: #f5f5f5; padding: 15px; margin: 10px 0;">
                <strong>Doctor:</strong> {{doctor_name}}<br>
                <strong>Date:</strong> {{appointment_date}}<br>
                <strong>Time:</strong> {{appointment_time}}<br>
                <strong>Department:</strong> {{department}}<br>
                <strong>Appointment ID:</strong> {{appointment_id}}
            </div>
            
            <p>Please arrive 15 minutes before your scheduled time.</p>
            
            <p>If you need to reschedule or cancel, please contact us at least 24 hours in advance.</p>
            
            <p>Best regards,<br>{{hospital_name}}</p>
        </body>
        </html>
        ''',
        text_template='''
        Appointment Confirmation
        
        Dear {{patient_name}},
        
        Your appointment has been confirmed with the following details:
        
        Doctor: {{doctor_name}}
        Date: {{appointment_date}}
        Time: {{appointment_time}}
        Department: {{department}}
        Appointment ID: {{appointment_id}}
        
        Please arrive 15 minutes before your scheduled time.
        
        If you need to reschedule or cancel, please contact us at least 24 hours in advance.
        
        Best regards,
        {{hospital_name}}
        ''',
        available_variables=[
            'patient_name', 'doctor_name', 'appointment_date', 'appointment_time',
            'department', 'appointment_id', 'hospital_name'
        ],
        is_active=True,
        is_default=True,
        created_by=user
    )
    
    # Payment confirmation template
    payment_template = EmailTemplate.objects.create(
        name='Payment Confirmation Template',
        template_type='payment_confirmation',
        description='Template for confirming payments',
        subject_template='Payment Received - ${{payment_amount}}',
        html_template='''
        <html>
        <body>
            <h2>Payment Confirmation</h2>
            <p>Dear {{patient_name}},</p>
            
            <p>We have successfully received your payment:</p>
            
            <div style="background-color: #e8f5e8; padding: 15px; margin: 10px 0;">
                <strong>Amount:</strong> ${{payment_amount}}<br>
                <strong>Payment Date:</strong> {{payment_date}}<br>
                <strong>Payment Method:</strong> {{payment_method}}<br>
                <strong>Transaction ID:</strong> {{transaction_id}}<br>
                <strong>Invoice Number:</strong> {{invoice_number}}
            </div>
            
            <p>Thank you for your prompt payment.</p>
            
            <p>Best regards,<br>{{hospital_name}}</p>
        </body>
        </html>
        ''',
        text_template='''
        Payment Confirmation
        
        Dear {{patient_name}},
        
        We have successfully received your payment:
        
        Amount: ${{payment_amount}}
        Payment Date: {{payment_date}}
        Payment Method: {{payment_method}}
        Transaction ID: {{transaction_id}}
        Invoice Number: {{invoice_number}}
        
        Thank you for your prompt payment.
        
        Best regards,
        {{hospital_name}}
        ''',
        available_variables=[
            'patient_name', 'payment_amount', 'payment_date', 'payment_method',
            'transaction_id', 'invoice_number', 'hospital_name'
        ],
        is_active=True,
        is_default=True,
        created_by=user
    )
    
    print(f'✓ Created appointment template: {appointment_template.name}')
    print(f'✓ Created payment template: {payment_template.name}')
    
    # Test 2: Create email configuration
    print('\n2. Creating email configuration...')
    
    email_config = EmailConfiguration.objects.create(
        name='Default SMTP Configuration',
        provider_type='smtp',
        configuration={
            'host': 'smtp.gmail.com',
            'port': 587,
            'use_tls': True,
            'username': 'hospital@example.com',
            'password': 'app_password',
            'from_email': 'noreply@hospital.com'
        },
        is_active=True,
        is_default=True,
        daily_limit=1000,
        hourly_limit=100
    )
    
    print(f'✓ Created email configuration: {email_config.name}')
    print(f'  Provider: {email_config.get_provider_type_display()}')
    print(f'  Daily limit: {email_config.daily_limit}')
    print(f'  Hourly limit: {email_config.hourly_limit}')
    
    # Test 3: Create email subscriptions
    print('\n3. Creating email subscriptions...')
    
    if patient:
        # Create subscriptions for patient
        subscriptions = [
            ('appointment_reminders', True, 'immediate'),
            ('test_results', True, 'immediate'),
            ('payment_reminders', True, 'daily'),
            ('promotional', False, 'weekly'),
        ]
        
        for sub_type, is_subscribed, frequency in subscriptions:
            subscription = EmailSubscription.objects.create(
                user=patient.user,
                subscription_type=sub_type,
                is_subscribed=is_subscribed,
                frequency=frequency
            )
            status = "Subscribed" if is_subscribed else "Unsubscribed"
            print(f'  {subscription.get_subscription_type_display()}: {status} ({frequency})')
    
    # Test 4: Test template rendering
    print('\n4. Testing template rendering...')
    
    template_service = EmailTemplateService()
    
    # Test appointment template
    appointment_variables = {
        'patient_name': 'John Doe',
        'doctor_name': 'Dr. Smith',
        'appointment_date': 'June 20, 2025',
        'appointment_time': '2:00 PM',
        'department': 'Cardiology',
        'appointment_id': 'APT001',
        'hospital_name': 'City General Hospital'
    }
    
    rendered_appointment = template_service.render_template(appointment_template, appointment_variables)
    print(f'✓ Rendered appointment template:')
    print(f'  Subject: {rendered_appointment["subject"]}')
    print(f'  Text length: {len(rendered_appointment["text_content"])} chars')
    print(f'  HTML length: {len(rendered_appointment["html_content"])} chars')
    
    # Test payment template
    payment_variables = {
        'patient_name': 'John Doe',
        'payment_amount': '150.00',
        'payment_date': 'June 19, 2025',
        'payment_method': 'Credit Card',
        'transaction_id': 'TXN123456',
        'invoice_number': 'INV001',
        'hospital_name': 'City General Hospital'
    }
    
    rendered_payment = template_service.render_template(payment_template, payment_variables)
    print(f'✓ Rendered payment template:')
    print(f'  Subject: {rendered_payment["subject"]}')
    print(f'  Text length: {len(rendered_payment["text_content"])} chars')
    print(f'  HTML length: {len(rendered_payment["html_content"])} chars')
    
    # Test 5: Create email notifications
    print('\n5. Creating email notifications...')
    
    email_service = EmailNotificationService()
    
    # Create appointment confirmation notification
    if patient:
        appointment_notification = email_service.send_notification(
            template_type='appointment_confirmation',
            recipient_email=patient.user.email,
            variables=appointment_variables,
            recipient_user=patient.user,
            priority='normal'
        )
        
        print(f'✓ Created appointment notification: {appointment_notification.notification_id}')
        print(f'  Recipient: {appointment_notification.recipient_email}')
        print(f'  Status: {appointment_notification.status}')
        print(f'  Subject: {appointment_notification.subject}')
    
    # Create payment confirmation notification
    if patient:
        payment_notification = email_service.send_notification(
            template_type='payment_confirmation',
            recipient_email=patient.user.email,
            variables=payment_variables,
            recipient_user=patient.user,
            priority='high'
        )
        
        print(f'✓ Created payment notification: {payment_notification.notification_id}')
        print(f'  Recipient: {payment_notification.recipient_email}')
        print(f'  Status: {payment_notification.status}')
        print(f'  Priority: {payment_notification.priority}')
    
    # Test 6: Email analytics
    print('\n6. Testing email analytics...')
    
    # Create analytics record
    today = timezone.now().date()
    analytics = EmailAnalytics.objects.create(
        date=today,
        emails_sent=10,
        emails_delivered=9,
        emails_opened=7,
        emails_clicked=3,
        emails_bounced=1,
        emails_failed=0,
        template_metrics={
            'appointment_confirmation': {'sent': 6, 'opened': 5},
            'payment_confirmation': {'sent': 4, 'opened': 2}
        },
        provider_metrics={
            'smtp': {'sent': 10, 'delivered': 9}
        }
    )
    
    print(f'✓ Created analytics for {analytics.date}:')
    print(f'  Emails sent: {analytics.emails_sent}')
    print(f'  Delivery rate: {analytics.delivery_rate:.1f}%')
    print(f'  Open rate: {analytics.open_rate:.1f}%')
    print(f'  Click rate: {analytics.click_rate:.1f}%')
    print(f'  Bounce rate: {analytics.bounce_rate:.1f}%')
    
    # Test 7: System statistics
    print('\n7. System statistics...')
    
    total_templates = EmailTemplate.objects.count()
    active_templates = EmailTemplate.objects.filter(is_active=True).count()
    total_notifications = EmailNotification.objects.count()
    total_configurations = EmailConfiguration.objects.count()
    total_subscriptions = EmailSubscription.objects.count()
    
    print(f'✓ Email system statistics:')
    print(f'  Total templates: {total_templates}')
    print(f'  Active templates: {active_templates}')
    print(f'  Total notifications: {total_notifications}')
    print(f'  Email configurations: {total_configurations}')
    print(f'  User subscriptions: {total_subscriptions}')
    
    # Notification status breakdown
    status_counts = {}
    for status_choice in EmailNotification.STATUS_CHOICES:
        status = status_choice[0]
        count = EmailNotification.objects.filter(status=status).count()
        if count > 0:
            status_counts[status] = count
    
    print(f'  Notification status breakdown: {status_counts}')
    
    # Template type breakdown
    template_counts = {}
    for template_type in EmailTemplate.TEMPLATE_TYPES:
        type_name = template_type[0]
        count = EmailTemplate.objects.filter(template_type=type_name, is_active=True).count()
        if count > 0:
            template_counts[type_name] = count
    
    print(f'  Active template types: {template_counts}')
    
    print('\n=== Email Notification System Testing Complete ===')

if __name__ == '__main__':
    test_email_notification_system()
