import requests
import json

def test_patient_api():
    print("Testing Patient Management API...")
    
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
        
        # Test patient list endpoint
        print("\n=== Testing Patient List ===")
        patients_response = requests.get('http://localhost:8000/api/patients/patients/', headers=headers)
        print(f'Patients List Status: {patients_response.status_code}')
        
        if patients_response.status_code == 200:
            patients = patients_response.json()
            print(f'Found {len(patients["results"])} patients')
            for patient in patients['results']:
                print(f'  - {patient["patient_id"]}: {patient["full_name"]} ({patient["email"]})')
        else:
            print(f'Error: {patients_response.text}')
        
        # Test patient detail endpoint
        if patients_response.status_code == 200 and patients['results']:
            patient_id = patients['results'][0]['id']
            print(f"\n=== Testing Patient Detail for {patient_id} ===")
            detail_response = requests.get(f'http://localhost:8000/api/patients/patients/{patient_id}/', headers=headers)
            print(f'Patient Detail Status: {detail_response.status_code}')
            
            if detail_response.status_code == 200:
                patient_detail = detail_response.json()
                print(f'Patient: {patient_detail["full_name"]}')
                print(f'Age: {patient_detail["age"]}')
                print(f'BMI: {patient_detail["bmi"]}')
                print(f'Blood Type: {patient_detail["blood_type"]}')
        
        # Test patient search
        print("\n=== Testing Patient Search ===")
        search_response = requests.get('http://localhost:8000/api/patients/patients/?search=John', headers=headers)
        print(f'Search Status: {search_response.status_code}')
        
        if search_response.status_code == 200:
            search_results = search_response.json()
            print(f'Search found {len(search_results["results"])} patients')
            for patient in search_results['results']:
                print(f'  - {patient["patient_id"]}: {patient["full_name"]}')
        
        # Test patient medical summary
        if patients_response.status_code == 200 and patients['results']:
            patient_id = patients['results'][0]['id']
            print(f"\n=== Testing Medical Summary for {patient_id} ===")
            summary_response = requests.get(f'http://localhost:8000/api/patients/patients/{patient_id}/medical_summary/', headers=headers)
            print(f'Medical Summary Status: {summary_response.status_code}')
            
            if summary_response.status_code == 200:
                summary = summary_response.json()
                print(f'Patient: {summary["full_name"]}')
                print(f'Age: {summary["age"]}')
                print(f'Blood Type: {summary["blood_type"]}')
                print(f'BMI: {summary["bmi"]}')
                print(f'Insurance Active: {summary["insurance_active"]}')
        
    else:
        print(f'Login failed: {login_response.text}')

def test_patient_profile_access():
    print("\n=== Testing Patient Profile Access ===")
    
    # Login as patient
    login_data = {
        'email': 'patient1@hospital.com',
        'password': 'SecurePass123!'
    }

    login_response = requests.post('http://localhost:8000/api/accounts/auth/login/', json=login_data)
    print(f'Patient Login Status: {login_response.status_code}')

    if login_response.status_code == 200:
        token = login_response.json()['access']
        headers = {'Authorization': f'Bearer {token}'}
        
        # Test patient profile endpoint
        profile_response = requests.get('http://localhost:8000/api/patients/profile/', headers=headers)
        print(f'Patient Profile Status: {profile_response.status_code}')
        
        if profile_response.status_code == 200:
            profile = profile_response.json()
            print(f'Patient Profile: {profile["full_name"]}')
            print(f'Patient ID: {profile["patient_id"]}')
            print(f'Email: {profile["email"]}')
        else:
            print(f'Profile Error: {profile_response.text}')
        
        # Test patient update
        print("\n=== Testing Patient Profile Update ===")
        update_data = {
            'allergies': 'Peanuts, Shellfish',
            'chronic_conditions': 'Hypertension',
            'current_medications': 'Lisinopril 10mg daily'
        }
        
        update_response = requests.patch('http://localhost:8000/api/patients/profile/', json=update_data, headers=headers)
        print(f'Profile Update Status: {update_response.status_code}')
        
        if update_response.status_code == 200:
            updated_profile = update_response.json()
            print(f'Updated Allergies: {updated_profile["allergies"]}')
            print(f'Updated Conditions: {updated_profile["chronic_conditions"]}')
            print(f'Updated Medications: {updated_profile["current_medications"]}')
        else:
            print(f'Update Error: {update_response.text}')
    else:
        print(f'Patient login failed: {login_response.text}')

if __name__ == '__main__':
    test_patient_api()
    test_patient_profile_access()
    print("\n=== Patient API Testing Complete ===")
