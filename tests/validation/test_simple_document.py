import requests
import tempfile
import os

BASE_URL = 'http://localhost:8000/api'

# Login
login_data = {'email': 'admin@hospital.com', 'password': 'admin123'}
login_response = requests.post(f'{BASE_URL}/accounts/auth/login/', json=login_data)
token = login_response.json()['access']
headers = {'Authorization': f'Bearer {token}'}

# Get medical record
records_response = requests.get(f'{BASE_URL}/medical-records/medical-records/', headers=headers)
medical_record_id = records_response.json()['results'][0]['id']
print(f'Using medical record: {medical_record_id}')

# Create a simple test file
test_content = "This is a test lab report file."
temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False)
temp_file.write(test_content)
temp_file.close()

try:
    # Test document upload
    with open(temp_file.name, 'rb') as test_file:
        document_data = {
            'medical_record': medical_record_id,
            'title': 'Simple Test Document',
            'document_type': 'lab_report',
            'description': 'A simple test document',
            'is_confidential': 'true'
        }
        
        files = {'file': ('test.txt', test_file, 'text/plain')}
        
        print("Uploading document...")
        upload_response = requests.post(
            f'{BASE_URL}/medical-records/documents/',
            data=document_data,
            files=files,
            headers=headers
        )
        
        print(f'Upload Status: {upload_response.status_code}')
        if upload_response.status_code == 201:
            result = upload_response.json()
            print(f'Success: {result["title"]}')
            print(f'File size: {result["file_size"]}')
        else:
            print(f'Error: {upload_response.text}')

finally:
    # Clean up
    os.unlink(temp_file.name)
