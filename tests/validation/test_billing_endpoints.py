import requests
import json

BASE_URL = 'http://localhost:8000/api'

def test_billing_endpoints():
    print("Testing Billing Endpoints...")
    
    # Login
    login_data = {'email': 'admin@hospital.com', 'password': 'admin123'}
    login_response = requests.post(f'{BASE_URL}/accounts/auth/login/', json=login_data)
    print(f"Login Status: {login_response.status_code}")
    
    if login_response.status_code != 200:
        print("Login failed!")
        return
    
    token = login_response.json()['access']
    headers = {'Authorization': f'Bearer {token}'}
    
    # Test 1: List service categories
    print("\n1. Testing service categories endpoint...")
    categories_response = requests.get(f'{BASE_URL}/billing/service-categories/', headers=headers)
    print(f"Service Categories Status: {categories_response.status_code}")
    if categories_response.status_code == 200:
        categories_data = categories_response.json()
        categories = categories_data if isinstance(categories_data, list) else categories_data.get('results', [])
        print(f"✓ Found {len(categories)} service categories")
        if categories:
            print(f"  First category: {categories[0]['name']}")
    else:
        print(f"Error: {categories_response.text}")
    
    # Test 2: List services
    print("\n2. Testing services endpoint...")
    services_response = requests.get(f'{BASE_URL}/billing/services/', headers=headers)
    print(f"Services Status: {services_response.status_code}")
    if services_response.status_code == 200:
        services_data = services_response.json()
        services = services_data if isinstance(services_data, list) else services_data.get('results', [])
        print(f"✓ Found {len(services)} services")
        if services:
            print(f"  First service: {services[0]['name']} (${services[0]['base_price']})")
            service_id = services[0]['id']
        else:
            print("No services found")
            return
    else:
        print(f"Error: {services_response.text}")
        return
    
    # Test 3: List invoices
    print("\n3. Testing invoices endpoint...")
    invoices_response = requests.get(f'{BASE_URL}/billing/invoices/', headers=headers)
    print(f"Invoices Status: {invoices_response.status_code}")
    if invoices_response.status_code == 200:
        invoices_data = invoices_response.json()
        invoices = invoices_data if isinstance(invoices_data, list) else invoices_data.get('results', [])
        print(f"✓ Found {len(invoices)} invoices")
        if invoices:
            print(f"  First invoice: {invoices[0]['invoice_number']} (${invoices[0]['total_amount']})")
    else:
        print(f"Error: {invoices_response.text}")
    
    # Test 4: Get patient for invoice creation
    print("\n4. Getting patient for invoice creation...")
    patients_response = requests.get(f'{BASE_URL}/patients/patients/', headers=headers)
    if patients_response.status_code == 200:
        patients_data = patients_response.json()
        patients = patients_data if isinstance(patients_data, list) else patients_data.get('results', [])
        if patients:
            patient_id = patients[0]['id']
            print(f"✓ Using patient: {patient_id}")
        else:
            print("No patients found")
            return
    else:
        print(f"Error getting patients: {patients_response.text}")
        return
    
    # Test 5: Create a simple invoice
    print("\n5. Testing invoice creation...")
    from datetime import datetime, timedelta
    
    today = datetime.now().date()
    due_date = today + timedelta(days=30)
    
    invoice_data = {
        'patient': patient_id,
        'invoice_date': today.isoformat(),
        'due_date': due_date.isoformat(),
        'tax_amount': '0.00',
        'discount_amount': '0.00',
        'notes': 'Test invoice from endpoint test',
        'items': [
            {
                'service': service_id,
                'description': 'Test service item',
                'quantity': 1,
                'unit_price': '100.00',
                'discount_amount': '0.00'
            }
        ]
    }
    
    print(f"Creating invoice with data: {json.dumps(invoice_data, indent=2)}")
    create_response = requests.post(f'{BASE_URL}/billing/invoices/', json=invoice_data, headers=headers)
    print(f"Create Invoice Status: {create_response.status_code}")
    
    if create_response.status_code == 201:
        invoice = create_response.json()
        print(f"✓ Successfully created invoice: {invoice['invoice_number']}")
        print(f"  Total Amount: ${invoice['total_amount']}")
        print(f"  Items: {len(invoice['items'])}")
        invoice_id = invoice['id']
        
        # Test 6: Get invoice details
        print("\n6. Testing invoice details...")
        details_response = requests.get(f'{BASE_URL}/billing/invoices/{invoice_id}/', headers=headers)
        print(f"Invoice Details Status: {details_response.status_code}")
        if details_response.status_code == 200:
            details = details_response.json()
            print(f"✓ Retrieved invoice details")
            print(f"  Patient: {details['patient_details']['name']}")
            print(f"  Balance Due: ${details['balance_due']}")
        
        # Test 7: Send invoice
        print("\n7. Testing invoice sending...")
        send_response = requests.post(f'{BASE_URL}/billing/invoices/{invoice_id}/send/', json={}, headers=headers)
        print(f"Send Invoice Status: {send_response.status_code}")
        if send_response.status_code == 200:
            sent_invoice = send_response.json()
            print(f"✓ Invoice sent successfully")
            print(f"  Status: {sent_invoice['status']}")
        
    else:
        print(f"Failed to create invoice: {create_response.text}")
    
    print("\n=== Billing Endpoints Testing Complete ===")

if __name__ == '__main__':
    test_billing_endpoints()
