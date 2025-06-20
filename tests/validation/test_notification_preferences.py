import os
import django
from datetime import datetime, timedelta, time

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hospital_backend.settings')
django.setup()

from django.utils import timezone
from notifications.models import (
    NotificationPreference, NotificationSettings, NotificationBlacklist, NotificationSchedule,
    TemplateLanguage
)
from notifications.services import NotificationPreferenceService
from accounts.models import User
from patients.models import Patient

def test_notification_preferences_system():
    print("=== Testing Notification Preferences System ===")
    
    # Get required objects
    patient = Patient.objects.first()
    user = patient.user if patient else User.objects.filter(user_type='patient').first()
    
    print(f'User: {user.get_full_name() if user else "No patient user"}')
    
    # Test 1: Create default notification settings
    print('\n1. Creating default notification settings...')
    
    preference_service = NotificationPreferenceService()
    
    # Create default settings
    settings = preference_service.create_default_settings(user)
    
    print(f'✓ Created default settings for {user.get_full_name()}:')
    print(f'  Notifications enabled: {settings.notifications_enabled}')
    print(f'  Email enabled: {settings.email_notifications_enabled}')
    print(f'  SMS enabled: {settings.sms_notifications_enabled}')
    print(f'  Push enabled: {settings.push_notifications_enabled}')
    print(f'  In-app enabled: {settings.in_app_notifications_enabled}')
    print(f'  Primary email: {settings.primary_email}')
    print(f'  Timezone: {settings.timezone}')
    print(f'  Default language: {settings.default_language.name if settings.default_language else "None"}')
    
    # Test 2: Create default notification preferences
    print('\n2. Creating default notification preferences...')
    
    preferences = preference_service.create_default_preferences(user)
    
    print(f'✓ Created {len(preferences)} default preferences')
    
    # Count preferences by channel
    channel_counts = {}
    enabled_counts = {}
    
    for pref in preferences:
        channel = pref.channel
        if channel not in channel_counts:
            channel_counts[channel] = 0
            enabled_counts[channel] = 0
        channel_counts[channel] += 1
        if pref.is_enabled:
            enabled_counts[channel] += 1
    
    for channel, total in channel_counts.items():
        enabled = enabled_counts[channel]
        print(f'  {channel.upper()}: {enabled}/{total} enabled')
    
    # Test 3: Test preference checking
    print('\n3. Testing preference checking...')
    
    # Test appointment reminder preferences
    test_cases = [
        ('appointment_reminder', 'email', 'normal'),
        ('appointment_reminder', 'sms', 'normal'),
        ('appointment_reminder', 'push', 'high'),
        ('marketing', 'email', 'normal'),
        ('emergency_alert', 'sms', 'urgent'),
        ('test_results_ready', 'push', 'high'),
    ]
    
    for notification_type, channel, priority in test_cases:
        should_receive = preference_service.check_user_preference(
            user=user,
            notification_type=notification_type,
            channel=channel,
            priority=priority
        )
        
        print(f'✓ {notification_type} via {channel} ({priority}): {should_receive}')
    
    # Test 4: Create and test blacklist
    print('\n4. Testing notification blacklist...')
    
    # Create blacklist entries
    email_blacklist = NotificationBlacklist.objects.create(
        user=user,
        blacklist_type='email',
        value='spam@example.com',
        reason='Spam email address',
        is_active=True
    )
    
    domain_blacklist = NotificationBlacklist.objects.create(
        user=user,
        blacklist_type='domain',
        value='marketing.com',
        reason='Marketing domain',
        is_active=True
    )
    
    phone_blacklist = NotificationBlacklist.objects.create(
        user=user,
        blacklist_type='phone',
        value='+1234567890',
        reason='Unwanted calls',
        is_active=True
    )
    
    print(f'✓ Created email blacklist: {email_blacklist.value}')
    print(f'✓ Created domain blacklist: {domain_blacklist.value}')
    print(f'✓ Created phone blacklist: {phone_blacklist.value}')
    
    # Test blacklist checking
    test_contacts = [
        ('spam@example.com', 'email'),
        ('user@marketing.com', 'email'),
        ('valid@hospital.com', 'email'),
        ('+1234567890', 'phone'),
        ('+1987654321', 'phone'),
    ]
    
    for contact, contact_type in test_contacts:
        is_blacklisted = preference_service.is_blacklisted(
            user=user,
            contact_info=contact,
            blacklist_type=contact_type
        )
        
        print(f'✓ {contact} ({contact_type}): {"BLACKLISTED" if is_blacklisted else "ALLOWED"}')
    
    # Test 5: Test language preferences
    print('\n5. Testing language preferences...')
    
    # Get user language for different notification types
    language_tests = [
        'appointment_reminder',
        'test_results_ready',
        'payment_confirmation',
        'emergency_alert'
    ]
    
    for notification_type in language_tests:
        user_language = preference_service.get_user_language(
            user=user,
            notification_type=notification_type
        )
        
        print(f'✓ {notification_type}: {user_language}')
    
    # Test 6: Create and test custom schedules
    print('\n6. Testing custom notification schedules...')
    
    # Create business hours schedule
    business_schedule = NotificationSchedule.objects.create(
        user=user,
        name='Business Hours',
        description='Only receive notifications during business hours',
        schedule_type='daily',
        start_time=time(9, 0),  # 9:00 AM
        end_time=time(17, 0),   # 5:00 PM
        days_of_week=['monday', 'tuesday', 'wednesday', 'thursday', 'friday'],
        notification_types=['appointment_reminder', 'test_results_ready'],
        is_active=True,
        priority=1
    )
    
    # Create emergency schedule (24/7)
    emergency_schedule = NotificationSchedule.objects.create(
        user=user,
        name='Emergency Alerts',
        description='Always receive emergency alerts',
        schedule_type='daily',
        start_time=time(0, 0),   # 12:00 AM
        end_time=time(23, 59),   # 11:59 PM
        days_of_week=['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'],
        notification_types=['emergency_alert'],
        is_active=True,
        priority=2  # Higher priority
    )
    
    print(f'✓ Created business hours schedule: {business_schedule.name}')
    print(f'  Time: {business_schedule.start_time} - {business_schedule.end_time}')
    print(f'  Days: {business_schedule.days_of_week}')
    print(f'  Types: {business_schedule.notification_types}')
    
    print(f'✓ Created emergency schedule: {emergency_schedule.name}')
    print(f'  Priority: {emergency_schedule.priority}')
    print(f'  Types: {emergency_schedule.notification_types}')
    
    # Test schedule checking
    schedule_tests = [
        'appointment_reminder',
        'emergency_alert',
        'marketing',
        'test_results_ready'
    ]
    
    for notification_type in schedule_tests:
        should_send = preference_service.should_send_during_schedule(
            user=user,
            notification_type=notification_type
        )
        
        print(f'✓ {notification_type} schedule check: {should_send}')
    
    # Test 7: Update notification settings
    print('\n7. Testing notification settings updates...')
    
    # Update settings
    settings.global_quiet_hours_enabled = True
    settings.global_quiet_hours_start = time(22, 0)  # 10:00 PM
    settings.global_quiet_hours_end = time(7, 0)     # 7:00 AM
    settings.weekend_notifications_enabled = False
    settings.daily_digest_enabled = True
    settings.daily_digest_time = time(8, 0)  # 8:00 AM
    settings.marketing_emails_enabled = False
    settings.save()
    
    print(f'✓ Updated notification settings:')
    print(f'  Quiet hours: {settings.global_quiet_hours_start} - {settings.global_quiet_hours_end}')
    print(f'  Weekend notifications: {settings.weekend_notifications_enabled}')
    print(f'  Daily digest: {settings.daily_digest_enabled} at {settings.daily_digest_time}')
    print(f'  Marketing emails: {settings.marketing_emails_enabled}')
    
    # Test 8: Update specific preferences
    print('\n8. Testing preference updates...')
    
    # Update some preferences
    appointment_email_pref = NotificationPreference.objects.get(
        user=user,
        notification_type='appointment_reminder',
        channel='email'
    )
    appointment_email_pref.frequency = 'daily_digest'
    appointment_email_pref.priority_threshold = 'high'
    appointment_email_pref.quiet_hours_start = time(21, 0)  # 9:00 PM
    appointment_email_pref.quiet_hours_end = time(8, 0)     # 8:00 AM
    appointment_email_pref.save()
    
    marketing_email_pref = NotificationPreference.objects.get(
        user=user,
        notification_type='marketing',
        channel='email'
    )
    marketing_email_pref.is_enabled = False
    marketing_email_pref.save()
    
    print(f'✓ Updated appointment reminder email preference:')
    print(f'  Frequency: {appointment_email_pref.frequency}')
    print(f'  Priority threshold: {appointment_email_pref.priority_threshold}')
    print(f'  Quiet hours: {appointment_email_pref.quiet_hours_start} - {appointment_email_pref.quiet_hours_end}')
    
    print(f'✓ Disabled marketing email preference')
    
    # Test 9: System statistics
    print('\n9. System statistics...')
    
    total_preferences = NotificationPreference.objects.filter(user=user).count()
    enabled_preferences = NotificationPreference.objects.filter(user=user, is_enabled=True).count()
    disabled_preferences = total_preferences - enabled_preferences
    
    total_blacklist = NotificationBlacklist.objects.filter(user=user, is_active=True).count()
    total_schedules = NotificationSchedule.objects.filter(user=user, is_active=True).count()
    
    print(f'✓ Notification preferences statistics:')
    print(f'  Total preferences: {total_preferences}')
    print(f'  Enabled preferences: {enabled_preferences}')
    print(f'  Disabled preferences: {disabled_preferences}')
    print(f'  Active blacklist entries: {total_blacklist}')
    print(f'  Custom schedules: {total_schedules}')
    
    # Preference breakdown by type
    preference_types = {}
    for pref in NotificationPreference.objects.filter(user=user):
        pref_type = pref.notification_type
        if pref_type not in preference_types:
            preference_types[pref_type] = {'total': 0, 'enabled': 0}
        preference_types[pref_type]['total'] += 1
        if pref.is_enabled:
            preference_types[pref_type]['enabled'] += 1
    
    print(f'  Preference breakdown by type:')
    for pref_type, counts in preference_types.items():
        print(f'    {pref_type}: {counts["enabled"]}/{counts["total"]} enabled')
    
    # Channel breakdown
    channel_breakdown = {}
    for pref in NotificationPreference.objects.filter(user=user, is_enabled=True):
        channel = pref.channel
        if channel not in channel_breakdown:
            channel_breakdown[channel] = 0
        channel_breakdown[channel] += 1
    
    print(f'  Enabled preferences by channel: {channel_breakdown}')
    
    print('\n=== Notification Preferences System Testing Complete ===')

if __name__ == '__main__':
    test_notification_preferences_system()
