#!/usr/bin/env python3
"""
Setup cache tables for Hospital Management System
Creates database cache tables when Redis is not available
"""
import os
import sys
import django
from django.core.management import execute_from_command_line

# Add parent directory to path to import Django modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hospital_backend.settings')
django.setup()

def setup_cache_tables():
    """
    Create cache tables for database caching
    """
    print("🗄️ Setting up cache tables for Hospital Management System")
    print("=" * 60)
    
    try:
        from django.conf import settings
        
        # Check if we're using database cache
        caches_config = getattr(settings, 'CACHES', {})
        
        cache_tables = []
        for cache_name, cache_config in caches_config.items():
            backend = cache_config.get('BACKEND', '')
            if 'DatabaseCache' in backend:
                location = cache_config.get('LOCATION', '')
                if location:
                    cache_tables.append(location)
        
        if cache_tables:
            print(f"Found {len(cache_tables)} database cache tables to create:")
            for table in cache_tables:
                print(f"  - {table}")
            
            # Create cache tables
            for table in cache_tables:
                try:
                    print(f"\n📊 Creating cache table: {table}")
                    execute_from_command_line(['manage.py', 'createcachetable', table])
                    print(f"✓ Successfully created cache table: {table}")
                except Exception as e:
                    if 'already exists' in str(e).lower():
                        print(f"⚠ Cache table {table} already exists")
                    else:
                        print(f"✗ Error creating cache table {table}: {e}")
            
            print(f"\n🎉 Cache table setup completed!")
            
        else:
            print("ℹ️  No database cache tables needed (using Redis or other backend)")
        
    except Exception as e:
        print(f"❌ Error setting up cache tables: {e}")
        return False
    
    return True

if __name__ == '__main__':
    try:
        success = setup_cache_tables()
        if success:
            print("\n✅ Cache setup completed successfully!")
        else:
            print("\n❌ Cache setup failed!")
    except Exception as e:
        print(f"❌ Error during cache setup: {e}")
