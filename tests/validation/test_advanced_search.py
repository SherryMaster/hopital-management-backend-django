import requests

BASE_URL = 'http://localhost:8000/api'

# Login
login_data = {'email': 'admin@hospital.com', 'password': 'admin123'}
login_response = requests.post(f'{BASE_URL}/accounts/auth/login/', json=login_data)
token = login_response.json()['access']
headers = {'Authorization': f'Bearer {token}'}

# Test advanced search
print("Testing advanced search...")
advanced_response = requests.get(
    f'{BASE_URL}/appointments/appointments/advanced_search/?status=scheduled',
    headers=headers
)
print(f'Advanced Search Status: {advanced_response.status_code}')
if advanced_response.status_code == 200:
    data = advanced_response.json()
    print(f'Response keys: {list(data.keys())}')
    if 'results' in data:
        print(f'Found {len(data["results"])} results')
    if 'count' in data:
        print(f'Total count: {data["count"]}')
    if 'statistics' in data:
        print(f'Statistics: {data["statistics"]}')
else:
    print(f'Error: {advanced_response.text}')

# Test search suggestions
print("\nTesting search suggestions...")
suggestions_response = requests.get(
    f'{BASE_URL}/appointments/appointments/search_suggestions/?q=John',
    headers=headers
)
print(f'Suggestions Status: {suggestions_response.status_code}')
if suggestions_response.status_code == 200:
    suggestions = suggestions_response.json()
    print(f'Found {len(suggestions["suggestions"])} suggestions')
    for suggestion in suggestions["suggestions"][:3]:
        print(f'  - {suggestion["type"]}: {suggestion["value"]}')
else:
    print(f'Error: {suggestions_response.text}')
