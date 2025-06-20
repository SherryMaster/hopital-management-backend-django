import os
import django
import requests
from datetime import datetime, timedelta

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hospital_backend.settings')
django.setup()

BASE_URL = 'http://localhost:8000/api'

def test_payment_processing_system():
    print("Testing Payment Processing System...")
    
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
    
    print("\n=== Testing Payment Processing System ===")
    
    # First, get an existing invoice to process payment for
    print("\n0. Getting existing invoice for payment processing...")
    invoices_response = requests.get(f'{BASE_URL}/billing/invoices/', headers=headers)
    if invoices_response.status_code == 200:
        invoices_data = invoices_response.json()
        invoices = invoices_data if isinstance(invoices_data, list) else invoices_data.get('results', [])
        if invoices:
            # Find an invoice that's not fully paid
            unpaid_invoice = None
            for invoice in invoices:
                if invoice['status'] in ['sent', 'draft', 'partially_paid']:
                    unpaid_invoice = invoice
                    break
            
            if unpaid_invoice:
                invoice_id = unpaid_invoice['id']
                invoice_number = unpaid_invoice['invoice_number']
                total_amount = float(unpaid_invoice['total_amount'])
                print(f"✓ Using invoice: {invoice_number} (${total_amount})")
            else:
                print("No unpaid invoices found. Creating a new one...")
                # Create a simple invoice for testing
                patient_response = requests.get(f'{BASE_URL}/patients/patients/', headers=headers)
                patient_id = patient_response.json()['results'][0]['id']
                service_response = requests.get(f'{BASE_URL}/billing/services/', headers=headers)
                service_id = service_response.json()[0]['id']
                
                today = datetime.now().date()
                invoice_data = {
                    'patient': patient_id,
                    'invoice_date': today.isoformat(),
                    'due_date': (today + timedelta(days=30)).isoformat(),
                    'tax_amount': '0.00',
                    'discount_amount': '0.00',
                    'notes': 'Test invoice for payment processing',
                    'items': [{
                        'service': service_id,
                        'description': 'Test service for payment',
                        'quantity': 1,
                        'unit_price': '100.00',
                        'discount_amount': '0.00'
                    }]
                }
                
                create_invoice_response = requests.post(f'{BASE_URL}/billing/invoices/', json=invoice_data, headers=headers)
                if create_invoice_response.status_code == 201:
                    new_invoice = create_invoice_response.json()
                    invoice_id = new_invoice['id']
                    invoice_number = new_invoice['invoice_number']
                    total_amount = float(new_invoice['total_amount'])
                    print(f"✓ Created new invoice: {invoice_number} (${total_amount})")
                else:
                    print("Failed to create test invoice")
                    return
        else:
            print("No invoices found")
            return
    else:
        print("Failed to get invoices")
        return
    
    # Test 1: Create a full payment
    print("\n1. Testing full payment processing...")
    payment_data = {
        'invoice': invoice_id,
        'amount': str(total_amount),
        'payment_method': 'credit_card',
        'status': 'completed',
        'transaction_id': 'TXN_TEST_001',
        'reference_number': 'REF_001',
        'notes': 'Full payment via credit card'
    }
    
    create_payment_response = requests.post(
        f'{BASE_URL}/billing/payments/',
        json=payment_data,
        headers=headers
    )
    print(f"Create Payment Status: {create_payment_response.status_code}")
    
    if create_payment_response.status_code == 201:
        payment = create_payment_response.json()
        payment_id = payment['id']
        payment_number = payment['payment_number']
        print(f"✓ Created payment: {payment_number}")
        print(f"  Amount: ${payment['amount']}")
        print(f"  Method: {payment['payment_method']}")
        print(f"  Status: {payment['status']}")
        print(f"  Transaction ID: {payment['transaction_id']}")
    else:
        print(f"Failed to create payment: {create_payment_response.text}")
        return
    
    # Test 2: List all payments
    print("\n2. Testing payment listing...")
    list_payments_response = requests.get(f'{BASE_URL}/billing/payments/', headers=headers)
    print(f"List Payments Status: {list_payments_response.status_code}")
    
    if list_payments_response.status_code == 200:
        payments_data = list_payments_response.json()
        payments_list = payments_data if isinstance(payments_data, list) else payments_data.get('results', [])
        print(f"✓ Retrieved {len(payments_list)} payments")
        
        for payment in payments_list[:3]:
            print(f"  - {payment['payment_number']}: ${payment['amount']} ({payment['status']})")
    
    # Test 3: Get payments by invoice
    print("\n3. Testing payments by invoice...")
    invoice_payments_response = requests.get(
        f'{BASE_URL}/billing/payments/by_invoice/?invoice_id={invoice_id}',
        headers=headers
    )
    print(f"Invoice Payments Status: {invoice_payments_response.status_code}")
    
    if invoice_payments_response.status_code == 200:
        invoice_payments = invoice_payments_response.json()
        print(f"✓ Retrieved invoice payment history")
        print(f"  Invoice: {invoice_payments['invoice']['invoice_number']}")
        print(f"  Total Amount: ${invoice_payments['invoice']['total_amount']}")
        print(f"  Paid Amount: ${invoice_payments['invoice']['paid_amount']}")
        print(f"  Balance Due: ${invoice_payments['invoice']['balance_due']}")
        print(f"  Total Payments: {invoice_payments['total_payments']}")
        
        if invoice_payments['payment_summary']:
            summary = invoice_payments['payment_summary']
            print(f"  Payment Summary:")
            print(f"    Total Amount: ${summary['total_amount']}")
            print(f"    Net Amount: ${summary['net_amount']}")
            print(f"    Method Counts: {summary['method_counts']}")
    
    # Test 4: Process a partial refund
    print("\n4. Testing payment refund...")
    refund_amount = total_amount / 2  # Refund half the amount
    refund_data = {
        'amount': str(refund_amount),
        'reason': 'Partial service cancellation'
    }
    
    refund_response = requests.post(
        f'{BASE_URL}/billing/payments/{payment_id}/refund/',
        json=refund_data,
        headers=headers
    )
    print(f"Refund Status: {refund_response.status_code}")
    
    if refund_response.status_code == 200:
        refund_result = refund_response.json()
        print(f"✓ Refund processed successfully")
        print(f"  Refund Amount: ${refund_amount}")
        print(f"  Refund Payment Number: {refund_result['refund_payment']['payment_number']}")
        print(f"  Original Payment Status: {refund_result['original_payment']['status']}")
    else:
        print(f"Failed to process refund: {refund_response.text}")
    
    # Test 5: Get payment statistics
    print("\n5. Testing payment statistics...")
    stats_response = requests.get(f'{BASE_URL}/billing/payments/statistics/', headers=headers)
    print(f"Payment Statistics Status: {stats_response.status_code}")
    
    if stats_response.status_code == 200:
        stats = stats_response.json()
        print(f"✓ Retrieved payment statistics")
        print(f"  Total Payments: {stats['total_payments']}")
        print(f"  Total Amount: ${stats['total_amount']}")
        print(f"  Total Refunds: ${stats['total_refunds']}")
        print(f"  Net Amount: ${stats['net_amount']}")
        print(f"  Recent Payments (30 days): {stats['recent_payments_30_days']}")
        print(f"  Average Payment: ${stats['average_payment_amount']:.2f}")
        print(f"  Status Breakdown: {stats['status_breakdown']}")
        print(f"  Payment Method Breakdown: {stats['payment_method_breakdown']}")
    
    # Test 6: Create another payment to test partial payments
    print("\n6. Testing partial payment processing...")
    partial_amount = total_amount / 4  # Pay 25% of remaining balance
    partial_payment_data = {
        'invoice': invoice_id,
        'amount': str(partial_amount),
        'payment_method': 'bank_transfer',
        'status': 'completed',
        'transaction_id': 'TXN_TEST_002',
        'reference_number': 'REF_002',
        'notes': 'Partial payment via bank transfer'
    }
    
    create_partial_response = requests.post(
        f'{BASE_URL}/billing/payments/',
        json=partial_payment_data,
        headers=headers
    )
    print(f"Create Partial Payment Status: {create_partial_response.status_code}")
    
    if create_partial_response.status_code == 201:
        partial_payment = create_partial_response.json()
        print(f"✓ Created partial payment: {partial_payment['payment_number']}")
        print(f"  Amount: ${partial_payment['amount']}")
        print(f"  Method: {partial_payment['payment_method']}")
    
    # Test 7: Check updated invoice status
    print("\n7. Testing updated invoice status...")
    updated_invoice_response = requests.get(f'{BASE_URL}/billing/invoices/{invoice_id}/', headers=headers)
    if updated_invoice_response.status_code == 200:
        updated_invoice = updated_invoice_response.json()
        print(f"✓ Retrieved updated invoice status")
        print(f"  Invoice Status: {updated_invoice['status']}")
        print(f"  Total Amount: ${updated_invoice['total_amount']}")
        print(f"  Paid Amount: ${updated_invoice['paid_amount']}")
        print(f"  Balance Due: ${updated_invoice['balance_due']}")
        print(f"  Is Overdue: {updated_invoice['is_overdue']}")
    
    # Test 8: Test payment method validation
    print("\n8. Testing payment validation...")
    invalid_payment_data = {
        'invoice': invoice_id,
        'amount': '-50.00',  # Invalid negative amount
        'payment_method': 'credit_card',
        'status': 'completed'
    }
    
    invalid_payment_response = requests.post(
        f'{BASE_URL}/billing/payments/',
        json=invalid_payment_data,
        headers=headers
    )
    print(f"Invalid Payment Status: {invalid_payment_response.status_code}")
    if invalid_payment_response.status_code == 400:
        print("✓ Properly rejected invalid payment amount")
    else:
        print(f"Unexpected response: {invalid_payment_response.text}")
    
    print("\n=== Payment Processing System Testing Complete ===")

if __name__ == '__main__':
    test_payment_processing_system()
