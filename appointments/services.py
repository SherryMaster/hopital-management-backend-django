from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from django.template.loader import render_to_string
from datetime import datetime, timedelta
import logging
from .models import Appointment, AppointmentReminder, RecurringPattern

logger = logging.getLogger(__name__)


class NotificationService:
    """
    Service for handling appointment notifications
    """
    
    @staticmethod
    def send_appointment_confirmation(appointment):
        """
        Send appointment confirmation notification
        """
        try:
            # Send email confirmation
            subject = f"Appointment Confirmation - {appointment.appointment_number}"
            message = f"""
Dear {appointment.patient.user.get_full_name()},

Your appointment has been confirmed with the following details:

Appointment Number: {appointment.appointment_number}
Doctor: Dr. {appointment.doctor.user.get_full_name()}
Date: {appointment.appointment_date.strftime('%B %d, %Y')}
Time: {appointment.appointment_time.strftime('%I:%M %p')}
Duration: {appointment.duration_minutes} minutes
Reason: {appointment.reason_for_visit}

Please arrive 15 minutes early for check-in.

If you need to reschedule or cancel, please contact us at least 24 hours in advance.

Thank you,
Hospital Management Team
            """
            
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[appointment.patient.user.email],
                fail_silently=False,
            )
            
            logger.info(f"Confirmation email sent for appointment {appointment.appointment_number}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send confirmation for appointment {appointment.appointment_number}: {str(e)}")
            return False
    
    @staticmethod
    def send_appointment_reminder(appointment, hours_before=24):
        """
        Send appointment reminder notification
        """
        try:
            subject = f"Appointment Reminder - {appointment.appointment_number}"
            message = f"""
Dear {appointment.patient.user.get_full_name()},

This is a reminder for your upcoming appointment:

Appointment Number: {appointment.appointment_number}
Doctor: Dr. {appointment.doctor.user.get_full_name()}
Date: {appointment.appointment_date.strftime('%B %d, %Y')}
Time: {appointment.appointment_time.strftime('%I:%M %p')}
Location: {appointment.doctor.department.name if appointment.doctor.department else 'Main Hospital'}

Please arrive 15 minutes early for check-in.

If you need to reschedule or cancel, please contact us as soon as possible.

Thank you,
Hospital Management Team
            """
            
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[appointment.patient.user.email],
                fail_silently=False,
            )
            
            logger.info(f"Reminder email sent for appointment {appointment.appointment_number}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send reminder for appointment {appointment.appointment_number}: {str(e)}")
            return False
    
    @staticmethod
    def send_appointment_cancellation(appointment, reason=None):
        """
        Send appointment cancellation notification
        """
        try:
            subject = f"Appointment Cancelled - {appointment.appointment_number}"
            message = f"""
Dear {appointment.patient.user.get_full_name()},

Your appointment has been cancelled:

Appointment Number: {appointment.appointment_number}
Doctor: Dr. {appointment.doctor.user.get_full_name()}
Original Date: {appointment.appointment_date.strftime('%B %d, %Y')}
Original Time: {appointment.appointment_time.strftime('%I:%M %p')}
"""
            
            if reason:
                message += f"\nReason: {reason}"
            
            message += """

If you would like to reschedule, please contact us to book a new appointment.

Thank you,
Hospital Management Team
            """
            
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[appointment.patient.user.email],
                fail_silently=False,
            )
            
            logger.info(f"Cancellation email sent for appointment {appointment.appointment_number}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send cancellation for appointment {appointment.appointment_number}: {str(e)}")
            return False
    
    @staticmethod
    def send_appointment_rescheduled(appointment, old_date=None, old_time=None):
        """
        Send appointment rescheduled notification
        """
        try:
            subject = f"Appointment Rescheduled - {appointment.appointment_number}"
            message = f"""
Dear {appointment.patient.user.get_full_name()},

Your appointment has been rescheduled:

Appointment Number: {appointment.appointment_number}
Doctor: Dr. {appointment.doctor.user.get_full_name()}
"""
            
            if old_date and old_time:
                message += f"""
Previous Date: {old_date.strftime('%B %d, %Y')}
Previous Time: {old_time.strftime('%I:%M %p')}
"""
            
            message += f"""
New Date: {appointment.appointment_date.strftime('%B %d, %Y')}
New Time: {appointment.appointment_time.strftime('%I:%M %p')}

Please arrive 15 minutes early for check-in.

Thank you,
Hospital Management Team
            """
            
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[appointment.patient.user.email],
                fail_silently=False,
            )
            
            logger.info(f"Reschedule email sent for appointment {appointment.appointment_number}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send reschedule notification for appointment {appointment.appointment_number}: {str(e)}")
            return False
    
    @staticmethod
    def schedule_appointment_reminders(appointment):
        """
        Schedule automatic reminders for an appointment
        """
        try:
            # Make appointment datetime timezone-aware
            appointment_datetime = timezone.make_aware(
                timezone.datetime.combine(
                    appointment.appointment_date,
                    appointment.appointment_time
                )
            )

            # Schedule 24-hour reminder
            reminder_24h = appointment_datetime - timedelta(hours=24)
            if reminder_24h > timezone.now():
                AppointmentReminder.objects.create(
                    appointment=appointment,
                    reminder_type='email',
                    scheduled_time=reminder_24h,
                    status='pending'
                )

            # Schedule 2-hour reminder
            reminder_2h = appointment_datetime - timedelta(hours=2)
            if reminder_2h > timezone.now():
                AppointmentReminder.objects.create(
                    appointment=appointment,
                    reminder_type='email',
                    scheduled_time=reminder_2h,
                    status='pending'
                )

            logger.info(f"Reminders scheduled for appointment {appointment.appointment_number}")
            return True

        except Exception as e:
            logger.error(f"Failed to schedule reminders for appointment {appointment.appointment_number}: {str(e)}")
            return False
    
    @staticmethod
    def process_pending_reminders():
        """
        Process all pending reminders that are due
        """
        now = timezone.now()
        pending_reminders = AppointmentReminder.objects.filter(
            status='pending',
            scheduled_time__lte=now
        )
        
        processed_count = 0
        for reminder in pending_reminders:
            try:
                if reminder.reminder_type == 'email':
                    success = NotificationService.send_appointment_reminder(reminder.appointment)
                    if success:
                        reminder.status = 'sent'
                        reminder.sent_at = now
                    else:
                        reminder.status = 'failed'
                        reminder.error_message = 'Failed to send email'
                else:
                    # Handle other reminder types (SMS, push, etc.)
                    reminder.status = 'failed'
                    reminder.error_message = f'Reminder type {reminder.reminder_type} not implemented'
                
                reminder.save()
                processed_count += 1
                
            except Exception as e:
                reminder.status = 'failed'
                reminder.error_message = str(e)
                reminder.save()
                logger.error(f"Failed to process reminder {reminder.id}: {str(e)}")
        
        logger.info(f"Processed {processed_count} pending reminders")
        return processed_count


class RecurringAppointmentService:
    """
    Service for handling recurring appointments
    """

    @staticmethod
    def create_recurring_appointments(base_appointment, pattern, start_date=None, end_date=None, max_count=None):
        """
        Create recurring appointments based on a pattern
        """
        try:
            if not start_date:
                start_date = base_appointment.appointment_date

            appointments_created = []
            current_date = start_date
            count = 0

            while True:
                # Check end conditions
                if end_date and current_date > end_date:
                    break
                if max_count and count >= max_count:
                    break
                if pattern.end_date and current_date > pattern.end_date:
                    break
                if pattern.max_occurrences and count >= pattern.max_occurrences:
                    break

                # Skip the base appointment date
                if current_date != base_appointment.appointment_date:
                    # Create new appointment
                    new_appointment = Appointment.objects.create(
                        patient=base_appointment.patient,
                        doctor=base_appointment.doctor,
                        appointment_type=base_appointment.appointment_type,
                        appointment_date=current_date,
                        appointment_time=base_appointment.appointment_time,
                        duration_minutes=base_appointment.duration_minutes,
                        reason_for_visit=base_appointment.reason_for_visit,
                        priority=base_appointment.priority,
                        is_recurring=True,
                        recurring_pattern=pattern,
                        parent_appointment=base_appointment,
                        created_by=base_appointment.created_by
                    )

                    appointments_created.append(new_appointment)

                    # Schedule reminders for the new appointment
                    NotificationService.schedule_appointment_reminders(new_appointment)

                # Calculate next date
                current_date = RecurringAppointmentService._calculate_next_date(current_date, pattern)
                count += 1

                # Safety check to prevent infinite loops
                if count > 1000:
                    logger.warning(f"Stopped creating recurring appointments after 1000 iterations for safety")
                    break

            logger.info(f"Created {len(appointments_created)} recurring appointments for pattern {pattern.name}")
            return appointments_created

        except Exception as e:
            logger.error(f"Failed to create recurring appointments: {str(e)}")
            return []

    @staticmethod
    def _calculate_next_date(current_date, pattern):
        """
        Calculate the next date based on the recurring pattern
        """
        if pattern.frequency == 'daily':
            return current_date + timedelta(days=pattern.interval)

        elif pattern.frequency == 'weekly':
            return current_date + timedelta(weeks=pattern.interval)

        elif pattern.frequency == 'biweekly':
            return current_date + timedelta(weeks=2 * pattern.interval)

        elif pattern.frequency == 'monthly':
            # Add months (approximate)
            next_month = current_date.month + pattern.interval
            next_year = current_date.year + (next_month - 1) // 12
            next_month = ((next_month - 1) % 12) + 1

            try:
                return current_date.replace(year=next_year, month=next_month)
            except ValueError:
                # Handle cases like Feb 31 -> Feb 28/29
                import calendar
                last_day = calendar.monthrange(next_year, next_month)[1]
                day = min(current_date.day, last_day)
                return current_date.replace(year=next_year, month=next_month, day=day)

        elif pattern.frequency == 'quarterly':
            # Add 3 months
            next_month = current_date.month + (3 * pattern.interval)
            next_year = current_date.year + (next_month - 1) // 12
            next_month = ((next_month - 1) % 12) + 1

            try:
                return current_date.replace(year=next_year, month=next_month)
            except ValueError:
                import calendar
                last_day = calendar.monthrange(next_year, next_month)[1]
                day = min(current_date.day, last_day)
                return current_date.replace(year=next_year, month=next_month, day=day)

        elif pattern.frequency == 'yearly':
            try:
                return current_date.replace(year=current_date.year + pattern.interval)
            except ValueError:
                # Handle leap year edge case (Feb 29)
                return current_date.replace(year=current_date.year + pattern.interval, day=28)

        else:
            # Default to weekly if unknown frequency
            return current_date + timedelta(weeks=pattern.interval)

    @staticmethod
    def cancel_recurring_series(parent_appointment, reason="Series cancelled", cancelled_by="staff"):
        """
        Cancel all future appointments in a recurring series
        """
        try:
            future_appointments = Appointment.objects.filter(
                parent_appointment=parent_appointment,
                appointment_date__gt=timezone.now().date(),
                status__in=['scheduled', 'confirmed']
            )

            cancelled_count = 0
            for appointment in future_appointments:
                appointment.status = 'cancelled'
                appointment.cancelled_at = timezone.now()
                appointment.cancellation_reason = reason
                appointment.cancelled_by = cancelled_by
                appointment.save()

                # Cancel reminders
                appointment.reminders.filter(status='pending').update(status='cancelled')

                # Send cancellation notification
                NotificationService.send_appointment_cancellation(appointment, reason)

                cancelled_count += 1

            logger.info(f"Cancelled {cancelled_count} future appointments in recurring series")
            return cancelled_count

        except Exception as e:
            logger.error(f"Failed to cancel recurring series: {str(e)}")
            return 0

    @staticmethod
    def schedule_follow_up(completed_appointment, follow_up_date, follow_up_notes=""):
        """
        Schedule a follow-up appointment
        """
        try:
            follow_up = Appointment.objects.create(
                patient=completed_appointment.patient,
                doctor=completed_appointment.doctor,
                appointment_type=completed_appointment.appointment_type,
                appointment_date=follow_up_date,
                appointment_time=completed_appointment.appointment_time,
                duration_minutes=completed_appointment.duration_minutes,
                reason_for_visit=f"Follow-up for {completed_appointment.appointment_number}",
                notes=follow_up_notes,
                priority=completed_appointment.priority,
                created_by=completed_appointment.created_by
            )

            # Update the original appointment
            completed_appointment.follow_up_required = True
            completed_appointment.follow_up_date = follow_up_date
            completed_appointment.follow_up_notes = follow_up_notes
            completed_appointment.save()

            # Schedule reminders for follow-up
            NotificationService.schedule_appointment_reminders(follow_up)

            # Send confirmation
            NotificationService.send_appointment_confirmation(follow_up)

            logger.info(f"Scheduled follow-up appointment {follow_up.appointment_number} for {completed_appointment.appointment_number}")
            return follow_up

        except Exception as e:
            logger.error(f"Failed to schedule follow-up: {str(e)}")
            return None
