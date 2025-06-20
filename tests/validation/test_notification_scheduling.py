import os
import django
from datetime import datetime, timedelta

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hospital_backend.settings')
django.setup()

from django.utils import timezone
from notifications.models import (
    NotificationJob, NotificationQueue, CronJob
)
from notifications.services import NotificationSchedulingService, CronJobService
from accounts.models import User
from patients.models import Patient

def test_notification_scheduling_system():
    print("=== Testing Notification Scheduling System ===")
    
    # Get required objects
    patient = Patient.objects.first()
    user = patient.user if patient else User.objects.filter(user_type='patient').first()
    admin_user = User.objects.filter(user_type='admin').first()
    
    print(f'User: {user.get_full_name() if user else "No patient user"}')
    print(f'Admin: {admin_user.get_full_name() if admin_user else "No admin user"}')
    
    # Test 1: Create scheduled notification job
    print('\n1. Creating scheduled notification job...')
    
    scheduling_service = NotificationSchedulingService()
    
    # Create immediate job
    immediate_job = scheduling_service.create_scheduled_job(
        name='Appointment Confirmation Email',
        notification_type='appointment_confirmation',
        channel='email',
        recipients=[user] if user else [],
        template_variables={
            'patient_name': user.get_full_name() if user else 'Test Patient',
            'doctor_name': 'Dr. Smith',
            'appointment_date': 'June 20, 2025',
            'appointment_time': '2:00 PM',
            'hospital_name': 'City Hospital'
        },
        scheduled_at=timezone.now(),
        job_type='immediate',
        priority='normal',
        created_by=admin_user
    )
    
    print(f'✓ Created immediate job: {immediate_job.job_id}')
    print(f'  Name: {immediate_job.name}')
    print(f'  Type: {immediate_job.get_job_type_display()}')
    print(f'  Channel: {immediate_job.channel}')
    print(f'  Status: {immediate_job.get_status_display()}')
    print(f'  Priority: {immediate_job.get_priority_display()}')
    
    # Create scheduled job for future
    future_time = timezone.now() + timedelta(hours=2)
    scheduled_job = scheduling_service.create_scheduled_job(
        name='Appointment Reminder Email',
        notification_type='appointment_reminder',
        channel='email',
        recipients=[user] if user else [],
        template_variables={
            'patient_name': user.get_full_name() if user else 'Test Patient',
            'doctor_name': 'Dr. Johnson',
            'appointment_date': 'June 21, 2025',
            'appointment_time': '10:00 AM'
        },
        scheduled_at=future_time,
        job_type='scheduled',
        priority='high',
        created_by=admin_user
    )
    
    print(f'✓ Created scheduled job: {scheduled_job.job_id}')
    print(f'  Scheduled for: {scheduled_job.scheduled_at}')
    print(f'  Status: {scheduled_job.get_status_display()}')
    
    # Test 2: Create recurring notification job
    print('\n2. Creating recurring notification job...')
    
    recurrence_pattern = {
        'type': 'daily',
        'interval': 1,
        'time': '09:00'
    }
    
    recurring_job = scheduling_service.create_recurring_job(
        name='Daily Health Tips',
        notification_type='health_tips',
        channel='email',
        recurrence_pattern=recurrence_pattern,
        recipients=[user] if user else [],
        template_variables={
            'patient_name': user.get_full_name() if user else 'Test Patient',
            'tip_category': 'General Health'
        },
        start_date=timezone.now(),
        created_by=admin_user
    )
    
    print(f'✓ Created recurring job: {recurring_job.job_id}')
    print(f'  Name: {recurring_job.name}')
    print(f'  Recurrence: {recurrence_pattern}')
    print(f'  Next run: {recurring_job.next_run_at}')
    print(f'  Is recurring: {recurring_job.is_recurring}')
    
    # Test 3: Create batch notification job
    print('\n3. Creating batch notification job...')
    
    # Get multiple users for batch job
    all_users = User.objects.filter(user_type='patient')[:5]
    
    batch_job = scheduling_service.create_batch_job(
        name='Monthly Newsletter',
        notification_type='newsletter',
        channel='email',
        recipients=list(all_users),
        template_variables={
            'newsletter_month': 'June 2025',
            'hospital_name': 'City Hospital'
        },
        batch_size=2,
        batch_delay=30,  # 30 seconds between batches
        scheduled_at=timezone.now(),
        created_by=admin_user
    )
    
    print(f'✓ Created batch job: {batch_job.job_id}')
    print(f'  Name: {batch_job.name}')
    print(f'  Total recipients: {batch_job.total_recipients}')
    print(f'  Batch size: {batch_job.batch_size}')
    print(f'  Batch delay: {batch_job.batch_delay} seconds')
    print(f'  Status: {batch_job.get_status_display()}')
    
    # Test 4: Check notification queue
    print('\n4. Checking notification queue...')
    
    total_queue_items = NotificationQueue.objects.count()
    pending_items = NotificationQueue.objects.filter(status='pending').count()
    
    print(f'✓ Notification queue status:')
    print(f'  Total queue items: {total_queue_items}')
    print(f'  Pending items: {pending_items}')
    
    # Show queue breakdown by job
    for job in [immediate_job, scheduled_job, recurring_job, batch_job]:
        job_queue_count = NotificationQueue.objects.filter(job=job).count()
        print(f'  {job.job_id}: {job_queue_count} queue items')
    
    # Test 5: Create cron jobs
    print('\n5. Creating cron jobs...')
    
    cron_service = CronJobService()
    
    # Daily appointment reminders
    reminder_cron = cron_service.create_cron_job(
        name='Daily Appointment Reminders',
        cron_expression='0 9 * * *',  # Daily at 9 AM
        task_function='send_appointment_reminders',
        cron_type='notification_reminders',
        task_parameters={'hours_ahead': 24},
        created_by=admin_user
    )
    
    print(f'✓ Created appointment reminder cron: {reminder_cron.name}')
    print(f'  Expression: {reminder_cron.cron_expression}')
    print(f'  Function: {reminder_cron.task_function}')
    print(f'  Next run: {reminder_cron.next_run_at}')
    
    # Daily digest emails
    digest_cron = cron_service.create_cron_job(
        name='Daily Digest Emails',
        cron_expression='0 8 * * *',  # Daily at 8 AM
        task_function='send_daily_digest',
        cron_type='digest_emails',
        task_parameters={'include_stats': True},
        created_by=admin_user
    )
    
    print(f'✓ Created daily digest cron: {digest_cron.name}')
    print(f'  Expression: {digest_cron.cron_expression}')
    print(f'  Type: {digest_cron.get_cron_type_display()}')
    
    # Weekly cleanup
    cleanup_cron = cron_service.create_cron_job(
        name='Weekly Notification Cleanup',
        cron_expression='0 2 * * 0',  # Weekly on Sunday at 2 AM
        task_function='cleanup_old_notifications',
        cron_type='cleanup_tasks',
        task_parameters={'days_to_keep': 90},
        created_by=admin_user
    )
    
    print(f'✓ Created cleanup cron: {cleanup_cron.name}')
    print(f'  Expression: {cleanup_cron.cron_expression}')
    print(f'  Parameters: {cleanup_cron.task_parameters}')
    
    # Test 6: Job control operations
    print('\n6. Testing job control operations...')
    
    # Pause a job
    pause_result = scheduling_service.pause_job(scheduled_job.job_id)
    scheduled_job.refresh_from_db()
    
    print(f'✓ Paused job {scheduled_job.job_id}: {pause_result}')
    print(f'  New status: {scheduled_job.get_status_display()}')
    
    # Resume the job
    resume_result = scheduling_service.resume_job(scheduled_job.job_id)
    scheduled_job.refresh_from_db()
    
    print(f'✓ Resumed job {scheduled_job.job_id}: {resume_result}')
    print(f'  New status: {scheduled_job.get_status_display()}')
    
    # Cancel a job
    cancel_result = scheduling_service.cancel_job(batch_job.job_id)
    batch_job.refresh_from_db()
    
    print(f'✓ Cancelled job {batch_job.job_id}: {cancel_result}')
    print(f'  New status: {batch_job.get_status_display()}')
    
    # Test 7: Process scheduled jobs (simulation)
    print('\n7. Testing job processing...')
    
    # Get jobs ready for processing
    ready_jobs = NotificationJob.objects.filter(
        status__in=['pending', 'queued'],
        scheduled_at__lte=timezone.now()
    ).exclude(status='cancelled')
    
    print(f'✓ Jobs ready for processing: {ready_jobs.count()}')
    
    for job in ready_jobs:
        print(f'  {job.job_id}: {job.name} - {job.get_status_display()}')
    
    # Test 8: System statistics
    print('\n8. System statistics...')
    
    total_jobs = NotificationJob.objects.count()
    pending_jobs = NotificationJob.objects.filter(status='pending').count()
    queued_jobs = NotificationJob.objects.filter(status='queued').count()
    completed_jobs = NotificationJob.objects.filter(status='completed').count()
    failed_jobs = NotificationJob.objects.filter(status='failed').count()
    cancelled_jobs = NotificationJob.objects.filter(status='cancelled').count()
    
    total_crons = CronJob.objects.count()
    active_crons = CronJob.objects.filter(is_active=True).count()
    
    print(f'✓ Notification scheduling statistics:')
    print(f'  Total jobs: {total_jobs}')
    print(f'  Pending jobs: {pending_jobs}')
    print(f'  Queued jobs: {queued_jobs}')
    print(f'  Completed jobs: {completed_jobs}')
    print(f'  Failed jobs: {failed_jobs}')
    print(f'  Cancelled jobs: {cancelled_jobs}')
    print(f'  Total cron jobs: {total_crons}')
    print(f'  Active cron jobs: {active_crons}')
    
    # Job type breakdown
    job_types = {}
    for job in NotificationJob.objects.all():
        job_type = job.job_type
        if job_type not in job_types:
            job_types[job_type] = 0
        job_types[job_type] += 1
    
    print(f'  Job types: {job_types}')
    
    # Channel breakdown
    channels = {}
    for job in NotificationJob.objects.all():
        channel = job.channel
        if channel not in channels:
            channels[channel] = 0
        channels[channel] += 1
    
    print(f'  Channels: {channels}')
    
    # Priority breakdown
    priorities = {}
    for job in NotificationJob.objects.all():
        priority = job.priority
        if priority not in priorities:
            priorities[priority] = 0
        priorities[priority] += 1
    
    print(f'  Priorities: {priorities}')
    
    print('\n=== Notification Scheduling System Testing Complete ===')

if __name__ == '__main__':
    test_notification_scheduling_system()
