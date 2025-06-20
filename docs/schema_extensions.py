"""
Custom schema extensions for drf-spectacular
"""
from drf_spectacular.extensions import OpenApiViewExtension
from drf_spectacular.utils import extend_schema
from drf_spectacular.openapi import AutoSchema


class CustomAutoSchema(AutoSchema):
    """
    Custom schema class to enhance API documentation
    """
    
    def get_operation_id(self):
        """
        Generate more descriptive operation IDs
        """
        operation_id = super().get_operation_id()
        
        # Add module prefix for better organization
        if hasattr(self.view, '__module__'):
            module_parts = self.view.__module__.split('.')
            if len(module_parts) >= 2:
                app_name = module_parts[-2]  # Get app name
                operation_id = f"{app_name}_{operation_id}"
        
        return operation_id
    
    def get_tags(self):
        """
        Generate tags based on view class and app
        """
        tags = super().get_tags()
        
        if not tags and hasattr(self.view, '__module__'):
            module_parts = self.view.__module__.split('.')
            if len(module_parts) >= 2:
                app_name = module_parts[-2].replace('_', ' ').title()
                tags = [app_name]
        
        return tags


class AuthenticationViewExtension(OpenApiViewExtension):
    """
    Custom extension for authentication views
    """
    target_component = 'accounts.views'
    
    def view_replacement(self):
        """
        Add custom documentation for authentication views
        """
        return extend_schema(
            summary="Authentication endpoint",
            description="Handle user authentication and token management",
            tags=['Authentication']
        )


class PatientViewExtension(OpenApiViewExtension):
    """
    Custom extension for patient management views
    """
    target_component = 'patients.views'
    
    def view_replacement(self):
        return extend_schema(
            summary="Patient management endpoint",
            description="Manage patient profiles, medical information, and records",
            tags=['Patient Management']
        )


class DoctorViewExtension(OpenApiViewExtension):
    """
    Custom extension for doctor management views
    """
    target_component = 'doctors.views'
    
    def view_replacement(self):
        return extend_schema(
            summary="Doctor management endpoint",
            description="Manage doctor profiles, specializations, and availability",
            tags=['Doctor Management']
        )


class AppointmentViewExtension(OpenApiViewExtension):
    """
    Custom extension for appointment views
    """
    target_component = 'appointments.views'
    
    def view_replacement(self):
        return extend_schema(
            summary="Appointment management endpoint",
            description="Handle appointment booking, scheduling, and management",
            tags=['Appointment Management']
        )


class MedicalRecordsViewExtension(OpenApiViewExtension):
    """
    Custom extension for medical records views
    """
    target_component = 'medical_records.views'
    
    def view_replacement(self):
        return extend_schema(
            summary="Medical records endpoint",
            description="Manage electronic health records, diagnoses, and treatments",
            tags=['Medical Records Management']
        )


class BillingViewExtension(OpenApiViewExtension):
    """
    Custom extension for billing views
    """
    target_component = 'billing.views'
    
    def view_replacement(self):
        return extend_schema(
            summary="Billing and invoicing endpoint",
            description="Handle invoice generation, payments, and insurance claims",
            tags=['Billing & Financial Management']
        )


class NotificationViewExtension(OpenApiViewExtension):
    """
    Custom extension for notification views
    """
    target_component = 'notifications.views'
    
    def view_replacement(self):
        return extend_schema(
            summary="Notification management endpoint",
            description="Manage email, SMS, and push notifications",
            tags=['Notification Services']
        )


class InfrastructureViewExtension(OpenApiViewExtension):
    """
    Custom extension for infrastructure views
    """
    target_component = 'infrastructure.views'
    
    def view_replacement(self):
        return extend_schema(
            summary="Hospital infrastructure endpoint",
            description="Manage hospital buildings, rooms, and equipment",
            tags=['Hospital Infrastructure']
        )


# Common response examples for documentation
COMMON_RESPONSES = {
    'authentication_error': {
        'description': 'Authentication credentials were not provided or are invalid',
        'content': {
            'application/json': {
                'example': {
                    'detail': 'Authentication credentials were not provided.'
                }
            }
        }
    },
    'permission_error': {
        'description': 'User does not have permission to perform this action',
        'content': {
            'application/json': {
                'example': {
                    'detail': 'You do not have permission to perform this action.'
                }
            }
        }
    },
    'validation_error': {
        'description': 'Invalid input data',
        'content': {
            'application/json': {
                'example': {
                    'field_name': ['This field is required.'],
                    'email': ['Enter a valid email address.']
                }
            }
        }
    },
    'not_found': {
        'description': 'Resource not found',
        'content': {
            'application/json': {
                'example': {
                    'detail': 'Not found.'
                }
            }
        }
    },
    'server_error': {
        'description': 'Internal server error',
        'content': {
            'application/json': {
                'example': {
                    'detail': 'A server error occurred.'
                }
            }
        }
    }
}


# Common parameter examples
COMMON_PARAMETERS = {
    'page': {
        'name': 'page',
        'in': 'query',
        'description': 'Page number for pagination',
        'required': False,
        'schema': {
            'type': 'integer',
            'minimum': 1,
            'default': 1
        }
    },
    'page_size': {
        'name': 'page_size',
        'in': 'query',
        'description': 'Number of results per page',
        'required': False,
        'schema': {
            'type': 'integer',
            'minimum': 1,
            'maximum': 100,
            'default': 20
        }
    },
    'search': {
        'name': 'search',
        'in': 'query',
        'description': 'Search term to filter results',
        'required': False,
        'schema': {
            'type': 'string'
        }
    },
    'ordering': {
        'name': 'ordering',
        'in': 'query',
        'description': 'Field to order results by. Prefix with "-" for descending order.',
        'required': False,
        'schema': {
            'type': 'string'
        }
    }
}
