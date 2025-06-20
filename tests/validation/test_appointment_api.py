import requests
import json
from datetime import datetime, timedelta

def test_appointment_api():
    print("Testing Appointment Booking API...")
    
    # Base URL
    base_url = 'http://localhost:8000/api'
    
    # Login as admin to get token
    login_data = {
        'email': 'admin@hospital.com',
        'password': 'admin123'
    }
    
    login_response = requests.post(f'{base_url}/accounts/auth/login/', json=login_data)
    print(f"Login Status: {login_response.status_code}")
    
    if login_response.status_code != 200:
        print("Failed to login")
        return
    
    token = login_response.json()['access']
    headers = {'Authorization': f'Bearer {token}'}
    
    print("\n=== Testing Appointment Types ===")
    
    # Get appointment types
    types_response = requests.get(f'{base_url}/appointments/appointment-types/', headers=headers)
    print(f"Appointment Types Status: {types_response.status_code}")
    
    if types_response.status_code == 200:
        types_data = types_response.json()
        print(f"Found {len(types_data['results'])} appointment types")
        for apt_type in types_data['results'][:3]:
            print(f"  - {apt_type['name']}: {apt_type['duration_minutes']} minutes")
    
    print("\n=== Testing Doctor Availability ===")
    
    # Check doctor availability
    tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
    availability_params = {
        'doctor_id': 'D000001',  # Assuming this doctor exists
        'date': tomorrow
    }
    
    availability_response = requests.get(
        f'{base_url}/appointments/appointments/check_availability/',
        headers=headers,
        params=availability_params
    )
    print(f"Availability Check Status: {availability_response.status_code}")
    
    if availability_response.status_code == 200:
        availability_data = availability_response.json()
        print(f"Doctor: {availability_data.get('doctor_name', 'Unknown')}")
        print(f"Date: {availability_data.get('date')}")
        print(f"Available slots: {len(availability_data.get('available_slots', []))}")
        print(f"Existing appointments: {len(availability_data.get('existing_appointments', []))}")
        
        # Show first few available slots
        for slot in availability_data.get('available_slots', [])[:3]:
            print(f"  - Available: {slot['time']}")
    
    print("\n=== Testing Appointment Booking ===")
    
    # Book a new appointment
    appointment_data = {
        'patient_id': 'P000001',  # Assuming this patient exists
        'doctor_id': 'D000001',   # Assuming this doctor exists
        'appointment_date': tomorrow,
        'appointment_time': '14:00',
        'duration_minutes': 30,
        'reason_for_visit': 'Regular check-up',
        'symptoms': 'General wellness check',
        'priority': 'normal'
    }
    
    booking_response = requests.post(
        f'{base_url}/appointments/appointments/',
        headers=headers,
        json=appointment_data
    )
    print(f"Appointment Booking Status: {booking_response.status_code}")
    
    if booking_response.status_code == 201:
        booking_data = booking_response.json()
        appointment_id = booking_data['id']
        appointment_number = booking_data['appointment_number']
        print(f"✓ Appointment booked successfully!")
        print(f"  Appointment Number: {appointment_number}")
        print(f"  Patient: {booking_data['patient']['name']}")
        print(f"  Doctor: {booking_data['doctor']['name']}")
        print(f"  Date & Time: {booking_data['appointment_date']} {booking_data['appointment_time']}")
        print(f"  Status: {booking_data['status']}")
        
        print("\n=== Testing Appointment Management ===")
        
        # Check in patient
        checkin_response = requests.post(
            f'{base_url}/appointments/appointments/{appointment_id}/check_in/',
            headers=headers
        )
        print(f"Check-in Status: {checkin_response.status_code}")
        
        if checkin_response.status_code == 200:
            checkin_data = checkin_response.json()
            print(f"✓ Patient checked in. Status: {checkin_data['status']}")
        
        # Start appointment
        start_response = requests.post(
            f'{base_url}/appointments/appointments/{appointment_id}/start/',
            headers=headers
        )
        print(f"Start Appointment Status: {start_response.status_code}")
        
        if start_response.status_code == 200:
            start_data = start_response.json()
            print(f"✓ Appointment started. Status: {start_data['status']}")
        
        # Complete appointment
        complete_response = requests.post(
            f'{base_url}/appointments/appointments/{appointment_id}/complete/',
            headers=headers
        )
        print(f"Complete Appointment Status: {complete_response.status_code}")
        
        if complete_response.status_code == 200:
            complete_data = complete_response.json()
            print(f"✓ Appointment completed. Status: {complete_data['status']}")
    
    elif booking_response.status_code == 400:
        error_data = booking_response.json()
        print(f"Booking failed with validation errors:")
        for field, errors in error_data.items():
            print(f"  {field}: {errors}")
    
    print("\n=== Testing Appointment List ===")
    
    # Get appointments list
    appointments_response = requests.get(f'{base_url}/appointments/appointments/', headers=headers)
    print(f"Appointments List Status: {appointments_response.status_code}")
    
    if appointments_response.status_code == 200:
        appointments_data = appointments_response.json()
        print(f"Found {appointments_data['count']} total appointments")
        
        for appointment in appointments_data['results'][:3]:
            print(f"  - {appointment['appointment_number']}: {appointment['patient_name']} "
                  f"with {appointment['doctor_name']} on {appointment['appointment_date']} "
                  f"at {appointment['appointment_time']} ({appointment['status']})")
    
    print("\n=== Testing Appointment Search ===")
    
    # Search appointments
    search_params = {'search': 'check-up'}
    search_response = requests.get(
        f'{base_url}/appointments/appointments/',
        headers=headers,
        params=search_params
    )
    print(f"Search Status: {search_response.status_code}")
    
    if search_response.status_code == 200:
        search_data = search_response.json()
        print(f"Search found {search_data['count']} appointments")
    
    print("\n=== Testing Appointment Filtering ===")
    
    # Filter by status
    filter_params = {'status': 'scheduled'}
    filter_response = requests.get(
        f'{base_url}/appointments/appointments/',
        headers=headers,
        params=filter_params
    )
    print(f"Filter Status: {filter_response.status_code}")
    
    if filter_response.status_code == 200:
        filter_data = filter_response.json()
        print(f"Found {filter_data['count']} scheduled appointments")
    
    print("\n=== Appointment API Testing Complete ===")

if __name__ == '__main__':
    test_appointment_api()
