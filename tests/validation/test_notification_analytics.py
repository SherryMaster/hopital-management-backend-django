import os
import django
from datetime import datetime, timedelta

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hospital_backend.settings')
django.setup()

from django.utils import timezone
from notifications.models import (
    NotificationAnalytics, NotificationEvent, NotificationCampaign,
    EmailNotification, SMSNotification, PushNotification
)
from notifications.services import NotificationAnalyticsService, NotificationCampaignService
from accounts.models import User
from patients.models import Patient

def test_notification_analytics_system():
    print("=== Testing Notification Analytics System ===")
    
    # Get required objects
    patient = Patient.objects.first()
    user = patient.user if patient else User.objects.filter(user_type='patient').first()
    admin_user = User.objects.filter(user_type='admin').first()
    
    print(f'User: {user.get_full_name() if user else "No patient user"}')
    print(f'Admin: {admin_user.get_full_name() if admin_user else "No admin user"}')
    
    # Test 1: Track notification events
    print('\n1. Tracking notification events...')
    
    analytics_service = NotificationAnalyticsService()
    
    # Create sample notification events
    events = []
    
    # Email events
    email_sent_event = analytics_service.track_notification_event(
        event_type='sent',
        notification_type='appointment_reminder',
        notification_channel='email',
        notification_id='12345678-1234-1234-1234-123456789012',
        recipient_user=user,
        recipient_email=user.email if user else 'test@example.com',
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        device_type='desktop',
        provider_name='SMTP',
        provider_message_id='smtp_msg_001'
    )
    events.append(email_sent_event)
    
    email_delivered_event = analytics_service.track_notification_event(
        event_type='delivered',
        notification_type='appointment_reminder',
        notification_channel='email',
        notification_id='12345678-1234-1234-1234-123456789012',
        recipient_user=user,
        recipient_email=user.email if user else 'test@example.com',
        provider_name='SMTP',
        provider_message_id='smtp_msg_001'
    )
    events.append(email_delivered_event)
    
    email_opened_event = analytics_service.track_notification_event(
        event_type='opened',
        notification_type='appointment_reminder',
        notification_channel='email',
        notification_id='12345678-1234-1234-1234-123456789012',
        recipient_user=user,
        recipient_email=user.email if user else 'test@example.com',
        user_agent='Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X)',
        device_type='mobile',
        event_data={'open_time': '2025-06-19T10:30:00Z'}
    )
    events.append(email_opened_event)
    
    # SMS events
    sms_sent_event = analytics_service.track_notification_event(
        event_type='sent',
        notification_type='verification_code',
        notification_channel='sms',
        notification_id='87654321-4321-4321-4321-210987654321',
        recipient_user=user,
        recipient_phone='+1234567890',
        provider_name='Twilio',
        provider_message_id='twilio_msg_001'
    )
    events.append(sms_sent_event)
    
    sms_delivered_event = analytics_service.track_notification_event(
        event_type='delivered',
        notification_type='verification_code',
        notification_channel='sms',
        notification_id='87654321-4321-4321-4321-210987654321',
        recipient_user=user,
        recipient_phone='+1234567890',
        provider_name='Twilio',
        provider_message_id='twilio_msg_001'
    )
    events.append(sms_delivered_event)
    
    # Push notification events
    push_sent_event = analytics_service.track_notification_event(
        event_type='sent',
        notification_type='test_results_ready',
        notification_channel='push',
        notification_id='11111111-2222-3333-4444-555555555555',
        recipient_user=user,
        device_type='mobile',
        provider_name='FCM',
        provider_message_id='fcm_msg_001'
    )
    events.append(push_sent_event)
    
    push_clicked_event = analytics_service.track_notification_event(
        event_type='clicked',
        notification_type='test_results_ready',
        notification_channel='push',
        notification_id='11111111-2222-3333-4444-555555555555',
        recipient_user=user,
        device_type='mobile',
        event_data={'click_action': 'view_results'}
    )
    events.append(push_clicked_event)
    
    print(f'✓ Created {len(events)} notification events:')
    for event in events:
        print(f'  {event.get_event_type_display()} - {event.notification_channel} - {event.event_timestamp}')
    
    # Test 2: Generate analytics report
    print('\n2. Generating analytics report...')
    
    # Set date range for the report
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=7)
    
    analytics_report = analytics_service.generate_analytics_report(
        start_date=start_date,
        end_date=end_date,
        report_type='weekly',
        generated_by=admin_user
    )
    
    print(f'✓ Generated analytics report: {analytics_report}')
    print(f'  Report type: {analytics_report.get_report_type_display()}')
    print(f'  Period: {analytics_report.start_date} to {analytics_report.end_date}')
    print(f'  Total notifications: {analytics_report.total_notifications}')
    print(f'  Total sent: {analytics_report.total_sent}')
    print(f'  Total delivered: {analytics_report.total_delivered}')
    print(f'  Total opened: {analytics_report.total_opened}')
    print(f'  Total clicked: {analytics_report.total_clicked}')
    print(f'  Total failed: {analytics_report.total_failed}')
    
    # Performance metrics
    print(f'  Delivery rate: {analytics_report.delivery_rate:.1f}%')
    print(f'  Open rate: {analytics_report.open_rate:.1f}%')
    print(f'  Click rate: {analytics_report.click_rate:.1f}%')
    print(f'  Bounce rate: {analytics_report.bounce_rate:.1f}%')
    
    # Channel metrics
    print(f'  Email metrics: {analytics_report.email_metrics}')
    print(f'  SMS metrics: {analytics_report.sms_metrics}')
    print(f'  Push metrics: {analytics_report.push_metrics}')
    
    # Test 3: User engagement metrics
    print('\n3. Testing user engagement metrics...')
    
    if user:
        engagement_metrics = analytics_service.get_user_engagement_metrics(user, days=30)
        
        print(f'✓ User engagement metrics for {engagement_metrics["user_name"]}:')
        print(f'  Period: {engagement_metrics["period_days"]} days')
        print(f'  Total sent: {engagement_metrics["total_sent"]}')
        print(f'  Total delivered: {engagement_metrics["total_delivered"]}')
        print(f'  Total opened: {engagement_metrics["total_opened"]}')
        print(f'  Total clicked: {engagement_metrics["total_clicked"]}')
        print(f'  Delivery rate: {engagement_metrics["delivery_rate"]:.1f}%')
        print(f'  Open rate: {engagement_metrics["open_rate"]:.1f}%')
        print(f'  Click rate: {engagement_metrics["click_rate"]:.1f}%')
        print(f'  Channel breakdown: {engagement_metrics["channel_breakdown"]}')
    
    # Test 4: Create notification campaign
    print('\n4. Creating notification campaign...')
    
    campaign_service = NotificationCampaignService()
    
    target_audience = {
        'user_type': 'patient',
        'is_active': True,
        'age_range': {'min': 18, 'max': 65},
        'location': 'city'
    }
    
    campaign = campaign_service.create_campaign(
        name='Monthly Health Newsletter',
        campaign_type='newsletter',
        target_audience=target_audience,
        description='Monthly newsletter with health tips and hospital updates',
        budget=500.00,
        start_date=timezone.now(),
        end_date=timezone.now() + timedelta(days=30),
        created_by=admin_user
    )
    
    print(f'✓ Created campaign: {campaign.campaign_id}')
    print(f'  Name: {campaign.name}')
    print(f'  Type: {campaign.get_campaign_type_display()}')
    print(f'  Status: {campaign.get_status_display()}')
    print(f'  Estimated recipients: {campaign.estimated_recipients}')
    print(f'  Budget: ${campaign.budget}')
    print(f'  Target audience: {campaign.target_audience}')
    
    # Test 5: Campaign management
    print('\n5. Testing campaign management...')
    
    # Launch campaign
    launch_result = campaign_service.launch_campaign(campaign.campaign_id)
    campaign.refresh_from_db()
    
    print(f'✓ Launched campaign: {launch_result}')
    print(f'  New status: {campaign.get_status_display()}')
    print(f'  Start date: {campaign.start_date}')
    
    # Update campaign metrics
    campaign_service.update_campaign_metrics(
        campaign_id=campaign.campaign_id,
        sent=150,
        delivered=145,
        opened=87,
        clicked=23,
        conversions=5,
        cost=45.50
    )
    
    campaign.refresh_from_db()
    print(f'✓ Updated campaign metrics:')
    print(f'  Total sent: {campaign.total_sent}')
    print(f'  Total delivered: {campaign.total_delivered}')
    print(f'  Total opened: {campaign.total_opened}')
    print(f'  Total clicked: {campaign.total_clicked}')
    print(f'  Total conversions: {campaign.total_conversions}')
    print(f'  Actual cost: ${campaign.actual_cost}')
    
    # Get campaign analytics
    campaign_analytics = campaign_service.get_campaign_analytics(campaign.campaign_id)
    
    print(f'✓ Campaign analytics:')
    print(f'  Delivery rate: {campaign_analytics["delivery_rate"]:.1f}%')
    print(f'  Open rate: {campaign_analytics["open_rate"]:.1f}%')
    print(f'  Click rate: {campaign_analytics["click_rate"]:.1f}%')
    print(f'  Conversion rate: {campaign_analytics["conversion_rate"]:.1f}%')
    
    # Test 6: System statistics
    print('\n6. System statistics...')
    
    total_events = NotificationEvent.objects.count()
    total_analytics = NotificationAnalytics.objects.count()
    total_campaigns = NotificationCampaign.objects.count()
    
    print(f'✓ Notification analytics statistics:')
    print(f'  Total events tracked: {total_events}')
    print(f'  Total analytics reports: {total_analytics}')
    print(f'  Total campaigns: {total_campaigns}')
    
    # Event type breakdown
    event_types = {}
    for event in NotificationEvent.objects.all():
        event_type = event.event_type
        if event_type not in event_types:
            event_types[event_type] = 0
        event_types[event_type] += 1
    
    print(f'  Event types: {event_types}')
    
    # Channel breakdown
    channels = {}
    for event in NotificationEvent.objects.all():
        channel = event.notification_channel
        if channel not in channels:
            channels[channel] = 0
        channels[channel] += 1
    
    print(f'  Channels: {channels}')
    
    # Campaign status breakdown
    campaign_statuses = {}
    for campaign in NotificationCampaign.objects.all():
        status = campaign.status
        if status not in campaign_statuses:
            campaign_statuses[status] = 0
        campaign_statuses[status] += 1
    
    print(f'  Campaign statuses: {campaign_statuses}')
    
    print('\n=== Notification Analytics System Testing Complete ===')

if __name__ == '__main__':
    test_notification_analytics_system()
