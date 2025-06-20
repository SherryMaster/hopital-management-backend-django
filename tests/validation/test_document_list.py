import requests

BASE_URL = 'http://localhost:8000/api'

# Login
login_data = {'email': 'admin@hospital.com', 'password': 'admin123'}
login_response = requests.post(f'{BASE_URL}/accounts/auth/login/', json=login_data)
token = login_response.json()['access']
headers = {'Authorization': f'Bearer {token}'}

# Test document listing
print('Testing document listing...')
list_response = requests.get(f'{BASE_URL}/medical-records/documents/', headers=headers)
print(f'List Status: {list_response.status_code}')
if list_response.status_code == 200:
    data = list_response.json()
    if isinstance(data, list):
        print(f'Found {len(data)} documents')
    else:
        print(f'Found {data.get("count", 0)} documents')
else:
    print(f'Error: {list_response.text}')

# Test statistics
print('\nTesting document statistics...')
stats_response = requests.get(f'{BASE_URL}/medical-records/documents/statistics/', headers=headers)
print(f'Stats Status: {stats_response.status_code}')
if stats_response.status_code == 200:
    stats = stats_response.json()
    print(f'Total documents: {stats["total_documents"]}')
else:
    print(f'Error: {stats_response.text}')
