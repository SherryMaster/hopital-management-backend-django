import requests
import json

def audit_api_documentation():
    """Audit the current API documentation structure"""
    print("=== HOSPITAL MANAGEMENT SYSTEM API DOCUMENTATION AUDIT ===\n")
    
    try:
        # Get the current API schema in JSON format
        response = requests.get('http://localhost:8000/api/schema/', headers={'Accept': 'application/json'})
        if response.status_code == 200:
            schema = response.json()
            
            # Basic API information
            info = schema.get('info', {})
            print(f"API Title: {info.get('title', 'N/A')}")
            print(f"API Version: {info.get('version', 'N/A')}")
            print(f"API Description Length: {len(info.get('description', ''))}")
            
            # Analyze tags (API groups)
            tags = schema.get('tags', [])
            print(f"\nTotal API Groups/Tags: {len(tags)}")
            print("\nCurrent API Groups:")
            for i, tag in enumerate(tags, 1):
                print(f"{i:2d}. '{tag['name']}' - {tag['description']}")
            
            # Analyze paths and their tags
            paths = schema.get('paths', {})
            print(f"\nTotal API Endpoints: {len(paths)}")
            
            # Group endpoints by tags
            endpoint_tags = {}
            untagged_endpoints = []
            
            for path, methods in paths.items():
                for method, details in methods.items():
                    if method.upper() in ['GET', 'POST', 'PUT', 'PATCH', 'DELETE']:
                        tags_list = details.get('tags', [])
                        if not tags_list:
                            untagged_endpoints.append(f"{method.upper()} {path}")
                        else:
                            for tag in tags_list:
                                if tag not in endpoint_tags:
                                    endpoint_tags[tag] = []
                                endpoint_tags[tag].append(f"{method.upper()} {path}")
            
            # Display endpoints by group
            print("\n=== ENDPOINTS BY GROUP ===")
            for tag, endpoints in sorted(endpoint_tags.items()):
                print(f"\n{tag} ({len(endpoints)} endpoints):")
                for endpoint in sorted(endpoints):
                    print(f"  - {endpoint}")
            
            if untagged_endpoints:
                print(f"\nUntagged Endpoints ({len(untagged_endpoints)}):")
                for endpoint in sorted(untagged_endpoints):
                    print(f"  - {endpoint}")
            
            # Identify potential issues
            print("\n=== POTENTIAL ISSUES IDENTIFIED ===")
            
            # Check for overlapping tags
            overlapping_tags = []
            tag_names = [tag['name'] for tag in tags]
            
            # Check for similar tag names
            for i, tag1 in enumerate(tag_names):
                for j, tag2 in enumerate(tag_names[i+1:], i+1):
                    if (tag1.lower() in tag2.lower() or tag2.lower() in tag1.lower()) and tag1 != tag2:
                        overlapping_tags.append((tag1, tag2))
            
            if overlapping_tags:
                print("\nPotential overlapping tags:")
                for tag1, tag2 in overlapping_tags:
                    print(f"  - '{tag1}' and '{tag2}'")
            
            # Check for endpoints that might belong to multiple categories
            auth_endpoints = endpoint_tags.get('Authentication', [])
            user_mgmt_endpoints = endpoint_tags.get('User Management', [])
            
            if auth_endpoints and user_mgmt_endpoints:
                print(f"\nPotential overlap between Authentication ({len(auth_endpoints)}) and User Management ({len(user_mgmt_endpoints)})")
            
            # Check naming consistency
            naming_issues = []
            for tag_name in tag_names:
                if not tag_name.replace(' ', '').replace('&', '').isalpha():
                    naming_issues.append(tag_name)
            
            if naming_issues:
                print(f"\nNaming consistency issues:")
                for tag in naming_issues:
                    print(f"  - '{tag}'")
            
            return schema, endpoint_tags
            
        else:
            print(f"Failed to get API schema: {response.status_code}")
            return None, None
            
    except Exception as e:
        print(f"Error during audit: {e}")
        return None, None

if __name__ == '__main__':
    schema, endpoint_tags = audit_api_documentation()
