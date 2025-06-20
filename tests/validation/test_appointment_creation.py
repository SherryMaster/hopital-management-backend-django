import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hospital_backend.settings')
django.setup()

from appointments.models import Appointment
from patients.models import Patient
from doctors.models import Doctor
from datetime import date, time

def test_appointment_creation():
    print("Testing direct appointment creation...")
    
    # Get patient and doctor
    patient = Patient.objects.first()
    doctor = Doctor.objects.first()
    
    print(f'Patient: {patient.patient_id if patient else "None"}')
    print(f'Doctor: {doctor.doctor_id if doctor else "None"}')
    
    if patient and doctor:
        # Try to create an appointment
        try:
            appointment = Appointment.objects.create(
                patient=patient,
                doctor=doctor,
                appointment_date=date(2025, 6, 21),
                appointment_time=time(11, 0),
                duration_minutes=30,
                reason_for_visit='Test appointment',
                priority='normal',
                status='scheduled'
            )
            print(f'✓ Appointment created successfully: {appointment.appointment_number}')
            print(f'  ID: {appointment.id}')
            print(f'  Patient: {appointment.patient.user.get_full_name()}')
            print(f'  Doctor: {appointment.doctor.user.get_full_name()}')
            print(f'  Date: {appointment.appointment_date}')
            print(f'  Time: {appointment.appointment_time}')
            
        except Exception as e:
            print(f'✗ Error creating appointment: {e}')
            import traceback
            traceback.print_exc()
    else:
        print("No patient or doctor found")

if __name__ == '__main__':
    test_appointment_creation()
