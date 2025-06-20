"""
Comprehensive API Documentation with detailed examples and schemas
"""
from drf_spectacular.utils import (
    extend_schema, extend_schema_view, OpenApiExample, OpenApiParameter, OpenApiResponse
)
from drf_spectacular.types import OpenApiTypes
from rest_framework import status


# Common response examples
COMMON_EXAMPLES = {
    'authentication_error': OpenApiExample(
        'Authentication Error',
        summary='Authentication credentials not provided',
        description='Returned when no authentication token is provided',
        value={
            'detail': 'Authentication credentials were not provided.'
        },
        response_only=True,
        status_codes=[status.HTTP_401_UNAUTHORIZED]
    ),
    'permission_error': OpenApiExample(
        'Permission Denied',
        summary='Insufficient permissions',
        description='Returned when user lacks required permissions',
        value={
            'detail': 'You do not have permission to perform this action.'
        },
        response_only=True,
        status_codes=[status.HTTP_403_FORBIDDEN]
    ),
    'validation_error': OpenApiExample(
        'Validation Error',
        summary='Invalid input data',
        description='Returned when request data fails validation',
        value={
            'field_name': ['This field is required.'],
            'email': ['Enter a valid email address.'],
            'password': ['This password is too short.']
        },
        response_only=True,
        status_codes=[status.HTTP_400_BAD_REQUEST]
    ),
    'not_found': OpenApiExample(
        'Not Found',
        summary='Resource not found',
        description='Returned when requested resource does not exist',
        value={
            'detail': 'Not found.'
        },
        response_only=True,
        status_codes=[status.HTTP_404_NOT_FOUND]
    )
}

# Authentication examples
AUTH_EXAMPLES = {
    'register_request': OpenApiExample(
        'User Registration',
        summary='Register a new user account',
        description='Example request to register a new patient user',
        value={
            'username': 'john_doe',
            'email': 'john.doe@example.com',
            'password': 'SecurePass123!',
            'first_name': 'John',
            'last_name': 'Doe',
            'user_type': 'patient'
        },
        request_only=True
    ),
    'register_response': OpenApiExample(
        'Registration Success',
        summary='Successful user registration',
        description='Response after successful user registration',
        value={
            'id': 1,
            'username': 'john_doe',
            'email': 'john.doe@example.com',
            'first_name': 'John',
            'last_name': 'Doe',
            'user_type': 'patient',
            'is_active': True,
            'date_joined': '2025-06-19T10:30:00Z'
        },
        response_only=True,
        status_codes=[status.HTTP_201_CREATED]
    ),
    'login_request': OpenApiExample(
        'User Login',
        summary='Authenticate user credentials',
        description='Example login request with username and password',
        value={
            'username': 'john_doe',
            'password': 'SecurePass123!'
        },
        request_only=True
    ),
    'login_response': OpenApiExample(
        'Login Success',
        summary='Successful authentication',
        description='JWT tokens returned after successful login',
        value={
            'access': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNjI0NTQ2ODAwLCJpYXQiOjE2MjQ1NDMyMDAsImp0aSI6IjEyMzQ1Njc4OTAiLCJ1c2VyX2lkIjoxfQ.example',
            'refresh': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTYyNDYzMDAwMCwiaWF0IjoxNjI0NTQzMjAwLCJqdGkiOiIwOTg3NjU0MzIxIiwidXNlcl9pZCI6MX0.example',
            'user': {
                'id': 1,
                'username': 'john_doe',
                'email': 'john.doe@example.com',
                'first_name': 'John',
                'last_name': 'Doe',
                'user_type': 'patient'
            }
        },
        response_only=True,
        status_codes=[status.HTTP_200_OK]
    )
}

# Patient management examples
PATIENT_EXAMPLES = {
    'patient_profile_request': OpenApiExample(
        'Create Patient Profile',
        summary='Create a new patient profile',
        description='Example request to create a patient profile',
        value={
            'date_of_birth': '1990-05-15',
            'gender': 'male',
            'phone_number': '+1234567890',
            'address': '123 Main St, City, State 12345',
            'blood_type': 'O+',
            'allergies': ['Penicillin', 'Shellfish'],
            'emergency_contact_name': 'Jane Doe',
            'emergency_contact_phone': '+1234567891',
            'emergency_contact_relationship': 'spouse'
        },
        request_only=True
    ),
    'patient_profile_response': OpenApiExample(
        'Patient Profile Created',
        summary='Successfully created patient profile',
        description='Response after creating a patient profile',
        value={
            'id': 1,
            'user': {
                'id': 1,
                'username': 'john_doe',
                'first_name': 'John',
                'last_name': 'Doe',
                'email': 'john.doe@example.com'
            },
            'date_of_birth': '1990-05-15',
            'gender': 'male',
            'phone_number': '+1234567890',
            'address': '123 Main St, City, State 12345',
            'blood_type': 'O+',
            'allergies': ['Penicillin', 'Shellfish'],
            'emergency_contact_name': 'Jane Doe',
            'emergency_contact_phone': '+1234567891',
            'emergency_contact_relationship': 'spouse',
            'created_at': '2025-06-19T10:30:00Z',
            'updated_at': '2025-06-19T10:30:00Z'
        },
        response_only=True,
        status_codes=[status.HTTP_201_CREATED]
    )
}

# Appointment examples
APPOINTMENT_EXAMPLES = {
    'appointment_request': OpenApiExample(
        'Book Appointment',
        summary='Book a new appointment',
        description='Example request to book an appointment with a doctor',
        value={
            'doctor': 1,
            'appointment_date': '2025-06-25',
            'appointment_time': '14:30:00',
            'appointment_type': 'consultation',
            'reason': 'Regular checkup',
            'notes': 'Patient reports feeling well, routine examination'
        },
        request_only=True
    ),
    'appointment_response': OpenApiExample(
        'Appointment Booked',
        summary='Successfully booked appointment',
        description='Response after booking an appointment',
        value={
            'id': 1,
            'patient': {
                'id': 1,
                'user': {
                    'first_name': 'John',
                    'last_name': 'Doe'
                }
            },
            'doctor': {
                'id': 1,
                'user': {
                    'first_name': 'Dr. Sarah',
                    'last_name': 'Smith'
                },
                'specialization': 'General Medicine'
            },
            'appointment_date': '2025-06-25',
            'appointment_time': '14:30:00',
            'appointment_type': 'consultation',
            'status': 'scheduled',
            'reason': 'Regular checkup',
            'notes': 'Patient reports feeling well, routine examination',
            'created_at': '2025-06-19T10:30:00Z',
            'updated_at': '2025-06-19T10:30:00Z'
        },
        response_only=True,
        status_codes=[status.HTTP_201_CREATED]
    ),
    'availability_response': OpenApiExample(
        'Doctor Availability',
        summary='Available appointment slots',
        description='Available time slots for a specific doctor on a given date',
        value={
            'doctor_id': 1,
            'doctor_name': 'Dr. Sarah Smith',
            'date': '2025-06-25',
            'available_slots': [
                {
                    'time': '09:00:00',
                    'duration': 30,
                    'available': True
                },
                {
                    'time': '09:30:00',
                    'duration': 30,
                    'available': True
                },
                {
                    'time': '10:00:00',
                    'duration': 30,
                    'available': False,
                    'reason': 'Already booked'
                },
                {
                    'time': '14:30:00',
                    'duration': 30,
                    'available': True
                }
            ],
            'total_slots': 16,
            'available_count': 14,
            'booked_count': 2
        },
        response_only=True,
        status_codes=[status.HTTP_200_OK]
    )
}

# Notification examples
NOTIFICATION_EXAMPLES = {
    'email_notification_request': OpenApiExample(
        'Send Email Notification',
        summary='Send an email notification',
        description='Example request to send an email notification',
        value={
            'recipient_email': 'john.doe@example.com',
            'template_type': 'appointment_reminder',
            'template_variables': {
                'patient_name': 'John Doe',
                'doctor_name': 'Dr. Sarah Smith',
                'appointment_date': 'June 25, 2025',
                'appointment_time': '2:30 PM',
                'hospital_name': 'City Hospital'
            },
            'priority': 'normal',
            'scheduled_at': '2025-06-24T09:00:00Z'
        },
        request_only=True
    ),
    'notification_response': OpenApiExample(
        'Notification Sent',
        summary='Successfully sent notification',
        description='Response after sending a notification',
        value={
            'id': '12345678-1234-1234-1234-123456789012',
            'recipient_email': 'john.doe@example.com',
            'template_type': 'appointment_reminder',
            'status': 'sent',
            'sent_at': '2025-06-19T10:30:00Z',
            'provider': 'SMTP',
            'provider_message_id': 'smtp_msg_001'
        },
        response_only=True,
        status_codes=[status.HTTP_201_CREATED]
    )
}

# Common parameters
COMMON_PARAMETERS = [
    OpenApiParameter(
        name='page',
        type=OpenApiTypes.INT,
        location=OpenApiParameter.QUERY,
        description='Page number for pagination',
        default=1
    ),
    OpenApiParameter(
        name='page_size',
        type=OpenApiTypes.INT,
        location=OpenApiParameter.QUERY,
        description='Number of results per page (max 100)',
        default=20
    ),
    OpenApiParameter(
        name='search',
        type=OpenApiTypes.STR,
        location=OpenApiParameter.QUERY,
        description='Search term to filter results'
    ),
    OpenApiParameter(
        name='ordering',
        type=OpenApiTypes.STR,
        location=OpenApiParameter.QUERY,
        description='Field to order results by. Prefix with "-" for descending order.'
    )
]

# Response schemas
COMMON_RESPONSES = {
    200: OpenApiResponse(
        description='Success',
        examples=[
            OpenApiExample(
                'Success Response',
                value={'message': 'Operation completed successfully'}
            )
        ]
    ),
    400: OpenApiResponse(
        description='Bad Request',
        examples=[COMMON_EXAMPLES['validation_error']]
    ),
    401: OpenApiResponse(
        description='Unauthorized',
        examples=[COMMON_EXAMPLES['authentication_error']]
    ),
    403: OpenApiResponse(
        description='Forbidden',
        examples=[COMMON_EXAMPLES['permission_error']]
    ),
    404: OpenApiResponse(
        description='Not Found',
        examples=[COMMON_EXAMPLES['not_found']]
    ),
    500: OpenApiResponse(
        description='Internal Server Error',
        examples=[
            OpenApiExample(
                'Server Error',
                value={'detail': 'A server error occurred.'}
            )
        ]
    )
}


def comprehensive_api_docs(
    summary: str,
    description: str,
    tags: list = None,
    request_examples: list = None,
    response_examples: list = None,
    parameters: list = None,
    responses: dict = None
):
    """
    Decorator to apply comprehensive API documentation to views
    """
    def decorator(view_func_or_class):
        # Combine provided examples with common examples
        all_examples = []
        if request_examples:
            all_examples.extend(request_examples)
        if response_examples:
            all_examples.extend(response_examples)

        # Add common error examples
        all_examples.extend([
            COMMON_EXAMPLES['authentication_error'],
            COMMON_EXAMPLES['permission_error'],
            COMMON_EXAMPLES['validation_error'],
            COMMON_EXAMPLES['not_found']
        ])

        # Combine provided parameters with common parameters
        all_parameters = COMMON_PARAMETERS.copy()
        if parameters:
            all_parameters.extend(parameters)

        # Use provided responses or default common responses
        final_responses = responses or COMMON_RESPONSES

        return extend_schema(
            summary=summary,
            description=description,
            tags=tags or ['API'],
            examples=all_examples,
            parameters=all_parameters,
            responses=final_responses
        )(view_func_or_class)

    return decorator


def auth_api_docs(summary: str, description: str):
    """
    Specialized decorator for authentication endpoints
    """
    return comprehensive_api_docs(
        summary=summary,
        description=description,
        tags=['Authentication'],
        request_examples=[AUTH_EXAMPLES['login_request'], AUTH_EXAMPLES['register_request']],
        response_examples=[AUTH_EXAMPLES['login_response'], AUTH_EXAMPLES['register_response']]
    )


def patient_api_docs(summary: str, description: str):
    """
    Specialized decorator for patient management endpoints
    """
    return comprehensive_api_docs(
        summary=summary,
        description=description,
        tags=['Patient Management'],
        request_examples=[PATIENT_EXAMPLES['patient_profile_request']],
        response_examples=[PATIENT_EXAMPLES['patient_profile_response']]
    )


def appointment_api_docs(summary: str, description: str):
    """
    Specialized decorator for appointment endpoints
    """
    return comprehensive_api_docs(
        summary=summary,
        description=description,
        tags=['Appointment Scheduling'],
        request_examples=[APPOINTMENT_EXAMPLES['appointment_request']],
        response_examples=[
            APPOINTMENT_EXAMPLES['appointment_response'],
            APPOINTMENT_EXAMPLES['availability_response']
        ]
    )


def notification_api_docs(summary: str, description: str):
    """
    Specialized decorator for notification endpoints
    """
    return comprehensive_api_docs(
        summary=summary,
        description=description,
        tags=['Notifications'],
        request_examples=[NOTIFICATION_EXAMPLES['email_notification_request']],
        response_examples=[NOTIFICATION_EXAMPLES['notification_response']]
    )
