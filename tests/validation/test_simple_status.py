import requests

BASE_URL = 'http://localhost:8000/api'

def test_simple_status():
    print("Testing simple status management...")
    
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
    
    # Get a scheduled appointment
    list_response = requests.get(f'{BASE_URL}/appointments/appointments/?status=scheduled', headers=headers)
    if list_response.status_code == 200:
        appointments = list_response.json()['results']
        if appointments:
            appointment_id = appointments[0]['id']
            print(f"Using scheduled appointment: {appointment_id}")
            print(f"Current status: {appointments[0]['status']}")
            print(f"Patient: {appointments[0]['patient_name']}")
            print(f"Doctor: {appointments[0]['doctor_name']}")
            print(f"Date: {appointments[0]['appointment_date']}")
            print(f"Time: {appointments[0]['appointment_time']}")

            # Try to check in
            print("\nTesting check-in...")
            checkin_response = requests.post(
                f'{BASE_URL}/appointments/appointments/{appointment_id}/check_in/',
                json={},
                headers=headers
            )
            print(f"Check-in Status: {checkin_response.status_code}")
            if checkin_response.status_code == 200:
                updated_appointment = checkin_response.json()
                print(f"✓ Check-in successful!")
                print(f"  New status: {updated_appointment['status']}")
                print(f"  Checked in at: {updated_appointment.get('checked_in_at', 'Not set')}")

                # Try to start the appointment
                print("\nTesting appointment start...")
                start_response = requests.post(
                    f'{BASE_URL}/appointments/appointments/{appointment_id}/start/',
                    json={},
                    headers=headers
                )
                print(f"Start Status: {start_response.status_code}")
                if start_response.status_code == 200:
                    started_appointment = start_response.json()
                    print(f"✓ Start successful!")
                    print(f"  New status: {started_appointment['status']}")
                    print(f"  Started at: {started_appointment.get('started_at', 'Not set')}")

                    # Try to complete the appointment
                    print("\nTesting appointment completion...")
                    complete_data = {
                        'notes': 'Test appointment completed successfully',
                        'follow_up_required': False
                    }
                    complete_response = requests.post(
                        f'{BASE_URL}/appointments/appointments/{appointment_id}/complete/',
                        json=complete_data,
                        headers=headers
                    )
                    print(f"Complete Status: {complete_response.status_code}")
                    if complete_response.status_code == 200:
                        completed_appointment = complete_response.json()
                        print(f"✓ Completion successful!")
                        print(f"  Final status: {completed_appointment['status']}")
                        print(f"  Completed at: {completed_appointment.get('completed_at', 'Not set')}")
                        print(f"  Notes: {completed_appointment.get('notes', 'No notes')}")
                    else:
                        print(f"✗ Complete failed: {complete_response.text}")
                else:
                    print(f"✗ Start failed: {start_response.text}")
            else:
                print(f"✗ Check-in failed: {checkin_response.text}")
        else:
            print("No scheduled appointments found")
    else:
        print(f"Failed to get appointments: {list_response.text}")

if __name__ == '__main__':
    test_simple_status()
