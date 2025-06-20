import os
import django
from datetime import datetime, timedelta

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hospital_backend.settings')
django.setup()

from django.utils import timezone
from notifications.models import (
    TemplateVariable, TemplateLanguage, UnifiedTemplate, TemplateContent, TemplateUsageLog
)
from notifications.services import UnifiedTemplateService, TemplateVariableService
from accounts.models import User

def test_template_management_system():
    print("=== Testing Template Management System ===")
    
    # Get required objects
    user = User.objects.filter(user_type='admin').first()
    print(f'User: {user.get_full_name() if user else "No admin user"}')
    
    # Test 1: Create template variables
    print('\n1. Creating template variables...')
    
    # Patient name variable
    patient_name_var = TemplateVariable.objects.create(
        name='patient_name',
        display_name='Patient Name',
        description='Full name of the patient',
        variable_type='string',
        format_type='title_case',
        is_required=True,
        default_value='Patient'
    )
    
    # Doctor name variable
    doctor_name_var = TemplateVariable.objects.create(
        name='doctor_name',
        display_name='Doctor Name',
        description='Full name of the doctor',
        variable_type='string',
        format_type='title_case',
        is_required=True
    )
    
    # Appointment date variable
    appointment_date_var = TemplateVariable.objects.create(
        name='appointment_date',
        display_name='Appointment Date',
        description='Date of the appointment',
        variable_type='date',
        format_type='date_long',
        is_required=True
    )
    
    # Payment amount variable
    payment_amount_var = TemplateVariable.objects.create(
        name='payment_amount',
        display_name='Payment Amount',
        description='Amount to be paid',
        variable_type='number',
        format_type='currency_usd',
        is_required=True
    )
    
    # Phone number variable
    phone_var = TemplateVariable.objects.create(
        name='patient_phone',
        display_name='Patient Phone',
        description='Patient phone number',
        variable_type='phone',
        format_type='phone_us',
        validation_regex=r'^\+?1?\d{9,15}$'
    )
    
    print(f'✓ Created patient name variable: {patient_name_var.name} ({patient_name_var.get_variable_type_display()})')
    print(f'  Format: {patient_name_var.get_format_type_display()}')
    print(f'  Required: {patient_name_var.is_required}')
    print(f'✓ Created doctor name variable: {doctor_name_var.name}')
    print(f'✓ Created appointment date variable: {appointment_date_var.name}')
    print(f'  Format: {appointment_date_var.get_format_type_display()}')
    print(f'✓ Created payment amount variable: {payment_amount_var.name}')
    print(f'  Format: {payment_amount_var.get_format_type_display()}')
    print(f'✓ Created phone variable: {phone_var.name}')
    print(f'  Validation regex: {phone_var.validation_regex}')
    
    # Test 2: Create template languages
    print('\n2. Creating template languages...')
    
    # English language
    english_lang = TemplateLanguage.objects.create(
        code='en',
        name='English',
        native_name='English',
        is_active=True,
        is_default=True,
        text_direction='ltr'
    )
    
    # Spanish language
    spanish_lang = TemplateLanguage.objects.create(
        code='es',
        name='Spanish',
        native_name='Español',
        is_active=True,
        is_default=False,
        text_direction='ltr'
    )
    
    # French language
    french_lang = TemplateLanguage.objects.create(
        code='fr',
        name='French',
        native_name='Français',
        is_active=True,
        is_default=False,
        text_direction='ltr'
    )
    
    print(f'✓ Created English language: {english_lang.name} ({english_lang.code})')
    print(f'  Default: {english_lang.is_default}')
    print(f'  Direction: {english_lang.get_text_direction_display()}')
    print(f'✓ Created Spanish language: {spanish_lang.name} ({spanish_lang.code})')
    print(f'✓ Created French language: {french_lang.name} ({french_lang.code})')
    
    # Test 3: Test variable validation and formatting
    print('\n3. Testing variable validation and formatting...')
    
    variable_service = TemplateVariableService()
    
    # Test patient name formatting
    test_name = 'john doe'
    formatted_name = variable_service.format_variable_value(patient_name_var, test_name)
    print(f'✓ Formatted patient name: "{test_name}" → "{formatted_name}"')
    
    # Test payment amount formatting
    test_amount = 150.75
    formatted_amount = variable_service.format_variable_value(payment_amount_var, test_amount)
    print(f'✓ Formatted payment amount: {test_amount} → "{formatted_amount}"')
    
    # Test phone number formatting
    test_phone = '1234567890'
    formatted_phone = variable_service.format_variable_value(phone_var, test_phone)
    print(f'✓ Formatted phone number: "{test_phone}" → "{formatted_phone}"')
    
    # Test date formatting
    test_date = '2025-06-20'
    formatted_date = variable_service.format_variable_value(appointment_date_var, test_date)
    print(f'✓ Formatted appointment date: "{test_date}" → "{formatted_date}"')
    
    # Test validation
    valid_email = 'patient@example.com'
    invalid_email = 'invalid-email'
    
    email_var = TemplateVariable.objects.create(
        name='patient_email',
        display_name='Patient Email',
        variable_type='email',
        is_required=True
    )
    
    email_valid = variable_service.validate_variable_value(email_var, valid_email)
    email_invalid = variable_service.validate_variable_value(email_var, invalid_email)
    
    print(f'✓ Email validation: "{valid_email}" → {email_valid}')
    print(f'✓ Email validation: "{invalid_email}" → {email_invalid}')
    
    # Test 4: Create unified template
    print('\n4. Creating unified template...')
    
    template_service = UnifiedTemplateService()
    
    # Create appointment reminder template
    content_data = {
        'en': {
            'email_subject': 'Appointment Reminder - {{appointment_date}}',
            'email_html': '''
            <h2>Appointment Reminder</h2>
            <p>Dear {{patient_name}},</p>
            <p>This is a reminder that you have an appointment with {{doctor_name}} on {{appointment_date}}.</p>
            <p>Please arrive 15 minutes early.</p>
            <p>Best regards,<br>City Hospital</p>
            ''',
            'email_text': 'Dear {{patient_name}}, reminder: appointment with {{doctor_name}} on {{appointment_date}}. Please arrive 15 minutes early. - City Hospital',
            'sms_message': 'Hi {{patient_name}}! Reminder: appointment with {{doctor_name}} on {{appointment_date}}. City Hospital',
            'push_title': 'Appointment Reminder',
            'push_body': 'Hi {{patient_name}}! You have an appointment with {{doctor_name}} on {{appointment_date}}.'
        },
        'es': {
            'email_subject': 'Recordatorio de Cita - {{appointment_date}}',
            'email_html': '''
            <h2>Recordatorio de Cita</h2>
            <p>Estimado/a {{patient_name}},</p>
            <p>Este es un recordatorio de que tiene una cita con {{doctor_name}} el {{appointment_date}}.</p>
            <p>Por favor llegue 15 minutos antes.</p>
            <p>Saludos cordiales,<br>Hospital Ciudad</p>
            ''',
            'email_text': 'Estimado/a {{patient_name}}, recordatorio: cita con {{doctor_name}} el {{appointment_date}}. Llegue 15 minutos antes. - Hospital Ciudad',
            'sms_message': '¡Hola {{patient_name}}! Recordatorio: cita con {{doctor_name}} el {{appointment_date}}. Hospital Ciudad',
            'push_title': 'Recordatorio de Cita',
            'push_body': '¡Hola {{patient_name}}! Tiene una cita con {{doctor_name}} el {{appointment_date}}.'
        },
        'fr': {
            'email_subject': 'Rappel de Rendez-vous - {{appointment_date}}',
            'email_html': '''
            <h2>Rappel de Rendez-vous</h2>
            <p>Cher/Chère {{patient_name}},</p>
            <p>Ceci est un rappel que vous avez un rendez-vous avec {{doctor_name}} le {{appointment_date}}.</p>
            <p>Veuillez arriver 15 minutes en avance.</p>
            <p>Cordialement,<br>Hôpital de la Ville</p>
            ''',
            'email_text': 'Cher/Chère {{patient_name}}, rappel: rendez-vous avec {{doctor_name}} le {{appointment_date}}. Arrivez 15 minutes en avance. - Hôpital de la Ville',
            'sms_message': 'Bonjour {{patient_name}}! Rappel: rendez-vous avec {{doctor_name}} le {{appointment_date}}. Hôpital de la Ville',
            'push_title': 'Rappel de Rendez-vous',
            'push_body': 'Bonjour {{patient_name}}! Vous avez un rendez-vous avec {{doctor_name}} le {{appointment_date}}.'
        }
    }
    
    appointment_template = template_service.create_template(
        name='Appointment Reminder Multi-Language',
        template_type='appointment_reminder',
        supported_channels=['email', 'sms', 'push'],
        content_data=content_data,
        variables=['patient_name', 'doctor_name', 'appointment_date'],
        created_by=user
    )
    
    print(f'✓ Created unified template: {appointment_template.name}')
    print(f'  Type: {appointment_template.get_template_type_display()}')
    print(f'  Version: {appointment_template.version}')
    print(f'  Supported channels: {appointment_template.supported_channels}')
    print(f'  Variables: {[var.name for var in appointment_template.variables.all()]}')
    print(f'  Content items: {appointment_template.content.count()}')
    
    # Test 5: Render template in different languages
    print('\n5. Testing template rendering...')
    
    test_variables = {
        'patient_name': 'john doe',
        'doctor_name': 'dr. sarah smith',
        'appointment_date': '2025-06-20'
    }
    
    # Render in English for email
    english_email = template_service.render_template(
        template=appointment_template,
        channel='email',
        language_code='en',
        variables=test_variables
    )
    
    print(f'✓ Rendered English email:')
    print(f'  Subject: "{english_email.get("email_subject", "")}"')
    print(f'  Text length: {len(english_email.get("email_text", ""))} chars')
    
    # Render in Spanish for SMS
    spanish_sms = template_service.render_template(
        template=appointment_template,
        channel='sms',
        language_code='es',
        variables=test_variables
    )
    
    print(f'✓ Rendered Spanish SMS:')
    print(f'  Message: "{spanish_sms.get("sms_message", "")}"')
    
    # Render in French for push notification
    french_push = template_service.render_template(
        template=appointment_template,
        channel='push',
        language_code='fr',
        variables=test_variables
    )
    
    print(f'✓ Rendered French push notification:')
    print(f'  Title: "{french_push.get("push_title", "")}"')
    print(f'  Body: "{french_push.get("push_body", "")}"')
    
    # Test 6: Template analytics
    print('\n6. Testing template analytics...')
    
    # Simulate some usage logs
    for i in range(10):
        TemplateUsageLog.objects.create(
            template=appointment_template,
            language=english_lang if i % 2 == 0 else spanish_lang,
            channel='email' if i % 3 == 0 else 'sms' if i % 3 == 1 else 'push',
            variables_used=test_variables,
            render_time_ms=50 + (i * 5),
            success=True if i < 8 else False,
            error_message='Template variable missing' if i >= 8 else ''
        )
    
    analytics = template_service.get_template_analytics(appointment_template, days=30)
    
    print(f'✓ Template analytics for {appointment_template.name}:')
    print(f'  Total usage: {analytics["total_usage"]}')
    print(f'  Successful usage: {analytics["successful_usage"]}')
    print(f'  Failed usage: {analytics["failed_usage"]}')
    print(f'  Success rate: {analytics["success_rate"]:.1f}%')
    print(f'  Average render time: {analytics["avg_render_time_ms"]:.1f}ms')
    print(f'  Channel usage: {analytics["channel_usage"]}')
    print(f'  Language usage: {analytics["language_usage"]}')
    
    # Test 7: System statistics
    print('\n7. System statistics...')
    
    total_variables = TemplateVariable.objects.count()
    total_languages = TemplateLanguage.objects.count()
    active_languages = TemplateLanguage.objects.filter(is_active=True).count()
    total_templates = UnifiedTemplate.objects.count()
    active_templates = UnifiedTemplate.objects.filter(is_active=True).count()
    total_content = TemplateContent.objects.count()
    total_usage_logs = TemplateUsageLog.objects.count()
    
    print(f'✓ Template management system statistics:')
    print(f'  Total variables: {total_variables}')
    print(f'  Total languages: {total_languages}')
    print(f'  Active languages: {active_languages}')
    print(f'  Total unified templates: {total_templates}')
    print(f'  Active templates: {active_templates}')
    print(f'  Total content items: {total_content}')
    print(f'  Total usage logs: {total_usage_logs}')
    
    # Variable type breakdown
    variable_types = {}
    for var_type in TemplateVariable.VARIABLE_TYPES:
        type_name = var_type[0]
        count = TemplateVariable.objects.filter(variable_type=type_name).count()
        if count > 0:
            variable_types[type_name] = count
    
    print(f'  Variable types: {variable_types}')
    
    # Language breakdown
    language_breakdown = {}
    for lang in TemplateLanguage.objects.filter(is_active=True):
        content_count = TemplateContent.objects.filter(language=lang).count()
        language_breakdown[lang.code] = content_count
    
    print(f'  Content by language: {language_breakdown}')
    
    print('\n=== Template Management System Testing Complete ===')

if __name__ == '__main__':
    test_template_management_system()
