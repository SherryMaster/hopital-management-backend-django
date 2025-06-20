import os
import django
import requests
from datetime import datetime, timedelta
import tempfile

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hospital_backend.settings')
django.setup()

BASE_URL = 'http://localhost:8000/api'

def create_test_file(filename, content):
    """Create a temporary test file"""
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix=f'.{filename.split(".")[-1]}', delete=False)
    temp_file.write(content)
    temp_file.close()
    return temp_file.name

def test_medical_document_storage():
    print("Testing Medical Document Storage System...")
    
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
    
    print("\n=== Testing Medical Document Storage System ===")
    
    # First, get a medical record ID to associate documents
    print("\n0. Getting existing medical record...")
    records_response = requests.get(f'{BASE_URL}/medical-records/medical-records/', headers=headers)
    if records_response.status_code == 200 and records_response.json()['results']:
        medical_record_id = records_response.json()['results'][0]['id']
        print(f"✓ Using medical record: {medical_record_id}")
    else:
        print("No medical records found. Please create one first.")
        return
    
    # Test 1: Upload a lab report document
    print("\n1. Testing document upload (Lab Report)...")
    
    # Create a test lab report file
    lab_report_content = """
    LABORATORY REPORT
    Patient: John Doe
    Date: 2025-06-19
    
    Complete Blood Count (CBC):
    - White Blood Cells: 7.2 K/uL (Normal: 4.0-11.0)
    - Red Blood Cells: 4.5 M/uL (Normal: 4.2-5.4)
    - Hemoglobin: 14.2 g/dL (Normal: 12.0-16.0)
    - Hematocrit: 42.1% (Normal: 36.0-46.0)
    - Platelets: 285 K/uL (Normal: 150-450)
    
    Results: All values within normal limits.
    """
    
    lab_file_path = create_test_file('lab_report.txt', lab_report_content)
    
    try:
        with open(lab_file_path, 'rb') as lab_file:
            document_data = {
                'medical_record': medical_record_id,
                'title': 'Complete Blood Count - June 2025',
                'document_type': 'lab_report',
                'description': 'Routine CBC test showing normal values across all parameters',
                'is_confidential': True
            }
            
            files = {'file': ('lab_report.txt', lab_file, 'text/plain')}
            
            upload_response = requests.post(
                f'{BASE_URL}/medical-records/documents/',
                data=document_data,
                files=files,
                headers=headers
            )
            print(f"Upload Lab Report Status: {upload_response.status_code}")
            
            if upload_response.status_code == 201:
                lab_document = upload_response.json()
                lab_document_id = lab_document['id']
                print(f"✓ Uploaded lab report: {lab_document['title']}")
                print(f"  Document Type: {lab_document['document_type']}")
                print(f"  File Size: {lab_document['file_size']} bytes")
                print(f"  MIME Type: {lab_document['mime_type']}")
                print(f"  Confidential: {lab_document['is_confidential']}")
            else:
                print(f"Failed to upload lab report: {upload_response.text}")
                return
    finally:
        # Clean up temp file
        os.unlink(lab_file_path)
    
    # Test 2: Upload an imaging document
    print("\n2. Testing document upload (Imaging)...")
    
    # Create a test imaging report
    imaging_content = """
    RADIOLOGY REPORT
    Patient: John Doe
    Study Date: 2025-06-19
    Modality: X-Ray Chest PA/Lateral
    
    CLINICAL HISTORY:
    Routine chest examination
    
    FINDINGS:
    The lungs are clear bilaterally with no evidence of consolidation, 
    pleural effusion, or pneumothorax. The cardiac silhouette is normal 
    in size and configuration. The mediastinal contours are unremarkable.
    
    IMPRESSION:
    Normal chest X-ray.
    """
    
    imaging_file_path = create_test_file('chest_xray_report.txt', imaging_content)
    
    try:
        with open(imaging_file_path, 'rb') as imaging_file:
            imaging_data = {
                'medical_record': medical_record_id,
                'title': 'Chest X-Ray Report - June 2025',
                'document_type': 'imaging',
                'description': 'Routine chest X-ray showing normal findings',
                'is_confidential': True
            }
            
            files = {'file': ('chest_xray_report.txt', imaging_file, 'text/plain')}
            
            upload_imaging_response = requests.post(
                f'{BASE_URL}/medical-records/documents/',
                data=imaging_data,
                files=files,
                headers=headers
            )
            print(f"Upload Imaging Status: {upload_imaging_response.status_code}")
            
            if upload_imaging_response.status_code == 201:
                imaging_document = upload_imaging_response.json()
                imaging_document_id = imaging_document['id']
                print(f"✓ Uploaded imaging report: {imaging_document['title']}")
                print(f"  Document Type: {imaging_document['document_type']}")
                print(f"  File Size: {imaging_document['file_size']} bytes")
            else:
                print(f"Failed to upload imaging report: {upload_imaging_response.text}")
                return
    finally:
        # Clean up temp file
        os.unlink(imaging_file_path)
    
    # Test 3: List all documents
    print("\n3. Testing document listing...")
    list_documents_response = requests.get(f'{BASE_URL}/medical-records/documents/', headers=headers)
    print(f"List Documents Status: {list_documents_response.status_code}")
    
    if list_documents_response.status_code == 200:
        documents_data = list_documents_response.json()
        documents_list = documents_data if isinstance(documents_data, list) else documents_data.get('results', [])
        print(f"✓ Retrieved {len(documents_list)} documents")
        
        for document in documents_list[:3]:
            print(f"  - {document['title']}: {document['document_type']} ({document['file_size']} bytes)")
    
    # Test 4: Get documents by patient
    print("\n4. Testing patient document history...")
    patient_documents_response = requests.get(
        f'{BASE_URL}/medical-records/documents/by_patient/?patient_id=P000001',
        headers=headers
    )
    print(f"Patient Documents Status: {patient_documents_response.status_code}")
    
    if patient_documents_response.status_code == 200:
        patient_documents = patient_documents_response.json()
        print(f"✓ Retrieved patient document history")
        print(f"  Patient: {patient_documents['patient']['name']}")
        print(f"  Total Documents: {patient_documents['total_documents']}")
        print(f"  Confidential: {patient_documents['statistics']['confidential']}")
        print(f"  Recent Uploads: {patient_documents['statistics']['recent_uploads']}")
        
        print(f"  Document Groups:")
        for doc_type, group_data in patient_documents['document_groups'].items():
            if group_data['count'] > 0:
                print(f"    - {group_data['name']}: {group_data['count']} documents")
    
    # Test 5: Get documents by type
    print("\n5. Testing document filtering by type...")
    lab_documents_response = requests.get(
        f'{BASE_URL}/medical-records/documents/by_type/?type=lab_report',
        headers=headers
    )
    print(f"Lab Documents Status: {lab_documents_response.status_code}")
    
    if lab_documents_response.status_code == 200:
        lab_documents = lab_documents_response.json()
        lab_docs_list = lab_documents if isinstance(lab_documents, list) else lab_documents.get('results', [])
        print(f"✓ Found {len(lab_docs_list)} lab report documents")
        
        for doc in lab_docs_list[:3]:
            print(f"  - {doc['title']}: {doc['upload_date']}")
    
    # Test 6: Download a document
    print("\n6. Testing document download...")
    download_response = requests.get(
        f'{BASE_URL}/medical-records/documents/{lab_document_id}/download/',
        headers=headers
    )
    print(f"Download Status: {download_response.status_code}")
    
    if download_response.status_code == 200:
        download_data = download_response.json()
        print(f"✓ Document download prepared")
        print(f"  Download URL: {download_data['download_url']}")
        print(f"  Filename: {download_data['filename']}")
        print(f"  File Size: {download_data['file_size']} bytes")
        print(f"  MIME Type: {download_data['mime_type']}")
    else:
        print(f"Failed to prepare download: {download_response.text}")
    
    # Test 7: Get document statistics
    print("\n7. Testing document statistics...")
    stats_response = requests.get(
        f'{BASE_URL}/medical-records/documents/statistics/',
        headers=headers
    )
    print(f"Statistics Status: {stats_response.status_code}")
    
    if stats_response.status_code == 200:
        stats = stats_response.json()
        print(f"✓ Retrieved document statistics")
        print(f"  Total Documents: {stats['total_documents']}")
        print(f"  Confidential: {stats['confidential_documents']}")
        print(f"  Public: {stats['public_documents']}")
        print(f"  Recent (30 days): {stats['recent_documents_30_days']}")
        print(f"  Total File Size: {stats['total_file_size_mb']} MB")
        
        print(f"  Document Types:")
        for doc_type, data in stats['document_types'].items():
            if data['count'] > 0:
                print(f"    - {data['name']}: {data['count']} documents")
    
    # Test 8: Test document filtering with date range
    print("\n8. Testing document filtering with date range...")
    today = datetime.now().date()
    yesterday = today - timedelta(days=1)
    
    filtered_response = requests.get(
        f'{BASE_URL}/medical-records/documents/by_type/?type=imaging&date_from={yesterday}&date_to={today}',
        headers=headers
    )
    print(f"Filtered Documents Status: {filtered_response.status_code}")
    
    if filtered_response.status_code == 200:
        filtered_data = filtered_response.json()
        filtered_docs = filtered_data if isinstance(filtered_data, list) else filtered_data.get('results', [])
        print(f"✓ Found {len(filtered_docs)} imaging documents from {yesterday} to {today}")
    
    print("\n=== Medical Document Storage Testing Complete ===")

if __name__ == '__main__':
    test_medical_document_storage()
