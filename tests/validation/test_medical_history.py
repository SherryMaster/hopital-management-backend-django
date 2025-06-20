import os
import django
import requests
from datetime import datetime, timedelta

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hospital_backend.settings')
django.setup()

BASE_URL = 'http://localhost:8000/api'

def test_medical_history_management():
    print("Testing Medical History Management System...")
    
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
    
    print("\n=== Testing Medical History Management System ===")
    
    # Test 1: Create a medical record
    print("\n1. Testing medical record creation...")
    medical_record_data = {
        'patient': 'bffb1fe9-6506-4806-8eb3-2dfd418da895',  # Patient UUID
        'doctor': '6015915e-8e24-489f-ab61-14c3fc07291d',   # Doctor UUID
        'record_type': 'consultation',
        'chief_complaint': 'Patient complains of persistent headaches for the past week',
        'history_of_present_illness': 'Patient reports severe headaches starting 7 days ago, worse in the morning, associated with nausea but no vomiting. No visual disturbances or neurological symptoms.',
        'past_medical_history': 'Hypertension diagnosed 2 years ago, currently on medication. No history of migraines or head trauma.',
        'family_history': 'Mother has history of migraines. Father has hypertension and diabetes.',
        'social_history': 'Non-smoker, occasional alcohol use, works as software engineer with long computer hours.',
        'physical_examination': 'Vital signs stable. Neurological examination normal. No focal deficits. Fundoscopy shows mild papilledema.',
        'assessment': 'Tension-type headaches vs. secondary headache. Rule out increased intracranial pressure.',
        'treatment_plan': 'Order brain MRI, start on analgesics, follow up in 1 week. Advise rest and stress management.',
        'notes': 'Patient appears anxious about symptoms. Reassured and educated about headache types.'
    }
    
    create_response = requests.post(
        f'{BASE_URL}/medical-records/medical-records/',
        json=medical_record_data,
        headers=headers
    )
    print(f"Create Medical Record Status: {create_response.status_code}")
    
    if create_response.status_code == 201:
        medical_record = create_response.json()
        record_id = medical_record['id']
        print(f"✓ Created medical record: {medical_record['record_number']}")
        print(f"  Patient: {medical_record['patient_name']}")
        print(f"  Doctor: {medical_record['doctor_name']}")
        print(f"  Chief Complaint: {medical_record['chief_complaint']}")
        print(f"  Record Type: {medical_record['record_type']}")
    else:
        print(f"Failed to create medical record: {create_response.text}")
        return
    
    # Test 2: Add vital signs to the medical record
    print("\n2. Testing vital signs addition...")
    # Note: This would require a separate endpoint for vital signs
    # For now, we'll test the medical record retrieval
    
    # Test 3: Get medical record details
    print("\n3. Testing medical record retrieval...")
    detail_response = requests.get(
        f'{BASE_URL}/medical-records/medical-records/{record_id}/',
        headers=headers
    )
    print(f"Get Medical Record Status: {detail_response.status_code}")
    
    if detail_response.status_code == 200:
        record_detail = detail_response.json()
        print(f"✓ Retrieved medical record details")
        print(f"  Record Number: {record_detail['record_number']}")
        print(f"  Finalized: {record_detail['is_finalized']}")
        print(f"  Vital Signs: {len(record_detail['vital_signs'])} records")
        print(f"  Diagnoses: {len(record_detail['diagnoses'])} records")
        print(f"  Prescriptions: {len(record_detail['prescriptions'])} records")
        print(f"  Lab Tests: {len(record_detail['lab_tests'])} records")
        print(f"  Documents: {len(record_detail['documents'])} records")
    else:
        print(f"Failed to retrieve medical record: {detail_response.text}")
    
    # Test 4: List medical records with filtering
    print("\n4. Testing medical records listing and filtering...")
    
    # List all records
    list_response = requests.get(
        f'{BASE_URL}/medical-records/medical-records/',
        headers=headers
    )
    print(f"List Medical Records Status: {list_response.status_code}")
    
    if list_response.status_code == 200:
        records_list = list_response.json()
        print(f"✓ Retrieved {records_list['count']} medical records")
        
        # Show first few records
        for record in records_list['results'][:3]:
            print(f"  - {record['record_number']}: {record['patient_name']} ({record['record_type']})")
    
    # Test filtering by patient
    patient_filter_response = requests.get(
        f'{BASE_URL}/medical-records/medical-records/?patient_id=P000001',
        headers=headers
    )
    print(f"Filter by Patient Status: {patient_filter_response.status_code}")
    
    if patient_filter_response.status_code == 200:
        patient_records = patient_filter_response.json()
        print(f"✓ Found {patient_records['count']} records for patient P000001")
    
    # Test 5: Get patient medical history
    print("\n5. Testing patient medical history...")
    history_response = requests.get(
        f'{BASE_URL}/medical-records/medical-records/patient_history/?patient_id=P000001',
        headers=headers
    )
    print(f"Patient History Status: {history_response.status_code}")
    
    if history_response.status_code == 200:
        patient_history = history_response.json()
        print(f"✓ Retrieved complete medical history")
        print(f"  Patient: {patient_history['patient']['name']}")
        print(f"  Date of Birth: {patient_history['patient']['date_of_birth']}")
        print(f"  Total Records: {patient_history['total_records']}")
        
        # Show recent records
        for record in patient_history['records'][:3]:
            print(f"  - {record['record_date']}: {record['chief_complaint']}")
    else:
        print(f"Failed to get patient history: {history_response.text}")
    
    # Test 6: Get medical timeline
    print("\n6. Testing medical timeline...")
    timeline_response = requests.get(
        f'{BASE_URL}/medical-records/medical-records/timeline/?patient_id=P000001',
        headers=headers
    )
    print(f"Medical Timeline Status: {timeline_response.status_code}")
    
    if timeline_response.status_code == 200:
        timeline = timeline_response.json()
        print(f"✓ Retrieved medical timeline")
        print(f"  Patient: {timeline['patient']['name']}")
        print(f"  Total Events: {timeline['total_events']}")
        
        # Show recent timeline events
        for event in timeline['timeline'][:5]:
            print(f"  - {event['date']}: {event['type']} - {event['title']}")
    else:
        print(f"Failed to get medical timeline: {timeline_response.text}")
    
    # Test 7: Finalize medical record
    print("\n7. Testing medical record finalization...")
    finalize_response = requests.post(
        f'{BASE_URL}/medical-records/medical-records/{record_id}/finalize/',
        json={},  # Empty JSON body
        headers=headers
    )
    print(f"Finalize Record Status: {finalize_response.status_code}")
    
    if finalize_response.status_code == 200:
        finalized_record = finalize_response.json()
        print(f"✓ Medical record finalized")
        print(f"  Finalized: {finalized_record['is_finalized']}")
        print(f"  Finalized At: {finalized_record['finalized_at']}")
    else:
        print(f"Failed to finalize record: {finalize_response.text}")
    
    # Test 8: Get medical records statistics
    print("\n8. Testing medical records statistics...")
    stats_response = requests.get(
        f'{BASE_URL}/medical-records/medical-records/statistics/',
        headers=headers
    )
    print(f"Statistics Status: {stats_response.status_code}")
    
    if stats_response.status_code == 200:
        stats = stats_response.json()
        print(f"✓ Retrieved medical records statistics")
        print(f"  Total Records: {stats['total_records']}")
        print(f"  Finalized Records: {stats['finalized_records']}")
        print(f"  Pending Records: {stats['pending_records']}")
        print(f"  Finalization Rate: {stats['finalization_rate']}%")
        print(f"  Recent Records (30 days): {stats['recent_records_30_days']}")
        
        print(f"  Record Types:")
        for record_type, data in stats['record_types'].items():
            print(f"    - {data['name']}: {data['count']} records")
    else:
        print(f"Failed to get statistics: {stats_response.text}")
    
    # Test 9: Search medical records
    print("\n9. Testing medical record search...")
    search_response = requests.get(
        f'{BASE_URL}/medical-records/medical-records/?search=headache',
        headers=headers
    )
    print(f"Search Status: {search_response.status_code}")
    
    if search_response.status_code == 200:
        search_results = search_response.json()
        print(f"✓ Found {search_results['count']} records matching 'headache'")
        
        for record in search_results['results'][:3]:
            print(f"  - {record['record_number']}: {record['chief_complaint']}")
    else:
        print(f"Failed to search records: {search_response.text}")
    
    print("\n=== Medical History Management Testing Complete ===")

if __name__ == '__main__':
    test_medical_history_management()
