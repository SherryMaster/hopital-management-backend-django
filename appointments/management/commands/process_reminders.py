from django.core.management.base import BaseCommand
from django.utils import timezone
from appointments.services import NotificationService
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Process pending appointment reminders'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be processed without actually sending notifications',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS(f'Starting reminder processing at {timezone.now()}')
        )

        if options['dry_run']:
            self.stdout.write(
                self.style.WARNING('DRY RUN MODE - No notifications will be sent')
            )
            # In dry run mode, just show what would be processed
            from appointments.models import AppointmentReminder
            now = timezone.now()
            pending_reminders = AppointmentReminder.objects.filter(
                status='pending',
                scheduled_time__lte=now
            )
            
            self.stdout.write(f'Found {pending_reminders.count()} pending reminders to process:')
            for reminder in pending_reminders:
                self.stdout.write(
                    f'  - {reminder.appointment.appointment_number}: '
                    f'{reminder.reminder_type} reminder scheduled for {reminder.scheduled_time}'
                )
        else:
            # Process reminders
            processed_count = NotificationService.process_pending_reminders()
            
            self.stdout.write(
                self.style.SUCCESS(f'Successfully processed {processed_count} reminders')
            )

        self.stdout.write(
            self.style.SUCCESS(f'Reminder processing completed at {timezone.now()}')
        )
