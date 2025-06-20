import requests
import json

BASE_URL = 'http://localhost:8000/api'

def test_login():
    print("Testing login...")
    
    # Test login with admin first
    admin_login_data = {
        'email': 'admin@hospital.com',
        'password': 'admin123'
    }

    print(f"Testing admin login: {admin_login_data['email']}")

    try:
        response = requests.post(f'{BASE_URL}/accounts/auth/login/', json=admin_login_data)
        print(f"Admin login - Status Code: {response.status_code}")
        print(f"Admin login - Response: {response.text}")

        if response.status_code == 200:
            data = response.json()
            print(f"Admin login successful!")
            return data.get('access')
    except Exception as e:
        print(f"Admin login error: {e}")

    # Test login with email
    login_data = {
        'email': 'doctor.test@hospital.com',
        'password': 'securepass123'
    }

    print(f"Attempting login with email: {login_data['email']}")

    try:
        response = requests.post(f'{BASE_URL}/accounts/auth/login/', json=login_data)
        print(f"Email login - Status Code: {response.status_code}")
        print(f"Email login - Response: {response.text}")

        if response.status_code == 200:
            data = response.json()
            print(f"Email login successful!")
            return data.get('access')
    except Exception as e:
        print(f"Email login error: {e}")

    # Try with username instead
    login_data_username = {
        'username': 'doctor.test@hospital.com',
        'password': 'securepass123'
    }
    
    print(f"Attempting username login: {login_data_username['username']}")

    try:
        response = requests.post(f'{BASE_URL}/accounts/auth/login/', json=login_data_username)
        print(f"Username login - Status Code: {response.status_code}")
        print(f"Username login - Response: {response.text}")

        if response.status_code == 200:
            data = response.json()
            print(f"Username login successful!")
            print(f"Access token: {data.get('access', 'N/A')[:50]}...")
            return data.get('access')
        else:
            print(f"Username login failed: {response.text}")
            return None

    except Exception as e:
        print(f"Username login error: {e}")
        return None

if __name__ == '__main__':
    test_login()
