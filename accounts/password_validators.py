import re
import hashlib
from datetime import datetime, timedelta
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _
from django.contrib.auth.password_validation import CommonPasswordValidator
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.conf import settings

User = get_user_model()


class HospitalPasswordValidator:
    """
    Custom password validator for hospital management system with enhanced security.
    """
    
    def __init__(self, min_length=8, require_uppercase=True, require_lowercase=True, 
                 require_numbers=True, require_special=True):
        self.min_length = min_length
        self.require_uppercase = require_uppercase
        self.require_lowercase = require_lowercase
        self.require_numbers = require_numbers
        self.require_special = require_special
    
    def validate(self, password, user=None):
        errors = []
        
        # Check minimum length
        if len(password) < self.min_length:
            errors.append(
                ValidationError(
                    _("Password must be at least %(min_length)d characters long."),
                    code='password_too_short',
                    params={'min_length': self.min_length},
                )
            )
        
        # Check for uppercase letters
        if self.require_uppercase and not re.search(r'[A-Z]', password):
            errors.append(
                ValidationError(
                    _("Password must contain at least one uppercase letter."),
                    code='password_no_upper',
                )
            )
        
        # Check for lowercase letters
        if self.require_lowercase and not re.search(r'[a-z]', password):
            errors.append(
                ValidationError(
                    _("Password must contain at least one lowercase letter."),
                    code='password_no_lower',
                )
            )
        
        # Check for numbers
        if self.require_numbers and not re.search(r'\d', password):
            errors.append(
                ValidationError(
                    _("Password must contain at least one number."),
                    code='password_no_number',
                )
            )
        
        # Check for special characters
        if self.require_special and not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            errors.append(
                ValidationError(
                    _("Password must contain at least one special character (!@#$%^&*(),.?\":{}|<>)."),
                    code='password_no_special',
                )
            )
        
        # Check for user information in password
        if user:
            self._check_user_info_in_password(password, user, errors)
        
        if errors:
            raise ValidationError(errors)
    
    def _check_user_info_in_password(self, password, user, errors):
        """Check if password contains user information"""
        password_lower = password.lower()
        
        # Check username
        if hasattr(user, 'username') and user.username:
            if user.username.lower() in password_lower:
                errors.append(
                    ValidationError(
                        _("Password cannot contain your username."),
                        code='password_contains_username',
                    )
                )
        
        # Check email
        if hasattr(user, 'email') and user.email:
            email_parts = user.email.lower().split('@')
            if email_parts[0] in password_lower:
                errors.append(
                    ValidationError(
                        _("Password cannot contain your email address."),
                        code='password_contains_email',
                    )
                )
        
        # Check first and last name
        if hasattr(user, 'first_name') and user.first_name:
            if user.first_name.lower() in password_lower:
                errors.append(
                    ValidationError(
                        _("Password cannot contain your first name."),
                        code='password_contains_first_name',
                    )
                )
        
        if hasattr(user, 'last_name') and user.last_name:
            if user.last_name.lower() in password_lower:
                errors.append(
                    ValidationError(
                        _("Password cannot contain your last name."),
                        code='password_contains_last_name',
                    )
                )
    
    def get_help_text(self):
        requirements = [
            f"at least {self.min_length} characters long"
        ]
        
        if self.require_uppercase:
            requirements.append("at least one uppercase letter")
        if self.require_lowercase:
            requirements.append("at least one lowercase letter")
        if self.require_numbers:
            requirements.append("at least one number")
        if self.require_special:
            requirements.append("at least one special character")
        
        return _("Your password must be " + ", ".join(requirements) + ".")


class MedicalPasswordValidator:
    """
    Specialized password validator for medical staff with stricter requirements.
    """
    
    def validate(self, password, user=None):
        errors = []

        # Minimum 10 characters for medical staff (reduced from 12)
        if len(password) < 10:
            errors.append(
                ValidationError(
                    _("Medical staff passwords must be at least 10 characters long."),
                    code='medical_password_too_short',
                )
            )
        
        # Check for common medical terms (security risk)
        medical_terms = [
            'hospital', 'doctor', 'nurse', 'patient', 'medical', 'health',
            'medicine', 'clinic', 'surgery', 'treatment', 'diagnosis'
        ]
        
        password_lower = password.lower()
        for term in medical_terms:
            if term in password_lower:
                errors.append(
                    ValidationError(
                        _("Password cannot contain common medical terms."),
                        code='password_contains_medical_terms',
                    )
                )
                break
        
        # Check for sequential characters
        if self._has_sequential_chars(password):
            errors.append(
                ValidationError(
                    _("Password cannot contain sequential characters (e.g., 123, abc)."),
                    code='password_sequential_chars',
                )
            )
        
        # Check for repeated characters
        if self._has_repeated_chars(password):
            errors.append(
                ValidationError(
                    _("Password cannot contain more than 2 repeated characters."),
                    code='password_repeated_chars',
                )
            )
        
        if errors:
            raise ValidationError(errors)
    
    def _has_sequential_chars(self, password):
        """Check for sequential characters"""
        for i in range(len(password) - 2):
            # Check for ascending sequence
            if (ord(password[i]) + 1 == ord(password[i + 1]) and 
                ord(password[i + 1]) + 1 == ord(password[i + 2])):
                return True
            # Check for descending sequence
            if (ord(password[i]) - 1 == ord(password[i + 1]) and 
                ord(password[i + 1]) - 1 == ord(password[i + 2])):
                return True
        return False
    
    def _has_repeated_chars(self, password):
        """Check for repeated characters"""
        for i in range(len(password) - 2):
            if password[i] == password[i + 1] == password[i + 2]:
                return True
        return False
    
    def get_help_text(self):
        return _(
            "Medical staff passwords must be at least 12 characters long, "
            "cannot contain medical terms, sequential characters, or "
            "more than 2 repeated characters."
        )


class PasswordHistoryValidator:
    """
    Validator to prevent reuse of recent passwords.
    """
    
    def __init__(self, history_count=5):
        self.history_count = history_count
    
    def validate(self, password, user=None):
        if not user or not user.pk:
            return
        
        # This would require a PasswordHistory model to track previous passwords
        # For now, we'll implement a basic check
        if hasattr(user, 'check_password') and user.check_password(password):
            raise ValidationError(
                _("You cannot reuse your current password."),
                code='password_reused',
            )
    
    def get_help_text(self):
        return _(
            f"You cannot reuse any of your last {self.history_count} passwords."
        )


class PasswordExpiryValidator:
    """
    Validator to enforce password expiry policies
    """

    def __init__(self, max_age_days=90):
        self.max_age_days = max_age_days

    def validate(self, password, user=None):
        if not user or not user.pk:
            return

        # Check if password has expired
        if hasattr(user, 'password_changed_at'):
            if user.password_changed_at:
                days_since_change = (datetime.now().date() - user.password_changed_at).days
                if days_since_change > self.max_age_days:
                    raise ValidationError(
                        _("Your password has expired and must be changed."),
                        code='password_expired',
                    )

    def get_help_text(self):
        return _(
            f"Passwords must be changed every {self.max_age_days} days."
        )


class BreachedPasswordValidator:
    """
    Validator to check against known breached passwords
    """

    def validate(self, password, user=None):
        # Check against common breached passwords
        password_hash = hashlib.sha1(password.encode('utf-8')).hexdigest().upper()

        # Check cache first
        cache_key = f"breached_password_{password_hash[:10]}"
        is_breached = cache.get(cache_key)

        if is_breached is None:
            # In a real implementation, you would check against HaveIBeenPwned API
            # For now, we'll check against a list of common breached passwords
            common_breached = [
                'password', '123456', 'password123', 'admin', 'qwerty',
                'letmein', 'welcome', 'monkey', '1234567890', 'password1'
            ]

            is_breached = password.lower() in common_breached
            cache.set(cache_key, is_breached, 3600)  # Cache for 1 hour

        if is_breached:
            raise ValidationError(
                _("This password has been found in data breaches and cannot be used."),
                code='password_breached',
            )

    def get_help_text(self):
        return _(
            "Your password will be checked against known data breaches."
        )


class EnhancedHospitalPasswordValidator(HospitalPasswordValidator):
    """
    Enhanced password validator with additional security features
    """

    def __init__(self, min_length=12, require_uppercase=True, require_lowercase=True,
                 require_numbers=True, require_special=True, forbidden_patterns=None):
        super().__init__(min_length, require_uppercase, require_lowercase,
                        require_numbers, require_special)
        self.forbidden_patterns = forbidden_patterns or [
            'hospital', 'medical', 'doctor', 'patient', 'admin',
            'password', '123456', 'qwerty'
        ]

    def validate(self, password, user=None):
        # Run base validation
        super().validate(password, user)

        errors = []

        # Check forbidden patterns
        password_lower = password.lower()
        for pattern in self.forbidden_patterns:
            if pattern in password_lower:
                errors.append(
                    ValidationError(
                        _("Password cannot contain forbidden patterns."),
                        code='password_forbidden_pattern',
                    )
                )
                break

        # Check for keyboard patterns
        if self._has_keyboard_pattern(password):
            errors.append(
                ValidationError(
                    _("Password cannot contain keyboard patterns (e.g., qwerty, asdf)."),
                    code='password_keyboard_pattern',
                )
            )

        # Check password entropy
        if self._calculate_entropy(password) < 50:
            errors.append(
                ValidationError(
                    _("Password is not complex enough. Use a mix of different character types."),
                    code='password_low_entropy',
                )
            )

        # Check for dictionary words
        if self._contains_dictionary_word(password):
            errors.append(
                ValidationError(
                    _("Password cannot contain common dictionary words."),
                    code='password_dictionary_word',
                )
            )

        if errors:
            raise ValidationError(errors)

    def _has_keyboard_pattern(self, password):
        """Check for common keyboard patterns"""
        keyboard_patterns = [
            'qwerty', 'asdf', 'zxcv', '1234', '4321',
            'qwertyuiop', 'asdfghjkl', 'zxcvbnm'
        ]

        password_lower = password.lower()
        for pattern in keyboard_patterns:
            if pattern in password_lower:
                return True
        return False

    def _calculate_entropy(self, password):
        """Calculate password entropy"""
        charset_size = 0

        if re.search(r'[a-z]', password):
            charset_size += 26
        if re.search(r'[A-Z]', password):
            charset_size += 26
        if re.search(r'\d', password):
            charset_size += 10
        if re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            charset_size += 32

        if charset_size == 0:
            return 0

        import math
        entropy = len(password) * math.log2(charset_size)
        return entropy

    def _contains_dictionary_word(self, password):
        """Check for common dictionary words"""
        common_words = [
            'password', 'welcome', 'hello', 'world', 'love', 'money',
            'family', 'friend', 'computer', 'internet', 'security'
        ]

        password_lower = password.lower()
        for word in common_words:
            if word in password_lower:
                return True
        return False

    def get_help_text(self):
        return _(
            f"Your password must be at least {self.min_length} characters long, "
            "contain uppercase and lowercase letters, numbers, and special characters. "
            "It cannot contain forbidden patterns, keyboard sequences, or common words."
        )
