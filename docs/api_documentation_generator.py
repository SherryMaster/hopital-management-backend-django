"""
API Documentation Generator for Hospital Management System
"""
import os
import django
import json
import yaml

# Setup Django first
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hospital_backend.settings')
django.setup()

from django.conf import settings


class HospitalAPIDocumentationGenerator:
    """
    Generate comprehensive API documentation for the Hospital Management System
    """

    def __init__(self):
        self.title = 'Hospital Management System API'
        self.description = 'Comprehensive hospital management system API'
        self.version = '1.0.0'
    
    def generate_endpoint_documentation(self):
        """
        Generate documentation for all API endpoints
        """
        documentation = {
            'info': {
                'title': 'Hospital Management System API',
                'version': '1.0.0',
                'description': 'Complete API documentation for hospital management operations'
            },
            'modules': {}
        }
        
        # Define modules and their endpoints
        modules = {
            'Authentication & User Management': {
                'base_url': '/api/accounts/',
                'description': 'User authentication, registration, and profile management',
                'endpoints': [
                    {
                        'path': 'register/',
                        'methods': ['POST'],
                        'description': 'Register a new user account',
                        'authentication': False,
                        'parameters': ['username', 'email', 'password', 'user_type']
                    },
                    {
                        'path': 'login/',
                        'methods': ['POST'],
                        'description': 'Authenticate user and get JWT tokens',
                        'authentication': False,
                        'parameters': ['username', 'password']
                    },
                    {
                        'path': 'logout/',
                        'methods': ['POST'],
                        'description': 'Logout user and invalidate tokens',
                        'authentication': True,
                        'parameters': []
                    },
                    {
                        'path': 'profile/',
                        'methods': ['GET', 'PUT', 'PATCH'],
                        'description': 'Get and update user profile',
                        'authentication': True,
                        'parameters': ['first_name', 'last_name', 'email']
                    },
                    {
                        'path': 'change-password/',
                        'methods': ['POST'],
                        'description': 'Change user password',
                        'authentication': True,
                        'parameters': ['old_password', 'new_password']
                    }
                ]
            },
            'Patient Management': {
                'base_url': '/api/patients/',
                'description': 'Patient registration, profiles, and medical information',
                'endpoints': [
                    {
                        'path': 'profiles/',
                        'methods': ['GET', 'POST'],
                        'description': 'List and create patient profiles',
                        'authentication': True,
                        'parameters': ['date_of_birth', 'gender', 'phone_number', 'address']
                    },
                    {
                        'path': 'profiles/{id}/',
                        'methods': ['GET', 'PUT', 'PATCH', 'DELETE'],
                        'description': 'Retrieve, update, or delete patient profile',
                        'authentication': True,
                        'parameters': ['id']
                    },
                    {
                        'path': 'emergency-contacts/',
                        'methods': ['GET', 'POST'],
                        'description': 'Manage patient emergency contacts',
                        'authentication': True,
                        'parameters': ['patient', 'name', 'relationship', 'phone_number']
                    }
                ]
            },
            'Doctor Management': {
                'base_url': '/api/doctors/',
                'description': 'Doctor profiles, specializations, and availability',
                'endpoints': [
                    {
                        'path': 'profiles/',
                        'methods': ['GET', 'POST'],
                        'description': 'List and create doctor profiles',
                        'authentication': True,
                        'parameters': ['license_number', 'specialization', 'department']
                    },
                    {
                        'path': 'availability/',
                        'methods': ['GET', 'POST'],
                        'description': 'Manage doctor availability schedules',
                        'authentication': True,
                        'parameters': ['doctor', 'day_of_week', 'start_time', 'end_time']
                    },
                    {
                        'path': 'specializations/',
                        'methods': ['GET'],
                        'description': 'List available medical specializations',
                        'authentication': True,
                        'parameters': []
                    }
                ]
            },
            'Appointment Scheduling': {
                'base_url': '/api/appointments/',
                'description': 'Appointment booking, scheduling, and management',
                'endpoints': [
                    {
                        'path': '',
                        'methods': ['GET', 'POST'],
                        'description': 'List and create appointments',
                        'authentication': True,
                        'parameters': ['doctor', 'patient', 'appointment_date', 'appointment_time']
                    },
                    {
                        'path': '{id}/',
                        'methods': ['GET', 'PUT', 'PATCH', 'DELETE'],
                        'description': 'Manage specific appointment',
                        'authentication': True,
                        'parameters': ['id', 'status', 'notes']
                    },
                    {
                        'path': 'availability/',
                        'methods': ['GET'],
                        'description': 'Check doctor availability for appointments',
                        'authentication': True,
                        'parameters': ['doctor', 'date']
                    }
                ]
            },
            'Medical Records': {
                'base_url': '/api/medical-records/',
                'description': 'Electronic health records, diagnoses, and treatments',
                'endpoints': [
                    {
                        'path': 'medical-histories/',
                        'methods': ['GET', 'POST'],
                        'description': 'Manage patient medical histories',
                        'authentication': True,
                        'parameters': ['patient', 'condition', 'diagnosis_date']
                    },
                    {
                        'path': 'prescriptions/',
                        'methods': ['GET', 'POST'],
                        'description': 'Manage patient prescriptions',
                        'authentication': True,
                        'parameters': ['patient', 'medication', 'dosage', 'frequency']
                    },
                    {
                        'path': 'vitals/',
                        'methods': ['GET', 'POST'],
                        'description': 'Record and track patient vital signs',
                        'authentication': True,
                        'parameters': ['patient', 'blood_pressure', 'heart_rate', 'temperature']
                    }
                ]
            },
            'Billing & Invoicing': {
                'base_url': '/api/billing/',
                'description': 'Invoice generation, payment processing, and insurance claims',
                'endpoints': [
                    {
                        'path': 'invoices/',
                        'methods': ['GET', 'POST'],
                        'description': 'Manage patient invoices',
                        'authentication': True,
                        'parameters': ['patient', 'amount', 'due_date', 'services']
                    },
                    {
                        'path': 'payments/',
                        'methods': ['GET', 'POST'],
                        'description': 'Process and track payments',
                        'authentication': True,
                        'parameters': ['invoice', 'amount', 'payment_method']
                    },
                    {
                        'path': 'insurance-claims/',
                        'methods': ['GET', 'POST'],
                        'description': 'Manage insurance claims',
                        'authentication': True,
                        'parameters': ['patient', 'insurance_provider', 'claim_amount']
                    }
                ]
            },
            'Notifications': {
                'base_url': '/api/notifications/',
                'description': 'Email, SMS, and push notifications',
                'endpoints': [
                    {
                        'path': 'email/',
                        'methods': ['GET', 'POST'],
                        'description': 'Manage email notifications',
                        'authentication': True,
                        'parameters': ['recipient', 'subject', 'template', 'variables']
                    },
                    {
                        'path': 'sms/',
                        'methods': ['GET', 'POST'],
                        'description': 'Manage SMS notifications',
                        'authentication': True,
                        'parameters': ['recipient_phone', 'message', 'template']
                    },
                    {
                        'path': 'templates/',
                        'methods': ['GET', 'POST'],
                        'description': 'Manage notification templates',
                        'authentication': True,
                        'parameters': ['name', 'template_type', 'content']
                    }
                ]
            },
            'Hospital Infrastructure': {
                'base_url': '/api/infrastructure/',
                'description': 'Hospital buildings, rooms, and equipment management',
                'endpoints': [
                    {
                        'path': 'buildings/',
                        'methods': ['GET', 'POST'],
                        'description': 'Manage hospital buildings',
                        'authentication': True,
                        'parameters': ['name', 'code', 'address', 'floors']
                    },
                    {
                        'path': 'rooms/',
                        'methods': ['GET', 'POST'],
                        'description': 'Manage hospital rooms',
                        'authentication': True,
                        'parameters': ['room_number', 'floor', 'room_type', 'status']
                    },
                    {
                        'path': 'equipment/',
                        'methods': ['GET', 'POST'],
                        'description': 'Manage hospital equipment',
                        'authentication': True,
                        'parameters': ['name', 'category', 'serial_number', 'status']
                    }
                ]
            }
        }
        
        documentation['modules'] = modules
        return documentation
    
    def generate_authentication_guide(self):
        """
        Generate authentication guide
        """
        return {
            'title': 'Authentication Guide',
            'description': 'How to authenticate with the Hospital Management System API',
            'steps': [
                {
                    'step': 1,
                    'title': 'Register or Login',
                    'description': 'Create an account or login to get JWT tokens',
                    'endpoints': ['/api/accounts/register/', '/api/accounts/login/']
                },
                {
                    'step': 2,
                    'title': 'Use Access Token',
                    'description': 'Include the access token in the Authorization header',
                    'example': 'Authorization: Bearer <your-access-token>'
                },
                {
                    'step': 3,
                    'title': 'Refresh Token',
                    'description': 'Use refresh token to get new access token when expired',
                    'endpoint': '/api/accounts/token/refresh/'
                }
            ],
            'token_types': {
                'access_token': {
                    'purpose': 'API authentication',
                    'lifetime': '60 minutes',
                    'usage': 'Include in Authorization header for API requests'
                },
                'refresh_token': {
                    'purpose': 'Token renewal',
                    'lifetime': '24 hours',
                    'usage': 'Use to get new access token when expired'
                }
            }
        }
    
    def export_documentation(self, format='json'):
        """
        Export documentation in specified format
        """
        docs = {
            'api_info': self.generate_endpoint_documentation(),
            'authentication_guide': self.generate_authentication_guide()
        }
        
        if format == 'json':
            return json.dumps(docs, indent=2)
        elif format == 'yaml':
            return yaml.dump(docs, default_flow_style=False)
        else:
            return docs


def generate_api_docs():
    """
    Generate and save API documentation
    """
    generator = HospitalAPIDocumentationGenerator()
    
    # Generate documentation
    docs_json = generator.export_documentation('json')

    # Save to file
    docs_dir = os.path.join(settings.BASE_DIR, 'docs', 'generated')
    os.makedirs(docs_dir, exist_ok=True)

    with open(os.path.join(docs_dir, 'api_documentation.json'), 'w') as f:
        f.write(docs_json)
    
    print("API documentation generated successfully!")
    return docs_json


if __name__ == '__main__':
    # Setup Django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hospital_backend.settings')
    django.setup()
    
    generate_api_docs()
