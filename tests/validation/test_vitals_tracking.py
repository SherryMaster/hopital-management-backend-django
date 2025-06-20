import os
import django
import requests
from datetime import datetime, timedelta

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hospital_backend.settings')
django.setup()

BASE_URL = 'http://localhost:8000/api'

def test_vitals_tracking_system():
    print("Testing Patient Vitals Tracking System...")
    
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
    
    print("\n=== Testing Patient Vitals Tracking System ===")
    
    # First, get a medical record ID to associate vital signs
    print("\n0. Getting existing medical record...")
    records_response = requests.get(f'{BASE_URL}/medical-records/medical-records/', headers=headers)
    if records_response.status_code == 200 and records_response.json()['results']:
        medical_record_id = records_response.json()['results'][0]['id']
        print(f"✓ Using medical record: {medical_record_id}")
    else:
        print("No medical records found. Please create one first.")
        return
    
    # Test 1: Record normal vital signs
    print("\n1. Testing normal vital signs recording...")
    normal_vitals_data = {
        'medical_record': medical_record_id,
        'temperature': 36.8,
        'blood_pressure_systolic': 120,
        'blood_pressure_diastolic': 80,
        'heart_rate': 72,
        'respiratory_rate': 16,
        'oxygen_saturation': 98.5,
        'height': 175.0,
        'weight': 70.0,
        'pain_scale': 2,
        'notes': 'Patient appears comfortable, vital signs stable'
    }
    
    create_vitals_response = requests.post(
        f'{BASE_URL}/medical-records/vital-signs/',
        json=normal_vitals_data,
        headers=headers
    )
    print(f"Create Normal Vitals Status: {create_vitals_response.status_code}")
    
    if create_vitals_response.status_code == 201:
        normal_vitals = create_vitals_response.json()
        normal_vitals_id = normal_vitals['id']
        print(f"✓ Recorded normal vital signs")
        print(f"  Temperature: {normal_vitals['temperature']}°C")
        print(f"  Blood Pressure: {normal_vitals['blood_pressure_systolic']}/{normal_vitals['blood_pressure_diastolic']} mmHg")
        print(f"  Heart Rate: {normal_vitals['heart_rate']} bpm")
        print(f"  Oxygen Saturation: {normal_vitals['oxygen_saturation']}%")
        print(f"  BMI: {normal_vitals['bmi']}")
        print(f"  Recorded by: {normal_vitals['recorded_by_name']}")
    else:
        print(f"Failed to record normal vitals: {create_vitals_response.text}")
        return
    
    # Test 2: Record abnormal vital signs (to test alerts)
    print("\n2. Testing abnormal vital signs recording...")
    abnormal_vitals_data = {
        'medical_record': medical_record_id,
        'temperature': 39.2,  # High fever
        'blood_pressure_systolic': 160,  # High blood pressure
        'blood_pressure_diastolic': 95,
        'heart_rate': 110,  # Tachycardia
        'respiratory_rate': 22,
        'oxygen_saturation': 92.0,  # Low oxygen
        'height': 175.0,
        'weight': 70.5,
        'pain_scale': 7,
        'notes': 'Patient reports feeling unwell, elevated temperature and heart rate'
    }
    
    create_abnormal_response = requests.post(
        f'{BASE_URL}/medical-records/vital-signs/',
        json=abnormal_vitals_data,
        headers=headers
    )
    print(f"Create Abnormal Vitals Status: {create_abnormal_response.status_code}")
    
    if create_abnormal_response.status_code == 201:
        abnormal_vitals = create_abnormal_response.json()
        print(f"✓ Recorded abnormal vital signs")
        print(f"  Temperature: {abnormal_vitals['temperature']}°C (HIGH)")
        print(f"  Blood Pressure: {abnormal_vitals['blood_pressure_systolic']}/{abnormal_vitals['blood_pressure_diastolic']} mmHg (HIGH)")
        print(f"  Heart Rate: {abnormal_vitals['heart_rate']} bpm (HIGH)")
        print(f"  Oxygen Saturation: {abnormal_vitals['oxygen_saturation']}% (LOW)")
    else:
        print(f"Failed to record abnormal vitals: {create_abnormal_response.text}")
        return
    
    # Test 3: List all vital signs
    print("\n3. Testing vital signs listing...")
    list_vitals_response = requests.get(f'{BASE_URL}/medical-records/vital-signs/', headers=headers)
    print(f"List Vital Signs Status: {list_vitals_response.status_code}")
    
    if list_vitals_response.status_code == 200:
        vitals_data = list_vitals_response.json()
        vitals_list = vitals_data if isinstance(vitals_data, list) else vitals_data.get('results', [])
        print(f"✓ Retrieved {len(vitals_list)} vital signs records")
        
        for vital in vitals_list[:3]:
            print(f"  - {vital['recorded_at']}: Temp {vital['temperature']}°C, BP {vital['blood_pressure_systolic']}/{vital['blood_pressure_diastolic']}")
    
    # Test 4: Get patient vital signs history
    print("\n4. Testing patient vital signs history...")
    patient_vitals_response = requests.get(
        f'{BASE_URL}/medical-records/vital-signs/by_patient/?patient_id=P000001',
        headers=headers
    )
    print(f"Patient Vitals Status: {patient_vitals_response.status_code}")
    
    if patient_vitals_response.status_code == 200:
        patient_vitals = patient_vitals_response.json()
        print(f"✓ Retrieved patient vital signs history")
        print(f"  Patient: {patient_vitals['patient']['name']}")
        print(f"  Total Records: {patient_vitals['total_records']}")
        
        if patient_vitals['latest_vitals']:
            latest = patient_vitals['latest_vitals']
            print(f"  Latest Vitals:")
            print(f"    Temperature: {latest['temperature']}°C")
            print(f"    Blood Pressure: {latest['blood_pressure_systolic']}/{latest['blood_pressure_diastolic']} mmHg")
            print(f"    Heart Rate: {latest['heart_rate']} bpm")
        
        if patient_vitals['statistics']:
            stats = patient_vitals['statistics']
            print(f"  Statistics:")
            print(f"    Total Records: {stats['total_records']}")
            if stats['averages']['temperature']:
                print(f"    Average Temperature: {stats['averages']['temperature']}°C")
    
    # Test 5: Get vital signs trends
    print("\n5. Testing vital signs trends...")
    trends_response = requests.get(
        f'{BASE_URL}/medical-records/vital-signs/trends/?patient_id=P000001&days=30',
        headers=headers
    )
    print(f"Trends Status: {trends_response.status_code}")
    
    if trends_response.status_code == 200:
        trends_data = trends_response.json()
        print(f"✓ Retrieved vital signs trends")
        print(f"  Patient: {trends_data['patient']['name']}")
        print(f"  Period: {trends_data['period_days']} days")
        print(f"  Trend Data Points: {len(trends_data['trends'])} days")
        
        if trends_data['summary']['trends']:
            print(f"  Trends Summary:")
            for vital_type, trend in trends_data['summary']['trends'].items():
                print(f"    {vital_type}: {trend['direction']} (change: {trend['change']})")
    
    # Test 6: Get vital signs alerts
    print("\n6. Testing vital signs alerts...")
    alerts_response = requests.get(
        f'{BASE_URL}/medical-records/vital-signs/alerts/?patient_id=P000001',
        headers=headers
    )
    print(f"Alerts Status: {alerts_response.status_code}")
    
    if alerts_response.status_code == 200:
        alerts_data = alerts_response.json()
        print(f"✓ Retrieved vital signs alerts")
        print(f"  Patient: {alerts_data['patient']['name']}")
        print(f"  Total Alerts: {alerts_data['total_alerts']}")
        
        if alerts_data['alerts']:
            print(f"  Recent Alerts:")
            for alert in alerts_data['alerts'][:5]:
                print(f"    - {alert['severity'].upper()}: {alert['message']}")
        
        if alerts_data['alert_summary']:
            summary = alerts_data['alert_summary']
            print(f"  Alert Summary:")
            print(f"    High Severity: {summary['by_severity']['high']}")
            print(f"    Medium Severity: {summary['by_severity']['medium']}")
            for alert_type, count in summary['by_type'].items():
                print(f"    {alert_type}: {count} alerts")
    
    # Test 7: Get vital signs statistics
    print("\n7. Testing vital signs statistics...")
    stats_response = requests.get(
        f'{BASE_URL}/medical-records/vital-signs/statistics/',
        headers=headers
    )
    print(f"Statistics Status: {stats_response.status_code}")
    
    if stats_response.status_code == 200:
        stats = stats_response.json()
        print(f"✓ Retrieved vital signs statistics")
        print(f"  Total Records: {stats['total_records']}")
        print(f"  Recent Records (30 days): {stats['recent_records_30_days']}")
        
        if stats['averages']:
            print(f"  System Averages:")
            for vital_type, avg_value in stats['averages'].items():
                if avg_value:
                    print(f"    {vital_type}: {avg_value}")
    
    # Test 8: Test date filtering
    print("\n8. Testing date filtering...")
    today = datetime.now().date()
    yesterday = today - timedelta(days=1)
    
    filtered_response = requests.get(
        f'{BASE_URL}/medical-records/vital-signs/by_patient/?patient_id=P000001&date_from={yesterday}&date_to={today}',
        headers=headers
    )
    print(f"Filtered Vitals Status: {filtered_response.status_code}")
    
    if filtered_response.status_code == 200:
        filtered_data = filtered_response.json()
        print(f"✓ Found {filtered_data['total_records']} vital signs from {yesterday} to {today}")
    
    print("\n=== Patient Vitals Tracking Testing Complete ===")

if __name__ == '__main__':
    test_vitals_tracking_system()
