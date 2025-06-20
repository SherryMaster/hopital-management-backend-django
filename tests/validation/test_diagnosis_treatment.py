import os
import django
import requests
from datetime import datetime, timedelta

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hospital_backend.settings')
django.setup()

BASE_URL = 'http://localhost:8000/api'

def test_diagnosis_treatment_system():
    print("Testing Diagnosis and Treatment Records System...")
    
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
    
    print("\n=== Testing Diagnosis and Treatment Records System ===")
    
    # First, get a medical record ID to associate diagnoses and prescriptions
    print("\n0. Getting existing medical record...")
    records_response = requests.get(f'{BASE_URL}/medical-records/medical-records/', headers=headers)
    if records_response.status_code == 200 and records_response.json()['results']:
        medical_record_id = records_response.json()['results'][0]['id']
        print(f"✓ Using medical record: {medical_record_id}")
    else:
        print("No medical records found. Please create one first.")
        return
    
    # Test 1: Create a diagnosis
    print("\n1. Testing diagnosis creation...")
    diagnosis_data = {
        'medical_record': medical_record_id,
        'icd10_code': 'G43.9',
        'diagnosis_name': 'Migraine, unspecified',
        'diagnosis_type': 'primary',
        'description': 'Patient presents with recurrent severe headaches consistent with migraine pattern. Episodes last 4-72 hours with associated nausea and photophobia.',
        'severity': 'moderate',
        'onset_date': '2025-06-15',
        'is_chronic': True,
        'is_resolved': False
    }
    
    create_diagnosis_response = requests.post(
        f'{BASE_URL}/medical-records/diagnoses/',
        json=diagnosis_data,
        headers=headers
    )
    print(f"Create Diagnosis Status: {create_diagnosis_response.status_code}")
    
    if create_diagnosis_response.status_code == 201:
        diagnosis = create_diagnosis_response.json()
        diagnosis_id = diagnosis['id']
        print(f"✓ Created diagnosis: {diagnosis['diagnosis_name']}")
        print(f"  ICD-10 Code: {diagnosis['icd10_code']}")
        print(f"  Type: {diagnosis['diagnosis_type']}")
        print(f"  Severity: {diagnosis['severity']}")
        print(f"  Chronic: {diagnosis['is_chronic']}")
        print(f"  Duration: {diagnosis['duration_days']} days")
    else:
        print(f"Failed to create diagnosis: {create_diagnosis_response.text}")
        return
    
    # Test 2: Create a prescription/treatment
    print("\n2. Testing prescription creation...")
    prescription_data = {
        'medical_record': medical_record_id,
        'medication_name': 'Sumatriptan',
        'generic_name': 'Sumatriptan succinate',
        'dosage': '50mg',
        'frequency': 'as_needed',
        'route': 'Oral',
        'quantity': 9,
        'refills': 2,
        'start_date': '2025-06-19',
        'end_date': '2025-09-19',
        'instructions': 'Take one tablet at the onset of migraine symptoms. Do not exceed 2 tablets in 24 hours.',
        'special_instructions': 'Avoid if patient has cardiovascular disease. Monitor for chest pain or tightness.',
        'status': 'active',
        'pharmacy_name': 'City Pharmacy',
        'pharmacy_phone': '+1-555-0123'
    }
    
    create_prescription_response = requests.post(
        f'{BASE_URL}/medical-records/prescriptions/',
        json=prescription_data,
        headers=headers
    )
    print(f"Create Prescription Status: {create_prescription_response.status_code}")
    
    if create_prescription_response.status_code == 201:
        prescription = create_prescription_response.json()
        prescription_id = prescription['id']
        print(f"✓ Created prescription: {prescription['medication_name']}")
        print(f"  Dosage: {prescription['dosage']}")
        print(f"  Frequency: {prescription['frequency']}")
        print(f"  Status: {prescription['status']}")
        print(f"  Active: {prescription['is_active']}")
        print(f"  Days Remaining: {prescription['days_remaining']}")
    else:
        print(f"Failed to create prescription: {create_prescription_response.text}")
        return
    
    # Test 3: List diagnoses
    print("\n3. Testing diagnosis listing...")
    list_diagnoses_response = requests.get(f'{BASE_URL}/medical-records/diagnoses/', headers=headers)
    print(f"List Diagnoses Status: {list_diagnoses_response.status_code}")
    
    if list_diagnoses_response.status_code == 200:
        diagnoses_data = list_diagnoses_response.json()
        diagnoses_list = diagnoses_data if isinstance(diagnoses_data, list) else diagnoses_data.get('results', [])
        print(f"✓ Retrieved {len(diagnoses_list)} diagnoses")

        for diagnosis in diagnoses_list[:3]:
            print(f"  - {diagnosis['diagnosis_name']}: {diagnosis['diagnosis_type']} ({diagnosis['severity']})")
    
    # Test 4: List prescriptions
    print("\n4. Testing prescription listing...")
    list_prescriptions_response = requests.get(f'{BASE_URL}/medical-records/prescriptions/', headers=headers)
    print(f"List Prescriptions Status: {list_prescriptions_response.status_code}")
    
    if list_prescriptions_response.status_code == 200:
        prescriptions_data = list_prescriptions_response.json()
        prescriptions_list = prescriptions_data if isinstance(prescriptions_data, list) else prescriptions_data.get('results', [])
        print(f"✓ Retrieved {len(prescriptions_list)} prescriptions")

        for prescription in prescriptions_list[:3]:
            print(f"  - {prescription['medication_name']}: {prescription['dosage']} ({prescription['status']})")
    
    # Test 5: Get diagnoses by patient
    print("\n5. Testing patient diagnosis history...")
    patient_diagnoses_response = requests.get(
        f'{BASE_URL}/medical-records/diagnoses/by_patient/?patient_id=P000001',
        headers=headers
    )
    print(f"Patient Diagnoses Status: {patient_diagnoses_response.status_code}")
    
    if patient_diagnoses_response.status_code == 200:
        patient_diagnoses = patient_diagnoses_response.json()
        print(f"✓ Retrieved patient diagnosis history")
        print(f"  Patient: {patient_diagnoses['patient']['name']}")
        print(f"  Total Diagnoses: {patient_diagnoses['total_diagnoses']}")
        print(f"  Active: {patient_diagnoses['statistics']['active']}")
        print(f"  Resolved: {patient_diagnoses['statistics']['resolved']}")
        print(f"  Chronic: {patient_diagnoses['statistics']['chronic']}")
        
        # Show active diagnoses
        for diagnosis in patient_diagnoses['active_diagnoses'][:3]:
            print(f"    Active: {diagnosis['diagnosis_name']} (since {diagnosis['onset_date']})")
    
    # Test 6: Get prescriptions by patient
    print("\n6. Testing patient prescription history...")
    patient_prescriptions_response = requests.get(
        f'{BASE_URL}/medical-records/prescriptions/by_patient/?patient_id=P000001',
        headers=headers
    )
    print(f"Patient Prescriptions Status: {patient_prescriptions_response.status_code}")
    
    if patient_prescriptions_response.status_code == 200:
        patient_prescriptions = patient_prescriptions_response.json()
        print(f"✓ Retrieved patient prescription history")
        print(f"  Patient: {patient_prescriptions['patient']['name']}")
        print(f"  Total Prescriptions: {patient_prescriptions['total_prescriptions']}")
        print(f"  Active: {patient_prescriptions['statistics']['active']}")
        print(f"  Completed: {patient_prescriptions['statistics']['completed']}")
        print(f"  Discontinued: {patient_prescriptions['statistics']['discontinued']}")
        
        # Show active prescriptions
        for prescription in patient_prescriptions['active_prescriptions'][:3]:
            print(f"    Active: {prescription['medication_name']} {prescription['dosage']}")
    
    # Test 7: Resolve a diagnosis
    print("\n7. Testing diagnosis resolution...")
    resolve_response = requests.post(
        f'{BASE_URL}/medical-records/diagnoses/{diagnosis_id}/resolve/',
        json={},
        headers=headers
    )
    print(f"Resolve Diagnosis Status: {resolve_response.status_code}")
    
    if resolve_response.status_code == 200:
        resolved_diagnosis = resolve_response.json()
        print(f"✓ Diagnosis resolved")
        print(f"  Resolved: {resolved_diagnosis['is_resolved']}")
        print(f"  Resolution Date: {resolved_diagnosis['resolution_date']}")
    else:
        print(f"Failed to resolve diagnosis: {resolve_response.text}")
    
    # Test 8: Discontinue a prescription
    print("\n8. Testing prescription discontinuation...")
    discontinue_response = requests.post(
        f'{BASE_URL}/medical-records/prescriptions/{prescription_id}/discontinue/',
        json={'reason': 'Patient reported adverse effects'},
        headers=headers
    )
    print(f"Discontinue Prescription Status: {discontinue_response.status_code}")
    
    if discontinue_response.status_code == 200:
        discontinued_prescription = discontinue_response.json()
        print(f"✓ Prescription discontinued")
        print(f"  Status: {discontinued_prescription['status']}")
        print(f"  Active: {discontinued_prescription['is_active']}")
    else:
        print(f"Failed to discontinue prescription: {discontinue_response.text}")
    
    # Test 9: Get diagnosis statistics
    print("\n9. Testing diagnosis statistics...")
    diagnosis_stats_response = requests.get(
        f'{BASE_URL}/medical-records/diagnoses/statistics/',
        headers=headers
    )
    print(f"Diagnosis Statistics Status: {diagnosis_stats_response.status_code}")
    
    if diagnosis_stats_response.status_code == 200:
        diagnosis_stats = diagnosis_stats_response.json()
        print(f"✓ Retrieved diagnosis statistics")
        print(f"  Total Diagnoses: {diagnosis_stats['total_diagnoses']}")
        print(f"  Active: {diagnosis_stats['active_diagnoses']}")
        print(f"  Resolved: {diagnosis_stats['resolved_diagnoses']}")
        print(f"  Chronic: {diagnosis_stats['chronic_diagnoses']}")
        print(f"  Resolution Rate: {diagnosis_stats['resolution_rate']}%")
        
        print(f"  Diagnosis Types:")
        for diagnosis_type, data in diagnosis_stats['diagnosis_types'].items():
            if data['count'] > 0:
                print(f"    - {data['name']}: {data['count']}")
        
        print(f"  Common Diagnoses:")
        for common in diagnosis_stats['common_diagnoses'][:3]:
            print(f"    - {common['diagnosis_name']}: {common['count']} cases")
    
    print("\n=== Diagnosis and Treatment Records Testing Complete ===")

if __name__ == '__main__':
    test_diagnosis_treatment_system()
