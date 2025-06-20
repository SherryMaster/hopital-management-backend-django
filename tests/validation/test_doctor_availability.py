import os
import django
import requests
import json
from datetime import datetime, timedelta

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hospital_backend.settings')
django.setup()

BASE_URL = 'http://localhost:8000/api'

def test_doctor_availability_management():
    print("Testing Doctor Availability Management...")
    
    # Login as doctor
    login_data = {
        'email': 'doctor.test@hospital.com',
        'password': 'securepass123'
    }
    
    login_response = requests.post(f'{BASE_URL}/accounts/auth/login/', json=login_data)
    print(f"Login Status: {login_response.status_code}")
    
    if login_response.status_code != 200:
        print("Login failed!")
        return
    
    token = login_response.json()['access']
    headers = {'Authorization': f'Bearer {token}'}
    
    print("\n=== Testing Doctor Availability Management ===")
    
    # Test 1: Get current availability
    print("\n1. Getting current availability...")
    availability_response = requests.get(
        f'{BASE_URL}/doctors/availability/my_availability/',
        headers=headers
    )
    print(f"Current Availability Status: {availability_response.status_code}")
    if availability_response.status_code == 200:
        current_availability = availability_response.json()
        print(f"Doctor: {current_availability.get('doctor_name')}")
        print(f"Current schedules: {len(current_availability.get('availability', []))}")
        for schedule in current_availability.get('availability', [])[:3]:
            print(f"  - {schedule['day_name']}: {schedule['start_time']} - {schedule['end_time']}")
    
    # Test 2: Create single availability schedule
    print("\n2. Creating single availability schedule...")
    single_schedule_data = {
        'day_of_week': 5,  # Friday
        'start_time': '09:00',
        'end_time': '17:00',
        'is_available': True,
        'break_start_time': '12:00',
        'break_end_time': '13:00'
    }
    
    create_response = requests.post(
        f'{BASE_URL}/doctors/availability/',
        json=single_schedule_data,
        headers=headers
    )
    print(f"Create Single Schedule Status: {create_response.status_code}")
    if create_response.status_code == 201:
        created_schedule = create_response.json()
        day_names = {1: 'Monday', 2: 'Tuesday', 3: 'Wednesday', 4: 'Thursday', 5: 'Friday', 6: 'Saturday', 0: 'Sunday'}
        day_name = day_names.get(created_schedule['day_of_week'], 'Unknown')
        print(f"Created schedule for {day_name}")
        print(f"  Time: {created_schedule['start_time']} - {created_schedule['end_time']}")
        print(f"  Break: {created_schedule.get('break_start_time', 'None')} - {created_schedule.get('break_end_time', 'None')}")
        print(f"  Available: {created_schedule['is_available']}")
    else:
        print(f"Failed to create schedule: {create_response.text}")
    
    # Test 3: Set weekly availability schedule
    print("\n3. Setting weekly availability schedule...")
    weekly_schedule_data = {
        'monday': {
            'start_time': '08:00',
            'end_time': '16:00',
            'is_available': True,
            'break_start_time': '12:00',
            'break_end_time': '13:00'
        },
        'tuesday': {
            'start_time': '09:00',
            'end_time': '17:00',
            'is_available': True,
            'break_start_time': '12:30',
            'break_end_time': '13:30'
        },
        'wednesday': {
            'start_time': '08:30',
            'end_time': '16:30',
            'is_available': True,
            'break_start_time': '12:00',
            'break_end_time': '13:00'
        },
        'friday': {
            'start_time': '10:00',
            'end_time': '18:00',
            'is_available': True,
            'break_start_time': '13:00',
            'break_end_time': '14:00'
        }
    }
    
    weekly_response = requests.post(
        f'{BASE_URL}/doctors/availability/set_weekly_schedule/',
        json=weekly_schedule_data,
        headers=headers
    )
    print(f"Set Weekly Schedule Status: {weekly_response.status_code}")
    if weekly_response.status_code == 201:
        weekly_result = weekly_response.json()
        print(f"Message: {weekly_result['message']}")
        print(f"Created {len(weekly_result['schedules'])} schedules:")
        for schedule in weekly_result['schedules']:
            print(f"  - {schedule['day_name']}: {schedule['start_time']} - {schedule['end_time']} (Available: {schedule['is_available']})")
    else:
        print(f"Failed to set weekly schedule: {weekly_response.text}")
    
    # Test 4: List all availability schedules
    print("\n4. Listing all availability schedules...")
    list_response = requests.get(
        f'{BASE_URL}/doctors/availability/',
        headers=headers
    )
    print(f"List Availability Status: {list_response.status_code}")
    if list_response.status_code == 200:
        schedules = list_response.json()
        print(f"Found {schedules['count']} availability schedules")
        for schedule in schedules['results'][:5]:
            print(f"  - {schedule['day_name']}: {schedule['start_time']} - {schedule['end_time']}")
            if schedule['break_start_time']:
                print(f"    Break: {schedule['break_start_time']} - {schedule['break_end_time']}")
            print(f"    Available: {schedule['is_available']}")
    
    # Test 5: Update an availability schedule
    if weekly_response.status_code == 201:
        print("\n5. Updating an availability schedule...")
        schedules = weekly_response.json()['schedules']
        if schedules:
            schedule_id = schedules[0]['id']
            update_data = {
                'start_time': '08:30',
                'end_time': '17:30',
                'is_available': True
            }
            
            update_response = requests.patch(
                f'{BASE_URL}/doctors/availability/{schedule_id}/',
                json=update_data,
                headers=headers
            )
            print(f"Update Schedule Status: {update_response.status_code}")
            if update_response.status_code == 200:
                updated_schedule = update_response.json()
                print(f"Updated {updated_schedule['day_name']} schedule:")
                print(f"  New time: {updated_schedule['start_time']} - {updated_schedule['end_time']}")
                print(f"  Available: {updated_schedule['is_available']}")
    
    # Test 6: Filter availability by day
    print("\n6. Filtering availability by day...")
    filter_response = requests.get(
        f'{BASE_URL}/doctors/availability/?day_of_week=1',  # Monday
        headers=headers
    )
    print(f"Filter by Monday Status: {filter_response.status_code}")
    if filter_response.status_code == 200:
        monday_schedules = filter_response.json()
        print(f"Found {monday_schedules['count']} Monday schedules")
        for schedule in monday_schedules['results']:
            print(f"  - Monday: {schedule['start_time']} - {schedule['end_time']}")
    
    print("\n=== Doctor Availability Management Testing Complete ===")

if __name__ == '__main__':
    test_doctor_availability_management()
