from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime, timedelta, time
from appointments.models import AppointmentType, Appointment
from patients.models import Patient
from doctors.models import Doctor
from accounts.models import User


class Command(BaseCommand):
    help = 'Create sample appointment types and appointments for testing'

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('Creating sample appointment data...')
        )
        
        # Create appointment types
        appointment_types_data = [
            {
                'name': 'General Consultation',
                'description': 'Standard consultation for general health concerns',
                'duration_minutes': 30,
                'color_code': '#007bff'
            },
            {
                'name': 'Follow-up Visit',
                'description': 'Follow-up appointment for ongoing treatment',
                'duration_minutes': 20,
                'color_code': '#28a745'
            },
            {
                'name': 'Emergency Consultation',
                'description': 'Urgent medical consultation',
                'duration_minutes': 45,
                'color_code': '#dc3545'
            },
            {
                'name': 'Specialist Consultation',
                'description': 'Consultation with medical specialist',
                'duration_minutes': 45,
                'color_code': '#6f42c1'
            },
            {
                'name': 'Routine Check-up',
                'description': 'Regular health check-up and screening',
                'duration_minutes': 30,
                'color_code': '#17a2b8'
            },
            {
                'name': 'Vaccination',
                'description': 'Vaccination and immunization appointment',
                'duration_minutes': 15,
                'color_code': '#ffc107'
            },
            {
                'name': 'Physical Therapy',
                'description': 'Physical therapy and rehabilitation session',
                'duration_minutes': 60,
                'color_code': '#fd7e14'
            },
            {
                'name': 'Mental Health Consultation',
                'description': 'Mental health and psychological consultation',
                'duration_minutes': 50,
                'color_code': '#e83e8c'
            }
        ]
        
        created_types = []
        for type_data in appointment_types_data:
            appointment_type, created = AppointmentType.objects.get_or_create(
                name=type_data['name'],
                defaults=type_data
            )
            if created:
                self.stdout.write(f'✓ Created appointment type: {appointment_type.name}')
            else:
                self.stdout.write(f'- Appointment type already exists: {appointment_type.name}')
            created_types.append(appointment_type)
        
        # Create sample appointments if we have patients and doctors
        patients = Patient.objects.filter(is_active=True)[:3]
        doctors = Doctor.objects.filter(employment_status='active')[:3]
        
        if not patients.exists():
            self.stdout.write(
                self.style.WARNING('No active patients found. Skipping appointment creation.')
            )
            return
        
        if not doctors.exists():
            self.stdout.write(
                self.style.WARNING('No active doctors found. Skipping appointment creation.')
            )
            return
        
        # Create appointments for the next few days
        today = timezone.now().date()
        appointment_times = [
            time(9, 0),   # 9:00 AM
            time(10, 30), # 10:30 AM
            time(14, 0),  # 2:00 PM
            time(15, 30), # 3:30 PM
            time(16, 30), # 4:30 PM
        ]
        
        sample_appointments = []
        for i in range(5):  # Create appointments for next 5 days
            appointment_date = today + timedelta(days=i+1)
            
            for j, appointment_time in enumerate(appointment_times[:3]):  # 3 appointments per day
                if j < len(patients) and j < len(doctors):
                    patient = patients[j]
                    doctor = doctors[j % len(doctors)]
                    appointment_type = created_types[j % len(created_types)]
                    
                    # Check if appointment already exists
                    if not Appointment.objects.filter(
                        patient=patient,
                        doctor=doctor,
                        appointment_date=appointment_date,
                        appointment_time=appointment_time
                    ).exists():
                        
                        appointment_data = {
                            'patient': patient,
                            'doctor': doctor,
                            'appointment_type': appointment_type,
                            'appointment_date': appointment_date,
                            'appointment_time': appointment_time,
                            'duration_minutes': appointment_type.duration_minutes,
                            'reason_for_visit': f'Sample {appointment_type.name.lower()} appointment',
                            'symptoms': 'Sample symptoms for testing',
                            'priority': 'normal',
                            'status': 'scheduled'
                        }
                        
                        try:
                            appointment = Appointment.objects.create(**appointment_data)
                            sample_appointments.append(appointment)
                            self.stdout.write(
                                f'✓ Created appointment: {appointment.appointment_number} - '
                                f'{patient.user.get_full_name()} with Dr. {doctor.user.get_full_name()} '
                                f'on {appointment_date} at {appointment_time}'
                            )
                        except Exception as e:
                            self.stdout.write(
                                self.style.ERROR(f'Failed to create appointment: {str(e)}')
                            )
        
        # Update some appointments with different statuses
        if sample_appointments:
            # Confirm some appointments
            for apt in sample_appointments[:2]:
                apt.status = 'confirmed'
                apt.save()
                self.stdout.write(f'✓ Confirmed appointment: {apt.appointment_number}')
            
            # Complete one appointment (from yesterday)
            if len(sample_appointments) > 2:
                past_apt = sample_appointments[2]
                past_apt.appointment_date = today - timedelta(days=1)
                past_apt.status = 'completed'
                past_apt.completed_at = timezone.now() - timedelta(days=1, hours=2)
                past_apt.save()
                self.stdout.write(f'✓ Completed appointment: {past_apt.appointment_number}')
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Sample appointment data creation completed!\n'
                f'Created {len(created_types)} appointment types and {len(sample_appointments)} appointments.'
            )
        )
