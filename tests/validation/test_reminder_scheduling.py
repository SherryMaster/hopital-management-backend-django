import os
import django
from datetime import datetime, timedelta

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hospital_backend.settings')
django.setup()

from django.utils import timezone
from appointments.models import Appointment, AppointmentReminder
from appointments.services import NotificationService
from patients.models import Patient
from doctors.models import Doctor

def test_reminder_scheduling():
    print("Testing Reminder Scheduling System...")
    
    # Get a patient and doctor for testing
    try:
        patient = Patient.objects.get(patient_id='P000001')
        doctor = Doctor.objects.get(doctor_id='D000001')
        print(f"Using Patient: {patient.user.get_full_name()}")
        print(f"Using Doctor: {doctor.user.get_full_name()}")
    except (Patient.DoesNotExist, Doctor.DoesNotExist) as e:
        print(f"Error: {e}")
        return
    
    # Create a test appointment for tomorrow
    tomorrow = timezone.now().date() + timedelta(days=1)
    appointment_time = timezone.now().time().replace(hour=14, minute=0, second=0, microsecond=0)
    
    # Check if appointment already exists
    existing = Appointment.objects.filter(
        patient=patient,
        doctor=doctor,
        appointment_date=tomorrow,
        appointment_time=appointment_time
    ).first()
    
    if existing:
        print(f"Using existing appointment: {existing.appointment_number}")
        appointment = existing
    else:
        # Create new appointment
        appointment = Appointment.objects.create(
            patient=patient,
            doctor=doctor,
            appointment_date=tomorrow,
            appointment_time=appointment_time,
            duration_minutes=30,
            reason_for_visit='Reminder scheduling test',
            priority='normal',
            status='scheduled'
        )
        print(f"Created new appointment: {appointment.appointment_number}")
    
    print(f"Appointment Date/Time: {appointment.appointment_date} {appointment.appointment_time}")
    
    # Test reminder scheduling
    print("\nTesting reminder scheduling...")
    
    # Clear existing reminders for this appointment
    appointment.reminders.all().delete()
    
    # Schedule reminders
    result = NotificationService.schedule_appointment_reminders(appointment)
    print(f"Reminder scheduling result: {'Success' if result else 'Failed'}")
    
    # Check scheduled reminders
    reminders = appointment.reminders.all().order_by('scheduled_time')
    print(f"\nScheduled reminders: {reminders.count()}")
    
    appointment_datetime = timezone.make_aware(
        timezone.datetime.combine(appointment.appointment_date, appointment.appointment_time)
    )

    for reminder in reminders:
        time_diff = appointment_datetime - reminder.scheduled_time
        hours_before = time_diff.total_seconds() / 3600
        print(f"  - {reminder.reminder_type} reminder: {reminder.scheduled_time}")
        print(f"    Status: {reminder.status}")
        print(f"    Hours before appointment: {hours_before:.1f}")
        print()
    
    # Test processing reminders that are due
    print("Testing reminder processing...")
    
    # Create a reminder that's due now for testing
    test_reminder = AppointmentReminder.objects.create(
        appointment=appointment,
        reminder_type='email',
        scheduled_time=timezone.now() - timedelta(minutes=1),  # 1 minute ago
        status='pending'
    )
    print(f"Created test reminder due 1 minute ago")
    
    # Process pending reminders
    processed_count = NotificationService.process_pending_reminders()
    print(f"Processed {processed_count} reminders")
    
    # Check the status of our test reminder
    test_reminder.refresh_from_db()
    print(f"Test reminder status: {test_reminder.status}")
    if test_reminder.sent_at:
        print(f"Test reminder sent at: {test_reminder.sent_at}")
    if test_reminder.error_message:
        print(f"Test reminder error: {test_reminder.error_message}")
    
    # Show all reminders for this appointment
    print(f"\nAll reminders for appointment {appointment.appointment_number}:")
    all_reminders = appointment.reminders.all().order_by('scheduled_time')
    for reminder in all_reminders:
        print(f"  - {reminder.reminder_type}: {reminder.scheduled_time} ({reminder.status})")
    
    # Test reminder statistics
    print("\nReminder Statistics:")
    from django.db.models import Count
    
    stats = AppointmentReminder.objects.values('status').annotate(count=Count('id'))
    for stat in stats:
        print(f"  {stat['status'].capitalize()}: {stat['count']} reminders")
    
    # Recent reminders
    recent = AppointmentReminder.objects.filter(
        created_at__gte=timezone.now() - timedelta(hours=1)
    ).order_by('-created_at')
    
    print(f"\nRecent reminders (last hour): {recent.count()}")
    for reminder in recent[:5]:
        print(f"  - {reminder.appointment.appointment_number}: {reminder.reminder_type} ({reminder.status})")
    
    print("\n=== Reminder Scheduling Test Complete ===")

if __name__ == '__main__':
    test_reminder_scheduling()
