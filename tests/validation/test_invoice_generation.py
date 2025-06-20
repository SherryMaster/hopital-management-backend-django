import os
import django
import requests
from datetime import datetime, timedelta

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hospital_backend.settings')
django.setup()

BASE_URL = 'http://localhost:8000/api'

def test_invoice_generation_system():
    print("Testing Invoice Generation System...")
    
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
    
    print("\n=== Testing Invoice Generation System ===")
    
    # First, get patient and appointment information
    print("\n0. Getting patient and appointment information...")
    
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
    
    # Get appointment
    appointments_response = requests.get(f'{BASE_URL}/appointments/appointments/', headers=headers)
    if appointments_response.status_code == 200 and appointments_response.json()['results']:
        appointment_data = appointments_response.json()['results'][0]
        appointment_id = appointment_data['id']
        print(f"✓ Using appointment: {appointment_data['appointment_number']}")
    else:
        print("No appointments found. Please create one first.")
        return
    
    # Test 1: Create service categories and services
    print("\n1. Testing service categories and services...")
    
    # Create service category
    category_data = {
        'name': 'Consultation Services',
        'description': 'Medical consultation and examination services',
        'is_active': True
    }
    
    create_category_response = requests.post(
        f'{BASE_URL}/billing/service-categories/',
        json=category_data,
        headers=headers
    )
    print(f"Create Service Category Status: {create_category_response.status_code}")
    
    if create_category_response.status_code == 201:
        category = create_category_response.json()
        category_id = category['id']
        print(f"✓ Created service category: {category['name']}")
    elif create_category_response.status_code == 400:
        # Category already exists, get existing one
        categories_response = requests.get(f'{BASE_URL}/billing/service-categories/', headers=headers)
        if categories_response.status_code == 200:
            categories_data = categories_response.json()
            categories = categories_data if isinstance(categories_data, list) else categories_data.get('results', [])
            if categories:
                category_id = categories[0]['id']
                print(f"✓ Using existing service category: {categories[0]['name']}")
            else:
                print("No service categories found")
                return
        else:
            print(f"Failed to get service categories: {categories_response.text}")
            return
    else:
        print(f"Failed to create service category: {create_category_response.text}")
        return
    
    # Create services
    services_data = [
        {
            'category': category_id,
            'name': 'General Consultation',
            'code': 'CONS001',
            'description': 'General medical consultation and examination',
            'base_price': '150.00',
            'insurance_price': '120.00',
            'duration_minutes': 30,
            'requires_authorization': False,
            'is_active': True
        },
        {
            'category': category_id,
            'name': 'Specialist Consultation',
            'code': 'CONS002',
            'description': 'Specialist medical consultation',
            'base_price': '250.00',
            'insurance_price': '200.00',
            'duration_minutes': 45,
            'requires_authorization': True,
            'is_active': True
        },
        {
            'category': category_id,
            'name': 'Follow-up Visit',
            'code': 'CONS003',
            'description': 'Follow-up consultation visit',
            'base_price': '100.00',
            'insurance_price': '80.00',
            'duration_minutes': 20,
            'requires_authorization': False,
            'is_active': True
        }
    ]
    
    created_services = []
    for service_data in services_data:
        create_service_response = requests.post(
            f'{BASE_URL}/billing/services/',
            json=service_data,
            headers=headers
        )
        if create_service_response.status_code == 201:
            service = create_service_response.json()
            created_services.append(service)
            print(f"✓ Created service: {service['name']} (${service['base_price']})")
        elif create_service_response.status_code == 400:
            # Service might already exist, try to get existing services
            print(f"Service {service_data['name']} might already exist")
        else:
            print(f"Failed to create service: {create_service_response.text}")

    # If no services were created, get existing services
    if not created_services:
        print("Getting existing services...")
        services_response = requests.get(f'{BASE_URL}/billing/services/', headers=headers)
        if services_response.status_code == 200:
            services_data = services_response.json()
            existing_services = services_data if isinstance(services_data, list) else services_data.get('results', [])
            if existing_services:
                created_services = existing_services[:3]  # Use first 3 services
                print(f"✓ Using {len(created_services)} existing services")
                for service in created_services:
                    print(f"  - {service['name']} (${service['base_price']})")
            else:
                print("No services found. Cannot proceed with invoice generation.")
                return
        else:
            print("Failed to get existing services. Cannot proceed.")
            return
    
    # Test 2: Create a comprehensive invoice
    print("\n2. Testing invoice creation...")
    
    today = datetime.now().date()
    due_date = today + timedelta(days=30)
    
    invoice_data = {
        'patient': patient_uuid,
        'appointment': appointment_id,
        'invoice_date': today.isoformat(),
        'due_date': due_date.isoformat(),
        'tax_amount': '15.75',
        'discount_amount': '25.00',
        'notes': 'Thank you for choosing our medical services. Payment is due within 30 days.',
        'terms_and_conditions': 'Payment terms: Net 30 days. Late payments may incur additional charges.',
        'items': [
            {
                'service': created_services[0]['id'],
                'description': 'General medical consultation and physical examination',
                'quantity': 1,
                'unit_price': '150.00',
                'discount_amount': '10.00'
            },
            {
                'service': created_services[2]['id'],
                'description': 'Follow-up consultation for treatment monitoring',
                'quantity': 1,
                'unit_price': '100.00',
                'discount_amount': '15.00'
            }
        ]
    }
    
    create_invoice_response = requests.post(
        f'{BASE_URL}/billing/invoices/',
        json=invoice_data,
        headers=headers
    )
    print(f"Create Invoice Status: {create_invoice_response.status_code}")
    
    if create_invoice_response.status_code == 201:
        invoice = create_invoice_response.json()
        invoice_id = invoice['id']
        invoice_number = invoice['invoice_number']
        print(f"✓ Created invoice: {invoice_number}")
        print(f"  Patient: {invoice['patient_name']}")
        print(f"  Subtotal: ${invoice['subtotal']}")
        print(f"  Tax: ${invoice['tax_amount']}")
        print(f"  Discount: ${invoice['discount_amount']}")
        print(f"  Total: ${invoice['total_amount']}")
        print(f"  Due Date: {invoice['due_date']}")
        print(f"  Items: {len(invoice['items'])} services")
    else:
        print(f"Failed to create invoice: {create_invoice_response.text}")
        return
    
    # Test 3: List all invoices
    print("\n3. Testing invoice listing...")
    list_invoices_response = requests.get(f'{BASE_URL}/billing/invoices/', headers=headers)
    print(f"List Invoices Status: {list_invoices_response.status_code}")
    
    if list_invoices_response.status_code == 200:
        invoices_data = list_invoices_response.json()
        invoices_list = invoices_data if isinstance(invoices_data, list) else invoices_data.get('results', [])
        print(f"✓ Retrieved {len(invoices_list)} invoices")
        
        for inv in invoices_list[:3]:
            print(f"  - {inv['invoice_number']}: ${inv['total_amount']} ({inv['status']})")
    
    # Test 4: Get invoice details
    print("\n4. Testing invoice details...")
    invoice_details_response = requests.get(f'{BASE_URL}/billing/invoices/{invoice_id}/', headers=headers)
    print(f"Invoice Details Status: {invoice_details_response.status_code}")
    
    if invoice_details_response.status_code == 200:
        invoice_details = invoice_details_response.json()
        print(f"✓ Retrieved invoice details")
        print(f"  Invoice Number: {invoice_details['invoice_number']}")
        print(f"  Patient: {invoice_details['patient_details']['name']}")
        print(f"  Patient Email: {invoice_details['patient_details']['email']}")
        print(f"  Total Amount: ${invoice_details['total_amount']}")
        print(f"  Balance Due: ${invoice_details['balance_due']}")
        print(f"  Items Count: {len(invoice_details['items'])}")
        
        for item in invoice_details['items']:
            print(f"    - {item['service_name']}: {item['quantity']} x ${item['unit_price']} = ${item['total_price']}")
    
    # Test 5: Send invoice
    print("\n5. Testing invoice sending...")
    send_invoice_response = requests.post(f'{BASE_URL}/billing/invoices/{invoice_id}/send/', json={}, headers=headers)
    print(f"Send Invoice Status: {send_invoice_response.status_code}")
    
    if send_invoice_response.status_code == 200:
        sent_invoice = send_invoice_response.json()
        print(f"✓ Invoice sent successfully")
        print(f"  Status: {sent_invoice['status']}")
        print(f"  Sent Date: {sent_invoice['sent_date']}")
    else:
        print(f"Failed to send invoice: {send_invoice_response.text}")
    
    # Test 6: Get patient invoices
    print("\n6. Testing patient invoice history...")
    patient_invoices_response = requests.get(
        f'{BASE_URL}/billing/invoices/by_patient/?patient_id={patient_id}',
        headers=headers
    )
    print(f"Patient Invoices Status: {patient_invoices_response.status_code}")
    
    if patient_invoices_response.status_code == 200:
        patient_invoices = patient_invoices_response.json()
        print(f"✓ Retrieved patient invoice history")
        print(f"  Patient: {patient_invoices['patient']['name']}")
        print(f"  Total Invoices: {patient_invoices['total_invoices']}")
        
        if patient_invoices['summary']:
            summary = patient_invoices['summary']
            print(f"  Summary:")
            print(f"    Total Amount: ${summary['total_amount']}")
            print(f"    Total Paid: ${summary['total_paid']}")
            print(f"    Total Outstanding: ${summary['total_outstanding']}")
            print(f"    Status Counts: {summary['status_counts']}")
    
    # Test 7: Get invoice statistics
    print("\n7. Testing invoice statistics...")
    stats_response = requests.get(f'{BASE_URL}/billing/invoices/statistics/', headers=headers)
    print(f"Invoice Statistics Status: {stats_response.status_code}")
    
    if stats_response.status_code == 200:
        stats = stats_response.json()
        print(f"✓ Retrieved invoice statistics")
        print(f"  Total Invoices: {stats['total_invoices']}")
        print(f"  Total Amount: ${stats['total_amount']}")
        print(f"  Total Paid: ${stats['total_paid']}")
        print(f"  Total Outstanding: ${stats['total_outstanding']}")
        print(f"  Recent Invoices (30 days): {stats['recent_invoices_30_days']}")
        print(f"  Average Invoice Amount: ${stats['average_invoice_amount']:.2f}")
        print(f"  Status Breakdown: {stats['status_breakdown']}")
    
    # Test 8: Search services
    print("\n8. Testing service search...")
    search_response = requests.get(f'{BASE_URL}/billing/services/search/?q=consultation', headers=headers)
    print(f"Service Search Status: {search_response.status_code}")
    
    if search_response.status_code == 200:
        search_results = search_response.json()
        print(f"✓ Found {len(search_results)} services matching 'consultation'")
        
        for service in search_results:
            print(f"  - {service['code']}: {service['name']} (${service['base_price']})")
    
    # Test 9: Filter invoices by status
    print("\n9. Testing invoice filtering...")
    sent_invoices_response = requests.get(
        f'{BASE_URL}/billing/invoices/by_patient/?patient_id={patient_id}&status=sent',
        headers=headers
    )
    print(f"Sent Invoices Filter Status: {sent_invoices_response.status_code}")
    
    if sent_invoices_response.status_code == 200:
        sent_invoices = sent_invoices_response.json()
        print(f"✓ Found {sent_invoices['total_invoices']} sent invoices")
    
    print("\n=== Invoice Generation System Testing Complete ===")

if __name__ == '__main__':
    test_invoice_generation_system()
