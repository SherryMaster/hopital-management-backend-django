import requests

BASE_URL = 'http://localhost:8000/api'

# Login
login_data = {'email': 'admin@hospital.com', 'password': 'admin123'}
login_response = requests.post(f'{BASE_URL}/accounts/auth/login/', json=login_data)
token = login_response.json()['access']
headers = {'Authorization': f'Bearer {token}'}

# Get the latest medical record
list_response = requests.get(f'{BASE_URL}/medical-records/medical-records/', headers=headers)
if list_response.status_code == 200:
    records = list_response.json()['results']
    if records:
        record_id = records[0]['id']
        print(f'Testing finalization for record: {record_id}')
        
        # Test finalization
        finalize_response = requests.post(
            f'{BASE_URL}/medical-records/medical-records/{record_id}/finalize/',
            json={},
            headers=headers
        )
        print(f'Finalize Status: {finalize_response.status_code}')
        if finalize_response.status_code == 200:
            result = finalize_response.json()
            print(f'Record finalized: {result["is_finalized"]}')
            print(f'Finalized at: {result["finalized_at"]}')
        else:
            print(f'Finalization failed: {finalize_response.text}')
