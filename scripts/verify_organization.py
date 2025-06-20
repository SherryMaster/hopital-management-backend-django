#!/usr/bin/env python3
"""
Verification script for Hospital Management System codebase organization
"""
import os
import sys
from pathlib import Path

def verify_organization():
    """Verify the codebase organization is correct"""
    
    print("🔍 Verifying Hospital Management System Codebase Organization")
    print("=" * 70)
    
    # Define expected structure
    expected_structure = {
        'root_files': [
            'manage.py',
            'requirements.txt',
            'CODEBASE_ORGANIZATION.md',
            'audit_api_docs.py'
        ],
        'directories': {
            'accounts': ['models.py', 'views.py', 'serializers.py', 'urls.py'],
            'appointments': ['models.py', 'views.py', 'serializers.py', 'urls.py'],
            'billing': ['models.py', 'views.py', 'serializers.py', 'urls.py'],
            'doctors': ['models.py', 'views.py', 'serializers.py', 'urls.py'],
            'patients': ['models.py', 'views.py', 'serializers.py', 'urls.py'],
            'medical_records': ['models.py', 'views.py', 'serializers.py', 'urls.py'],
            'notifications': ['models.py', 'views.py', 'serializers.py', 'urls.py'],
            'infrastructure': ['models.py', 'views.py', 'serializers.py', 'urls.py'],
            'hospital_backend': ['settings.py', 'urls.py', 'wsgi.py', 'asgi.py'],
            'docs': ['testing'],
            'scripts': ['run_tests.py', 'run_integration_tests.py', 'run_performance_tests.py'],
            'tests': ['factories.py', 'fixtures.py', 'demo', 'validation', 'management']
        },
        'test_subdirectories': {
            'tests/demo': ['demo_performance_tests.py', 'demo_test_data_management.py'],
            'tests/validation': [
                'test_api_documentation.py',
                'test_data_management_suite.py',
                'test_documentation_suite.py',
                'test_integration_suite.py',
                'test_performance_suite.py',
                'test_unit_testing_suite.py'
            ],
            'tests/management': ['commands'],
            'docs/testing': ['README.md', 'testing-cheat-sheet.md', 'api-testing-guide.md']
        }
    }
    
    issues = []
    successes = []
    
    # Check root files
    print("\n1. 📄 Checking Root Files...")
    for file in expected_structure['root_files']:
        if os.path.exists(file):
            successes.append(f"✓ {file}")
            print(f"  ✓ {file}")
        else:
            issues.append(f"✗ Missing root file: {file}")
            print(f"  ✗ {file}")
    
    # Check main directories
    print("\n2. 📁 Checking Main Directories...")
    for directory, expected_files in expected_structure['directories'].items():
        if os.path.exists(directory):
            successes.append(f"✓ Directory: {directory}")
            print(f"  ✓ {directory}/")
            
            # Check key files in directory
            for file in expected_files:
                file_path = os.path.join(directory, file)
                if os.path.exists(file_path):
                    print(f"    ✓ {file}")
                else:
                    print(f"    ⚠ {file} (optional)")
        else:
            issues.append(f"✗ Missing directory: {directory}")
            print(f"  ✗ {directory}/")
    
    # Check test subdirectories
    print("\n3. 🧪 Checking Test Organization...")
    for subdir, expected_files in expected_structure['test_subdirectories'].items():
        if os.path.exists(subdir):
            successes.append(f"✓ Test directory: {subdir}")
            print(f"  ✓ {subdir}/")
            
            # Count files in directory
            actual_files = []
            if os.path.isdir(subdir):
                actual_files = [f for f in os.listdir(subdir) 
                              if os.path.isfile(os.path.join(subdir, f)) and f.endswith('.py')]
            
            print(f"    Files found: {len(actual_files)}")
            for file in actual_files[:5]:  # Show first 5 files
                print(f"    - {file}")
            if len(actual_files) > 5:
                print(f"    ... and {len(actual_files) - 5} more files")
                
        else:
            issues.append(f"✗ Missing test directory: {subdir}")
            print(f"  ✗ {subdir}/")
    
    # Check for old test files in root
    print("\n4. 🧹 Checking for Leftover Test Files in Root...")
    root_files = [f for f in os.listdir('.') if f.endswith('.py')]
    test_files_in_root = [f for f in root_files if f.startswith('test_') or f.startswith('demo_')]
    
    if test_files_in_root:
        print(f"  ⚠ Found {len(test_files_in_root)} test files still in root:")
        for file in test_files_in_root:
            print(f"    - {file}")
        issues.append(f"Test files still in root: {test_files_in_root}")
    else:
        print("  ✓ No test files found in root directory")
        successes.append("✓ Root directory clean of test files")
    
    # Check scripts functionality
    print("\n5. ⚙️ Checking Script Accessibility...")
    script_files = ['scripts/run_tests.py', 'scripts/run_integration_tests.py', 'scripts/run_performance_tests.py']
    for script in script_files:
        if os.path.exists(script):
            print(f"  ✓ {script}")
            successes.append(f"✓ Script: {script}")
        else:
            print(f"  ✗ {script}")
            issues.append(f"✗ Missing script: {script}")
    
    # Check documentation
    print("\n6. 📚 Checking Documentation...")
    doc_files = [
        'docs/testing/README.md',
        'docs/testing/testing-cheat-sheet.md', 
        'docs/testing/api-testing-guide.md',
        'CODEBASE_ORGANIZATION.md'
    ]
    for doc in doc_files:
        if os.path.exists(doc):
            print(f"  ✓ {doc}")
            successes.append(f"✓ Documentation: {doc}")
        else:
            print(f"  ✗ {doc}")
            issues.append(f"✗ Missing documentation: {doc}")
    
    # Summary
    print("\n" + "=" * 70)
    print("📊 ORGANIZATION VERIFICATION SUMMARY")
    print("=" * 70)
    
    print(f"\n✅ Successes: {len(successes)}")
    for success in successes[:10]:  # Show first 10
        print(f"  {success}")
    if len(successes) > 10:
        print(f"  ... and {len(successes) - 10} more successes")
    
    if issues:
        print(f"\n⚠️  Issues Found: {len(issues)}")
        for issue in issues:
            print(f"  {issue}")
    else:
        print(f"\n🎉 No Issues Found!")
    
    # Calculate organization score
    total_checks = len(successes) + len(issues)
    organization_score = (len(successes) / total_checks * 100) if total_checks > 0 else 0
    
    print(f"\n📈 Organization Score: {organization_score:.1f}%")
    
    if organization_score >= 95:
        print("🎉 Excellent! Codebase is well-organized and clean.")
        status = "EXCELLENT"
    elif organization_score >= 85:
        print("✅ Good! Codebase organization is solid with minor issues.")
        status = "GOOD"
    elif organization_score >= 70:
        print("⚠️  Fair. Some organization improvements needed.")
        status = "FAIR"
    else:
        print("❌ Poor. Significant organization issues need attention.")
        status = "POOR"
    
    # Directory size analysis
    print(f"\n📁 Directory Analysis:")
    directories_to_check = ['tests', 'scripts', 'docs', 'accounts', 'appointments']
    for directory in directories_to_check:
        if os.path.exists(directory):
            file_count = sum([len(files) for r, d, files in os.walk(directory)])
            print(f"  {directory}: {file_count} files")
    
    # Recommendations
    print(f"\n💡 Recommendations:")
    if organization_score >= 95:
        print("  - Maintain current organization standards")
        print("  - Consider adding automated organization checks")
        print("  - Document any new organizational patterns")
    elif issues:
        print("  - Address the issues listed above")
        print("  - Run this verification script regularly")
        print("  - Update documentation to reflect changes")
    
    print(f"\n🏁 Verification Complete!")
    print(f"Status: {status} ({organization_score:.1f}%)")
    
    return {
        'status': status,
        'score': organization_score,
        'successes': len(successes),
        'issues': len(issues),
        'total_checks': total_checks
    }

if __name__ == '__main__':
    try:
        results = verify_organization()
        
        # Exit with appropriate code
        if results['score'] >= 85:
            sys.exit(0)  # Success
        else:
            sys.exit(1)  # Issues found
            
    except Exception as e:
        print(f"❌ Error during verification: {e}")
        sys.exit(2)  # Error
