import os
import django
from decimal import Decimal
from datetime import datetime, timedelta

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hospital_backend.settings')
django.setup()

from django.utils import timezone
from billing.models import (
    FinancialReport, RevenueMetrics, Invoice, Payment, Service, ServiceCategory,
    FinancialTransaction
)
from billing.serializers import FinancialReportSerializer, RevenueMetricsSerializer
from accounts.models import User
from patients.models import Patient

def test_financial_reporting_system():
    print("=== Testing Financial Reporting System ===")
    
    # Get required objects
    user = User.objects.filter(user_type='admin').first()
    patient = Patient.objects.first()
    
    print(f'User: {user.get_full_name()}')
    print(f'Patient: {patient.patient_id}')
    
    # Test 1: Create sample data for reporting
    print('\n1. Setting up sample financial data...')
    
    # Get or create service category
    category, created = ServiceCategory.objects.get_or_create(
        name='Financial Test Services',
        defaults={'description': 'Services for financial reporting tests'}
    )
    
    # Create test services
    services = []
    service_data = [
        ('Financial Test Consultation', 'FTC001', 150.00),
        ('Financial Test Procedure', 'FTP002', 300.00),
        ('Financial Test Follow-up', 'FTF003', 75.00)
    ]

    for name, code, price in service_data:
        service, created = Service.objects.get_or_create(
            code=code,
            defaults={
                'name': name,
                'category': category,
                'description': f'Test service: {name}',
                'base_price': Decimal(str(price)),
                'is_active': True
            }
        )
        services.append(service)
    
    print(f'✓ Created {len(services)} test services')
    
    # Use existing invoices and payments for testing
    existing_invoices = Invoice.objects.all()
    existing_payments = Payment.objects.all()

    print(f'✓ Using {existing_invoices.count()} existing invoices')
    print(f'✓ Using {existing_payments.count()} existing payments')
    
    # Test 2: Generate revenue summary report
    print('\n2. Generating revenue summary report...')
    
    date_from = timezone.now().date() - timedelta(days=30)
    date_to = timezone.now().date()
    
    # Create a financial report instance
    report = FinancialReport.objects.create(
        report_type='revenue_summary',
        title=f'Test Revenue Summary - {date_from} to {date_to}',
        description='Test revenue summary for financial reporting system',
        date_from=date_from,
        date_to=date_to,
        status='generating',
        generated_by=user
    )
    
    print(f'✓ Created financial report: {report.report_number}')
    
    # Generate report data manually (simulating the view method)
    invoices = Invoice.objects.filter(
        invoice_date__range=[date_from, date_to]
    )
    
    payments = Payment.objects.filter(
        payment_date__range=[date_from, date_to]
    )
    
    # Calculate metrics
    total_invoices = invoices.count()
    total_billed = sum(invoice.total_amount for invoice in invoices)
    total_paid = sum(payment.amount for payment in payments if payment.amount > 0)
    total_outstanding = sum(invoice.balance_due for invoice in invoices)
    
    # Generate report data
    report_data = {
        'period': {
            'date_from': date_from.isoformat(),
            'date_to': date_to.isoformat(),
            'days': (date_to - date_from).days + 1
        },
        'summary': {
            'total_invoices': total_invoices,
            'total_billed': float(total_billed),
            'total_paid': float(total_paid),
            'total_outstanding': float(total_outstanding),
            'collection_rate': float(total_paid / total_billed * 100) if total_billed > 0 else 0,
            'average_invoice_amount': float(total_billed / total_invoices) if total_invoices > 0 else 0
        },
        'generated_at': timezone.now().isoformat()
    }
    
    # Update report with data
    report.report_data = report_data
    report.status = 'completed'
    report.save()
    
    print(f'✓ Revenue summary completed:')
    print(f'  Total invoices: {total_invoices}')
    print(f'  Total billed: ${total_billed}')
    print(f'  Total paid: ${total_paid}')
    print(f'  Collection rate: {report_data["summary"]["collection_rate"]:.1f}%')
    
    # Test 3: Create revenue metrics
    print('\n3. Creating revenue metrics...')
    
    revenue_metrics = RevenueMetrics.objects.create(
        period_type='monthly',
        period_start=date_from,
        period_end=date_to,
        total_revenue=total_paid,
        cash_revenue=total_paid,
        insurance_revenue=Decimal('0.00'),
        total_invoices=total_invoices,
        paid_invoices=payments.count(),
        pending_invoices=invoices.filter(status='sent').count(),
        overdue_invoices=0,
        total_payments=payments.count(),
        total_outstanding=total_outstanding,
        top_services=[
            ['Financial Test Consultation', {'count': 5, 'revenue': 750.00}],
            ['Financial Test Procedure', {'count': 3, 'revenue': 900.00}]
        ],
        service_revenue_breakdown={
            'Financial Test Services': float(total_paid)
        }
    )
    
    print(f'✓ Created revenue metrics for {revenue_metrics.period_type} period')
    print(f'  Period: {revenue_metrics.period_start} to {revenue_metrics.period_end}')
    print(f'  Total revenue: ${revenue_metrics.total_revenue}')
    print(f'  Total invoices: {revenue_metrics.total_invoices}')
    
    # Test 4: Test serializers
    print('\n4. Testing serializers...')
    
    # Test FinancialReportSerializer
    report_serializer = FinancialReportSerializer(report)
    print(f'✓ Financial report serializer data:')
    print(f'  Report number: {report_serializer.data["report_number"]}')
    print(f'  Report type: {report_serializer.data["report_type"]}')
    print(f'  Status: {report_serializer.data["status"]}')
    print(f'  Generated by: {report_serializer.data.get("generated_by_name", "Unknown")}')
    
    # Test RevenueMetricsSerializer
    metrics_serializer = RevenueMetricsSerializer(revenue_metrics)
    print(f'✓ Revenue metrics serializer data:')
    print(f'  Period type: {metrics_serializer.data["period_type"]}')
    print(f'  Total revenue: ${metrics_serializer.data["total_revenue"]}')
    print(f'  Total invoices: {metrics_serializer.data["total_invoices"]}')
    
    # Test 5: Financial analytics
    print('\n5. Financial analytics summary...')
    
    # Calculate additional metrics
    all_reports = FinancialReport.objects.all()
    all_metrics = RevenueMetrics.objects.all()
    all_transactions = FinancialTransaction.objects.all()
    
    print(f'✓ System financial overview:')
    print(f'  Total reports generated: {all_reports.count()}')
    print(f'  Total revenue metrics: {all_metrics.count()}')
    print(f'  Total financial transactions: {all_transactions.count()}')
    
    # Revenue trends
    if all_metrics.exists():
        total_system_revenue = sum(m.total_revenue for m in all_metrics)
        avg_revenue_per_period = total_system_revenue / all_metrics.count()
        print(f'  Total system revenue: ${total_system_revenue}')
        print(f'  Average revenue per period: ${avg_revenue_per_period:.2f}')
    
    # Test 6: Report status tracking
    print('\n6. Report status tracking...')
    
    # Create a failed report for testing
    failed_report = FinancialReport.objects.create(
        report_type='custom',
        title='Test Failed Report',
        description='Test report that failed generation',
        date_from=date_from,
        date_to=date_to,
        status='failed',
        generated_by=user
    )
    
    # Count reports by status
    status_counts = {}
    for status_choice in FinancialReport.STATUS_CHOICES:
        status = status_choice[0]
        count = FinancialReport.objects.filter(status=status).count()
        status_counts[status] = count
    
    print(f'✓ Report status breakdown:')
    for status, count in status_counts.items():
        print(f'  {status.title()}: {count} reports')
    
    # Test 7: Performance metrics
    print('\n7. Performance metrics...')
    
    # Calculate performance indicators
    if total_billed > 0:
        collection_efficiency = (total_paid / total_billed) * 100
        print(f'✓ Collection efficiency: {collection_efficiency:.1f}%')
    
    if total_invoices > 0:
        average_invoice_value = total_billed / total_invoices
        print(f'✓ Average invoice value: ${average_invoice_value:.2f}')
    
    if payments.exists():
        average_payment_time = sum(
            (p.payment_date.date() - p.invoice.invoice_date).days 
            for p in payments if hasattr(p, 'invoice')
        ) / payments.count()
        print(f'✓ Average payment time: {average_payment_time:.1f} days')
    
    print('\n=== Financial Reporting System Testing Complete ===')

if __name__ == '__main__':
    test_financial_reporting_system()
