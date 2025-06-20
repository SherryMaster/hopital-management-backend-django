"""
Test data factories for Hospital Management System
Using Factory Boy to create consistent test data
"""
import factory
from factory.django import DjangoModelFactory
from factory import Faker, SubFactory, LazyAttribute, LazyFunction
from django.contrib.auth import get_user_model
from datetime import date, time, datetime, timedelta
from decimal import Decimal
import random

from accounts.models import User
from patients.models import PatientProfile, EmergencyContact, Insurance
from doctors.models import DoctorProfile, Specialization, DoctorAvailability
from appointments.models import Appointment, AppointmentType
from medical_records.models import MedicalHistory, Prescription, VitalSigns
from billing.models import Invoice, Payment, InsuranceClaim
from notifications.models import EmailNotification, SMSNotification, EmailTemplate
from infrastructure.models import Building, Floor, Room, Equipment

User = get_user_model()


class UserFactory(DjangoModelFactory):
    """Factory for creating User instances"""
    
    class Meta:
        model = User
    
    username = Faker('user_name')
    email = Faker('email')
    first_name = Faker('first_name')
    last_name = Faker('last_name')
    is_active = True
    is_staff = False
    user_type = 'patient'
    
    @factory.post_generation
    def password(self, create, extracted, **kwargs):
        if not create:
            return
        
        password = extracted or 'testpass123'
        self.set_password(password)
        self.save()


class AdminUserFactory(UserFactory):
    """Factory for creating Admin users"""
    
    user_type = 'admin'
    is_staff = True
    is_superuser = True


class PatientUserFactory(UserFactory):
    """Factory for creating Patient users"""
    
    user_type = 'patient'


class DoctorUserFactory(UserFactory):
    """Factory for creating Doctor users"""
    
    user_type = 'doctor'


class StaffUserFactory(UserFactory):
    """Factory for creating Staff users"""
    
    user_type = 'staff'


class SpecializationFactory(DjangoModelFactory):
    """Factory for creating Specialization instances"""
    
    class Meta:
        model = Specialization
    
    name = Faker('random_element', elements=[
        'General Medicine', 'Cardiology', 'Neurology', 'Orthopedics',
        'Pediatrics', 'Dermatology', 'Psychiatry', 'Radiology',
        'Emergency Medicine', 'Internal Medicine', 'Surgery', 'Oncology'
    ])
    description = Faker('text', max_nb_chars=200)


class PatientProfileFactory(DjangoModelFactory):
    """Factory for creating PatientProfile instances"""
    
    class Meta:
        model = PatientProfile
    
    user = SubFactory(PatientUserFactory)
    date_of_birth = Faker('date_of_birth', minimum_age=18, maximum_age=90)
    gender = Faker('random_element', elements=['male', 'female', 'other'])
    phone_number = Faker('phone_number')
    address = Faker('address')
    blood_type = Faker('random_element', elements=['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-'])
    allergies = Faker('random_elements', elements=[
        'Penicillin', 'Shellfish', 'Nuts', 'Latex', 'Pollen', 'Dust'
    ], length=lambda: random.randint(0, 3), unique=True)
    medical_conditions = Faker('random_elements', elements=[
        'Hypertension', 'Diabetes', 'Asthma', 'Arthritis', 'Heart Disease'
    ], length=lambda: random.randint(0, 2), unique=True)
    emergency_contact_name = Faker('name')
    emergency_contact_phone = Faker('phone_number')
    emergency_contact_relationship = Faker('random_element', elements=[
        'spouse', 'parent', 'child', 'sibling', 'friend', 'other'
    ])


class DoctorProfileFactory(DjangoModelFactory):
    """Factory for creating DoctorProfile instances"""
    
    class Meta:
        model = DoctorProfile
    
    user = SubFactory(DoctorUserFactory)
    license_number = Faker('bothify', text='MD######')
    specialization = SubFactory(SpecializationFactory)
    phone_number = Faker('phone_number')
    years_of_experience = Faker('random_int', min=1, max=40)
    consultation_fee = Faker('pydecimal', left_digits=3, right_digits=2, positive=True, min_value=50, max_value=500)
    bio = Faker('text', max_nb_chars=500)
    education = Faker('random_elements', elements=[
        'Harvard Medical School', 'Johns Hopkins University', 'Stanford University',
        'Mayo Clinic College of Medicine', 'University of Pennsylvania'
    ], length=lambda: random.randint(1, 2), unique=True)
    certifications = Faker('random_elements', elements=[
        'Board Certified Internal Medicine', 'American Board of Surgery',
        'American Board of Pediatrics', 'Board Certified Emergency Medicine'
    ], length=lambda: random.randint(1, 3), unique=True)


class EmergencyContactFactory(DjangoModelFactory):
    """Factory for creating EmergencyContact instances"""
    
    class Meta:
        model = EmergencyContact
    
    patient = SubFactory(PatientProfileFactory)
    name = Faker('name')
    relationship = Faker('random_element', elements=[
        'spouse', 'parent', 'child', 'sibling', 'friend', 'other'
    ])
    phone_number = Faker('phone_number')
    email = Faker('email')
    is_primary = Faker('boolean', chance_of_getting_true=30)


class InsuranceFactory(DjangoModelFactory):
    """Factory for creating Insurance instances"""
    
    class Meta:
        model = Insurance
    
    patient = SubFactory(PatientProfileFactory)
    provider_name = Faker('random_element', elements=[
        'Blue Cross Blue Shield', 'Aetna', 'Cigna', 'UnitedHealth',
        'Humana', 'Kaiser Permanente', 'Anthem'
    ])
    policy_number = Faker('bothify', text='POL########')
    group_number = Faker('bothify', text='GRP####')
    coverage_type = Faker('random_element', elements=[
        'individual', 'family', 'group', 'medicare', 'medicaid'
    ])
    effective_date = Faker('date_between', start_date='-2y', end_date='today')
    expiration_date = Faker('date_between', start_date='today', end_date='+2y')
    copay_amount = Faker('pydecimal', left_digits=2, right_digits=2, positive=True, min_value=10, max_value=100)


class AppointmentTypeFactory(DjangoModelFactory):
    """Factory for creating AppointmentType instances"""
    
    class Meta:
        model = AppointmentType
    
    name = Faker('random_element', elements=[
        'Consultation', 'Follow-up', 'Check-up', 'Emergency',
        'Surgery', 'Therapy', 'Vaccination', 'Screening'
    ])
    duration = Faker('random_element', elements=[15, 30, 45, 60, 90, 120])
    price = Faker('pydecimal', left_digits=3, right_digits=2, positive=True, min_value=50, max_value=300)
    description = Faker('text', max_nb_chars=200)


class AppointmentFactory(DjangoModelFactory):
    """Factory for creating Appointment instances"""
    
    class Meta:
        model = Appointment
    
    patient = SubFactory(PatientProfileFactory)
    doctor = SubFactory(DoctorProfileFactory)
    appointment_date = Faker('date_between', start_date='today', end_date='+30d')
    appointment_time = Faker('time_object')
    appointment_type = SubFactory(AppointmentTypeFactory)
    status = Faker('random_element', elements=[
        'scheduled', 'confirmed', 'in_progress', 'completed', 'cancelled', 'no_show'
    ])
    reason = Faker('sentence', nb_words=6)
    notes = Faker('text', max_nb_chars=300)
    
    @LazyAttribute
    def appointment_datetime(self):
        return datetime.combine(self.appointment_date, self.appointment_time)


class DoctorAvailabilityFactory(DjangoModelFactory):
    """Factory for creating DoctorAvailability instances"""
    
    class Meta:
        model = DoctorAvailability
    
    doctor = SubFactory(DoctorProfileFactory)
    day_of_week = Faker('random_int', min=0, max=6)  # 0=Monday, 6=Sunday
    start_time = Faker('time_object')
    end_time = LazyAttribute(lambda obj: time(
        hour=min(obj.start_time.hour + random.randint(4, 8), 23),
        minute=obj.start_time.minute
    ))
    is_available = True


class MedicalHistoryFactory(DjangoModelFactory):
    """Factory for creating MedicalHistory instances"""
    
    class Meta:
        model = MedicalHistory
    
    patient = SubFactory(PatientProfileFactory)
    doctor = SubFactory(DoctorProfileFactory)
    condition = Faker('random_element', elements=[
        'Hypertension', 'Diabetes Type 2', 'Asthma', 'Migraine',
        'Arthritis', 'Depression', 'Anxiety', 'High Cholesterol'
    ])
    diagnosis_date = Faker('date_between', start_date='-2y', end_date='today')
    treatment = Faker('text', max_nb_chars=300)
    notes = Faker('text', max_nb_chars=500)
    severity = Faker('random_element', elements=['mild', 'moderate', 'severe'])
    is_chronic = Faker('boolean', chance_of_getting_true=40)


class PrescriptionFactory(DjangoModelFactory):
    """Factory for creating Prescription instances"""
    
    class Meta:
        model = Prescription
    
    patient = SubFactory(PatientProfileFactory)
    doctor = SubFactory(DoctorProfileFactory)
    medication_name = Faker('random_element', elements=[
        'Lisinopril', 'Metformin', 'Amlodipine', 'Metoprolol',
        'Omeprazole', 'Simvastatin', 'Losartan', 'Albuterol'
    ])
    dosage = Faker('random_element', elements=[
        '5mg', '10mg', '25mg', '50mg', '100mg', '250mg', '500mg'
    ])
    frequency = Faker('random_element', elements=[
        'Once daily', 'Twice daily', 'Three times daily', 'As needed',
        'Every 8 hours', 'Every 12 hours', 'Before meals'
    ])
    duration = Faker('random_element', elements=[
        '7 days', '14 days', '30 days', '60 days', '90 days', 'Ongoing'
    ])
    instructions = Faker('text', max_nb_chars=200)
    refills_allowed = Faker('random_int', min=0, max=5)
    prescribed_date = Faker('date_between', start_date='-1y', end_date='today')


class VitalSignsFactory(DjangoModelFactory):
    """Factory for creating VitalSigns instances"""
    
    class Meta:
        model = VitalSigns
    
    patient = SubFactory(PatientProfileFactory)
    recorded_by = SubFactory(DoctorProfileFactory)
    blood_pressure_systolic = Faker('random_int', min=90, max=180)
    blood_pressure_diastolic = Faker('random_int', min=60, max=120)
    heart_rate = Faker('random_int', min=60, max=120)
    temperature = Faker('pyfloat', left_digits=2, right_digits=1, positive=True, min_value=96.0, max_value=104.0)
    respiratory_rate = Faker('random_int', min=12, max=25)
    oxygen_saturation = Faker('random_int', min=95, max=100)
    weight = Faker('pyfloat', left_digits=2, right_digits=1, positive=True, min_value=40.0, max_value=150.0)
    height = Faker('pyfloat', left_digits=3, right_digits=1, positive=True, min_value=140.0, max_value=200.0)
    recorded_at = Faker('date_time_between', start_date='-1y', end_date='now')


class InvoiceFactory(DjangoModelFactory):
    """Factory for creating Invoice instances"""
    
    class Meta:
        model = Invoice
    
    patient = SubFactory(PatientProfileFactory)
    invoice_number = Faker('bothify', text='INV-########')
    amount = Faker('pydecimal', left_digits=4, right_digits=2, positive=True, min_value=50, max_value=2000)
    due_date = Faker('date_between', start_date='today', end_date='+60d')
    status = Faker('random_element', elements=['pending', 'paid', 'overdue', 'cancelled'])
    description = Faker('text', max_nb_chars=300)
    services = Faker('random_elements', elements=[
        {'name': 'Consultation', 'price': '100.00'},
        {'name': 'Blood Test', 'price': '50.00'},
        {'name': 'X-Ray', 'price': '75.00'},
        {'name': 'MRI', 'price': '500.00'},
        {'name': 'Surgery', 'price': '1500.00'}
    ], length=lambda: random.randint(1, 3), unique=True)
    
    @LazyAttribute
    def paid_amount(self):
        if self.status == 'paid':
            return self.amount
        elif self.status == 'pending':
            return Decimal('0.00')
        else:
            return Faker('pydecimal', left_digits=4, right_digits=2, 
                        positive=True, min_value=0, max_value=float(self.amount)).generate()


class PaymentFactory(DjangoModelFactory):
    """Factory for creating Payment instances"""
    
    class Meta:
        model = Payment
    
    invoice = SubFactory(InvoiceFactory)
    amount = LazyAttribute(lambda obj: obj.invoice.amount)
    payment_method = Faker('random_element', elements=[
        'credit_card', 'debit_card', 'cash', 'check', 'bank_transfer', 'insurance'
    ])
    transaction_id = Faker('bothify', text='TXN############')
    payment_date = Faker('date_between', start_date='-30d', end_date='today')
    status = Faker('random_element', elements=['pending', 'completed', 'failed', 'refunded'])
    notes = Faker('text', max_nb_chars=200)


class EmailTemplateFactory(DjangoModelFactory):
    """Factory for creating EmailTemplate instances"""
    
    class Meta:
        model = EmailTemplate
    
    name = Faker('random_element', elements=[
        'Appointment Reminder', 'Appointment Confirmation', 'Test Results',
        'Payment Reminder', 'Welcome Email', 'Password Reset'
    ])
    subject = Faker('sentence', nb_words=4)
    html_content = Faker('text', max_nb_chars=500)
    text_content = Faker('text', max_nb_chars=300)
    template_type = Faker('random_element', elements=[
        'appointment_reminder', 'appointment_confirmation', 'test_results',
        'payment_reminder', 'welcome', 'password_reset'
    ])


class EmailNotificationFactory(DjangoModelFactory):
    """Factory for creating EmailNotification instances"""
    
    class Meta:
        model = EmailNotification
    
    recipient_email = Faker('email')
    subject = Faker('sentence', nb_words=4)
    html_content = Faker('text', max_nb_chars=500)
    text_content = Faker('text', max_nb_chars=300)
    template = SubFactory(EmailTemplateFactory)
    status = Faker('random_element', elements=['pending', 'sent', 'delivered', 'failed'])
    priority = Faker('random_element', elements=['low', 'normal', 'high', 'urgent'])
    scheduled_at = Faker('date_time_between', start_date='now', end_date='+7d')
    sent_at = Faker('date_time_between', start_date='-7d', end_date='now')


class BuildingFactory(DjangoModelFactory):
    """Factory for creating Building instances"""
    
    class Meta:
        model = Building
    
    name = Faker('random_element', elements=[
        'Main Hospital Building', 'Emergency Wing', 'Outpatient Center',
        'Surgical Center', 'Diagnostic Center', 'Administrative Building'
    ])
    address = Faker('address')
    floors_count = Faker('random_int', min=1, max=10)
    description = Faker('text', max_nb_chars=300)


class FloorFactory(DjangoModelFactory):
    """Factory for creating Floor instances"""
    
    class Meta:
        model = Floor
    
    building = SubFactory(BuildingFactory)
    floor_number = Faker('random_int', min=1, max=10)
    name = LazyAttribute(lambda obj: f"Floor {obj.floor_number}")
    department = Faker('random_element', elements=[
        'Emergency', 'Surgery', 'ICU', 'Pediatrics', 'Maternity',
        'Cardiology', 'Neurology', 'Radiology', 'Laboratory'
    ])


class RoomFactory(DjangoModelFactory):
    """Factory for creating Room instances"""
    
    class Meta:
        model = Room
    
    floor = SubFactory(FloorFactory)
    room_number = Faker('bothify', text='###')
    room_type = Faker('random_element', elements=[
        'patient_room', 'operating_room', 'consultation_room',
        'emergency_room', 'icu_room', 'laboratory', 'radiology'
    ])
    capacity = Faker('random_int', min=1, max=4)
    is_occupied = Faker('boolean', chance_of_getting_true=60)
    equipment_list = Faker('random_elements', elements=[
        'Hospital Bed', 'Monitor', 'IV Stand', 'Ventilator',
        'Defibrillator', 'X-Ray Machine', 'Ultrasound'
    ], length=lambda: random.randint(1, 4), unique=True)


class EquipmentFactory(DjangoModelFactory):
    """Factory for creating Equipment instances"""

    class Meta:
        model = Equipment

    name = Faker('random_element', elements=[
        'MRI Machine', 'CT Scanner', 'X-Ray Machine', 'Ultrasound',
        'Ventilator', 'Defibrillator', 'ECG Machine', 'Blood Analyzer'
    ])
    equipment_type = Faker('random_element', elements=[
        'diagnostic', 'therapeutic', 'monitoring', 'surgical', 'laboratory'
    ])
    manufacturer = Faker('random_element', elements=[
        'GE Healthcare', 'Siemens', 'Philips', 'Medtronic', 'Abbott'
    ])
    model = Faker('bothify', text='Model-####')
    serial_number = Faker('bothify', text='SN########')
    purchase_date = Faker('date_between', start_date='-5y', end_date='-1y')
    warranty_expiry = Faker('date_between', start_date='today', end_date='+3y')
    status = Faker('random_element', elements=[
        'operational', 'maintenance', 'out_of_order', 'retired'
    ])
    location = SubFactory(RoomFactory)
    maintenance_schedule = Faker('random_element', elements=[
        'weekly', 'monthly', 'quarterly', 'annually'
    ])


# Batch creation utilities
class TestDataBatch:
    """Utility class for creating batches of test data"""

    @staticmethod
    def create_complete_patient_data(count=1):
        """Create complete patient data including profile, contacts, and insurance"""
        patients = []

        for _ in range(count):
            patient = PatientProfileFactory()

            # Add emergency contacts
            EmergencyContactFactory.create_batch(
                random.randint(1, 3),
                patient=patient
            )

            # Add insurance
            if random.choice([True, False]):
                InsuranceFactory(patient=patient)

            patients.append(patient)

        return patients

    @staticmethod
    def create_complete_doctor_data(count=1):
        """Create complete doctor data including profile and availability"""
        doctors = []

        for _ in range(count):
            doctor = DoctorProfileFactory()

            # Add availability for weekdays
            for day in range(5):  # Monday to Friday
                DoctorAvailabilityFactory(
                    doctor=doctor,
                    day_of_week=day,
                    start_time=time(9, 0),
                    end_time=time(17, 0)
                )

            doctors.append(doctor)

        return doctors

    @staticmethod
    def create_appointment_workflow_data():
        """Create data for testing complete appointment workflow"""
        # Create patient and doctor
        patient = PatientProfileFactory()
        doctor = DoctorProfileFactory()

        # Create appointment type
        appointment_type = AppointmentTypeFactory()

        # Create appointment
        appointment = AppointmentFactory(
            patient=patient,
            doctor=doctor,
            appointment_type=appointment_type,
            status='scheduled'
        )

        # Create medical history
        medical_history = MedicalHistoryFactory(
            patient=patient,
            doctor=doctor
        )

        # Create prescription
        prescription = PrescriptionFactory(
            patient=patient,
            doctor=doctor
        )

        # Create invoice
        invoice = InvoiceFactory(
            patient=patient,
            status='pending'
        )

        return {
            'patient': patient,
            'doctor': doctor,
            'appointment': appointment,
            'appointment_type': appointment_type,
            'medical_history': medical_history,
            'prescription': prescription,
            'invoice': invoice
        }

    @staticmethod
    def create_hospital_infrastructure():
        """Create complete hospital infrastructure data"""
        # Create building
        building = BuildingFactory()

        # Create floors
        floors = []
        for floor_num in range(1, 4):  # 3 floors
            floor = FloorFactory(
                building=building,
                floor_number=floor_num
            )
            floors.append(floor)

        # Create rooms
        rooms = []
        for floor in floors:
            for room_num in range(1, 6):  # 5 rooms per floor
                room = RoomFactory(
                    floor=floor,
                    room_number=f"{floor.floor_number}0{room_num}"
                )
                rooms.append(room)

        # Create equipment
        equipment = []
        for room in rooms[:5]:  # Equipment in first 5 rooms
            eq = EquipmentFactory(location=room)
            equipment.append(eq)

        return {
            'building': building,
            'floors': floors,
            'rooms': rooms,
            'equipment': equipment
        }


# Specialized factories for specific test scenarios
class PastAppointmentFactory(AppointmentFactory):
    """Factory for creating past appointments"""

    appointment_date = Faker('date_between', start_date='-30d', end_date='-1d')
    status = 'completed'


class FutureAppointmentFactory(AppointmentFactory):
    """Factory for creating future appointments"""

    appointment_date = Faker('date_between', start_date='+1d', end_date='+30d')
    status = 'scheduled'


class EmergencyAppointmentFactory(AppointmentFactory):
    """Factory for creating emergency appointments"""

    appointment_date = Faker('date_between', start_date='today', end_date='+1d')
    status = 'confirmed'

    @LazyAttribute
    def appointment_type(self):
        return AppointmentTypeFactory(name='Emergency', duration=60)


class PaidInvoiceFactory(InvoiceFactory):
    """Factory for creating paid invoices"""

    status = 'paid'

    @factory.post_generation
    def create_payment(self, create, extracted, **kwargs):
        if not create:
            return

        PaymentFactory(
            invoice=self,
            amount=self.amount,
            status='completed'
        )


class OverdueInvoiceFactory(InvoiceFactory):
    """Factory for creating overdue invoices"""

    due_date = Faker('date_between', start_date='-30d', end_date='-1d')
    status = 'overdue'


class ChronicConditionFactory(MedicalHistoryFactory):
    """Factory for creating chronic medical conditions"""

    is_chronic = True
    severity = 'moderate'
    diagnosis_date = Faker('date_between', start_date='-2y', end_date='-6m')


class RecentVitalSignsFactory(VitalSignsFactory):
    """Factory for creating recent vital signs"""

    recorded_at = Faker('date_time_between', start_date='-7d', end_date='now')
