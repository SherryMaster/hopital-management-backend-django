from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from patients.serializers import PatientRegistrationSerializer
import json

User = get_user_model()


class Command(BaseCommand):
    help = 'Test Patient Registration'

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('Testing Patient Registration...')
        )
        
        # Test data
        data = {
            'email': 'patient_test@hospital.com',
            'first_name': 'John',
            'last_name': 'Doe',
            'phone_number': '+1234567890',
            'date_of_birth': '1990-01-15',
            'gender': 'M',  # Use single character code
            'address': '123 Main St, City',
            'password': 'SecurePass123!',
            'blood_type': 'O+',
            'height': 175,
            'weight': 70
        }
        
        try:
            # Test serializer validation
            serializer = PatientRegistrationSerializer(data=data)
            
            if serializer.is_valid():
                self.stdout.write(self.style.SUCCESS('✓ Serializer validation passed'))
                
                # Test patient creation
                patient = serializer.save()
                self.stdout.write(self.style.SUCCESS(f'✓ Patient created: {patient.patient_id}'))
                self.stdout.write(f'  - User: {patient.user.get_full_name()}')
                self.stdout.write(f'  - Email: {patient.user.email}')
                self.stdout.write(f'  - Blood Type: {patient.blood_type}')
                self.stdout.write(f'  - Height: {patient.height}cm')
                self.stdout.write(f'  - Weight: {patient.weight}kg')
                self.stdout.write(f'  - BMI: {patient.bmi}')
                
            else:
                self.stdout.write(self.style.ERROR('✗ Serializer validation failed'))
                for field, errors in serializer.errors.items():
                    self.stdout.write(f'  - {field}: {errors}')
                    
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ Error during patient registration: {e}'))
            import traceback
            traceback.print_exc()
        
        self.stdout.write(
            self.style.SUCCESS('Patient Registration testing completed!')
        )
