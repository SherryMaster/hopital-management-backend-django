#!/usr/bin/env python3
"""
Create Performance Indexes for Hospital Management System
Adds database indexes for optimal query performance
"""
import os
import sys
import django

# Add parent directory to path to import Django modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hospital_backend.settings')
django.setup()

from django.db import connection
from django.core.management.color import make_style

style = make_style()

def create_performance_indexes():
    """
    Create additional database indexes for performance optimization
    """
    print(style.SUCCESS("🗄️ Creating Performance Indexes for Hospital Management System"))
    print("=" * 70)
    
    # SQL statements for creating performance indexes
    index_statements = [
        # User model indexes
        {
            'name': 'idx_accounts_user_email_active',
            'sql': 'CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_accounts_user_email_active ON accounts_user (email, is_active);',
            'description': 'User authentication queries by email and active status'
        },
        {
            'name': 'idx_accounts_user_type_active',
            'sql': 'CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_accounts_user_type_active ON accounts_user (user_type, is_active);',
            'description': 'User queries by type and active status'
        },
        {
            'name': 'idx_accounts_user_last_login',
            'sql': 'CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_accounts_user_last_login ON accounts_user (last_login DESC);',
            'description': 'Recent login queries'
        },
        
        # Patient model indexes
        {
            'name': 'idx_patients_patient_dob_active',
            'sql': 'CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_patients_patient_dob_active ON patients_patient (date_of_birth, is_active);',
            'description': 'Patient age calculations and active status'
        },
        {
            'name': 'idx_patients_patient_blood_type',
            'sql': 'CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_patients_patient_blood_type ON patients_patient (blood_type);',
            'description': 'Blood type searches for emergencies'
        },
        {
            'name': 'idx_patients_patient_registration_date',
            'sql': 'CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_patients_patient_registration_date ON patients_patient (registration_date DESC);',
            'description': 'Recent patient registrations'
        },
        
        # Appointment model indexes
        {
            'name': 'idx_appointments_appointment_patient_date_status',
            'sql': 'CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_appointments_appointment_patient_date_status ON appointments_appointment (patient_id, appointment_date, status);',
            'description': 'Patient appointment history and status queries'
        },
        {
            'name': 'idx_appointments_appointment_doctor_date_status',
            'sql': 'CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_appointments_appointment_doctor_date_status ON appointments_appointment (doctor_id, appointment_date, status);',
            'description': 'Doctor schedule and appointment status queries'
        },
        {
            'name': 'idx_appointments_appointment_date_time',
            'sql': 'CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_appointments_appointment_date_time ON appointments_appointment (appointment_date, appointment_time);',
            'description': 'Appointment scheduling conflict detection'
        },
        {
            'name': 'idx_appointments_appointment_status_date',
            'sql': 'CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_appointments_appointment_status_date ON appointments_appointment (status, appointment_date);',
            'description': 'Appointment status reports and filtering'
        },
        {
            'name': 'idx_appointments_appointment_created_at',
            'sql': 'CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_appointments_appointment_created_at ON appointments_appointment (created_at DESC);',
            'description': 'Recent appointment creation queries'
        },
        
        # Medical Records indexes
        {
            'name': 'idx_medical_records_patient_date',
            'sql': 'CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_medical_records_patient_date ON medical_records_medicalrecord (patient_id, record_date DESC);',
            'description': 'Patient medical history chronological queries'
        },
        {
            'name': 'idx_medical_records_doctor_date',
            'sql': 'CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_medical_records_doctor_date ON medical_records_medicalrecord (doctor_id, record_date DESC);',
            'description': 'Doctor patient records queries'
        },
        {
            'name': 'idx_medical_records_type_date',
            'sql': 'CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_medical_records_type_date ON medical_records_medicalrecord (record_type, record_date DESC);',
            'description': 'Medical record type filtering'
        },
        {
            'name': 'idx_medical_records_finalized',
            'sql': 'CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_medical_records_finalized ON medical_records_medicalrecord (is_finalized, finalized_at);',
            'description': 'Finalized records queries'
        },
        
        # Billing indexes
        {
            'name': 'idx_billing_invoice_patient_status_date',
            'sql': 'CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_billing_invoice_patient_status_date ON billing_invoice (patient_id, status, invoice_date DESC);',
            'description': 'Patient billing history and status queries'
        },
        {
            'name': 'idx_billing_invoice_due_date_status',
            'sql': 'CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_billing_invoice_due_date_status ON billing_invoice (due_date, status);',
            'description': 'Overdue invoice queries'
        },
        {
            'name': 'idx_billing_invoice_total_amount',
            'sql': 'CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_billing_invoice_total_amount ON billing_invoice (total_amount DESC);',
            'description': 'High-value invoice queries'
        },
        {
            'name': 'idx_billing_payment_date_amount',
            'sql': 'CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_billing_payment_date_amount ON billing_payment (payment_date DESC, amount);',
            'description': 'Payment history and amount queries'
        },
        
        # Doctor model indexes
        {
            'name': 'idx_doctors_doctor_specialization',
            'sql': 'CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_doctors_doctor_specialization ON doctors_doctor (specialization);',
            'description': 'Doctor specialization searches'
        },
        {
            'name': 'idx_doctors_doctor_available',
            'sql': 'CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_doctors_doctor_available ON doctors_doctor (is_available);',
            'description': 'Available doctor queries'
        },
        
        # Notification indexes
        {
            'name': 'idx_notifications_notification_user_read',
            'sql': 'CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_notifications_notification_user_read ON notifications_notification (user_id, is_read, created_at DESC);',
            'description': 'User notification queries'
        },
        {
            'name': 'idx_notifications_notification_type_status',
            'sql': 'CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_notifications_notification_type_status ON notifications_notification (notification_type, status);',
            'description': 'Notification type and status queries'
        },
        
        # Composite indexes for complex queries
        {
            'name': 'idx_appointments_today_active',
            'sql': '''CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_appointments_today_active 
                     ON appointments_appointment (appointment_date, status) 
                     WHERE status IN ('scheduled', 'confirmed', 'in_progress');''',
            'description': 'Today\'s active appointments (partial index)'
        },
        {
            'name': 'idx_patients_active_with_insurance',
            'sql': '''CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_patients_active_with_insurance 
                     ON patients_patient (insurance_provider) 
                     WHERE is_active = true AND insurance_provider IS NOT NULL;''',
            'description': 'Active patients with insurance (partial index)'
        },
        {
            'name': 'idx_medical_records_recent',
            'sql': '''CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_medical_records_recent 
                     ON medical_records_medicalrecord (patient_id, record_date DESC) 
                     WHERE record_date >= CURRENT_DATE - INTERVAL '1 year';''',
            'description': 'Recent medical records (partial index)'
        },
        
        # Full-text search indexes (PostgreSQL specific)
        {
            'name': 'idx_patients_search_gin',
            'sql': '''CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_patients_search_gin 
                     ON patients_patient USING gin(to_tsvector('english', 
                     COALESCE(patient_id, '') || ' ' || 
                     COALESCE(notes, '')));''',
            'description': 'Patient full-text search index'
        },
        {
            'name': 'idx_medical_records_search_gin',
            'sql': '''CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_medical_records_search_gin 
                     ON medical_records_medicalrecord USING gin(to_tsvector('english', 
                     COALESCE(chief_complaint, '') || ' ' || 
                     COALESCE(assessment, '') || ' ' || 
                     COALESCE(notes, '')));''',
            'description': 'Medical records full-text search index'
        },
    ]
    
    # Execute index creation
    created_count = 0
    failed_count = 0
    
    with connection.cursor() as cursor:
        for index in index_statements:
            try:
                print(f"\n📊 Creating index: {index['name']}")
                print(f"   Purpose: {index['description']}")
                
                # Execute the SQL
                cursor.execute(index['sql'])
                
                print(style.SUCCESS(f"   ✓ Successfully created index: {index['name']}"))
                created_count += 1
                
            except Exception as e:
                error_msg = str(e)
                if 'already exists' in error_msg.lower():
                    print(style.WARNING(f"   ⚠ Index already exists: {index['name']}"))
                else:
                    print(style.ERROR(f"   ✗ Failed to create index {index['name']}: {error_msg}"))
                    failed_count += 1
    
    # Summary
    print("\n" + "=" * 70)
    print(style.SUCCESS("📊 INDEX CREATION SUMMARY"))
    print("=" * 70)
    
    total_indexes = len(index_statements)
    print(f"Total indexes processed: {total_indexes}")
    print(style.SUCCESS(f"Successfully created: {created_count}"))
    if failed_count > 0:
        print(style.ERROR(f"Failed to create: {failed_count}"))
    
    # Performance recommendations
    print(f"\n💡 Performance Recommendations:")
    print(f"  - Monitor query performance using Django Debug Toolbar")
    print(f"  - Use EXPLAIN ANALYZE for slow queries")
    print(f"  - Consider partitioning large tables (appointments, medical_records)")
    print(f"  - Implement connection pooling for high-traffic scenarios")
    print(f"  - Regular VACUUM and ANALYZE operations for PostgreSQL")
    
    return {
        'total': total_indexes,
        'created': created_count,
        'failed': failed_count
    }


def analyze_database_performance():
    """
    Analyze current database performance
    """
    print(f"\n🔍 Database Performance Analysis")
    print("-" * 40)
    
    with connection.cursor() as cursor:
        try:
            # Check database size
            cursor.execute("SELECT pg_size_pretty(pg_database_size(current_database()));")
            db_size = cursor.fetchone()[0]
            print(f"Database size: {db_size}")
            
            # Check active connections
            cursor.execute("SELECT count(*) FROM pg_stat_activity WHERE state = 'active';")
            active_connections = cursor.fetchone()[0]
            print(f"Active connections: {active_connections}")
            
            # Check cache hit ratio
            cursor.execute("""
                SELECT round(
                    (sum(heap_blks_hit) / (sum(heap_blks_hit) + sum(heap_blks_read))) * 100, 2
                ) as cache_hit_ratio
                FROM pg_statio_user_tables;
            """)
            result = cursor.fetchone()
            cache_hit_ratio = result[0] if result[0] else 0
            print(f"Cache hit ratio: {cache_hit_ratio}%")
            
            # Check table sizes
            cursor.execute("""
                SELECT 
                    schemaname,
                    tablename,
                    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
                FROM pg_tables 
                WHERE schemaname NOT IN ('information_schema', 'pg_catalog')
                ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
                LIMIT 10;
            """)
            
            print(f"\nLargest tables:")
            for row in cursor.fetchall():
                print(f"  {row[1]}: {row[2]}")
                
        except Exception as e:
            print(f"Error analyzing database: {e}")


if __name__ == '__main__':
    try:
        # Analyze current performance
        analyze_database_performance()
        
        # Create performance indexes
        results = create_performance_indexes()
        
        print(f"\n🎉 Database optimization completed!")
        print(f"Results: {results}")
        
        # Exit with appropriate code
        if results['failed'] == 0:
            exit(0)  # Success
        else:
            exit(1)  # Some failures
            
    except Exception as e:
        print(style.ERROR(f"❌ Error during database optimization: {e}"))
        exit(2)  # Error
