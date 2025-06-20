import os
import django
import requests
from datetime import datetime, timedelta

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hospital_backend.settings')
django.setup()

BASE_URL = 'http://localhost:8000/api'

def test_medical_alerts_system():
    print("Testing Medical Alerts System...")
    
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
    
    print("\n=== Testing Medical Alerts System ===")
    
    # First, get patient and medical record IDs
    print("\n0. Getting patient and medical record information...")
    
    # Get patient
    patients_response = requests.get(f'{BASE_URL}/patients/patients/', headers=headers)
    if patients_response.status_code == 200 and patients_response.json()['results']:
        patient_data = patients_response.json()['results'][0]
        patient_uuid = patient_data['id']
        patient_id = patient_data['patient_id']
        patient_name = patient_data.get('name', patient_data.get('user', {}).get('first_name', 'Unknown'))
        print(f"✓ Using patient: {patient_name} ({patient_id})")
    else:
        print("No patients found. Please create one first.")
        return
    
    # Get medical record
    records_response = requests.get(f'{BASE_URL}/medical-records/medical-records/', headers=headers)
    if records_response.status_code == 200 and records_response.json()['results']:
        medical_record_id = records_response.json()['results'][0]['id']
        print(f"✓ Using medical record: {medical_record_id}")
    else:
        print("No medical records found. Please create one first.")
        return
    
    # Test 1: Create an allergy alert
    print("\n1. Testing allergy alert creation...")
    allergy_alert_data = {
        'patient': patient_uuid,
        'medical_record': medical_record_id,
        'alert_type': 'allergy',
        'severity': 'high',
        'title': 'Penicillin Allergy Alert',
        'description': 'Patient has a documented severe allergy to penicillin. Previous reaction included hives, swelling, and difficulty breathing. Avoid all penicillin-based antibiotics.',
        'alert_data': {
            'allergen': 'Penicillin',
            'reaction_type': 'Anaphylaxis',
            'last_reaction_date': '2024-03-15',
            'alternative_medications': ['Cephalexin', 'Azithromycin']
        }
    }
    
    create_allergy_alert_response = requests.post(
        f'{BASE_URL}/medical-records/alerts/',
        json=allergy_alert_data,
        headers=headers
    )
    print(f"Create Allergy Alert Status: {create_allergy_alert_response.status_code}")
    
    if create_allergy_alert_response.status_code == 201:
        allergy_alert = create_allergy_alert_response.json()
        allergy_alert_id = allergy_alert['id']
        print(f"✓ Created allergy alert: {allergy_alert['title']}")
        print(f"  Alert Type: {allergy_alert['alert_type']}")
        print(f"  Severity: {allergy_alert['severity']}")
        print(f"  Status: {allergy_alert['status']}")
        print(f"  Triggered by: {allergy_alert['triggered_by_name']}")
    else:
        print(f"Failed to create allergy alert: {create_allergy_alert_response.text}")
        return
    
    # Test 2: Create a drug interaction alert
    print("\n2. Testing drug interaction alert creation...")
    drug_interaction_alert_data = {
        'patient': patient_uuid,
        'medical_record': medical_record_id,
        'alert_type': 'drug_interaction',
        'severity': 'medium',
        'title': 'Warfarin-Aspirin Interaction Warning',
        'description': 'Patient is prescribed both Warfarin and Aspirin. This combination significantly increases bleeding risk. Monitor INR levels closely and consider alternative pain management.',
        'alert_data': {
            'drug1': 'Warfarin',
            'drug2': 'Aspirin',
            'interaction_type': 'major',
            'clinical_effect': 'Increased bleeding risk',
            'monitoring_required': 'INR levels every 2 weeks'
        }
    }
    
    create_drug_alert_response = requests.post(
        f'{BASE_URL}/medical-records/alerts/',
        json=drug_interaction_alert_data,
        headers=headers
    )
    print(f"Create Drug Interaction Alert Status: {create_drug_alert_response.status_code}")
    
    if create_drug_alert_response.status_code == 201:
        drug_alert = create_drug_alert_response.json()
        drug_alert_id = drug_alert['id']
        print(f"✓ Created drug interaction alert: {drug_alert['title']}")
        print(f"  Alert Type: {drug_alert['alert_type']}")
        print(f"  Severity: {drug_alert['severity']}")
    else:
        print(f"Failed to create drug interaction alert: {create_drug_alert_response.text}")
        return
    
    # Test 3: Create a critical condition alert
    print("\n3. Testing critical condition alert creation...")
    critical_alert_data = {
        'patient': patient_uuid,
        'medical_record': medical_record_id,
        'alert_type': 'critical_condition',
        'severity': 'critical',
        'title': 'Acute Myocardial Infarction - STEMI',
        'description': 'Patient presenting with ST-elevation myocardial infarction. Immediate cardiac catheterization required. Activate cardiac emergency protocol.',
        'alert_data': {
            'condition_type': 'myocardial_infarction',
            'onset_time': '2025-06-19T14:30:00Z',
            'ecg_findings': 'ST elevation in leads II, III, aVF',
            'troponin_level': '15.2 ng/mL',
            'emergency_protocol': 'STEMI Protocol activated'
        }
    }
    
    create_critical_alert_response = requests.post(
        f'{BASE_URL}/medical-records/alerts/',
        json=critical_alert_data,
        headers=headers
    )
    print(f"Create Critical Alert Status: {create_critical_alert_response.status_code}")
    
    if create_critical_alert_response.status_code == 201:
        critical_alert = create_critical_alert_response.json()
        critical_alert_id = critical_alert['id']
        print(f"✓ Created critical condition alert: {critical_alert['title']}")
        print(f"  Alert Type: {critical_alert['alert_type']}")
        print(f"  Severity: {critical_alert['severity']}")
    else:
        print(f"Failed to create critical alert: {create_critical_alert_response.text}")
        return
    
    # Test 4: List all alerts
    print("\n4. Testing alerts listing...")
    list_alerts_response = requests.get(f'{BASE_URL}/medical-records/alerts/', headers=headers)
    print(f"List Alerts Status: {list_alerts_response.status_code}")
    
    if list_alerts_response.status_code == 200:
        alerts_data = list_alerts_response.json()
        alerts_list = alerts_data if isinstance(alerts_data, list) else alerts_data.get('results', [])
        print(f"✓ Retrieved {len(alerts_list)} medical alerts")
        
        for alert in alerts_list[:3]:
            print(f"  - {alert['title']}: {alert['alert_type']} ({alert['severity']})")
    
    # Test 5: Get alerts by patient
    print("\n5. Testing patient alerts history...")
    patient_alerts_response = requests.get(
        f'{BASE_URL}/medical-records/alerts/by_patient/?patient_id={patient_id}',
        headers=headers
    )
    print(f"Patient Alerts Status: {patient_alerts_response.status_code}")
    
    if patient_alerts_response.status_code == 200:
        patient_alerts = patient_alerts_response.json()
        print(f"✓ Retrieved patient alerts history")
        print(f"  Patient: {patient_alerts['patient']['name']}")
        print(f"  Total Alerts: {patient_alerts['total_alerts']}")
        
        if patient_alerts['statistics']:
            stats = patient_alerts['statistics']
            print(f"  Statistics:")
            print(f"    Active Alerts: {stats['active_alerts']}")
            print(f"    Critical Alerts: {stats['critical_alerts']}")
            print(f"    By Severity: {stats['by_severity']}")
            print(f"    By Type: {stats['by_type']}")
    
    # Test 6: Acknowledge an alert
    print("\n6. Testing alert acknowledgment...")
    acknowledge_response = requests.post(
        f'{BASE_URL}/medical-records/alerts/{allergy_alert_id}/acknowledge/',
        json={},
        headers=headers
    )
    print(f"Acknowledge Alert Status: {acknowledge_response.status_code}")
    
    if acknowledge_response.status_code == 200:
        acknowledged_alert = acknowledge_response.json()
        print(f"✓ Alert acknowledged")
        print(f"  Status: {acknowledged_alert['status']}")
        print(f"  Acknowledged by: {acknowledged_alert['acknowledged_by_name']}")
        print(f"  Acknowledged at: {acknowledged_alert['acknowledged_at']}")
    else:
        print(f"Failed to acknowledge alert: {acknowledge_response.text}")
    
    # Test 7: Resolve an alert
    print("\n7. Testing alert resolution...")
    resolve_response = requests.post(
        f'{BASE_URL}/medical-records/alerts/{drug_alert_id}/resolve/',
        json={'resolution_notes': 'Aspirin discontinued. Patient switched to acetaminophen for pain management. INR levels normalized.'},
        headers=headers
    )
    print(f"Resolve Alert Status: {resolve_response.status_code}")
    
    if resolve_response.status_code == 200:
        resolved_alert = resolve_response.json()
        print(f"✓ Alert resolved")
        print(f"  Status: {resolved_alert['status']}")
        print(f"  Resolved by: {resolved_alert['resolved_by_name']}")
        print(f"  Resolution notes: {resolved_alert['resolution_notes'][:100]}...")
    else:
        print(f"Failed to resolve alert: {resolve_response.text}")
    
    # Test 8: Filter alerts by severity
    print("\n8. Testing alert filtering...")
    critical_alerts_response = requests.get(
        f'{BASE_URL}/medical-records/alerts/by_patient/?patient_id={patient_id}&severity=critical',
        headers=headers
    )
    print(f"Critical Alerts Filter Status: {critical_alerts_response.status_code}")
    
    if critical_alerts_response.status_code == 200:
        critical_alerts = critical_alerts_response.json()
        print(f"✓ Found {critical_alerts['total_alerts']} critical alerts")
    
    # Test 9: Filter alerts by type
    print("\n9. Testing alert type filtering...")
    allergy_alerts_response = requests.get(
        f'{BASE_URL}/medical-records/alerts/by_patient/?patient_id={patient_id}&alert_type=allergy',
        headers=headers
    )
    print(f"Allergy Alerts Filter Status: {allergy_alerts_response.status_code}")
    
    if allergy_alerts_response.status_code == 200:
        allergy_alerts = allergy_alerts_response.json()
        print(f"✓ Found {allergy_alerts['total_alerts']} allergy alerts")
    
    print("\n=== Medical Alerts System Testing Complete ===")

if __name__ == '__main__':
    test_medical_alerts_system()
