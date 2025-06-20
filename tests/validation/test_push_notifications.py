import os
import django
from datetime import datetime, timedelta

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hospital_backend.settings')
django.setup()

from django.utils import timezone
from notifications.models import (
    PushNotificationTemplate, PushNotification, PushNotificationConfiguration,
    PushNotificationAnalytics, DeviceToken
)
from notifications.services import PushNotificationService, PushNotificationTemplateService
from accounts.models import User
from patients.models import Patient
from appointments.models import Appointment

def test_push_notification_system():
    print("=== Testing Push Notification System ===")
    
    # Get required objects
    user = User.objects.filter(user_type='admin').first()
    patient = Patient.objects.first()
    appointment = Appointment.objects.first()
    
    print(f'User: {user.get_full_name() if user else "No admin user"}')
    print(f'Patient: {patient.patient_id if patient else "No patient"}')
    print(f'Appointment: {appointment.id if appointment else "No appointment"}')
    
    # Test 1: Create push notification templates
    print('\n1. Creating push notification templates...')
    
    # Appointment reminder template
    appointment_template = PushNotificationTemplate.objects.create(
        name='Appointment Reminder Push',
        template_type='appointment_reminder',
        description='Push notification for upcoming appointments',
        title_template='Appointment Reminder',
        body_template='Hi {{patient_name}}! You have an appointment with {{doctor_name}} on {{appointment_date}} at {{appointment_time}}.',
        icon_url='https://hospital.com/icons/appointment.png',
        action_url='https://hospital.com/appointments/{{appointment_id}}',
        available_variables=[
            'patient_name', 'doctor_name', 'appointment_date', 'appointment_time', 'appointment_id'
        ],
        is_active=True,
        is_default=True,
        requires_interaction=False,
        created_by=user
    )
    
    # Test results ready template
    test_results_template = PushNotificationTemplate.objects.create(
        name='Test Results Ready Push',
        template_type='test_results_ready',
        description='Push notification when test results are available',
        title_template='Test Results Available',
        body_template='{{patient_name}}, your {{test_name}} results are now available. Tap to view.',
        icon_url='https://hospital.com/icons/results.png',
        action_url='https://hospital.com/results/{{result_id}}',
        available_variables=[
            'patient_name', 'test_name', 'result_id', 'hospital_name'
        ],
        is_active=True,
        is_default=True,
        requires_interaction=True,
        created_by=user
    )
    
    # Emergency alert template
    emergency_template = PushNotificationTemplate.objects.create(
        name='Emergency Alert Push',
        template_type='emergency_alert',
        description='Push notification for emergency situations',
        title_template='EMERGENCY ALERT',
        body_template='{{alert_message}} Please contact {{hospital_name}} immediately.',
        icon_url='https://hospital.com/icons/emergency.png',
        image_url='https://hospital.com/images/emergency-banner.png',
        action_url='tel:911',
        available_variables=[
            'patient_name', 'alert_message', 'hospital_name', 'emergency_phone'
        ],
        is_active=True,
        is_default=True,
        requires_interaction=True,
        created_by=user
    )
    
    print(f'✓ Created appointment reminder template: {appointment_template.name}')
    print(f'  Title: "{appointment_template.title_template}"')
    print(f'  Body length: {len(appointment_template.body_template)} chars')
    print(f'✓ Created test results template: {test_results_template.name}')
    print(f'  Requires interaction: {test_results_template.requires_interaction}')
    print(f'✓ Created emergency alert template: {emergency_template.name}')
    print(f'  Has image: {bool(emergency_template.image_url)}')
    
    # Test 2: Create push notification configuration
    print('\n2. Creating push notification configuration...')
    
    # Mock push provider configuration
    push_config = PushNotificationConfiguration.objects.create(
        name='Mock Push Provider',
        provider_type='mock',
        configuration={
            'api_key': 'mock_push_api_key_12345',
            'app_id': 'hospital_app',
            'webhook_url': 'https://hospital.com/push/webhook'
        },
        is_active=True,
        is_default=True,
        daily_limit=10000,
        hourly_limit=1000
    )
    
    # Firebase FCM configuration (for reference)
    fcm_config = PushNotificationConfiguration.objects.create(
        name='Firebase Cloud Messaging',
        provider_type='fcm',
        configuration={
            'server_key': 'fcm_server_key',
            'sender_id': '123456789',
            'project_id': 'hospital-app-firebase'
        },
        is_active=False,
        is_default=False,
        daily_limit=50000,
        hourly_limit=5000
    )
    
    print(f'✓ Created mock push configuration: {push_config.name}')
    print(f'  Provider: {push_config.get_provider_type_display()}')
    print(f'  Daily limit: {push_config.daily_limit}')
    print(f'✓ Created FCM configuration: {fcm_config.name} (inactive)')
    
    # Test 3: Register device tokens
    print('\n3. Registering device tokens...')
    
    push_service = PushNotificationService()
    
    if patient:
        # Register web device
        web_device = push_service.register_device_token(
            user=patient.user,
            device_token='web_push_token_abc123def456',
            device_type='web',
            device_name='Chrome Browser',
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            ip_address='192.168.1.100'
        )
        
        # Register mobile device
        mobile_device = push_service.register_device_token(
            user=patient.user,
            device_token='fcm_token_xyz789uvw012',
            device_type='android',
            device_name='Samsung Galaxy S21',
            user_agent='HospitalApp/1.0 Android/11',
            ip_address='192.168.1.101'
        )
        
        print(f'✓ Registered web device: {web_device.device_name}')
        print(f'  Token: {web_device.device_token[:20]}...')
        print(f'  Type: {web_device.get_device_type_display()}')
        print(f'✓ Registered mobile device: {mobile_device.device_name}')
        print(f'  Token: {mobile_device.device_token[:20]}...')
        print(f'  Type: {mobile_device.get_device_type_display()}')
    
    # Test 4: Test template rendering
    print('\n4. Testing template rendering...')
    
    template_service = PushNotificationTemplateService()
    
    # Test appointment reminder template
    appointment_variables = {
        'patient_name': 'John',
        'doctor_name': 'Dr. Smith',
        'appointment_date': 'June 20, 2025',
        'appointment_time': '2:00 PM',
        'appointment_id': 'APT001'
    }
    
    rendered_appointment = template_service.render_template(appointment_template, appointment_variables)
    print(f'✓ Rendered appointment reminder:')
    print(f'  Title: "{rendered_appointment["title"]}"')
    print(f'  Body: "{rendered_appointment["body"]}"')
    print(f'  Action URL: {rendered_appointment.get("action_url", "None")}')
    
    # Test test results template
    test_variables = {
        'patient_name': 'John',
        'test_name': 'Blood Test',
        'result_id': 'RES001',
        'hospital_name': 'City Hospital'
    }
    
    rendered_test = template_service.render_template(test_results_template, test_variables)
    print(f'✓ Rendered test results notification:')
    print(f'  Title: "{rendered_test["title"]}"')
    print(f'  Body: "{rendered_test["body"]}"')
    
    # Test 5: Create push notifications
    print('\n5. Creating push notifications...')
    
    # Create appointment reminder notification
    if patient:
        appointment_notification = push_service.send_notification(
            template_type='appointment_reminder',
            recipient_user=patient.user,
            variables=appointment_variables,
            device_type='web',
            priority='normal'
        )
        
        print(f'✓ Created appointment reminder: {appointment_notification.notification_id}')
        print(f'  Recipient: {appointment_notification.recipient_user.get_full_name()}')
        print(f'  Device type: {appointment_notification.device_type}')
        print(f'  Status: {appointment_notification.status}')
        print(f'  Title: "{appointment_notification.title}"')
    
    # Create test results notification
    if patient:
        test_notification = push_service.send_notification(
            template_type='test_results_ready',
            recipient_user=patient.user,
            variables=test_variables,
            device_type='android',
            priority='high',
            custom_data={'result_id': 'RES001', 'test_type': 'blood_test'}
        )
        
        print(f'✓ Created test results notification: {test_notification.notification_id}')
        print(f'  Device type: {test_notification.device_type}')
        print(f'  Priority: {test_notification.priority}')
        print(f'  Custom data: {test_notification.custom_data}')
    
    # Create emergency alert notification
    if patient:
        emergency_variables = {
            'patient_name': patient.user.get_full_name(),
            'alert_message': 'Critical lab results require immediate attention',
            'hospital_name': 'City Hospital',
            'emergency_phone': '911'
        }
        
        emergency_notification = push_service.send_notification(
            template_type='emergency_alert',
            recipient_user=patient.user,
            variables=emergency_variables,
            device_type='web',
            priority='urgent'
        )
        
        print(f'✓ Created emergency alert: {emergency_notification.notification_id}')
        print(f'  Priority: {emergency_notification.priority}')
        print(f'  Requires interaction: {emergency_notification.template.requires_interaction}')
    
    # Test 6: Push notification analytics
    print('\n6. Testing push notification analytics...')
    
    # Create analytics record
    today = timezone.now().date()
    analytics = PushNotificationAnalytics.objects.create(
        date=today,
        notifications_sent=25,
        notifications_delivered=23,
        notifications_clicked=12,
        notifications_dismissed=8,
        notifications_failed=2,
        notifications_expired=0,
        device_metrics={
            'web': {'sent': 15, 'delivered': 14, 'clicked': 8},
            'android': {'sent': 8, 'delivered': 7, 'clicked': 3},
            'ios': {'sent': 2, 'delivered': 2, 'clicked': 1}
        },
        template_metrics={
            'appointment_reminder': {'sent': 12, 'clicked': 6},
            'test_results_ready': {'sent': 8, 'clicked': 4},
            'emergency_alert': {'sent': 5, 'clicked': 2}
        },
        provider_metrics={
            'mock': {'sent': 25, 'delivered': 23}
        }
    )
    
    print(f'✓ Created analytics for {analytics.date}:')
    print(f'  Notifications sent: {analytics.notifications_sent}')
    print(f'  Delivery rate: {analytics.delivery_rate:.1f}%')
    print(f'  Click rate: {analytics.click_rate:.1f}%')
    print(f'  Dismissal rate: {analytics.dismissal_rate:.1f}%')
    print(f'  Failure rate: {analytics.failure_rate:.1f}%')
    
    # Test 7: System statistics
    print('\n7. System statistics...')
    
    total_templates = PushNotificationTemplate.objects.count()
    active_templates = PushNotificationTemplate.objects.filter(is_active=True).count()
    total_notifications = PushNotification.objects.count()
    total_configurations = PushNotificationConfiguration.objects.count()
    total_devices = DeviceToken.objects.count()
    active_devices = DeviceToken.objects.filter(is_active=True).count()
    
    print(f'✓ Push notification system statistics:')
    print(f'  Total templates: {total_templates}')
    print(f'  Active templates: {active_templates}')
    print(f'  Total notifications: {total_notifications}')
    print(f'  Push configurations: {total_configurations}')
    print(f'  Total devices: {total_devices}')
    print(f'  Active devices: {active_devices}')
    
    # Notification status breakdown
    status_counts = {}
    for status_choice in PushNotification.STATUS_CHOICES:
        status = status_choice[0]
        count = PushNotification.objects.filter(status=status).count()
        if count > 0:
            status_counts[status] = count
    
    print(f'  Notification status breakdown: {status_counts}')
    
    # Device type breakdown
    device_counts = {}
    for device_type in DeviceToken.DEVICE_TYPES:
        type_name = device_type[0]
        count = DeviceToken.objects.filter(device_type=type_name, is_active=True).count()
        if count > 0:
            device_counts[type_name] = count
    
    print(f'  Active device types: {device_counts}')
    
    print('\n=== Push Notification System Testing Complete ===')

if __name__ == '__main__':
    test_push_notification_system()
