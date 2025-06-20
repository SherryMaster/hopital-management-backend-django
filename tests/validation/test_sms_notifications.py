import os
import django
from decimal import Decimal
from datetime import datetime, timedelta

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hospital_backend.settings')
django.setup()

from django.utils import timezone
from notifications.models import (
    SMSTemplate, SMSNotification, SMSConfiguration, SMSAnalytics
)
from notifications.services import SMSNotificationService, SMSTemplateService
from accounts.models import User
from patients.models import Patient
from appointments.models import Appointment

def test_sms_notification_system():
    print("=== Testing SMS Notification System ===")
    
    # Get required objects
    user = User.objects.filter(user_type='admin').first()
    patient = Patient.objects.first()
    appointment = Appointment.objects.first()
    
    print(f'User: {user.get_full_name() if user else "No admin user"}')
    print(f'Patient: {patient.patient_id if patient else "No patient"}')
    print(f'Appointment: {appointment.id if appointment else "No appointment"}')
    
    # Test 1: Create SMS templates
    print('\n1. Creating SMS templates...')
    
    # Appointment reminder template
    appointment_template = SMSTemplate.objects.create(
        name='Appointment Reminder SMS',
        template_type='appointment_reminder',
        description='SMS reminder for upcoming appointments',
        message_template='Hi {{patient_name}}! Reminder: You have an appointment with {{doctor_name}} on {{appointment_date}} at {{appointment_time}}. {{hospital_name}}',
        available_variables=[
            'patient_name', 'doctor_name', 'appointment_date', 'appointment_time', 'hospital_name'
        ],
        is_active=True,
        is_default=True,
        max_length=160,
        created_by=user
    )
    
    # Verification code template
    verification_template = SMSTemplate.objects.create(
        name='Verification Code SMS',
        template_type='verification_code',
        description='SMS for sending verification codes',
        message_template='Your {{hospital_name}} verification code is: {{verification_code}}. Valid for 10 minutes. Do not share this code.',
        available_variables=[
            'user_name', 'verification_code', 'hospital_name'
        ],
        is_active=True,
        is_default=True,
        max_length=160,
        created_by=user
    )
    
    # Emergency alert template
    emergency_template = SMSTemplate.objects.create(
        name='Emergency Alert SMS',
        template_type='emergency_alert',
        description='SMS for emergency notifications',
        message_template='EMERGENCY: {{alert_message}} Please contact {{hospital_name}} immediately at {{emergency_phone}}.',
        available_variables=[
            'patient_name', 'alert_message', 'hospital_name', 'emergency_phone'
        ],
        is_active=True,
        is_default=True,
        max_length=160,
        created_by=user
    )
    
    print(f'✓ Created appointment reminder template: {appointment_template.name} ({len(appointment_template.message_template)} chars)')
    print(f'✓ Created verification code template: {verification_template.name} ({len(verification_template.message_template)} chars)')
    print(f'✓ Created emergency alert template: {emergency_template.name} ({len(emergency_template.message_template)} chars)')
    
    # Test 2: Create SMS configuration
    print('\n2. Creating SMS configuration...')
    
    # Mock SMS provider configuration
    sms_config = SMSConfiguration.objects.create(
        name='Mock SMS Provider',
        provider_type='mock',
        configuration={
            'api_key': 'mock_api_key_12345',
            'sender_id': 'HOSPITAL',
            'webhook_url': 'https://hospital.com/sms/webhook'
        },
        is_active=True,
        is_default=True,
        daily_limit=1000,
        hourly_limit=100,
        cost_per_sms=Decimal('0.05'),
        currency='USD'
    )
    
    # Twilio configuration (for reference)
    twilio_config = SMSConfiguration.objects.create(
        name='Twilio SMS Provider',
        provider_type='twilio',
        configuration={
            'account_sid': 'twilio_account_sid',
            'auth_token': 'twilio_auth_token',
            'from_phone': '+1234567890'
        },
        is_active=False,
        is_default=False,
        daily_limit=5000,
        hourly_limit=500,
        cost_per_sms=Decimal('0.0075'),
        currency='USD'
    )
    
    print(f'✓ Created mock SMS configuration: {sms_config.name}')
    print(f'  Provider: {sms_config.get_provider_type_display()}')
    print(f'  Daily limit: {sms_config.daily_limit}')
    print(f'  Cost per SMS: ${sms_config.cost_per_sms}')
    print(f'✓ Created Twilio configuration: {twilio_config.name} (inactive)')
    
    # Test 3: Test template rendering
    print('\n3. Testing template rendering...')
    
    template_service = SMSTemplateService()
    
    # Test appointment reminder template
    appointment_variables = {
        'patient_name': 'John',
        'doctor_name': 'Dr. Smith',
        'appointment_date': '06/20/2025',
        'appointment_time': '2:00 PM',
        'hospital_name': 'City Hospital'
    }
    
    rendered_appointment = template_service.render_template(appointment_template, appointment_variables)
    print(f'✓ Rendered appointment reminder:')
    print(f'  Message: "{rendered_appointment}"')
    print(f'  Length: {len(rendered_appointment)} characters')
    
    # Test verification code template
    verification_variables = {
        'user_name': 'John',
        'verification_code': '123456',
        'hospital_name': 'City Hospital'
    }
    
    rendered_verification = template_service.render_template(verification_template, verification_variables)
    print(f'✓ Rendered verification code:')
    print(f'  Message: "{rendered_verification}"')
    print(f'  Length: {len(rendered_verification)} characters')
    
    # Test 4: Create SMS notifications
    print('\n4. Creating SMS notifications...')
    
    sms_service = SMSNotificationService()
    
    # Create appointment reminder notification
    if patient:
        appointment_notification = sms_service.send_notification(
            template_type='appointment_reminder',
            recipient_phone='+1234567890',
            variables=appointment_variables,
            recipient_user=patient.user,
            priority='normal'
        )
        
        print(f'✓ Created appointment reminder: {appointment_notification.notification_id}')
        print(f'  Recipient: {appointment_notification.recipient_phone}')
        print(f'  Status: {appointment_notification.status}')
        print(f'  Message: "{appointment_notification.message}"')
        print(f'  Cost: ${appointment_notification.cost}')
    
    # Create verification code notification
    verification_notification = sms_service.send_notification(
        template_type='verification_code',
        recipient_phone='+1987654321',
        variables=verification_variables,
        priority='high'
    )
    
    print(f'✓ Created verification code: {verification_notification.notification_id}')
    print(f'  Recipient: {verification_notification.recipient_phone}')
    print(f'  Status: {verification_notification.status}')
    print(f'  Priority: {verification_notification.priority}')
    print(f'  Cost: ${verification_notification.cost}')
    
    # Create emergency alert notification
    emergency_variables = {
        'patient_name': 'John Doe',
        'alert_message': 'Test results require immediate attention',
        'hospital_name': 'City Hospital',
        'emergency_phone': '911'
    }
    
    emergency_notification = sms_service.send_notification(
        template_type='emergency_alert',
        recipient_phone='+1555123456',
        variables=emergency_variables,
        priority='urgent'
    )
    
    print(f'✓ Created emergency alert: {emergency_notification.notification_id}')
    print(f'  Recipient: {emergency_notification.recipient_phone}')
    print(f'  Status: {emergency_notification.status}')
    print(f'  Priority: {emergency_notification.priority}')
    
    # Test 5: SMS analytics
    print('\n5. Testing SMS analytics...')
    
    # Create analytics record
    today = timezone.now().date()
    analytics = SMSAnalytics.objects.create(
        date=today,
        sms_sent=15,
        sms_delivered=14,
        sms_failed=1,
        sms_undelivered=0,
        total_cost=Decimal('0.75'),
        currency='USD',
        template_metrics={
            'appointment_reminder': {'sent': 8, 'delivered': 8},
            'verification_code': {'sent': 5, 'delivered': 4},
            'emergency_alert': {'sent': 2, 'delivered': 2}
        },
        provider_metrics={
            'mock': {'sent': 15, 'delivered': 14, 'cost': '0.75'}
        }
    )
    
    print(f'✓ Created analytics for {analytics.date}:')
    print(f'  SMS sent: {analytics.sms_sent}')
    print(f'  Delivery rate: {analytics.delivery_rate:.1f}%')
    print(f'  Failure rate: {analytics.failure_rate:.1f}%')
    print(f'  Total cost: ${analytics.total_cost}')
    print(f'  Average cost per SMS: ${analytics.average_cost_per_sms:.4f}')
    
    # Test 6: System statistics
    print('\n6. System statistics...')
    
    total_templates = SMSTemplate.objects.count()
    active_templates = SMSTemplate.objects.filter(is_active=True).count()
    total_notifications = SMSNotification.objects.count()
    total_configurations = SMSConfiguration.objects.count()
    active_configurations = SMSConfiguration.objects.filter(is_active=True).count()
    
    print(f'✓ SMS system statistics:')
    print(f'  Total templates: {total_templates}')
    print(f'  Active templates: {active_templates}')
    print(f'  Total notifications: {total_notifications}')
    print(f'  SMS configurations: {total_configurations}')
    print(f'  Active configurations: {active_configurations}')
    
    # Notification status breakdown
    status_counts = {}
    for status_choice in SMSNotification.STATUS_CHOICES:
        status = status_choice[0]
        count = SMSNotification.objects.filter(status=status).count()
        if count > 0:
            status_counts[status] = count
    
    print(f'  Notification status breakdown: {status_counts}')
    
    # Template type breakdown
    template_counts = {}
    for template_type in SMSTemplate.TEMPLATE_TYPES:
        type_name = template_type[0]
        count = SMSTemplate.objects.filter(template_type=type_name, is_active=True).count()
        if count > 0:
            template_counts[type_name] = count
    
    print(f'  Active template types: {template_counts}')
    
    # Cost analysis
    total_cost = sum(
        notification.cost for notification in SMSNotification.objects.all() 
        if notification.cost is not None
    )
    print(f'  Total SMS cost: ${total_cost}')
    
    # Test 7: Provider comparison
    print('\n7. Provider comparison...')
    
    providers = SMSConfiguration.objects.all()
    for provider in providers:
        status = "Active" if provider.is_active else "Inactive"
        print(f'  {provider.name}: {provider.get_provider_type_display()} - {status}')
        print(f'    Daily limit: {provider.daily_limit}')
        print(f'    Cost per SMS: ${provider.cost_per_sms}')
        print(f'    SMS sent today: {provider.sms_sent_today}')
        print(f'    Total cost today: ${provider.total_cost_today}')
    
    print('\n=== SMS Notification System Testing Complete ===')

if __name__ == '__main__':
    test_sms_notification_system()
