import os
import django
import requests
from datetime import datetime, timedelta

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hospital_backend.settings')
django.setup()

BASE_URL = 'http://localhost:8000/api'

def test_appointment_notifications():
    print("Testing Appointment Notification System...")
    
    # Login as admin
    login_data = {
        'email': 'admin@hospital.com',
        'password': 'admin123'
    }
    
    login_response = requests.post(f'{BASE_URL}/accounts/auth/login/', json=login_data)
    print(f"Login Status: {login_response.status_code}")
    
    if login_response.status_code != 200:
        print("Login failed!")
        return
    
    token = login_response.json()['access']
    headers = {'Authorization': f'Bearer {token}'}
    
    print("\n=== Testing Appointment Notification System ===")
    
    # Test 1: Create appointment and check for confirmation notification
    print("\n1. Testing appointment creation with confirmation notification...")
    tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
    appointment_data = {
        'patient_id': 'P000001',
        'doctor_id': 'D000001',
        'appointment_date': tomorrow,
        'appointment_time': '10:30',  # Use a time that's likely available
        'duration_minutes': 30,
        'reason_for_visit': 'Notification system test',
        'priority': 'normal'
    }
    
    create_response = requests.post(
        f'{BASE_URL}/appointments/appointments/',
        json=appointment_data,
        headers=headers
    )
    print(f"Create Appointment Status: {create_response.status_code}")
    
    if create_response.status_code == 201:
        appointment = create_response.json()
        appointment_id = appointment['id']
        print(f"✓ Created appointment: {appointment.get('appointment_number', appointment['id'])}")
        print(f"  Patient: {appointment.get('patient_name', 'Patient info not available')}")
        print(f"  Doctor: {appointment.get('doctor_name', 'Doctor info not available')}")
        print(f"  Date/Time: {appointment['appointment_date']} {appointment['appointment_time']}")
        
        # Check if reminders were scheduled
        print("\n2. Checking scheduled reminders...")
        detail_response = requests.get(
            f'{BASE_URL}/appointments/appointments/{appointment_id}/',
            headers=headers
        )
        if detail_response.status_code == 200:
            appointment_detail = detail_response.json()
            reminders = appointment_detail.get('reminders', [])
            print(f"  Scheduled reminders: {len(reminders)}")
            for reminder in reminders:
                print(f"    - {reminder['reminder_type']} reminder at {reminder['scheduled_time']} (Status: {reminder['status']})")
        
        # Test 3: Cancel appointment and check for cancellation notification
        print("\n3. Testing appointment cancellation with notification...")
        cancel_data = {
            'reason': 'Testing cancellation notification system',
            'cancelled_by': 'patient'
        }
        cancel_response = requests.post(
            f'{BASE_URL}/appointments/appointments/{appointment_id}/cancel/',
            json=cancel_data,
            headers=headers
        )
        print(f"Cancel Status: {cancel_response.status_code}")
        if cancel_response.status_code == 200:
            cancelled_appointment = cancel_response.json()
            print(f"✓ Cancelled appointment: {cancelled_appointment['status']}")
            print(f"  Cancellation reason: {cancelled_appointment.get('cancellation_reason', 'Not set')}")
            print(f"  Cancelled by: {cancelled_appointment.get('cancelled_by', 'Not set')}")
            
            # Check if reminders were cancelled
            reminders = cancelled_appointment.get('reminders', [])
            cancelled_reminders = [r for r in reminders if r['status'] == 'cancelled']
            print(f"  Cancelled reminders: {len(cancelled_reminders)}")
    
    else:
        print(f"Failed to create appointment: {create_response.text}")
        # Use existing appointment for testing
        list_response = requests.get(f'{BASE_URL}/appointments/appointments/?status=scheduled', headers=headers)
        if list_response.status_code == 200 and list_response.json()['results']:
            appointment = list_response.json()['results'][0]
            appointment_id = appointment['id']
            print(f"Using existing appointment: {appointment.get('appointment_number', appointment['id'])}")
        else:
            print("No appointments available for testing")
            return
    
    # Test 4: Test reminder processing command
    print("\n4. Testing reminder processing...")
    
    # Check pending reminders in the database
    from appointments.models import AppointmentReminder
    from django.utils import timezone
    
    now = timezone.now()
    pending_reminders = AppointmentReminder.objects.filter(
        status='pending',
        scheduled_time__lte=now + timedelta(hours=1)  # Check reminders due in next hour
    )
    
    print(f"  Pending reminders in database: {pending_reminders.count()}")
    for reminder in pending_reminders[:3]:  # Show first 3
        print(f"    - {reminder.appointment.appointment_number}: {reminder.reminder_type} at {reminder.scheduled_time}")
    
    # Test the notification service directly
    print("\n5. Testing notification service directly...")
    from appointments.services import NotificationService
    
    # Get a scheduled appointment
    from appointments.models import Appointment
    scheduled_appointments = Appointment.objects.filter(status='scheduled')[:1]
    
    if scheduled_appointments:
        test_appointment = scheduled_appointments[0]
        print(f"Testing with appointment: {test_appointment.appointment_number}")
        
        # Test confirmation notification
        try:
            result = NotificationService.send_appointment_confirmation(test_appointment)
            print(f"  ✓ Confirmation notification: {'Sent' if result else 'Failed'}")
        except Exception as e:
            print(f"  ✗ Confirmation notification failed: {str(e)}")
        
        # Test reminder notification
        try:
            result = NotificationService.send_appointment_reminder(test_appointment)
            print(f"  ✓ Reminder notification: {'Sent' if result else 'Failed'}")
        except Exception as e:
            print(f"  ✗ Reminder notification failed: {str(e)}")
        
        # Test cancellation notification
        try:
            result = NotificationService.send_appointment_cancellation(test_appointment, "Test cancellation")
            print(f"  ✓ Cancellation notification: {'Sent' if result else 'Failed'}")
        except Exception as e:
            print(f"  ✗ Cancellation notification failed: {str(e)}")
    
    # Test 6: Check notification statistics
    print("\n6. Notification statistics...")
    
    # Count reminders by status
    from django.db.models import Count
    reminder_stats = AppointmentReminder.objects.values('status').annotate(count=Count('id'))
    
    print("  Reminder statistics:")
    for stat in reminder_stats:
        print(f"    - {stat['status'].capitalize()}: {stat['count']} reminders")
    
    # Recent reminders
    recent_reminders = AppointmentReminder.objects.filter(
        created_at__gte=now - timedelta(hours=24)
    ).order_by('-created_at')[:5]
    
    print(f"\n  Recent reminders (last 24 hours): {recent_reminders.count()}")
    for reminder in recent_reminders:
        print(f"    - {reminder.appointment.appointment_number}: {reminder.reminder_type} ({reminder.status})")
    
    print("\n=== Appointment Notification System Testing Complete ===")

if __name__ == '__main__':
    test_appointment_notifications()
