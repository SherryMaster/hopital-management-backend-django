import os
import django
import requests
from datetime import datetime, timedelta

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hospital_backend.settings')
django.setup()

BASE_URL = 'http://localhost:8000/api'

def test_appointment_search_filtering():
    print("Testing Appointment Search and Filtering System...")
    
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
    
    print("\n=== Testing Appointment Search and Filtering System ===")
    
    # Test 1: Basic listing and pagination
    print("\n1. Testing basic appointment listing...")
    list_response = requests.get(f'{BASE_URL}/appointments/appointments/', headers=headers)
    print(f"List Appointments Status: {list_response.status_code}")
    
    if list_response.status_code == 200:
        appointments = list_response.json()
        print(f"✓ Retrieved {appointments['count']} total appointments")
        print(f"  Results per page: {len(appointments['results'])}")
        print(f"  Has next page: {appointments['next'] is not None}")
        
        # Show sample appointments
        for apt in appointments['results'][:3]:
            print(f"  - {apt['appointment_number']}: {apt.get('patient_name', 'N/A')} with {apt.get('doctor_name', 'N/A')} on {apt['appointment_date']}")
    
    # Test 2: Filter by status
    print("\n2. Testing status filtering...")
    status_filters = ['scheduled', 'confirmed', 'completed', 'cancelled']
    
    for status_filter in status_filters:
        status_response = requests.get(
            f'{BASE_URL}/appointments/appointments/?status={status_filter}',
            headers=headers
        )
        if status_response.status_code == 200:
            status_data = status_response.json()
            print(f"  {status_filter.capitalize()}: {status_data['count']} appointments")
    
    # Test 3: Filter by date range
    print("\n3. Testing date range filtering...")
    today = datetime.now().date()
    tomorrow = today + timedelta(days=1)
    next_week = today + timedelta(days=7)
    
    date_range_response = requests.get(
        f'{BASE_URL}/appointments/appointments/?date_from={today}&date_to={next_week}',
        headers=headers
    )
    print(f"Date Range Filter Status: {date_range_response.status_code}")
    
    if date_range_response.status_code == 200:
        date_data = date_range_response.json()
        print(f"✓ Found {date_data['count']} appointments in next 7 days")
    
    # Test 4: Filter by doctor
    print("\n4. Testing doctor filtering...")
    doctor_response = requests.get(
        f'{BASE_URL}/appointments/appointments/?doctor_name=John',
        headers=headers
    )
    print(f"Doctor Filter Status: {doctor_response.status_code}")
    
    if doctor_response.status_code == 200:
        doctor_data = doctor_response.json()
        print(f"✓ Found {doctor_data['count']} appointments with doctors named 'John'")
    
    # Test 5: Filter by patient
    print("\n5. Testing patient filtering...")
    patient_response = requests.get(
        f'{BASE_URL}/appointments/appointments/?patient_name=Jane',
        headers=headers
    )
    print(f"Patient Filter Status: {patient_response.status_code}")
    
    if patient_response.status_code == 200:
        patient_data = patient_response.json()
        print(f"✓ Found {patient_data['count']} appointments with patients named 'Jane'")
    
    # Test 6: Filter by time range
    print("\n6. Testing time range filtering...")
    time_response = requests.get(
        f'{BASE_URL}/appointments/appointments/?time_from=09:00&time_to=17:00',
        headers=headers
    )
    print(f"Time Range Filter Status: {time_response.status_code}")
    
    if time_response.status_code == 200:
        time_data = time_response.json()
        print(f"✓ Found {time_data['count']} appointments between 9 AM and 5 PM")
    
    # Test 7: Filter by duration
    print("\n7. Testing duration filtering...")
    duration_response = requests.get(
        f'{BASE_URL}/appointments/appointments/?duration_min=30&duration_max=60',
        headers=headers
    )
    print(f"Duration Filter Status: {duration_response.status_code}")
    
    if duration_response.status_code == 200:
        duration_data = duration_response.json()
        print(f"✓ Found {duration_data['count']} appointments between 30-60 minutes")
    
    # Test 8: Search functionality
    print("\n8. Testing search functionality...")
    search_terms = ['headache', 'consultation', 'checkup']
    
    for term in search_terms:
        search_response = requests.get(
            f'{BASE_URL}/appointments/appointments/?search={term}',
            headers=headers
        )
        if search_response.status_code == 200:
            search_data = search_response.json()
            print(f"  Search '{term}': {search_data['count']} results")
    
    # Test 9: Advanced search with multiple filters
    print("\n9. Testing advanced search...")
    advanced_params = {
        'status': 'scheduled',
        'date_from': str(today),
        'date_to': str(next_week),
        'time_from': '08:00',
        'time_to': '18:00',
        'ordering': '-appointment_date'
    }
    
    advanced_response = requests.get(
        f'{BASE_URL}/appointments/appointments/advanced_search/',
        params=advanced_params,
        headers=headers
    )
    print(f"Advanced Search Status: {advanced_response.status_code}")
    
    if advanced_response.status_code == 200:
        advanced_data = advanced_response.json()
        if 'statistics' in advanced_data:
            print(f"✓ Advanced search found {advanced_data['statistics']['total_count']} appointments")
            print(f"  Status breakdown:")
            for status, count in advanced_data['statistics']['status_counts'].items():
                if count > 0:
                    print(f"    - {status}: {count}")
        else:
            # Handle regular paginated response
            total_count = advanced_data.get('count', len(advanced_data.get('results', [])))
            print(f"✓ Advanced search found {total_count} appointments")
            results = advanced_data.get('results', [])
            for apt in results[:3]:
                print(f"  - {apt['appointment_number']}: {apt['status']} on {apt['appointment_date']}")
    
    # Test 10: Search suggestions
    print("\n10. Testing search suggestions...")
    suggestion_queries = ['John', 'Jane', 'APT']
    
    for query in suggestion_queries:
        suggestions_response = requests.get(
            f'{BASE_URL}/appointments/appointments/search_suggestions/?q={query}',
            headers=headers
        )
        if suggestions_response.status_code == 200:
            suggestions_data = suggestions_response.json()
            print(f"  Suggestions for '{query}': {len(suggestions_data['suggestions'])} items")
            for suggestion in suggestions_data['suggestions'][:3]:
                print(f"    - {suggestion['type']}: {suggestion['value']}")
    
    # Test 11: Ordering functionality
    print("\n11. Testing ordering functionality...")
    ordering_options = ['appointment_date', '-appointment_date', 'appointment_time', '-appointment_time']
    
    for ordering in ordering_options:
        order_response = requests.get(
            f'{BASE_URL}/appointments/appointments/?ordering={ordering}',
            headers=headers
        )
        if order_response.status_code == 200:
            order_data = order_response.json()
            if order_data['results']:
                first_apt = order_data['results'][0]
                print(f"  Ordering by '{ordering}': First appointment on {first_apt['appointment_date']} at {first_apt['appointment_time']}")
    
    # Test 12: Combined filters
    print("\n12. Testing combined filters...")
    combined_params = {
        'status': 'scheduled',
        'priority': 'normal',
        'date_from': str(today),
        'search': 'consultation',
        'ordering': 'appointment_date'
    }
    
    combined_response = requests.get(
        f'{BASE_URL}/appointments/appointments/',
        params=combined_params,
        headers=headers
    )
    print(f"Combined Filters Status: {combined_response.status_code}")
    
    if combined_response.status_code == 200:
        combined_data = combined_response.json()
        print(f"✓ Combined filters found {combined_data['count']} appointments")
        
        # Show filtered results
        for apt in combined_data['results'][:3]:
            print(f"  - {apt['appointment_number']}: {apt['status']} on {apt['appointment_date']}")
    
    # Test 13: Filter by recurring appointments
    print("\n13. Testing recurring appointment filtering...")
    recurring_response = requests.get(
        f'{BASE_URL}/appointments/appointments/?is_recurring=true',
        headers=headers
    )
    print(f"Recurring Filter Status: {recurring_response.status_code}")
    
    if recurring_response.status_code == 200:
        recurring_data = recurring_response.json()
        print(f"✓ Found {recurring_data['count']} recurring appointments")
    
    # Test 14: Performance test with large result set
    print("\n14. Testing performance with large queries...")
    start_time = datetime.now()
    
    large_query_response = requests.get(
        f'{BASE_URL}/appointments/appointments/?date_from=2024-01-01&date_to=2025-12-31',
        headers=headers
    )
    
    end_time = datetime.now()
    query_time = (end_time - start_time).total_seconds()
    
    print(f"Large Query Status: {large_query_response.status_code}")
    print(f"Query time: {query_time:.2f} seconds")
    
    if large_query_response.status_code == 200:
        large_data = large_query_response.json()
        print(f"✓ Retrieved {large_data['count']} appointments in {query_time:.2f}s")
    
    print("\n=== Appointment Search and Filtering Testing Complete ===")

if __name__ == '__main__':
    test_appointment_search_filtering()
