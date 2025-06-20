"""
Comprehensive input validation and sanitization for Hospital Management System
Prevents injection attacks and ensures data integrity
"""
import re
import html
import bleach
from datetime import datetime, date
from decimal import Decimal, InvalidOperation
from django.core.exceptions import ValidationError
from django.core.validators import validate_email, RegexValidator
from django.utils.translation import gettext as _


class InputSanitizer:
    """
    Comprehensive input sanitization class
    """
    
    # Allowed HTML tags for rich text fields
    ALLOWED_TAGS = [
        'p', 'br', 'strong', 'em', 'u', 'ol', 'ul', 'li',
        'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'blockquote'
    ]
    
    # Allowed HTML attributes
    ALLOWED_ATTRIBUTES = {
        '*': ['class'],
        'a': ['href', 'title'],
        'img': ['src', 'alt', 'width', 'height'],
    }
    
    @staticmethod
    def sanitize_html(value):
        """
        Sanitize HTML content to prevent XSS attacks
        """
        if not value:
            return value
        
        # Use bleach to clean HTML
        cleaned = bleach.clean(
            value,
            tags=InputSanitizer.ALLOWED_TAGS,
            attributes=InputSanitizer.ALLOWED_ATTRIBUTES,
            strip=True
        )
        
        return cleaned
    
    @staticmethod
    def sanitize_text(value):
        """
        Sanitize plain text input
        """
        if not value:
            return value
        
        # Remove null bytes
        value = value.replace('\x00', '')
        
        # Escape HTML entities
        value = html.escape(value)
        
        # Remove control characters except newlines and tabs
        value = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', value)
        
        return value.strip()
    
    @staticmethod
    def sanitize_sql_input(value):
        """
        Sanitize input to prevent SQL injection
        """
        if not value:
            return value
        
        # Remove SQL injection patterns
        sql_patterns = [
            r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION)\b)",
            r"(--|#|/\*|\*/)",
            r"(\b(OR|AND)\s+\d+\s*=\s*\d+)",
            r"(\b(OR|AND)\s+['\"].*['\"])",
            r"(;|\||&)",
        ]
        
        for pattern in sql_patterns:
            value = re.sub(pattern, '', value, flags=re.IGNORECASE)
        
        return value.strip()
    
    @staticmethod
    def sanitize_filename(value):
        """
        Sanitize filename to prevent directory traversal
        """
        if not value:
            return value
        
        # Remove path separators and dangerous characters
        value = re.sub(r'[<>:"/\\|?*]', '', value)
        value = re.sub(r'\.\.', '', value)
        value = value.replace('\x00', '')
        
        # Remove leading/trailing dots and spaces
        value = value.strip('. ')
        
        # Limit length
        if len(value) > 255:
            name, ext = value.rsplit('.', 1) if '.' in value else (value, '')
            value = name[:250] + ('.' + ext if ext else '')
        
        return value
    
    @staticmethod
    def sanitize_phone_number(value):
        """
        Sanitize and format phone number
        """
        if not value:
            return value
        
        # Remove all non-digit characters except + at the beginning
        cleaned = re.sub(r'[^\d+]', '', value)
        
        # Ensure + is only at the beginning
        if '+' in cleaned:
            parts = cleaned.split('+')
            cleaned = '+' + ''.join(parts[1:])
        
        return cleaned
    
    @staticmethod
    def sanitize_medical_id(value):
        """
        Sanitize medical ID numbers
        """
        if not value:
            return value
        
        # Remove all non-alphanumeric characters
        cleaned = re.sub(r'[^a-zA-Z0-9]', '', value)
        
        return cleaned.upper()


class MedicalDataValidator:
    """
    Specialized validators for medical data
    """
    
    @staticmethod
    def validate_blood_type(value):
        """
        Validate blood type
        """
        valid_blood_types = [
            'A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-'
        ]
        
        if value not in valid_blood_types:
            raise ValidationError(
                _('Invalid blood type. Must be one of: %(types)s'),
                params={'types': ', '.join(valid_blood_types)},
                code='invalid_blood_type'
            )
    
    @staticmethod
    def validate_medical_record_number(value):
        """
        Validate medical record number format
        """
        # Medical record number should be alphanumeric, 6-20 characters
        if not re.match(r'^[A-Z0-9]{6,20}$', value):
            raise ValidationError(
                _('Medical record number must be 6-20 alphanumeric characters'),
                code='invalid_medical_record_number'
            )
    
    @staticmethod
    def validate_license_number(value):
        """
        Validate medical license number
        """
        # License number should be alphanumeric, 6-15 characters
        if not re.match(r'^[A-Z0-9]{6,15}$', value):
            raise ValidationError(
                _('License number must be 6-15 alphanumeric characters'),
                code='invalid_license_number'
            )
    
    @staticmethod
    def validate_age(value):
        """
        Validate age is reasonable for medical context
        """
        if not isinstance(value, int) or value < 0 or value > 150:
            raise ValidationError(
                _('Age must be between 0 and 150 years'),
                code='invalid_age'
            )
    
    @staticmethod
    def validate_weight(value):
        """
        Validate weight in kg
        """
        try:
            weight = float(value)
            if weight < 0.1 or weight > 1000:
                raise ValidationError(
                    _('Weight must be between 0.1 and 1000 kg'),
                    code='invalid_weight'
                )
        except (ValueError, TypeError):
            raise ValidationError(
                _('Weight must be a valid number'),
                code='invalid_weight_format'
            )
    
    @staticmethod
    def validate_height(value):
        """
        Validate height in cm
        """
        try:
            height = float(value)
            if height < 10 or height > 300:
                raise ValidationError(
                    _('Height must be between 10 and 300 cm'),
                    code='invalid_height'
                )
        except (ValueError, TypeError):
            raise ValidationError(
                _('Height must be a valid number'),
                code='invalid_height_format'
            )
    
    @staticmethod
    def validate_temperature(value):
        """
        Validate body temperature in Celsius
        """
        try:
            temp = float(value)
            if temp < 30 or temp > 45:
                raise ValidationError(
                    _('Temperature must be between 30 and 45 degrees Celsius'),
                    code='invalid_temperature'
                )
        except (ValueError, TypeError):
            raise ValidationError(
                _('Temperature must be a valid number'),
                code='invalid_temperature_format'
            )
    
    @staticmethod
    def validate_blood_pressure(systolic, diastolic):
        """
        Validate blood pressure readings
        """
        try:
            sys = int(systolic)
            dia = int(diastolic)
            
            if sys < 50 or sys > 300:
                raise ValidationError(
                    _('Systolic pressure must be between 50 and 300 mmHg'),
                    code='invalid_systolic'
                )
            
            if dia < 30 or dia > 200:
                raise ValidationError(
                    _('Diastolic pressure must be between 30 and 200 mmHg'),
                    code='invalid_diastolic'
                )
            
            if sys <= dia:
                raise ValidationError(
                    _('Systolic pressure must be higher than diastolic pressure'),
                    code='invalid_pressure_ratio'
                )
                
        except (ValueError, TypeError):
            raise ValidationError(
                _('Blood pressure values must be valid numbers'),
                code='invalid_pressure_format'
            )


class SecurityValidator:
    """
    Security-focused validators
    """
    
    @staticmethod
    def validate_no_script_tags(value):
        """
        Ensure no script tags in input
        """
        if '<script' in value.lower() or '</script>' in value.lower():
            raise ValidationError(
                _('Script tags are not allowed'),
                code='script_tags_detected'
            )
    
    @staticmethod
    def validate_no_sql_injection(value):
        """
        Check for SQL injection patterns
        """
        sql_patterns = [
            r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION)\b)",
            r"(--|#|/\*|\*/)",
            r"(\b(OR|AND)\s+\d+\s*=\s*\d+)",
            r"(\';|\")",
        ]
        
        for pattern in sql_patterns:
            if re.search(pattern, value, re.IGNORECASE):
                raise ValidationError(
                    _('Input contains potentially dangerous content'),
                    code='sql_injection_detected'
                )
    
    @staticmethod
    def validate_file_extension(filename, allowed_extensions):
        """
        Validate file extension
        """
        if not filename:
            return
        
        ext = filename.lower().split('.')[-1] if '.' in filename else ''
        
        if f'.{ext}' not in allowed_extensions:
            raise ValidationError(
                _('File type not allowed. Allowed types: %(types)s'),
                params={'types': ', '.join(allowed_extensions)},
                code='invalid_file_type'
            )
    
    @staticmethod
    def validate_file_size(file_size, max_size):
        """
        Validate file size
        """
        if file_size > max_size:
            max_mb = max_size / (1024 * 1024)
            raise ValidationError(
                _('File size too large. Maximum size: %(max)s MB'),
                params={'max': max_mb},
                code='file_too_large'
            )


class DataIntegrityValidator:
    """
    Validators for data integrity and consistency
    """
    
    @staticmethod
    def validate_date_not_future(value):
        """
        Ensure date is not in the future
        """
        if isinstance(value, str):
            try:
                value = datetime.strptime(value, '%Y-%m-%d').date()
            except ValueError:
                raise ValidationError(
                    _('Invalid date format. Use YYYY-MM-DD'),
                    code='invalid_date_format'
                )
        
        if value > date.today():
            raise ValidationError(
                _('Date cannot be in the future'),
                code='future_date'
            )
    
    @staticmethod
    def validate_birth_date(value):
        """
        Validate birth date is reasonable
        """
        if isinstance(value, str):
            try:
                value = datetime.strptime(value, '%Y-%m-%d').date()
            except ValueError:
                raise ValidationError(
                    _('Invalid date format. Use YYYY-MM-DD'),
                    code='invalid_date_format'
                )
        
        today = date.today()
        
        # Check if date is not in the future
        if value > today:
            raise ValidationError(
                _('Birth date cannot be in the future'),
                code='future_birth_date'
            )
        
        # Check if age is reasonable (not older than 150 years)
        age = today.year - value.year - ((today.month, today.day) < (value.month, value.day))
        if age > 150:
            raise ValidationError(
                _('Birth date indicates age over 150 years'),
                code='unrealistic_birth_date'
            )
    
    @staticmethod
    def validate_appointment_date(value):
        """
        Validate appointment date is reasonable
        """
        if isinstance(value, str):
            try:
                value = datetime.strptime(value, '%Y-%m-%d').date()
            except ValueError:
                raise ValidationError(
                    _('Invalid date format. Use YYYY-MM-DD'),
                    code='invalid_date_format'
                )
        
        today = date.today()
        
        # Appointments can't be more than 1 year in the past
        if value < today - timedelta(days=365):
            raise ValidationError(
                _('Appointment date cannot be more than 1 year in the past'),
                code='appointment_too_old'
            )
        
        # Appointments can't be more than 2 years in the future
        if value > today + timedelta(days=730):
            raise ValidationError(
                _('Appointment date cannot be more than 2 years in the future'),
                code='appointment_too_far'
            )
    
    @staticmethod
    def validate_positive_decimal(value):
        """
        Validate positive decimal value
        """
        try:
            decimal_value = Decimal(str(value))
            if decimal_value <= 0:
                raise ValidationError(
                    _('Value must be positive'),
                    code='negative_value'
                )
        except (InvalidOperation, ValueError):
            raise ValidationError(
                _('Invalid decimal value'),
                code='invalid_decimal'
            )


# Custom regex validators
phone_validator = RegexValidator(
    regex=r'^\+?1?\d{9,15}$',
    message=_('Phone number must be entered in the format: "+999999999". Up to 15 digits allowed.'),
    code='invalid_phone'
)

postal_code_validator = RegexValidator(
    regex=r'^\d{5}(-\d{4})?$',
    message=_('Postal code must be in format: 12345 or 12345-6789'),
    code='invalid_postal_code'
)

medical_id_validator = RegexValidator(
    regex=r'^[A-Z0-9]{6,20}$',
    message=_('Medical ID must be 6-20 alphanumeric characters'),
    code='invalid_medical_id'
)

# Comprehensive validation function
def validate_and_sanitize_input(value, field_type='text', **kwargs):
    """
    Comprehensive validation and sanitization function
    """
    if value is None:
        return value
    
    # Convert to string for processing
    str_value = str(value)
    
    # Security validation first
    SecurityValidator.validate_no_script_tags(str_value)
    SecurityValidator.validate_no_sql_injection(str_value)
    
    # Sanitize based on field type
    if field_type == 'html':
        return InputSanitizer.sanitize_html(str_value)
    elif field_type == 'filename':
        return InputSanitizer.sanitize_filename(str_value)
    elif field_type == 'phone':
        sanitized = InputSanitizer.sanitize_phone_number(str_value)
        phone_validator(sanitized)
        return sanitized
    elif field_type == 'medical_id':
        sanitized = InputSanitizer.sanitize_medical_id(str_value)
        medical_id_validator(sanitized)
        return sanitized
    else:
        return InputSanitizer.sanitize_text(str_value)
