# Hospital Management System API Documentation

## Overview

The Hospital Management System API provides comprehensive endpoints for managing all aspects of a healthcare facility, from patient registration to billing and notifications.

## API Documentation Access

- **Swagger UI**: http://127.0.0.1:8000/api/docs/
- **ReDoc**: http://127.0.0.1:8000/api/redoc/
- **OpenAPI Schema**: http://127.0.0.1:8000/api/schema/

## Authentication

The API uses JWT (JSON Web Token) authentication. All endpoints except registration and login require authentication.

### Getting Started

1. **Register a new account**:
   ```
   POST /api/accounts/register/
   ```

2. **Login to get tokens**:
   ```
   POST /api/accounts/login/
   ```

3. **Use access token in requests**:
   ```
   Authorization: Bearer <your-access-token>
   ```

### Token Types

- **Access Token**: Used for API authentication (60 minutes lifetime)
- **Refresh Token**: Used to get new access tokens (24 hours lifetime)

## API Modules

### 1. Authentication & User Management (`/api/accounts/`)
- User registration and login
- Profile management
- Password changes
- Token refresh

**Key Endpoints:**
- `POST /api/accounts/register/` - Register new user
- `POST /api/accounts/login/` - User authentication
- `GET /api/accounts/profile/` - Get user profile
- `POST /api/accounts/change-password/` - Change password

### 2. Patient Management (`/api/patients/`)
- Patient profile creation and management
- Medical information tracking
- Emergency contact management

**Key Endpoints:**
- `GET/POST /api/patients/profiles/` - List/create patient profiles
- `GET/PUT/PATCH/DELETE /api/patients/profiles/{id}/` - Manage specific patient
- `GET/POST /api/patients/emergency-contacts/` - Emergency contacts

### 3. Doctor Management (`/api/doctors/`)
- Doctor profile management
- Specialization tracking
- Availability scheduling

**Key Endpoints:**
- `GET/POST /api/doctors/profiles/` - List/create doctor profiles
- `GET/POST /api/doctors/availability/` - Manage availability
- `GET /api/doctors/specializations/` - List specializations

### 4. Appointment Scheduling (`/api/appointments/`)
- Appointment booking and management
- Availability checking
- Status tracking

**Key Endpoints:**
- `GET/POST /api/appointments/` - List/create appointments
- `GET/PUT/PATCH/DELETE /api/appointments/{id}/` - Manage appointments
- `GET /api/appointments/availability/` - Check availability

### 5. Medical Records (`/api/medical-records/`)
- Electronic health records
- Medical history tracking
- Prescription management
- Vital signs recording

**Key Endpoints:**
- `GET/POST /api/medical-records/medical-histories/` - Medical histories
- `GET/POST /api/medical-records/prescriptions/` - Prescriptions
- `GET/POST /api/medical-records/vitals/` - Vital signs

### 6. Billing & Invoicing (`/api/billing/`)
- Invoice generation and management
- Payment processing
- Insurance claim handling

**Key Endpoints:**
- `GET/POST /api/billing/invoices/` - Manage invoices
- `GET/POST /api/billing/payments/` - Process payments
- `GET/POST /api/billing/insurance-claims/` - Insurance claims

### 7. Notifications (`/api/notifications/`)
- Email, SMS, and push notifications
- Template management
- Notification scheduling and analytics

**Key Endpoints:**
- `GET/POST /api/notifications/email/` - Email notifications
- `GET/POST /api/notifications/sms/` - SMS notifications
- `GET/POST /api/notifications/templates/` - Template management

### 8. Hospital Infrastructure (`/api/infrastructure/`)
- Building and room management
- Equipment tracking
- Facility organization

**Key Endpoints:**
- `GET/POST /api/infrastructure/buildings/` - Manage buildings
- `GET/POST /api/infrastructure/rooms/` - Manage rooms
- `GET/POST /api/infrastructure/equipment/` - Manage equipment

## Common Features

### Pagination
All list endpoints support pagination:
- `page`: Page number (default: 1)
- `page_size`: Results per page (default: 20, max: 100)

### Filtering and Search
Most endpoints support:
- `search`: Search term for text fields
- `ordering`: Sort by field (prefix with `-` for descending)
- Various field-specific filters

### Response Format
All responses follow consistent JSON format:
```json
{
  "count": 100,
  "next": "http://api/endpoint/?page=2",
  "previous": null,
  "results": [...]
}
```

## Error Handling

### Common HTTP Status Codes
- `200 OK`: Success
- `201 Created`: Resource created
- `400 Bad Request`: Invalid input data
- `401 Unauthorized`: Authentication required
- `403 Forbidden`: Insufficient permissions
- `404 Not Found`: Resource not found
- `500 Internal Server Error`: Server error

### Error Response Format
```json
{
  "detail": "Error message",
  "field_name": ["Field-specific error"]
}
```

## Rate Limiting
- Authentication endpoints: 10 requests per minute
- General API: 100 requests per minute
- File uploads: 5 requests per minute

## Data Formats
- **Dates**: ISO 8601 format (`YYYY-MM-DD`)
- **Times**: 24-hour format (`HH:MM:SS`)
- **Datetimes**: ISO 8601 with timezone (`YYYY-MM-DDTHH:MM:SSZ`)
- **Phone numbers**: International format (`+1234567890`)

## Example Workflows

### 1. Patient Registration and Appointment Booking
```
1. POST /api/accounts/register/ (patient registration)
2. POST /api/accounts/login/ (get tokens)
3. POST /api/patients/profiles/ (create patient profile)
4. GET /api/doctors/profiles/ (find available doctors)
5. GET /api/appointments/availability/ (check doctor availability)
6. POST /api/appointments/ (book appointment)
```

### 2. Medical Record Management
```
1. GET /api/patients/profiles/ (find patient)
2. POST /api/medical-records/vitals/ (record vital signs)
3. POST /api/medical-records/medical-histories/ (add medical history)
4. POST /api/medical-records/prescriptions/ (create prescription)
```

### 3. Billing Process
```
1. GET /api/appointments/ (find completed appointments)
2. POST /api/billing/invoices/ (generate invoice)
3. POST /api/billing/payments/ (process payment)
4. POST /api/notifications/email/ (send receipt)
```

## Support and Contact
- API Support: api-support@hospital.com
- Documentation: https://docs.hospital.com
- Status Page: https://status.hospital.com

## Version Information
- **API Version**: 1.0.0
- **Last Updated**: June 19, 2025
- **OpenAPI Version**: 3.0.3
- **Framework**: Django REST Framework with drf-spectacular
