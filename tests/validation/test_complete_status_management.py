import requests

BASE_URL = 'http://localhost:8000/api'

def test_complete_status_management():
    print("Testing Complete Appointment Status Management...")
    
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
    
    print("\n=== Testing Complete Appointment Status Management ===")
    
    # Test 1: Complete workflow (scheduled -> confirmed -> in_progress -> completed)
    print("\n1. Testing complete workflow...")
    scheduled_response = requests.get(f'{BASE_URL}/appointments/appointments/?status=scheduled', headers=headers)
    if scheduled_response.status_code == 200 and scheduled_response.json()['results']:
        appointment = scheduled_response.json()['results'][0]
        appointment_id = appointment['id']
        print(f"Using appointment: {appointment_id} ({appointment['status']})")
        
        # Check-in
        checkin_response = requests.post(f'{BASE_URL}/appointments/appointments/{appointment_id}/check_in/', json={}, headers=headers)
        if checkin_response.status_code == 200:
            print(f"✓ Check-in: {checkin_response.json()['status']}")
            
            # Start
            start_response = requests.post(f'{BASE_URL}/appointments/appointments/{appointment_id}/start/', json={}, headers=headers)
            if start_response.status_code == 200:
                print(f"✓ Start: {start_response.json()['status']}")
                
                # Complete
                complete_response = requests.post(f'{BASE_URL}/appointments/appointments/{appointment_id}/complete/', json={'notes': 'Test completion'}, headers=headers)
                if complete_response.status_code == 200:
                    print(f"✓ Complete: {complete_response.json()['status']}")
                else:
                    print(f"✗ Complete failed: {complete_response.text}")
            else:
                print(f"✗ Start failed: {start_response.text}")
        else:
            print(f"✗ Check-in failed: {checkin_response.text}")
    
    # Test 2: Cancellation workflow
    print("\n2. Testing cancellation workflow...")
    scheduled_response = requests.get(f'{BASE_URL}/appointments/appointments/?status=scheduled', headers=headers)
    if scheduled_response.status_code == 200 and scheduled_response.json()['results']:
        appointment = scheduled_response.json()['results'][0]
        appointment_id = appointment['id']
        print(f"Using appointment: {appointment_id} ({appointment['status']})")
        
        cancel_data = {
            'reason': 'Patient requested cancellation due to emergency',
            'cancelled_by': 'patient'
        }
        cancel_response = requests.post(f'{BASE_URL}/appointments/appointments/{appointment_id}/cancel/', json=cancel_data, headers=headers)
        if cancel_response.status_code == 200:
            cancelled_appointment = cancel_response.json()
            print(f"✓ Cancellation successful: {cancelled_appointment['status']}")
            print(f"  Reason: {cancelled_appointment.get('cancellation_reason', 'Not set')}")
            print(f"  Cancelled by: {cancelled_appointment.get('cancelled_by', 'Not set')}")
        else:
            print(f"✗ Cancellation failed: {cancel_response.text}")
    
    # Test 3: No-show workflow
    print("\n3. Testing no-show workflow...")
    confirmed_response = requests.get(f'{BASE_URL}/appointments/appointments/?status=confirmed', headers=headers)
    if confirmed_response.status_code == 200 and confirmed_response.json()['results']:
        appointment = confirmed_response.json()['results'][0]
        appointment_id = appointment['id']
        print(f"Using appointment: {appointment_id} ({appointment['status']})")
        
        noshow_response = requests.post(f'{BASE_URL}/appointments/appointments/{appointment_id}/no_show/', json={}, headers=headers)
        if noshow_response.status_code == 200:
            noshow_appointment = noshow_response.json()
            print(f"✓ No-show successful: {noshow_appointment['status']}")
            print(f"  No-show time: {noshow_appointment.get('no_show_at', 'Not set')}")
        else:
            print(f"✗ No-show failed: {noshow_response.text}")
    
    # Test 4: Status filtering and statistics
    print("\n4. Testing status filtering and statistics...")
    
    statuses = ['scheduled', 'confirmed', 'in_progress', 'completed', 'cancelled', 'no_show']
    for status in statuses:
        filter_response = requests.get(f'{BASE_URL}/appointments/appointments/?status={status}', headers=headers)
        if filter_response.status_code == 200:
            count = filter_response.json()['count']
            print(f"  {status.capitalize()}: {count} appointments")
        else:
            print(f"  {status.capitalize()}: Error getting count")
    
    # Test 5: Invalid status transitions
    print("\n5. Testing invalid status transitions...")
    completed_response = requests.get(f'{BASE_URL}/appointments/appointments/?status=completed', headers=headers)
    if completed_response.status_code == 200 and completed_response.json()['results']:
        appointment = completed_response.json()['results'][0]
        appointment_id = appointment['id']
        print(f"Using completed appointment: {appointment_id}")
        
        # Try to check-in a completed appointment (should fail)
        invalid_checkin = requests.post(f'{BASE_URL}/appointments/appointments/{appointment_id}/check_in/', json={}, headers=headers)
        if invalid_checkin.status_code == 400:
            print("✓ Correctly rejected check-in for completed appointment")
        else:
            print(f"✗ Should have rejected check-in: {invalid_checkin.status_code}")
        
        # Try to start a completed appointment (should fail)
        invalid_start = requests.post(f'{BASE_URL}/appointments/appointments/{appointment_id}/start/', json={}, headers=headers)
        if invalid_start.status_code == 400:
            print("✓ Correctly rejected start for completed appointment")
        else:
            print(f"✗ Should have rejected start: {invalid_start.status_code}")
    
    # Test 6: Appointment details with status information
    print("\n6. Testing appointment details with status information...")
    list_response = requests.get(f'{BASE_URL}/appointments/appointments/', headers=headers)
    if list_response.status_code == 200:
        appointments = list_response.json()['results'][:3]  # Get first 3 appointments
        print(f"Sample appointments with status information:")
        for apt in appointments:
            print(f"  - {apt['appointment_number']}: {apt['status']}")
            print(f"    Patient: {apt['patient_name']}")
            print(f"    Doctor: {apt['doctor_name']}")
            print(f"    Date/Time: {apt['appointment_date']} {apt['appointment_time']}")
            if apt.get('checked_in_at'):
                print(f"    Checked in: {apt['checked_in_at']}")
            if apt.get('started_at'):
                print(f"    Started: {apt['started_at']}")
            if apt.get('completed_at'):
                print(f"    Completed: {apt['completed_at']}")
            if apt.get('cancelled_at'):
                print(f"    Cancelled: {apt['cancelled_at']}")
            print()
    
    print("=== Complete Appointment Status Management Testing Complete ===")

if __name__ == '__main__':
    test_complete_status_management()
