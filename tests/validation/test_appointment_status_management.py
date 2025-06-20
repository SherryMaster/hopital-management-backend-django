import os
import django
import requests
from datetime import datetime, timedelta

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hospital_backend.settings')
django.setup()

BASE_URL = 'http://localhost:8000/api'

def test_appointment_status_management():
    print("Testing Appointment Status Management...")
    
    # Login as admin to have full access
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
    
    print("\n=== Testing Appointment Status Management ===")
    
    # Step 1: Create a new appointment for testing
    print("\n1. Creating test appointment...")
    tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
    appointment_data = {
        'patient_id': 'P000001',
        'doctor_id': 'D000001',
        'appointment_date': tomorrow,
        'appointment_time': '08:00',  # Early morning to avoid conflicts
        'duration_minutes': 30,
        'reason_for_visit': 'Status management test',
        'priority': 'normal'
    }
    
    create_response = requests.post(
        f'{BASE_URL}/appointments/appointments/',
        json=appointment_data,
        headers=headers
    )
    print(f"Create Appointment Status: {create_response.status_code}")
    
    if create_response.status_code != 201:
        print(f"Failed to create appointment: {create_response.text}")
        # Try to use an existing appointment
        list_response = requests.get(f'{BASE_URL}/appointments/appointments/', headers=headers)
        if list_response.status_code == 200:
            appointments = list_response.json()['results']
            if appointments:
                appointment_id = appointments[0]['id']
                print(f"Using existing appointment: {appointment_id}")
            else:
                print("No appointments available for testing")
                return
        else:
            print("Failed to get existing appointments")
            return
    else:
        appointment = create_response.json()
        appointment_id = appointment['id']
        print(f"Created appointment: {appointment_id}")
        print(f"  Patient: {appointment['patient_name']}")
        print(f"  Doctor: {appointment['doctor_name']}")
        print(f"  Date: {appointment['appointment_date']}")
        print(f"  Time: {appointment['appointment_time']}")
        print(f"  Initial Status: {appointment['status']}")
    
    # Step 2: Test status transitions
    print(f"\n2. Testing status transitions for appointment {appointment_id}...")
    
    # Get current status
    detail_response = requests.get(
        f'{BASE_URL}/appointments/appointments/{appointment_id}/',
        headers=headers
    )
    if detail_response.status_code == 200:
        current_appointment = detail_response.json()
        print(f"Current status: {current_appointment['status']}")
    
    # Test 2a: Check-in patient
    print("\n2a. Testing patient check-in...")
    checkin_response = requests.post(
        f'{BASE_URL}/appointments/appointments/{appointment_id}/check_in/',
        json={},  # Empty JSON body
        headers=headers
    )
    print(f"Check-in Status: {checkin_response.status_code}")
    if checkin_response.status_code == 200:
        updated_appointment = checkin_response.json()
        print(f"  Status after check-in: {updated_appointment['status']}")
        print(f"  Check-in time: {updated_appointment.get('checked_in_at', 'Not set')}")
    else:
        print(f"Check-in failed: {checkin_response.text}")
    
    # Test 2b: Start appointment
    print("\n2b. Testing appointment start...")
    start_response = requests.post(
        f'{BASE_URL}/appointments/appointments/{appointment_id}/start/',
        json={},  # Empty JSON body
        headers=headers
    )
    print(f"Start Status: {start_response.status_code}")
    if start_response.status_code == 200:
        updated_appointment = start_response.json()
        print(f"  Status after start: {updated_appointment['status']}")
        print(f"  Started at: {updated_appointment.get('started_at', 'Not set')}")
    else:
        print(f"Start failed: {start_response.text}")
    
    # Test 2c: Complete appointment
    print("\n2c. Testing appointment completion...")
    complete_data = {
        'notes': 'Appointment completed successfully. Patient responded well to treatment.',
        'follow_up_required': True,
        'follow_up_date': (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
    }
    complete_response = requests.post(
        f'{BASE_URL}/appointments/appointments/{appointment_id}/complete/',
        json=complete_data,
        headers=headers
    )
    print(f"Complete Status: {complete_response.status_code}")
    if complete_response.status_code == 200:
        updated_appointment = complete_response.json()
        print(f"  Status after completion: {updated_appointment['status']}")
        print(f"  Completed at: {updated_appointment.get('completed_at', 'Not set')}")
        print(f"  Notes: {updated_appointment.get('notes', 'No notes')}")
    else:
        print(f"Complete failed: {complete_response.text}")
    
    # Step 3: Test cancellation workflow (create another appointment)
    print("\n3. Testing cancellation workflow...")
    
    # Create another appointment for cancellation test
    cancel_appointment_data = {
        'patient_id': 'P000001',
        'doctor_id': 'D000002',
        'appointment_date': tomorrow,
        'appointment_time': '08:30',  # Early morning to avoid conflicts
        'duration_minutes': 30,
        'reason_for_visit': 'Cancellation test',
        'priority': 'normal'
    }
    
    cancel_create_response = requests.post(
        f'{BASE_URL}/appointments/appointments/',
        json=cancel_appointment_data,
        headers=headers
    )
    
    if cancel_create_response.status_code == 201:
        cancel_appointment = cancel_create_response.json()
        cancel_appointment_id = cancel_appointment['id']
        print(f"Created appointment for cancellation test: {cancel_appointment_id}")
        
        # Test cancellation
        cancel_data = {
            'reason': 'Patient requested cancellation due to scheduling conflict',
            'cancelled_by': 'patient'
        }
        cancel_response = requests.post(
            f'{BASE_URL}/appointments/appointments/{cancel_appointment_id}/cancel/',
            json=cancel_data,
            headers=headers
        )
        print(f"Cancel Status: {cancel_response.status_code}")
        if cancel_response.status_code == 200:
            cancelled_appointment = cancel_response.json()
            print(f"  Status after cancellation: {cancelled_appointment['status']}")
            print(f"  Cancelled at: {cancelled_appointment.get('cancelled_at', 'Not set')}")
            print(f"  Cancellation reason: {cancelled_appointment.get('cancellation_reason', 'No reason')}")
        else:
            print(f"Cancel failed: {cancel_response.text}")
    else:
        print(f"Failed to create appointment for cancellation test: {cancel_create_response.text}")
    
    # Step 4: Test no-show workflow (create another appointment)
    print("\n4. Testing no-show workflow...")
    
    # Create another appointment for no-show test
    noshow_appointment_data = {
        'patient_id': 'P000002',
        'doctor_id': 'D000001',
        'appointment_date': tomorrow,
        'appointment_time': '09:00',  # Early morning to avoid conflicts
        'duration_minutes': 30,
        'reason_for_visit': 'No-show test',
        'priority': 'normal'
    }
    
    noshow_create_response = requests.post(
        f'{BASE_URL}/appointments/appointments/',
        json=noshow_appointment_data,
        headers=headers
    )
    
    if noshow_create_response.status_code == 201:
        noshow_appointment = noshow_create_response.json()
        noshow_appointment_id = noshow_appointment['id']
        print(f"Created appointment for no-show test: {noshow_appointment_id}")
        
        # Test no-show
        noshow_response = requests.post(
            f'{BASE_URL}/appointments/appointments/{noshow_appointment_id}/no_show/',
            json={},  # Empty JSON body
            headers=headers
        )
        print(f"No-show Status: {noshow_response.status_code}")
        if noshow_response.status_code == 200:
            noshow_appointment_result = noshow_response.json()
            print(f"  Status after no-show: {noshow_appointment_result['status']}")
            print(f"  No-show marked at: {noshow_appointment_result.get('no_show_at', 'Not set')}")
        else:
            print(f"No-show failed: {noshow_response.text}")
    else:
        print(f"Failed to create appointment for no-show test: {noshow_create_response.text}")
    
    # Step 5: Test status filtering
    print("\n5. Testing status filtering...")
    
    # Filter by completed status
    completed_response = requests.get(
        f'{BASE_URL}/appointments/appointments/?status=completed',
        headers=headers
    )
    print(f"Filter Completed Status: {completed_response.status_code}")
    if completed_response.status_code == 200:
        completed_appointments = completed_response.json()
        print(f"  Found {completed_appointments['count']} completed appointments")
    
    # Filter by cancelled status
    cancelled_response = requests.get(
        f'{BASE_URL}/appointments/appointments/?status=cancelled',
        headers=headers
    )
    print(f"Filter Cancelled Status: {cancelled_response.status_code}")
    if cancelled_response.status_code == 200:
        cancelled_appointments = cancelled_response.json()
        print(f"  Found {cancelled_appointments['count']} cancelled appointments")
    
    # Filter by no-show status
    noshow_filter_response = requests.get(
        f'{BASE_URL}/appointments/appointments/?status=no_show',
        headers=headers
    )
    print(f"Filter No-show Status: {noshow_filter_response.status_code}")
    if noshow_filter_response.status_code == 200:
        noshow_appointments = noshow_filter_response.json()
        print(f"  Found {noshow_appointments['count']} no-show appointments")
    
    print("\n=== Appointment Status Management Testing Complete ===")

if __name__ == '__main__':
    test_appointment_status_management()
