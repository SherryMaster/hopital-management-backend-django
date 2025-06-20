import requests
import json

def test_doctor_api():
    print("Testing Doctor Management API...")
    
    # First login to get token
    login_data = {
        'email': 'admin@hospital.com',
        'password': 'MyStr0ngP@ssw0rd!'
    }

    login_response = requests.post('http://localhost:8000/api/accounts/auth/login/', json=login_data)
    print(f'Login Status: {login_response.status_code}')

    if login_response.status_code == 200:
        token = login_response.json()['access']
        headers = {'Authorization': f'Bearer {token}'}
        
        # Test specializations endpoint
        print("\n=== Testing Specializations ===")
        spec_response = requests.get('http://localhost:8000/api/doctors/specializations/', headers=headers)
        print(f'Specializations Status: {spec_response.status_code}')
        
        if spec_response.status_code == 200:
            specializations = spec_response.json()
            print(f'Found {len(specializations["results"])} specializations')
            for spec in specializations['results'][:3]:  # Show first 3
                print(f'  - {spec["name"]}')
        
        # Test departments endpoint
        print("\n=== Testing Departments ===")
        dept_response = requests.get('http://localhost:8000/api/doctors/departments/', headers=headers)
        print(f'Departments Status: {dept_response.status_code}')
        
        if dept_response.status_code == 200:
            departments = dept_response.json()
            print(f'Found {len(departments["results"])} departments')
            for dept in departments['results'][:3]:  # Show first 3
                print(f'  - {dept["name"]} (Location: {dept["location"]})')
        
        # Test doctors list endpoint
        print("\n=== Testing Doctors List ===")
        doctors_response = requests.get('http://localhost:8000/api/doctors/doctors/', headers=headers)
        print(f'Doctors List Status: {doctors_response.status_code}')
        
        if doctors_response.status_code == 200:
            doctors = doctors_response.json()
            print(f'Found {len(doctors["results"])} doctors')
            for doctor in doctors['results']:
                dept_name = doctor.get("department_name", "No Department")
                print(f'  - {doctor["doctor_id"]}: Dr. {doctor["full_name"]} ({dept_name})')
                print(f'    Specializations: {[s["name"] for s in doctor["specializations"]]}')
                print(f'    Fee: ${doctor["consultation_fee"]}, Experience: {doctor["years_of_experience"]} years')
        
        # Test doctor search
        print("\n=== Testing Doctor Search ===")
        search_response = requests.get('http://localhost:8000/api/doctors/doctors/?search=cardiology', headers=headers)
        print(f'Search Status: {search_response.status_code}')
        
        if search_response.status_code == 200:
            search_results = search_response.json()
            print(f'Search found {len(search_results["results"])} doctors')
        
        # Test doctor registration
        print("\n=== Testing Doctor Registration ===")
        doctor_data = {
            'email': 'doctor.test@hospital.com',
            'first_name': 'John',
            'last_name': 'Smith',
            'phone_number': '+1234567890',
            'date_of_birth': '1980-05-15',
            'gender': 'M',
            'address': '123 Medical St, City',
            'password': 'SecurePass123!',
            'medical_license_number': 'MD123456',
            'license_expiry_date': '2025-12-31',
            'hire_date': '2024-01-01',
            'consultation_fee': 150.00,
            'years_of_experience': 10,
            'bio': 'Experienced cardiologist with 10 years of practice',
            'languages_spoken': 'English, Spanish',
            'max_patients_per_day': 15
        }
        
        register_response = requests.post('http://localhost:8000/api/doctors/register/', json=doctor_data, headers=headers)
        print(f'Doctor Registration Status: {register_response.status_code}')
        
        if register_response.status_code == 201:
            new_doctor = register_response.json()
            print(f'✓ Doctor registered: {new_doctor["doctor"]["doctor_id"]} - Dr. {new_doctor["doctor"]["full_name"]}')
            doctor_id = new_doctor["doctor"]["id"]
            
            # Test doctor detail endpoint
            print(f"\n=== Testing Doctor Detail for {doctor_id} ===")
            detail_response = requests.get(f'http://localhost:8000/api/doctors/doctors/{doctor_id}/', headers=headers)
            print(f'Doctor Detail Status: {detail_response.status_code}')
            
            if detail_response.status_code == 200:
                doctor_detail = detail_response.json()
                print(f'Doctor: Dr. {doctor_detail["full_name"]}')
                print(f'License: {doctor_detail["medical_license_number"]}')
                print(f'Experience: {doctor_detail["years_of_experience"]} years')
                print(f'Fee: ${doctor_detail["consultation_fee"]}')
                print(f'Bio: {doctor_detail["bio"][:50]}...')
        else:
            print(f'Registration failed: {register_response.text}')
    
    else:
        print(f'Login failed: {login_response.text}')

def test_doctor_profile_access():
    print("\n=== Testing Doctor Profile Access ===")
    
    # Try to login as the newly created doctor
    login_data = {
        'email': 'doctor.test@hospital.com',
        'password': 'SecurePass123!'
    }

    login_response = requests.post('http://localhost:8000/api/accounts/auth/login/', json=login_data)
    print(f'Doctor Login Status: {login_response.status_code}')

    if login_response.status_code == 200:
        token = login_response.json()['access']
        headers = {'Authorization': f'Bearer {token}'}
        
        # Test doctor profile endpoint
        profile_response = requests.get('http://localhost:8000/api/doctors/profile/', headers=headers)
        print(f'Doctor Profile Status: {profile_response.status_code}')
        
        if profile_response.status_code == 200:
            profile = profile_response.json()
            print(f'Doctor Profile: Dr. {profile["full_name"]}')
            print(f'Doctor ID: {profile["doctor_id"]}')
            print(f'License: {profile["medical_license_number"]}')
            print(f'Department: {profile["department"]["name"] if profile["department"] else "Not assigned"}')
        else:
            print(f'Profile Error: {profile_response.text}')
        
        # Test doctor profile update
        print("\n=== Testing Doctor Profile Update ===")
        update_data = {
            'bio': 'Updated bio: Experienced cardiologist specializing in interventional procedures',
            'consultation_fee': 175.00,
            'max_patients_per_day': 20
        }
        
        update_response = requests.patch('http://localhost:8000/api/doctors/profile/', json=update_data, headers=headers)
        print(f'Profile Update Status: {update_response.status_code}')
        
        if update_response.status_code == 200:
            updated_profile = update_response.json()
            print(f'Updated Bio: {updated_profile["bio"][:50]}...')
            print(f'Updated Fee: ${updated_profile["consultation_fee"]}')
            print(f'Updated Max Patients: {updated_profile["max_patients_per_day"]}')
        else:
            print(f'Update Error: {update_response.text}')
    else:
        print(f'Doctor login failed: {login_response.text}')

if __name__ == '__main__':
    test_doctor_api()
    test_doctor_profile_access()
    print("\n=== Doctor API Testing Complete ===")
