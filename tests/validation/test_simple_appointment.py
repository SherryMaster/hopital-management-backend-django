import requests
import json
from datetime import datetime, timedelta

# Base URL
base_url = 'http://localhost:8000/api'

# Login as admin
login_data = {
    'email': 'admin@hospital.com',
    'password': 'admin123'
}

login_response = requests.post(f'{base_url}/accounts/auth/login/', json=login_data)
print(f"Login Status: {login_response.status_code}")

if login_response.status_code == 200:
    token = login_response.json()['access']
    headers = {'Authorization': f'Bearer {token}'}
    
    # Try to create an appointment
    tomorrow = (datetime.now() + timedelta(days=2)).strftime('%Y-%m-%d')
    appointment_data = {
        'patient_id': 'P000001',
        'doctor_id': 'D000002',
        'appointment_date': tomorrow,
        'appointment_time': '08:00',
        'duration_minutes': 30,
        'reason_for_visit': 'Test appointment',
        'priority': 'normal'
    }
    
    print(f"Creating appointment with data: {json.dumps(appointment_data, indent=2)}")
    
    booking_response = requests.post(
        f'{base_url}/appointments/appointments/',
        headers=headers,
        json=appointment_data
    )
    
    print(f"Booking Status: {booking_response.status_code}")
    print(f"Response: {booking_response.text}")
else:
    print("Login failed")
    print(f"Response: {login_response.text}")
