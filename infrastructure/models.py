from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.validators import RegexValidator, MinValueValidator, MaxValueValidator
import uuid


class Building(models.Model):
    """
    Hospital buildings
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=10, unique=True)
    address = models.TextField()
    floors = models.PositiveIntegerField(default=1)
    description = models.TextField(blank=True)

    # Contact information
    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
    )
    phone_number = models.CharField(validators=[phone_regex], max_length=17, blank=True)
    email = models.EmailField(blank=True)

    # Status
    is_active = models.BooleanField(default=True)
    construction_year = models.PositiveIntegerField(null=True, blank=True)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.code})"


class Floor(models.Model):
    """
    Building floors
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    building = models.ForeignKey(Building, on_delete=models.CASCADE, related_name='building_floors')
    floor_number = models.IntegerField()
    name = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)

    # Floor details
    area_sqft = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    is_accessible = models.BooleanField(default=True, help_text="Wheelchair accessible")

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['building', 'floor_number']
        unique_together = ['building', 'floor_number']

    def __str__(self):
        return f"{self.building.name} - Floor {self.floor_number}"


class RoomType(models.Model):
    """
    Types of rooms in the hospital
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    color_code = models.CharField(max_length=7, default='#007bff', help_text="Hex color code for floor plans")

    # Room specifications
    requires_special_equipment = models.BooleanField(default=False)
    max_occupancy = models.PositiveIntegerField(default=1)
    is_sterile_required = models.BooleanField(default=False)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Room(models.Model):
    """
    Individual rooms in the hospital
    """
    STATUS_CHOICES = (
        ('available', 'Available'),
        ('occupied', 'Occupied'),
        ('maintenance', 'Under Maintenance'),
        ('cleaning', 'Being Cleaned'),
        ('reserved', 'Reserved'),
        ('out_of_service', 'Out of Service'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    room_number = models.CharField(max_length=20)
    floor = models.ForeignKey(Floor, on_delete=models.CASCADE, related_name='rooms')
    room_type = models.ForeignKey(RoomType, on_delete=models.CASCADE, related_name='rooms')

    # Room details
    name = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    area_sqft = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)

    # Status and availability
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='available')
    is_active = models.BooleanField(default=True)

    # Features
    has_window = models.BooleanField(default=False)
    has_private_bathroom = models.BooleanField(default=False)
    has_oxygen_supply = models.BooleanField(default=False)
    has_suction = models.BooleanField(default=False)
    has_nurse_call = models.BooleanField(default=True)

    # Bed information
    bed_count = models.PositiveIntegerField(default=1)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['floor', 'room_number']
        unique_together = ['floor', 'room_number']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['room_type']),
        ]

    def __str__(self):
        return f"Room {self.room_number} - {self.floor.building.name}"

    @property
    def full_room_identifier(self):
        return f"{self.floor.building.code}-{self.floor.floor_number}-{self.room_number}"


class Bed(models.Model):
    """
    Individual beds in rooms
    """
    STATUS_CHOICES = (
        ('available', 'Available'),
        ('occupied', 'Occupied'),
        ('maintenance', 'Under Maintenance'),
        ('cleaning', 'Being Cleaned'),
        ('reserved', 'Reserved'),
        ('out_of_service', 'Out of Service'),
    )

    BED_TYPES = (
        ('standard', 'Standard'),
        ('icu', 'ICU'),
        ('pediatric', 'Pediatric'),
        ('bariatric', 'Bariatric'),
        ('isolation', 'Isolation'),
        ('maternity', 'Maternity'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    bed_number = models.CharField(max_length=10)
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='beds')
    bed_type = models.CharField(max_length=20, choices=BED_TYPES, default='standard')

    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='available')
    is_active = models.BooleanField(default=True)

    # Current occupancy
    current_patient = models.ForeignKey(
        'patients.Patient',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='current_bed'
    )
    admission_date = models.DateTimeField(null=True, blank=True)

    # Features
    has_monitoring = models.BooleanField(default=False)
    has_ventilator = models.BooleanField(default=False)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['room', 'bed_number']
        unique_together = ['room', 'bed_number']

    def __str__(self):
        return f"Bed {self.bed_number} - {self.room}"


class EquipmentCategory(models.Model):
    """
    Categories for medical equipment
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    requires_certification = models.BooleanField(default=False)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'Equipment Categories'

    def __str__(self):
        return self.name


class Equipment(models.Model):
    """
    Medical equipment and devices
    """
    STATUS_CHOICES = (
        ('available', 'Available'),
        ('in_use', 'In Use'),
        ('maintenance', 'Under Maintenance'),
        ('repair', 'Under Repair'),
        ('calibration', 'Calibration Required'),
        ('retired', 'Retired'),
        ('out_of_service', 'Out of Service'),
    )

    CONDITION_CHOICES = (
        ('excellent', 'Excellent'),
        ('good', 'Good'),
        ('fair', 'Fair'),
        ('poor', 'Poor'),
        ('needs_replacement', 'Needs Replacement'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    equipment_id = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=200)
    category = models.ForeignKey(EquipmentCategory, on_delete=models.CASCADE, related_name='equipment')

    # Equipment details
    manufacturer = models.CharField(max_length=100)
    model_number = models.CharField(max_length=100)
    serial_number = models.CharField(max_length=100, unique=True)

    # Purchase information
    purchase_date = models.DateField()
    purchase_price = models.DecimalField(max_digits=12, decimal_places=2)
    warranty_expiry = models.DateField(null=True, blank=True)
    supplier = models.CharField(max_length=200, blank=True)

    # Current status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='available')
    condition = models.CharField(max_length=20, choices=CONDITION_CHOICES, default='excellent')

    # Location
    current_room = models.ForeignKey(Room, on_delete=models.SET_NULL, null=True, blank=True, related_name='equipment')
    assigned_to = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_equipment'
    )

    # Maintenance
    last_maintenance_date = models.DateField(null=True, blank=True)
    next_maintenance_date = models.DateField(null=True, blank=True)
    maintenance_interval_days = models.PositiveIntegerField(null=True, blank=True)

    # Additional information
    description = models.TextField(blank=True)
    specifications = models.JSONField(default=dict, blank=True)
    notes = models.TextField(blank=True)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['equipment_id']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['category']),
            models.Index(fields=['current_room']),
        ]

    def __str__(self):
        return f"{self.equipment_id} - {self.name}"

    @property
    def is_maintenance_due(self):
        if self.next_maintenance_date:
            return self.next_maintenance_date <= timezone.now().date()
        return False

    def save(self, *args, **kwargs):
        if not self.equipment_id:
            # Generate equipment ID if not provided
            last_equipment = Equipment.objects.order_by('id').last()
            if last_equipment:
                last_id = int(last_equipment.equipment_id.split('EQ')[1])
                self.equipment_id = f'EQ{last_id + 1:06d}'
            else:
                self.equipment_id = 'EQ000001'
        super().save(*args, **kwargs)


class MaintenanceRecord(models.Model):
    """
    Equipment maintenance records
    """
    MAINTENANCE_TYPES = (
        ('preventive', 'Preventive'),
        ('corrective', 'Corrective'),
        ('emergency', 'Emergency'),
        ('calibration', 'Calibration'),
        ('inspection', 'Inspection'),
    )

    STATUS_CHOICES = (
        ('scheduled', 'Scheduled'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('deferred', 'Deferred'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    equipment = models.ForeignKey(Equipment, on_delete=models.CASCADE, related_name='maintenance_records')
    maintenance_type = models.CharField(max_length=20, choices=MAINTENANCE_TYPES)

    # Scheduling
    scheduled_date = models.DateField()
    actual_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')

    # Personnel
    technician = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='performed_maintenance'
    )
    supervisor = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='supervised_maintenance'
    )

    # Details
    description = models.TextField()
    work_performed = models.TextField(blank=True)
    parts_replaced = models.TextField(blank=True)
    cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    # Results
    equipment_condition_before = models.CharField(max_length=20, choices=Equipment.CONDITION_CHOICES, blank=True)
    equipment_condition_after = models.CharField(max_length=20, choices=Equipment.CONDITION_CHOICES, blank=True)
    next_maintenance_date = models.DateField(null=True, blank=True)

    # Documentation
    maintenance_report = models.FileField(upload_to='maintenance_reports/', null=True, blank=True)
    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-scheduled_date']

    def __str__(self):
        return f"{self.equipment.equipment_id} - {self.maintenance_type} - {self.scheduled_date}"


class RoomAssignment(models.Model):
    """
    Track room assignments for patients
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey('patients.Patient', on_delete=models.CASCADE, related_name='room_assignments')
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='assignments')
    bed = models.ForeignKey(Bed, on_delete=models.CASCADE, related_name='assignments', null=True, blank=True)

    # Assignment details
    assigned_date = models.DateTimeField(default=timezone.now)
    discharge_date = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    # Assignment reason
    assignment_reason = models.TextField(blank=True)
    assigned_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='room_assignments_made'
    )

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-assigned_date']
        indexes = [
            models.Index(fields=['patient', 'assigned_date']),
            models.Index(fields=['room', 'assigned_date']),
        ]

    def __str__(self):
        return f"{self.patient.user.get_full_name()} - {self.room} - {self.assigned_date.date()}"
