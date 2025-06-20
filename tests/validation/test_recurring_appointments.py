import os
import django
from datetime import datetime, timedelta

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hospital_backend.settings')
django.setup()

from django.utils import timezone
from appointments.models import Appointment, RecurringPattern
from appointments.services import RecurringAppointmentService
from patients.models import Patient
from doctors.models import Doctor

def test_recurring_appointments():
    print("Testing Recurring Appointments System...")
    
    # Get a patient and doctor for testing
    try:
        patient = Patient.objects.get(patient_id='P000001')
        doctor = Doctor.objects.get(doctor_id='D000001')
        print(f"Using Patient: {patient.user.get_full_name()}")
        print(f"Using Doctor: {doctor.user.get_full_name()}")
    except (Patient.DoesNotExist, Doctor.DoesNotExist) as e:
        print(f"Error: {e}")
        return
    
    # Test 1: Create a recurring pattern
    print("\n1. Creating recurring patterns...")
    
    # Weekly pattern
    weekly_pattern, created = RecurringPattern.objects.get_or_create(
        name="Weekly Therapy Sessions",
        defaults={
            'frequency': 'weekly',
            'interval': 1,
            'max_occurrences': 8,
            'is_active': True
        }
    )
    print(f"Weekly pattern: {weekly_pattern.name} ({'created' if created else 'existing'})")
    
    # Monthly pattern
    monthly_pattern, created = RecurringPattern.objects.get_or_create(
        name="Monthly Check-up",
        defaults={
            'frequency': 'monthly',
            'interval': 1,
            'max_occurrences': 6,
            'is_active': True
        }
    )
    print(f"Monthly pattern: {monthly_pattern.name} ({'created' if created else 'existing'})")
    
    # Test 2: Create a base appointment
    print("\n2. Creating base appointment...")
    
    # Use a future date
    base_date = timezone.now().date() + timedelta(days=7)
    base_time = timezone.now().time().replace(hour=10, minute=0, second=0, microsecond=0)
    
    # Check if appointment already exists
    existing_base = Appointment.objects.filter(
        patient=patient,
        doctor=doctor,
        appointment_date=base_date,
        appointment_time=base_time,
        is_recurring=False
    ).first()
    
    if existing_base:
        print(f"Using existing base appointment: {existing_base.appointment_number}")
        base_appointment = existing_base
    else:
        base_appointment = Appointment.objects.create(
            patient=patient,
            doctor=doctor,
            appointment_date=base_date,
            appointment_time=base_time,
            duration_minutes=30,
            reason_for_visit='Base appointment for recurring series',
            priority='normal',
            status='scheduled',
            is_recurring=False
        )
        print(f"Created base appointment: {base_appointment.appointment_number}")
    
    print(f"Base appointment: {base_appointment.appointment_date} at {base_appointment.appointment_time}")
    
    # Test 3: Create weekly recurring appointments
    print("\n3. Creating weekly recurring appointments...")
    
    # Clear any existing recurring appointments for this base
    Appointment.objects.filter(parent_appointment=base_appointment).delete()
    
    weekly_appointments = RecurringAppointmentService.create_recurring_appointments(
        base_appointment=base_appointment,
        pattern=weekly_pattern,
        max_count=4  # Create 4 weekly appointments
    )
    
    print(f"Created {len(weekly_appointments)} weekly recurring appointments:")
    for apt in weekly_appointments:
        print(f"  - {apt.appointment_number}: {apt.appointment_date} at {apt.appointment_time}")
    
    # Test 4: Test follow-up scheduling
    print("\n4. Testing follow-up scheduling...")
    
    # Create a completed appointment
    completed_appointment = Appointment.objects.create(
        patient=patient,
        doctor=doctor,
        appointment_date=timezone.now().date() - timedelta(days=1),
        appointment_time=timezone.now().time().replace(hour=14, minute=0, second=0, microsecond=0),
        duration_minutes=30,
        reason_for_visit='Completed appointment for follow-up test',
        priority='normal',
        status='completed',
        completed_at=timezone.now()
    )
    
    # Schedule follow-up
    follow_up_date = timezone.now().date() + timedelta(days=14)
    follow_up = RecurringAppointmentService.schedule_follow_up(
        completed_appointment=completed_appointment,
        follow_up_date=follow_up_date,
        follow_up_notes="Follow-up to check treatment progress"
    )
    
    if follow_up:
        print(f"✓ Scheduled follow-up: {follow_up.appointment_number}")
        print(f"  Date: {follow_up.appointment_date}")
        print(f"  Reason: {follow_up.reason_for_visit}")
        print(f"  Original appointment follow-up required: {completed_appointment.follow_up_required}")
    else:
        print("✗ Failed to schedule follow-up")
    
    # Test 5: Test recurring series cancellation
    print("\n5. Testing recurring series cancellation...")
    
    if weekly_appointments:
        cancelled_count = RecurringAppointmentService.cancel_recurring_series(
            parent_appointment=base_appointment,
            reason="Patient requested cancellation of entire series",
            cancelled_by="patient"
        )
        print(f"✓ Cancelled {cancelled_count} future appointments in the series")
        
        # Check status of cancelled appointments
        cancelled_appointments = Appointment.objects.filter(
            parent_appointment=base_appointment,
            status='cancelled'
        )
        print(f"  Cancelled appointments:")
        for apt in cancelled_appointments:
            print(f"    - {apt.appointment_number}: {apt.status} (Reason: {apt.cancellation_reason})")
    
    # Test 6: Test pattern calculations
    print("\n6. Testing pattern calculations...")
    
    test_date = timezone.now().date()
    
    # Test weekly calculation
    next_weekly = RecurringAppointmentService._calculate_next_date(test_date, weekly_pattern)
    print(f"Next weekly date from {test_date}: {next_weekly}")
    
    # Test monthly calculation
    next_monthly = RecurringAppointmentService._calculate_next_date(test_date, monthly_pattern)
    print(f"Next monthly date from {test_date}: {next_monthly}")
    
    # Test 7: Statistics and summary
    print("\n7. Recurring appointments statistics...")
    
    # Count recurring appointments
    total_recurring = Appointment.objects.filter(is_recurring=True).count()
    active_recurring = Appointment.objects.filter(
        is_recurring=True,
        status__in=['scheduled', 'confirmed']
    ).count()
    
    print(f"Total recurring appointments: {total_recurring}")
    print(f"Active recurring appointments: {active_recurring}")
    
    # Count by pattern
    for pattern in RecurringPattern.objects.filter(is_active=True):
        pattern_count = Appointment.objects.filter(recurring_pattern=pattern).count()
        print(f"  {pattern.name}: {pattern_count} appointments")
    
    # Recent recurring appointments
    recent_recurring = Appointment.objects.filter(
        is_recurring=True,
        created_at__gte=timezone.now() - timedelta(hours=1)
    ).order_by('-created_at')
    
    print(f"\nRecent recurring appointments (last hour): {recent_recurring.count()}")
    for apt in recent_recurring[:5]:
        print(f"  - {apt.appointment_number}: {apt.appointment_date} ({apt.status})")
    
    # Follow-up appointments
    follow_ups = Appointment.objects.filter(
        reason_for_visit__icontains='follow-up'
    )
    print(f"\nFollow-up appointments: {follow_ups.count()}")
    for apt in follow_ups[:3]:
        print(f"  - {apt.appointment_number}: {apt.appointment_date}")
    
    print("\n=== Recurring Appointments Testing Complete ===")

if __name__ == '__main__':
    test_recurring_appointments()
