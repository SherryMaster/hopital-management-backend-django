import os
import django
import requests
import json

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hospital_backend.settings')
django.setup()

def test_api_documentation():
    """
    Test the API documentation endpoints and verify they're working correctly
    """
    print("=== Testing API Documentation System ===")
    
    base_url = "http://127.0.0.1:8000"
    
    # Test 1: Check if Swagger UI is accessible
    print("\n1. Testing Swagger UI accessibility...")
    try:
        response = requests.get(f"{base_url}/api/docs/", timeout=10)
        if response.status_code == 200:
            print("✓ Swagger UI is accessible")
            print(f"  Status: {response.status_code}")
            print(f"  Content-Type: {response.headers.get('content-type', 'N/A')}")
        else:
            print(f"✗ Swagger UI failed with status: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"✗ Error accessing Swagger UI: {e}")
    
    # Test 2: Check if ReDoc is accessible
    print("\n2. Testing ReDoc accessibility...")
    try:
        response = requests.get(f"{base_url}/api/redoc/", timeout=10)
        if response.status_code == 200:
            print("✓ ReDoc is accessible")
            print(f"  Status: {response.status_code}")
            print(f"  Content-Type: {response.headers.get('content-type', 'N/A')}")
        else:
            print(f"✗ ReDoc failed with status: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"✗ Error accessing ReDoc: {e}")
    
    # Test 3: Check OpenAPI schema endpoint
    print("\n3. Testing OpenAPI schema endpoint...")
    try:
        response = requests.get(f"{base_url}/api/schema/", timeout=10)
        if response.status_code == 200:
            print("✓ OpenAPI schema is accessible")
            print(f"  Status: {response.status_code}")
            print(f"  Content-Type: {response.headers.get('content-type', 'N/A')}")
            
            # Try to parse the schema
            try:
                schema = response.json()
                print(f"  Schema version: {schema.get('openapi', 'N/A')}")
                print(f"  API title: {schema.get('info', {}).get('title', 'N/A')}")
                print(f"  API version: {schema.get('info', {}).get('version', 'N/A')}")
                
                # Count endpoints
                paths = schema.get('paths', {})
                endpoint_count = len(paths)
                print(f"  Total endpoints documented: {endpoint_count}")
                
                # Show some example endpoints
                print("  Sample endpoints:")
                for i, (path, methods) in enumerate(list(paths.items())[:5]):
                    method_list = list(methods.keys())
                    print(f"    {path}: {', '.join(method_list)}")
                
                if endpoint_count > 5:
                    print(f"    ... and {endpoint_count - 5} more endpoints")
                
            except json.JSONDecodeError:
                print("  ✗ Schema is not valid JSON")
        else:
            print(f"✗ OpenAPI schema failed with status: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"✗ Error accessing OpenAPI schema: {e}")
    
    # Test 4: Check specific API endpoints are documented
    print("\n4. Testing specific API endpoint documentation...")
    
    documented_endpoints = [
        "/api/accounts/",
        "/api/patients/",
        "/api/doctors/",
        "/api/appointments/",
        "/api/medical-records/",
        "/api/billing/",
        "/api/notifications/",
        "/api/infrastructure/"
    ]
    
    try:
        response = requests.get(f"{base_url}/api/schema/", timeout=10)
        if response.status_code == 200:
            schema = response.json()
            paths = schema.get('paths', {})
            
            documented_count = 0
            for endpoint in documented_endpoints:
                # Check if any path starts with this endpoint
                found = any(path.startswith(endpoint) for path in paths.keys())
                if found:
                    documented_count += 1
                    print(f"  ✓ {endpoint} endpoints are documented")
                else:
                    print(f"  ✗ {endpoint} endpoints not found in documentation")
            
            print(f"\n  Summary: {documented_count}/{len(documented_endpoints)} endpoint groups documented")
            
    except Exception as e:
        print(f"✗ Error checking endpoint documentation: {e}")
    
    # Test 5: Check authentication documentation
    print("\n5. Testing authentication documentation...")
    try:
        response = requests.get(f"{base_url}/api/schema/", timeout=10)
        if response.status_code == 200:
            schema = response.json()
            
            # Check for security schemes
            security_schemes = schema.get('components', {}).get('securitySchemes', {})
            if security_schemes:
                print("✓ Security schemes documented:")
                for scheme_name, scheme_details in security_schemes.items():
                    scheme_type = scheme_details.get('type', 'N/A')
                    print(f"    {scheme_name}: {scheme_type}")
            else:
                print("✗ No security schemes found in documentation")
            
            # Check for authentication endpoints
            auth_endpoints = [path for path in schema.get('paths', {}).keys() 
                            if 'login' in path or 'register' in path or 'token' in path]
            
            if auth_endpoints:
                print("✓ Authentication endpoints documented:")
                for endpoint in auth_endpoints:
                    print(f"    {endpoint}")
            else:
                print("✗ No authentication endpoints found")
                
    except Exception as e:
        print(f"✗ Error checking authentication documentation: {e}")
    
    # Test 6: Check for comprehensive examples and descriptions
    print("\n6. Testing documentation quality...")
    try:
        response = requests.get(f"{base_url}/api/schema/", timeout=10)
        if response.status_code == 200:
            schema = response.json()
            paths = schema.get('paths', {})
            
            endpoints_with_examples = 0
            endpoints_with_descriptions = 0
            total_endpoints = 0
            
            for path, methods in paths.items():
                for method, details in methods.items():
                    if method in ['get', 'post', 'put', 'patch', 'delete']:
                        total_endpoints += 1
                        
                        # Check for description
                        if details.get('description') or details.get('summary'):
                            endpoints_with_descriptions += 1
                        
                        # Check for examples in request body or responses
                        has_examples = False
                        
                        # Check request body examples
                        request_body = details.get('requestBody', {})
                        if request_body:
                            content = request_body.get('content', {})
                            for content_type, content_details in content.items():
                                if content_details.get('examples'):
                                    has_examples = True
                                    break
                        
                        # Check response examples
                        responses = details.get('responses', {})
                        for response_code, response_details in responses.items():
                            content = response_details.get('content', {})
                            for content_type, content_details in content.items():
                                if content_details.get('examples'):
                                    has_examples = True
                                    break
                        
                        if has_examples:
                            endpoints_with_examples += 1
            
            print(f"✓ Documentation quality metrics:")
            print(f"    Total endpoints: {total_endpoints}")
            print(f"    Endpoints with descriptions: {endpoints_with_descriptions} ({endpoints_with_descriptions/total_endpoints*100:.1f}%)")
            print(f"    Endpoints with examples: {endpoints_with_examples} ({endpoints_with_examples/total_endpoints*100:.1f}%)")
            
    except Exception as e:
        print(f"✗ Error checking documentation quality: {e}")
    
    # Test 7: Check generated documentation file
    print("\n7. Testing generated documentation file...")
    try:
        from docs.api_documentation_generator import generate_api_docs
        
        # Generate fresh documentation
        docs_json = generate_api_docs()
        docs = json.loads(docs_json)
        
        print("✓ Generated documentation file:")
        print(f"    API title: {docs['api_info']['info']['title']}")
        print(f"    API version: {docs['api_info']['info']['version']}")
        print(f"    Modules documented: {len(docs['api_info']['modules'])}")
        
        # List modules
        for module_name in docs['api_info']['modules'].keys():
            module_info = docs['api_info']['modules'][module_name]
            endpoint_count = len(module_info['endpoints'])
            print(f"      {module_name}: {endpoint_count} endpoints")
        
        # Check authentication guide
        auth_guide = docs.get('authentication_guide', {})
        if auth_guide:
            print(f"    Authentication guide: {len(auth_guide.get('steps', []))} steps")
            print(f"    Token types documented: {len(auth_guide.get('token_types', {}))}")
        
    except Exception as e:
        print(f"✗ Error checking generated documentation: {e}")
    
    print("\n=== API Documentation Testing Complete ===")


if __name__ == '__main__':
    test_api_documentation()
