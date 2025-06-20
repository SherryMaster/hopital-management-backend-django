import requests

BASE_URL = 'http://localhost:8000/api'

def test_simple_availability():
    print("Testing simple availability creation...")
    
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
    
    # Test simple availability creation
    print("\nCreating simple availability...")
    simple_data = {
        'day_of_week': 3,  # Wednesday
        'start_time': '09:00',
        'end_time': '17:00',
        'is_available': True
    }
    
    create_response = requests.post(
        f'{BASE_URL}/doctors/availability/',
        json=simple_data,
        headers=headers
    )
    print(f"Create Status: {create_response.status_code}")
    print(f"Response: {create_response.text}")

if __name__ == '__main__':
    test_simple_availability()
