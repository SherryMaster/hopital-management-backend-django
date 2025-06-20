from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from doctors.models import Specialization, Department, Doctor

User = get_user_model()


class Command(BaseCommand):
    help = 'Create sample specializations and departments for the hospital'

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('Creating sample doctor data...')
        )
        
        # Create specializations
        specializations_data = [
            {
                'name': 'Cardiology',
                'description': 'Diagnosis and treatment of heart and cardiovascular diseases'
            },
            {
                'name': 'Neurology',
                'description': 'Diagnosis and treatment of nervous system disorders'
            },
            {
                'name': 'Orthopedics',
                'description': 'Treatment of musculoskeletal system disorders'
            },
            {
                'name': 'Pediatrics',
                'description': 'Medical care for infants, children, and adolescents'
            },
            {
                'name': 'Dermatology',
                'description': 'Diagnosis and treatment of skin, hair, and nail conditions'
            },
            {
                'name': 'Psychiatry',
                'description': 'Diagnosis and treatment of mental health disorders'
            },
            {
                'name': 'Radiology',
                'description': 'Medical imaging and diagnostic procedures'
            },
            {
                'name': 'Emergency Medicine',
                'description': 'Acute care and emergency medical services'
            },
            {
                'name': 'Internal Medicine',
                'description': 'Comprehensive care for adult patients'
            },
            {
                'name': 'Surgery',
                'description': 'Surgical procedures and operative care'
            }
        ]
        
        created_specializations = []
        for spec_data in specializations_data:
            specialization, created = Specialization.objects.get_or_create(
                name=spec_data['name'],
                defaults={'description': spec_data['description']}
            )
            if created:
                self.stdout.write(f'✓ Created specialization: {specialization.name}')
            else:
                self.stdout.write(f'- Specialization already exists: {specialization.name}')
            created_specializations.append(specialization)
        
        # Create departments
        departments_data = [
            {
                'name': 'Cardiology Department',
                'description': 'Heart and cardiovascular care',
                'location': 'Building A, Floor 3',
                'phone_number': '+1-555-0101',
                'email': 'cardiology@hospital.com'
            },
            {
                'name': 'Neurology Department',
                'description': 'Neurological care and treatment',
                'location': 'Building B, Floor 2',
                'phone_number': '+1-555-0102',
                'email': 'neurology@hospital.com'
            },
            {
                'name': 'Orthopedics Department',
                'description': 'Bone and joint care',
                'location': 'Building A, Floor 2',
                'phone_number': '+1-555-0103',
                'email': 'orthopedics@hospital.com'
            },
            {
                'name': 'Pediatrics Department',
                'description': 'Children and adolescent care',
                'location': 'Building C, Floor 1',
                'phone_number': '+1-555-0104',
                'email': 'pediatrics@hospital.com'
            },
            {
                'name': 'Emergency Department',
                'description': 'Emergency and trauma care',
                'location': 'Building A, Ground Floor',
                'phone_number': '+1-555-0911',
                'email': 'emergency@hospital.com'
            },
            {
                'name': 'Internal Medicine Department',
                'description': 'General internal medicine',
                'location': 'Building B, Floor 1',
                'phone_number': '+1-555-0105',
                'email': 'internal@hospital.com'
            },
            {
                'name': 'Surgery Department',
                'description': 'Surgical procedures and operations',
                'location': 'Building A, Floor 4',
                'phone_number': '+1-555-0106',
                'email': 'surgery@hospital.com'
            },
            {
                'name': 'Radiology Department',
                'description': 'Medical imaging and diagnostics',
                'location': 'Building B, Basement',
                'phone_number': '+1-555-0107',
                'email': 'radiology@hospital.com'
            }
        ]
        
        created_departments = []
        for dept_data in departments_data:
            department, created = Department.objects.get_or_create(
                name=dept_data['name'],
                defaults={
                    'description': dept_data['description'],
                    'location': dept_data['location'],
                    'phone_number': dept_data['phone_number'],
                    'email': dept_data['email']
                }
            )
            if created:
                self.stdout.write(f'✓ Created department: {department.name}')
            else:
                self.stdout.write(f'- Department already exists: {department.name}')
            created_departments.append(department)
        
        # Create sample doctors
        sample_doctors_data = [
            {
                'email': 'dr.sarah.johnson@hospital.com',
                'first_name': 'Sarah',
                'last_name': 'Johnson',
                'phone_number': '+1-555-1001',
                'date_of_birth': '1975-03-15',
                'gender': 'F',
                'address': '123 Medical Plaza, City',
                'password': 'SecurePass123!',
                'medical_license_number': 'MD001234',
                'license_expiry_date': '2026-12-31',
                'department': 'Cardiology Department',
                'specializations': ['Cardiology'],
                'hire_date': '2020-01-15',
                'consultation_fee': 200.00,
                'years_of_experience': 15,
                'bio': 'Board-certified cardiologist with expertise in interventional cardiology',
                'languages_spoken': 'English, French',
                'max_patients_per_day': 12
            },
            {
                'email': 'dr.michael.chen@hospital.com',
                'first_name': 'Michael',
                'last_name': 'Chen',
                'phone_number': '+1-555-1002',
                'date_of_birth': '1980-07-22',
                'gender': 'M',
                'address': '456 Healthcare Ave, City',
                'password': 'SecurePass123!',
                'medical_license_number': 'MD001235',
                'license_expiry_date': '2027-06-30',
                'department': 'Neurology Department',
                'specializations': ['Neurology'],
                'hire_date': '2018-09-01',
                'consultation_fee': 180.00,
                'years_of_experience': 12,
                'bio': 'Neurologist specializing in movement disorders and epilepsy',
                'languages_spoken': 'English, Mandarin',
                'max_patients_per_day': 10
            },
            {
                'email': 'dr.emily.rodriguez@hospital.com',
                'first_name': 'Emily',
                'last_name': 'Rodriguez',
                'phone_number': '+1-555-1003',
                'date_of_birth': '1985-11-08',
                'gender': 'F',
                'address': '789 Medical Center Dr, City',
                'password': 'SecurePass123!',
                'medical_license_number': 'MD001236',
                'license_expiry_date': '2028-03-31',
                'department': 'Pediatrics Department',
                'specializations': ['Pediatrics'],
                'hire_date': '2022-03-01',
                'consultation_fee': 150.00,
                'years_of_experience': 8,
                'bio': 'Pediatrician with special interest in developmental pediatrics',
                'languages_spoken': 'English, Spanish',
                'max_patients_per_day': 15
            }
        ]
        
        for doctor_data in sample_doctors_data:
            # Check if doctor already exists
            if User.objects.filter(email=doctor_data['email']).exists():
                self.stdout.write(f'- Doctor already exists: {doctor_data["email"]}')
                continue
            
            # Get department and specializations
            department = Department.objects.get(name=doctor_data['department'])
            specializations = Specialization.objects.filter(name__in=doctor_data['specializations'])
            
            # Create user
            user_data = {
                'email': doctor_data['email'],
                'first_name': doctor_data['first_name'],
                'last_name': doctor_data['last_name'],
                'phone_number': doctor_data['phone_number'],
                'date_of_birth': doctor_data['date_of_birth'],
                'gender': doctor_data['gender'],
                'address': doctor_data['address'],
                'user_type': 'doctor',
                'is_active': True,
            }
            
            user = User.objects.create_user(
                username=doctor_data['email'],
                password=doctor_data['password'],
                **user_data
            )
            
            # Create doctor profile
            doctor = Doctor.objects.create(
                user=user,
                medical_license_number=doctor_data['medical_license_number'],
                license_expiry_date=doctor_data['license_expiry_date'],
                department=department,
                hire_date=doctor_data['hire_date'],
                consultation_fee=doctor_data['consultation_fee'],
                years_of_experience=doctor_data['years_of_experience'],
                bio=doctor_data['bio'],
                languages_spoken=doctor_data['languages_spoken'],
                max_patients_per_day=doctor_data['max_patients_per_day']
            )
            
            # Add specializations
            doctor.specializations.set(specializations)
            
            self.stdout.write(f'✓ Created doctor: {doctor.doctor_id} - Dr. {doctor.user.get_full_name()}')
        
        self.stdout.write(
            self.style.SUCCESS('Sample doctor data creation completed!')
        )
