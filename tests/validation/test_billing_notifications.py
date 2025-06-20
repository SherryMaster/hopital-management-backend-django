import os
import django
from decimal import Decimal
from datetime import datetime, timedelta

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hospital_backend.settings')
django.setup()

from django.utils import timezone
from billing.models import (
    BillingNotification, NotificationTemplate, NotificationSchedule,
    Invoice, Payment
)
from billing.serializers import (
    BillingNotificationSerializer, NotificationTemplateSerializer,
    NotificationScheduleSerializer
)
from accounts.models import User
from patients.models import Patient

def test_billing_notifications_system():
    print("=== Testing Billing Notifications System ===")
    
    # Get required objects
    user = User.objects.filter(user_type='admin').first()
    patient = Patient.objects.first()
    invoice = Invoice.objects.first()
    
    print(f'User: {user.get_full_name() if user else "No admin user"}')
    print(f'Patient: {patient.patient_id if patient else "No patient"}')
    print(f'Invoice: {invoice.invoice_number if invoice else "No invoice"} (${invoice.total_amount if invoice else 0})')
    
    # Test 1: Create notification templates
    print('\n1. Creating notification templates...')
    
    # Payment reminder template
    payment_reminder_template = NotificationTemplate.objects.create(
        name='Payment Reminder Template',
        template_type='payment_reminder',
        subject_template='Payment Reminder - Invoice {invoice_number}',
        email_template='''
Dear {patient_name},

This is a friendly reminder that your invoice {invoice_number} for ${invoice_amount} is due on {due_date}.

Please make your payment at your earliest convenience to avoid any late fees.

Invoice Details:
- Invoice Number: {invoice_number}
- Amount Due: ${invoice_amount}
- Due Date: {due_date}

Thank you for your prompt attention to this matter.

Best regards,
Hospital Billing Department
        ''',
        sms_template='Payment reminder: Invoice {invoice_number} for ${invoice_amount} is due on {due_date}. Please pay promptly.',
        available_variables=['patient_name', 'invoice_number', 'invoice_amount', 'due_date'],
        is_active=True,
        is_default=True,
        send_immediately=False,
        delay_hours=24
    )
    
    # Overdue notice template
    overdue_template = NotificationTemplate.objects.create(
        name='Overdue Notice Template',
        template_type='overdue_notice',
        subject_template='OVERDUE NOTICE - Invoice {invoice_number}',
        email_template='''
Dear {patient_name},

Your invoice {invoice_number} for ${invoice_amount} is now OVERDUE.

Original Due Date: {due_date}
Days Overdue: {days_overdue}

Please remit payment immediately to avoid further collection actions.

Invoice Details:
- Invoice Number: {invoice_number}
- Amount Due: ${invoice_amount}
- Original Due Date: {due_date}

Contact our billing department if you have any questions.

Best regards,
Hospital Billing Department
        ''',
        sms_template='OVERDUE: Invoice {invoice_number} for ${invoice_amount} is {days_overdue} days overdue. Pay now.',
        available_variables=['patient_name', 'invoice_number', 'invoice_amount', 'due_date', 'days_overdue'],
        is_active=True,
        is_default=True
    )
    
    print(f'✓ Created payment reminder template: {payment_reminder_template.name}')
    print(f'✓ Created overdue notice template: {overdue_template.name}')
    
    # Test 2: Create notification schedules
    print('\n2. Creating notification schedules...')
    
    # Payment reminder schedule (7 days after due date)
    reminder_schedule = NotificationSchedule.objects.create(
        name='7-Day Payment Reminder',
        schedule_type='payment_reminder',
        days_after_due=7,
        minimum_amount=Decimal('50.00'),
        template=payment_reminder_template,
        delivery_method='email',
        is_active=True,
        max_notifications=2
    )
    
    # Overdue notice schedule (14 days after due date)
    overdue_schedule = NotificationSchedule.objects.create(
        name='14-Day Overdue Notice',
        schedule_type='overdue_notice',
        days_after_due=14,
        minimum_amount=Decimal('100.00'),
        template=overdue_template,
        delivery_method='email',
        is_active=True,
        max_notifications=1
    )
    
    print(f'✓ Created reminder schedule: {reminder_schedule.name} ({reminder_schedule.days_after_due} days)')
    print(f'✓ Created overdue schedule: {overdue_schedule.name} ({overdue_schedule.days_after_due} days)')
    
    # Test 3: Create billing notifications
    print('\n3. Creating billing notifications...')
    
    # Invoice sent notification
    invoice_sent_notification = BillingNotification.objects.create(
        patient=patient,
        invoice=invoice,
        notification_type='invoice_sent',
        delivery_method='email',
        subject=f'Invoice {invoice.invoice_number} - ${invoice.total_amount}',
        message=f'Your invoice {invoice.invoice_number} for ${invoice.total_amount} has been sent.',
        recipient_email=patient.user.email,
        status='pending',
        created_by=user
    )
    
    # Payment reminder notification
    payment_reminder_notification = BillingNotification.objects.create(
        patient=patient,
        invoice=invoice,
        notification_type='payment_reminder',
        delivery_method='email',
        subject=f'Payment Reminder - Invoice {invoice.invoice_number}',
        message=f'This is a reminder that your invoice {invoice.invoice_number} for ${invoice.total_amount} is due.',
        recipient_email=patient.user.email,
        scheduled_at=timezone.now() + timedelta(hours=24),
        status='pending',
        created_by=user
    )
    
    print(f'✓ Created invoice sent notification: {invoice_sent_notification.notification_number}')
    print(f'✓ Created payment reminder: {payment_reminder_notification.notification_number}')
    
    # Test 4: Test serializers
    print('\n4. Testing serializers...')
    
    # Test NotificationTemplateSerializer
    template_serializer = NotificationTemplateSerializer(payment_reminder_template)
    print(f'✓ Template serializer data:')
    print(f'  Name: {template_serializer.data["name"]}')
    print(f'  Type: {template_serializer.data["template_type"]}')
    print(f'  Is active: {template_serializer.data["is_active"]}')
    print(f'  Variables: {template_serializer.data["available_variables"]}')
    
    # Test NotificationScheduleSerializer
    schedule_serializer = NotificationScheduleSerializer(reminder_schedule)
    print(f'✓ Schedule serializer data:')
    print(f'  Name: {schedule_serializer.data["name"]}')
    print(f'  Days after due: {schedule_serializer.data["days_after_due"]}')
    print(f'  Minimum amount: ${schedule_serializer.data["minimum_amount"]}')
    
    # Test BillingNotificationSerializer
    notification_serializer = BillingNotificationSerializer(invoice_sent_notification)
    print(f'✓ Notification serializer data:')
    print(f'  Number: {notification_serializer.data["notification_number"]}')
    print(f'  Type: {notification_serializer.data["notification_type"]}')
    print(f'  Status: {notification_serializer.data["status"]}')
    print(f'  Patient: {notification_serializer.data.get("patient_name", "Unknown")}')
    
    # Test 5: Simulate sending notifications
    print('\n5. Simulating notification sending...')
    
    # Send invoice notification
    invoice_sent_notification.status = 'sent'
    invoice_sent_notification.sent_at = timezone.now()
    invoice_sent_notification.attempts = 1
    invoice_sent_notification.delivery_response = {
        'status': 'delivered',
        'message_id': 'msg_001',
        'delivered_at': timezone.now().isoformat()
    }
    invoice_sent_notification.save()
    
    print(f'✓ Sent invoice notification: {invoice_sent_notification.notification_number}')
    print(f'  Status: {invoice_sent_notification.status}')
    print(f'  Sent at: {invoice_sent_notification.sent_at}')
    
    # Test 6: Create payment received notification
    print('\n6. Creating payment received notification...')
    
    # Get or create a payment for testing
    payment = Payment.objects.filter(invoice=invoice).first()
    if not payment:
        payment = Payment.objects.create(
            invoice=invoice,
            amount=Decimal('100.00'),
            payment_method='credit_card',
            status='completed',
            transaction_id='TXN_TEST_NOTIF',
            notes='Test payment for notification testing',
            processed_by=user
        )
    
    payment_received_notification = BillingNotification.objects.create(
        patient=patient,
        invoice=invoice,
        payment=payment,
        notification_type='payment_received',
        delivery_method='email',
        subject=f'Payment Received - ${payment.amount}',
        message=f'We have received your payment of ${payment.amount} for invoice {invoice.invoice_number}.',
        recipient_email=patient.user.email,
        status='sent',
        sent_at=timezone.now(),
        attempts=1,
        delivery_response={
            'status': 'delivered',
            'message_id': 'msg_002'
        },
        created_by=user
    )
    
    print(f'✓ Created payment received notification: {payment_received_notification.notification_number}')
    print(f'  Payment amount: ${payment.amount}')
    print(f'  Status: {payment_received_notification.status}')
    
    # Test 7: Notification statistics
    print('\n7. Notification statistics...')
    
    total_notifications = BillingNotification.objects.count()
    pending_notifications = BillingNotification.objects.filter(status='pending').count()
    sent_notifications = BillingNotification.objects.filter(status='sent').count()
    failed_notifications = BillingNotification.objects.filter(status='failed').count()
    
    print(f'✓ Notification statistics:')
    print(f'  Total notifications: {total_notifications}')
    print(f'  Pending: {pending_notifications}')
    print(f'  Sent: {sent_notifications}')
    print(f'  Failed: {failed_notifications}')
    
    # Notification type breakdown
    type_counts = {}
    for notification_type in BillingNotification.NOTIFICATION_TYPES:
        type_name = notification_type[0]
        count = BillingNotification.objects.filter(notification_type=type_name).count()
        if count > 0:
            type_counts[type_name] = count
    
    print(f'  Type breakdown: {type_counts}')
    
    # Test 8: Template and schedule statistics
    print('\n8. Template and schedule statistics...')
    
    total_templates = NotificationTemplate.objects.count()
    active_templates = NotificationTemplate.objects.filter(is_active=True).count()
    total_schedules = NotificationSchedule.objects.count()
    active_schedules = NotificationSchedule.objects.filter(is_active=True).count()
    
    print(f'✓ Template statistics:')
    print(f'  Total templates: {total_templates}')
    print(f'  Active templates: {active_templates}')
    print(f'✓ Schedule statistics:')
    print(f'  Total schedules: {total_schedules}')
    print(f'  Active schedules: {active_schedules}')
    
    print('\n=== Billing Notifications System Testing Complete ===')

if __name__ == '__main__':
    test_billing_notifications_system()
