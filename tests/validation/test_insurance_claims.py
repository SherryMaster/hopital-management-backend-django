import os
import django
from decimal import Decimal
from datetime import datetime, timedelta

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hospital_backend.settings')
django.setup()

from django.utils import timezone
from billing.models import InsuranceClaim, ClaimDocument, ClaimAuditLog, InsurancePreAuthorization, Invoice
from billing.serializers import InsuranceClaimSerializer
from patients.models import Patient, InsuranceInformation
from accounts.models import User

def test_insurance_claims_management():
    print("=== Testing Insurance Claims Management System ===")
    
    # Get required objects
    user = User.objects.filter(user_type='admin').first()
    patient = Patient.objects.first()
    invoice = Invoice.objects.first()
    
    print(f'User: {user.get_full_name()}')
    print(f'Patient: {patient.patient_id}')
    print(f'Invoice: {invoice.invoice_number} (${invoice.total_amount})')
    
    # Test 1: Create insurance information if not exists
    print('\n1. Setting up insurance information...')
    insurance_info, created = InsuranceInformation.objects.get_or_create(
        patient=patient,
        defaults={
            'provider_name': 'Blue Cross Blue Shield',
            'policy_number': 'BCBS123456789',
            'group_number': 'GRP001',
            'subscriber_name': patient.user.get_full_name(),
            'subscriber_id': 'SUB123456',
            'relationship_to_subscriber': 'self',
            'effective_date': timezone.now().date() - timedelta(days=365),
            'expiration_date': timezone.now().date() + timedelta(days=365),
            'copay_amount': Decimal('25.00'),
            'deductible_amount': Decimal('1000.00'),
            'provider_phone': '1-800-555-0123',
            'provider_address': '123 Insurance St, City, State 12345',
            'is_active': True
        }
    )
    if created:
        print(f'✓ Created insurance information: {insurance_info.provider_name}')
    else:
        print(f'✓ Using existing insurance: {insurance_info.provider_name}')
    
    # Test 2: Create pre-authorization
    print('\n2. Creating pre-authorization...')
    pre_auth = InsurancePreAuthorization.objects.create(
        patient=patient,
        insurance_info=insurance_info,
        service_description='Specialist consultation and diagnostic procedures',
        procedure_codes=['99213', '71020', '85025'],
        diagnosis_codes=['Z00.00', 'R06.02'],
        requested_amount=Decimal('500.00'),
        service_date_from=timezone.now().date(),
        service_date_to=timezone.now().date() + timedelta(days=7),
        status='pending',
        notes='Pre-authorization for specialist consultation',
        created_by=user
    )
    print(f'✓ Created pre-authorization: {pre_auth.authorization_number}')
    print(f'  Status: {pre_auth.status}')
    print(f'  Requested amount: ${pre_auth.requested_amount}')
    
    # Test 3: Approve pre-authorization
    print('\n3. Approving pre-authorization...')
    pre_auth.status = 'approved'
    pre_auth.authorized_amount = Decimal('450.00')
    pre_auth.authorization_date = timezone.now().date()
    pre_auth.expiry_date = timezone.now().date() + timedelta(days=30)
    pre_auth.save()
    print(f'✓ Pre-authorization approved: ${pre_auth.authorized_amount}')
    
    # Test 4: Create insurance claim
    print('\n4. Creating insurance claim...')
    claim_data = {
        'patient': str(patient.id),
        'insurance_info': str(insurance_info.id),
        'invoice': str(invoice.id),
        'service_date': timezone.now().date().isoformat(),
        'billed_amount': str(invoice.total_amount),
        'notes': 'Insurance claim for specialist consultation and procedures'
    }
    
    # Test serializer
    serializer = InsuranceClaimSerializer(data=claim_data)
    print(f'Claim serializer valid: {serializer.is_valid()}')
    if not serializer.is_valid():
        print(f'Errors: {serializer.errors}')
        return
    
    claim = serializer.save(created_by=user)
    print(f'✓ Created insurance claim: {claim.claim_number}')
    print(f'  Status: {claim.status}')
    print(f'  Billed amount: ${claim.billed_amount}')
    print(f'  Insurance company: {claim.insurance_info.provider_name}')
    
    # Test 5: Create audit log entry
    print('\n5. Creating audit log entry...')
    audit_log = ClaimAuditLog.objects.create(
        claim=claim,
        action='created',
        description=f'Insurance claim {claim.claim_number} created for ${claim.billed_amount}',
        new_values={
            'status': claim.status,
            'billed_amount': str(claim.billed_amount),
            'patient': claim.patient.patient_id,
            'insurance_company': claim.insurance_info.provider_name
        },
        performed_by=user,
        ip_address='127.0.0.1',
        user_agent='Test User Agent'
    )
    print(f'✓ Created audit log: {audit_log.action}')
    
    # Test 6: Submit claim
    print('\n6. Submitting insurance claim...')
    previous_status = claim.status
    claim.status = 'submitted'
    claim.submitted_date = timezone.now()
    claim.save()
    
    # Create audit log for submission
    ClaimAuditLog.objects.create(
        claim=claim,
        action='submitted',
        description=f'Insurance claim {claim.claim_number} submitted to {claim.insurance_info.provider_name}',
        previous_values={'status': previous_status},
        new_values={'status': 'submitted', 'submitted_date': claim.submitted_date.isoformat()},
        performed_by=user,
        ip_address='127.0.0.1'
    )
    print(f'✓ Claim submitted: {claim.status}')
    print(f'  Submitted date: {claim.submitted_date}')
    
    # Test 7: Process claim approval
    print('\n7. Processing claim approval...')
    previous_status = claim.status
    claim.status = 'approved'
    claim.approved_amount = Decimal('400.00')
    claim.patient_responsibility = Decimal('25.00')  # Copay
    claim.processed_date = timezone.now()
    claim.save()
    
    # Create audit log for approval
    ClaimAuditLog.objects.create(
        claim=claim,
        action='approved',
        description=f'Insurance claim {claim.claim_number} approved for ${claim.approved_amount}',
        previous_values={
            'status': previous_status,
            'approved_amount': None,
            'patient_responsibility': '0.00'
        },
        new_values={
            'status': 'approved',
            'approved_amount': str(claim.approved_amount),
            'patient_responsibility': str(claim.patient_responsibility),
            'processed_date': claim.processed_date.isoformat()
        },
        performed_by=user,
        ip_address='127.0.0.1'
    )
    print(f'✓ Claim approved: ${claim.approved_amount}')
    print(f'  Patient responsibility: ${claim.patient_responsibility}')
    print(f'  Processed date: {claim.processed_date}')
    
    # Test 8: Create claim document
    print('\n8. Adding claim document...')
    claim_doc = ClaimDocument.objects.create(
        claim=claim,
        document_type='medical_record',
        title='Medical Record - Specialist Consultation',
        description='Complete medical record for specialist consultation and diagnostic procedures',
        file_size=1024000,  # 1MB
        file_type='application/pdf',
        uploaded_by=user
    )
    print(f'✓ Added claim document: {claim_doc.title}')
    print(f'  Document type: {claim_doc.document_type}')
    print(f'  File size: {claim_doc.file_size} bytes')
    
    # Test 9: Process insurance payment
    print('\n9. Processing insurance payment...')
    previous_status = claim.status
    claim.status = 'paid'
    claim.paid_amount = claim.approved_amount
    claim.save()
    
    # Create audit log for payment
    ClaimAuditLog.objects.create(
        claim=claim,
        action='paid',
        description=f'Insurance payment of ${claim.paid_amount} received for claim {claim.claim_number}',
        previous_values={
            'status': previous_status,
            'paid_amount': '0.00'
        },
        new_values={
            'status': 'paid',
            'paid_amount': str(claim.paid_amount)
        },
        performed_by=user,
        ip_address='127.0.0.1'
    )
    print(f'✓ Insurance payment processed: ${claim.paid_amount}')
    print(f'  Final status: {claim.status}')
    
    # Test 10: Claims statistics
    print('\n10. Insurance claims statistics...')
    total_claims = InsuranceClaim.objects.count()
    total_billed = sum(c.billed_amount for c in InsuranceClaim.objects.all())
    total_approved = sum(c.approved_amount for c in InsuranceClaim.objects.all() if c.approved_amount)
    total_paid = sum(c.paid_amount for c in InsuranceClaim.objects.all())
    
    print(f'✓ Claims statistics:')
    print(f'  Total claims: {total_claims}')
    print(f'  Total billed: ${total_billed}')
    print(f'  Total approved: ${total_approved}')
    print(f'  Total paid: ${total_paid}')
    
    # Test 11: Audit trail
    print('\n11. Audit trail review...')
    audit_logs = ClaimAuditLog.objects.filter(claim=claim).order_by('performed_at')
    print(f'✓ Audit trail ({audit_logs.count()} entries):')
    for log in audit_logs:
        print(f'  - {log.performed_at.strftime("%Y-%m-%d %H:%M")} - {log.action}: {log.description}')
    
    print('\n=== Insurance Claims Management System Testing Complete ===')

if __name__ == '__main__':
    test_insurance_claims_management()
