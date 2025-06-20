"""
Security configuration for Hospital Management System
Implements comprehensive security hardening measures
"""
import os
from decouple import config

# Security Headers Configuration
SECURITY_HEADERS = {
    # Content Security Policy
    'CONTENT_SECURITY_POLICY': {
        'default-src': ["'self'"],
        'script-src': ["'self'", "'unsafe-inline'", 'https://cdn.jsdelivr.net'],
        'style-src': ["'self'", "'unsafe-inline'", 'https://fonts.googleapis.com'],
        'font-src': ["'self'", 'https://fonts.gstatic.com'],
        'img-src': ["'self'", 'data:', 'https:'],
        'connect-src': ["'self'"],
        'frame-ancestors': ["'none'"],
        'base-uri': ["'self'"],
        'form-action': ["'self'"],
    },
    
    # Security Headers
    'X_FRAME_OPTIONS': 'DENY',
    'X_CONTENT_TYPE_OPTIONS': 'nosniff',
    'X_XSS_PROTECTION': '1; mode=block',
    'REFERRER_POLICY': 'strict-origin-when-cross-origin',
    'PERMISSIONS_POLICY': {
        'geolocation': [],
        'microphone': [],
        'camera': [],
        'payment': [],
        'usb': [],
        'magnetometer': [],
        'gyroscope': [],
        'speaker': [],
    }
}

# HTTPS and SSL Configuration
SSL_SECURITY = {
    'SECURE_SSL_REDIRECT': config('SECURE_SSL_REDIRECT', default=True, cast=bool),
    'SECURE_HSTS_SECONDS': config('SECURE_HSTS_SECONDS', default=31536000, cast=int),  # 1 year
    'SECURE_HSTS_INCLUDE_SUBDOMAINS': config('SECURE_HSTS_INCLUDE_SUBDOMAINS', default=True, cast=bool),
    'SECURE_HSTS_PRELOAD': config('SECURE_HSTS_PRELOAD', default=True, cast=bool),
    'SECURE_PROXY_SSL_HEADER': ('HTTP_X_FORWARDED_PROTO', 'https'),
    'SECURE_REDIRECT_EXEMPT': [],
}

# Cookie Security
COOKIE_SECURITY = {
    'SESSION_COOKIE_SECURE': config('SESSION_COOKIE_SECURE', default=True, cast=bool),
    'SESSION_COOKIE_HTTPONLY': True,
    'SESSION_COOKIE_SAMESITE': 'Strict',
    'SESSION_COOKIE_AGE': config('SESSION_COOKIE_AGE', default=3600, cast=int),  # 1 hour
    'CSRF_COOKIE_SECURE': config('CSRF_COOKIE_SECURE', default=True, cast=bool),
    'CSRF_COOKIE_HTTPONLY': True,
    'CSRF_COOKIE_SAMESITE': 'Strict',
    'CSRF_COOKIE_AGE': config('CSRF_COOKIE_AGE', default=3600, cast=int),
    'CSRF_USE_SESSIONS': False,
    'CSRF_TRUSTED_ORIGINS': config(
        'CSRF_TRUSTED_ORIGINS',
        default='https://localhost,https://127.0.0.1',
        cast=lambda v: [s.strip() for s in v.split(',')]
    ),
}

# Password Security
PASSWORD_SECURITY = {
    'AUTH_PASSWORD_VALIDATORS': [
        {
            'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
            'OPTIONS': {
                'user_attributes': ('username', 'email', 'first_name', 'last_name'),
                'max_similarity': 0.7,
            }
        },
        {
            'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
            'OPTIONS': {
                'min_length': 12,
            }
        },
        {
            'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
        },
        {
            'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
        },
        {
            'NAME': 'accounts.password_validators.HospitalPasswordValidator',
            'OPTIONS': {
                'min_length': 12,
                'require_uppercase': True,
                'require_lowercase': True,
                'require_numbers': True,
                'require_special': True,
                'forbidden_patterns': [
                    'hospital', 'medical', 'doctor', 'patient', 'admin',
                    'password', '123456', 'qwerty'
                ],
            }
        },
        {
            'NAME': 'accounts.password_validators.PasswordHistoryValidator',
            'OPTIONS': {
                'history_count': 10,
            }
        },
        {
            'NAME': 'accounts.password_validators.PasswordExpiryValidator',
            'OPTIONS': {
                'max_age_days': 90,
            }
        },
    ],
    'PASSWORD_HASHERS': [
        'django.contrib.auth.hashers.Argon2PasswordHasher',
        'django.contrib.auth.hashers.PBKDF2PasswordHasher',
        'django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher',
        'django.contrib.auth.hashers.BCryptSHA256PasswordHasher',
    ],
}

# File Upload Security
FILE_UPLOAD_SECURITY = {
    'FILE_UPLOAD_MAX_MEMORY_SIZE': config('FILE_UPLOAD_MAX_MEMORY_SIZE', default=5242880, cast=int),  # 5MB
    'DATA_UPLOAD_MAX_MEMORY_SIZE': config('DATA_UPLOAD_MAX_MEMORY_SIZE', default=5242880, cast=int),  # 5MB
    'FILE_UPLOAD_PERMISSIONS': 0o644,
    'FILE_UPLOAD_DIRECTORY_PERMISSIONS': 0o755,
    'ALLOWED_FILE_EXTENSIONS': [
        '.pdf', '.doc', '.docx', '.txt', '.rtf',  # Documents
        '.jpg', '.jpeg', '.png', '.gif', '.bmp',  # Images
        '.mp4', '.avi', '.mov', '.wmv',  # Videos (for medical recordings)
        '.zip', '.rar',  # Archives
    ],
    'MAX_FILE_SIZE': config('MAX_FILE_SIZE', default=10485760, cast=int),  # 10MB
    'VIRUS_SCAN_ENABLED': config('VIRUS_SCAN_ENABLED', default=False, cast=bool),
}

# Database Security
DATABASE_SECURITY = {
    'CONN_MAX_AGE': config('DB_CONN_MAX_AGE', default=600, cast=int),  # 10 minutes
    'CONN_HEALTH_CHECKS': True,
    'OPTIONS': {
        'sslmode': 'require',
        'connect_timeout': 10,
        'options': '-c default_transaction_isolation=serializable'
    },
}

# API Security
API_SECURITY = {
    'ALLOWED_HOSTS': config(
        'ALLOWED_HOSTS',
        default='localhost,127.0.0.1,testserver',
        cast=lambda v: [s.strip() for s in v.split(',')]
    ),
    'INTERNAL_IPS': config(
        'INTERNAL_IPS',
        default='127.0.0.1,localhost',
        cast=lambda v: [s.strip() for s in v.split(',')]
    ),
    'CORS_ALLOWED_ORIGINS': config(
        'CORS_ALLOWED_ORIGINS',
        default='http://localhost:3000,http://127.0.0.1:3000',
        cast=lambda v: [s.strip() for s in v.split(',')]
    ),
    'CORS_ALLOW_CREDENTIALS': True,
    'CORS_ALLOW_ALL_ORIGINS': config('CORS_ALLOW_ALL_ORIGINS', default=False, cast=bool),
    'CORS_ALLOWED_HEADERS': [
        'accept',
        'accept-encoding',
        'authorization',
        'content-type',
        'dnt',
        'origin',
        'user-agent',
        'x-csrftoken',
        'x-requested-with',
    ],
    'CORS_ALLOWED_METHODS': [
        'DELETE',
        'GET',
        'OPTIONS',
        'PATCH',
        'POST',
        'PUT',
    ],
}

# Rate Limiting Configuration
RATE_LIMITING = {
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle'
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': config('ANON_RATE_LIMIT', default='100/hour'),
        'user': config('USER_RATE_LIMIT', default='1000/hour'),
        'login': config('LOGIN_RATE_LIMIT', default='10/minute'),
        'password_reset': config('PASSWORD_RESET_RATE_LIMIT', default='5/hour'),
        'api': config('API_RATE_LIMIT', default='500/hour'),
        'upload': config('UPLOAD_RATE_LIMIT', default='20/hour'),
    }
}

# Logging Security
LOGGING_SECURITY = {
    'SECURITY_LOG_LEVEL': config('SECURITY_LOG_LEVEL', default='INFO'),
    'LOG_SENSITIVE_DATA': config('LOG_SENSITIVE_DATA', default=False, cast=bool),
    'AUDIT_LOG_ENABLED': config('AUDIT_LOG_ENABLED', default=True, cast=bool),
    'FAILED_LOGIN_LOG_ENABLED': config('FAILED_LOGIN_LOG_ENABLED', default=True, cast=bool),
    'MAX_LOG_FILE_SIZE': config('MAX_LOG_FILE_SIZE', default=10485760, cast=int),  # 10MB
    'LOG_BACKUP_COUNT': config('LOG_BACKUP_COUNT', default=5, cast=int),
}

# Security Monitoring
SECURITY_MONITORING = {
    'FAILED_LOGIN_THRESHOLD': config('FAILED_LOGIN_THRESHOLD', default=5, cast=int),
    'ACCOUNT_LOCKOUT_DURATION': config('ACCOUNT_LOCKOUT_DURATION', default=1800, cast=int),  # 30 minutes
    'SUSPICIOUS_ACTIVITY_THRESHOLD': config('SUSPICIOUS_ACTIVITY_THRESHOLD', default=10, cast=int),
    'IP_WHITELIST_ENABLED': config('IP_WHITELIST_ENABLED', default=False, cast=bool),
    'IP_BLACKLIST_ENABLED': config('IP_BLACKLIST_ENABLED', default=True, cast=bool),
    'GEOLOCATION_BLOCKING': config('GEOLOCATION_BLOCKING', default=False, cast=bool),
}

# Data Protection
DATA_PROTECTION = {
    'ENCRYPTION_KEY': config('ENCRYPTION_KEY', default=None),
    'FIELD_ENCRYPTION_ENABLED': config('FIELD_ENCRYPTION_ENABLED', default=True, cast=bool),
    'PII_ENCRYPTION_REQUIRED': True,
    'DATA_RETENTION_DAYS': config('DATA_RETENTION_DAYS', default=2555, cast=int),  # 7 years
    'ANONYMIZATION_ENABLED': config('ANONYMIZATION_ENABLED', default=True, cast=bool),
    'GDPR_COMPLIANCE': config('GDPR_COMPLIANCE', default=True, cast=bool),
    'HIPAA_COMPLIANCE': config('HIPAA_COMPLIANCE', default=True, cast=bool),
}

# Environment-specific security settings
def get_security_settings(debug=False):
    """
    Get security settings based on environment
    """
    settings = {}
    
    # Apply all security configurations
    if not debug:
        settings.update(SSL_SECURITY)
        settings.update(COOKIE_SECURITY)
        settings.update(API_SECURITY)
        
        # Production-only security headers
        settings['SECURE_CONTENT_TYPE_NOSNIFF'] = True
        settings['SECURE_BROWSER_XSS_FILTER'] = True
        settings['X_FRAME_OPTIONS'] = SECURITY_HEADERS['X_FRAME_OPTIONS']
        
    else:
        # Development settings (less restrictive)
        settings.update({
            'SESSION_COOKIE_SECURE': False,
            'CSRF_COOKIE_SECURE': False,
            'SECURE_SSL_REDIRECT': False,
        })
    
    # Always apply these security measures
    settings.update(PASSWORD_SECURITY)
    settings.update(FILE_UPLOAD_SECURITY)
    settings.update(LOGGING_SECURITY)
    settings.update(SECURITY_MONITORING)
    settings.update(DATA_PROTECTION)
    
    return settings

# Security middleware order (important for proper security)
SECURITY_MIDDLEWARE_ORDER = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'accounts.middleware.SecurityHeadersMiddleware',  # Custom security headers
    'accounts.middleware.RateLimitingMiddleware',     # Rate limiting
    'accounts.middleware.IPFilteringMiddleware',      # IP filtering
    'accounts.middleware.APIRequestValidationMiddleware',
    'accounts.middleware.APIAuthenticationMiddleware',
    'accounts.middleware.RoleBasedAccessMiddleware',
    'accounts.middleware.UserActivityMiddleware',
    'accounts.middleware.SecurityAuditMiddleware',    # Security auditing
    'accounts.middleware.APIErrorHandlingMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]
