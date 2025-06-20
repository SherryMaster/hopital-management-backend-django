from rest_framework import permissions
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object to edit it.
    """
    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed for any request,
        # so we'll always allow GET, HEAD or OPTIONS requests.
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions are only allowed to the owner of the object.
        return obj.user == request.user


class IsAdminUser(permissions.BasePermission):
    """
    Custom permission to only allow admin users.
    """
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            (request.user.is_staff or request.user.user_type == 'admin')
        )


class IsDoctorUser(permissions.BasePermission):
    """
    Custom permission to only allow doctor users.
    """
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.user_type == 'doctor'
        )


class IsPatientUser(permissions.BasePermission):
    """
    Custom permission to only allow patient users.
    """
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.user_type == 'patient'
        )


class IsStaffUser(permissions.BasePermission):
    """
    Custom permission to only allow staff users (nurses, receptionists, etc.).
    """
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.user_type in ['nurse', 'receptionist', 'lab_technician', 'pharmacist']
        )


class IsDoctorOrStaff(permissions.BasePermission):
    """
    Custom permission to allow doctors or staff users.
    """
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.user_type in ['doctor', 'nurse', 'receptionist', 'lab_technician', 'pharmacist']
        )


class IsPatientOwnerOrStaff(permissions.BasePermission):
    """
    Custom permission to allow patient owners or staff to access patient data.
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        # Staff and doctors can access any patient data
        if request.user.user_type in ['admin', 'doctor', 'nurse', 'receptionist']:
            return True
        
        # Patients can only access their own data
        if request.user.user_type == 'patient':
            # Check if the object has a patient field or is a patient
            if hasattr(obj, 'patient'):
                return obj.patient.user == request.user
            elif hasattr(obj, 'user'):
                return obj.user == request.user
            elif hasattr(obj, 'patient_profile'):
                return obj.patient_profile.user == request.user
        
        return False


class IsDoctorOwnerOrAdmin(permissions.BasePermission):
    """
    Custom permission to allow doctor owners or admins to access doctor data.
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        # Admins can access any doctor data
        if request.user.user_type == 'admin' or request.user.is_staff:
            return True
        
        # Doctors can only access their own data
        if request.user.user_type == 'doctor':
            if hasattr(obj, 'doctor'):
                return obj.doctor.user == request.user
            elif hasattr(obj, 'user'):
                return obj.user == request.user
            elif hasattr(obj, 'doctor_profile'):
                return obj.doctor_profile.user == request.user
        
        return False


class CanViewMedicalRecords(permissions.BasePermission):
    """
    Custom permission for viewing medical records.
    """
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.user_type in ['admin', 'doctor', 'nurse']
        )
    
    def has_object_permission(self, request, view, obj):
        # Admins can view all records
        if request.user.user_type == 'admin':
            return True
        
        # Doctors can view records for their patients
        if request.user.user_type == 'doctor':
            if hasattr(obj, 'doctor'):
                return obj.doctor.user == request.user
            elif hasattr(obj, 'appointment') and hasattr(obj.appointment, 'doctor'):
                return obj.appointment.doctor.user == request.user
        
        # Nurses can view records in their department
        if request.user.user_type == 'nurse':
            # Add logic for department-based access
            return True
        
        return False


class CanManageBilling(permissions.BasePermission):
    """
    Custom permission for managing billing.
    """
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.user_type in ['admin', 'receptionist']
        )


class CanManageAppointments(permissions.BasePermission):
    """
    Custom permission for managing appointments.
    """
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.user_type in ['admin', 'doctor', 'receptionist', 'patient']
        )
    
    def has_object_permission(self, request, view, obj):
        # Admins and receptionists can manage all appointments
        if request.user.user_type in ['admin', 'receptionist']:
            return True
        
        # Doctors can manage their own appointments
        if request.user.user_type == 'doctor':
            return obj.doctor.user == request.user
        
        # Patients can manage their own appointments
        if request.user.user_type == 'patient':
            return obj.patient.user == request.user
        
        return False


def create_user_groups():
    """
    Create default user groups with appropriate permissions.
    """
    # Define groups and their permissions
    groups_permissions = {
        'Administrators': [
            'add_user', 'change_user', 'delete_user', 'view_user',
            'add_patient', 'change_patient', 'delete_patient', 'view_patient',
            'add_doctor', 'change_doctor', 'delete_doctor', 'view_doctor',
            'add_appointment', 'change_appointment', 'delete_appointment', 'view_appointment',
            'add_medicalrecord', 'change_medicalrecord', 'delete_medicalrecord', 'view_medicalrecord',
            'add_invoice', 'change_invoice', 'delete_invoice', 'view_invoice',
        ],
        'Doctors': [
            'view_patient', 'change_patient',
            'view_doctor', 'change_doctor',
            'add_appointment', 'change_appointment', 'view_appointment',
            'add_medicalrecord', 'change_medicalrecord', 'view_medicalrecord',
            'view_invoice',
        ],
        'Nurses': [
            'view_patient', 'change_patient',
            'view_appointment',
            'add_medicalrecord', 'change_medicalrecord', 'view_medicalrecord',
        ],
        'Receptionists': [
            'add_patient', 'change_patient', 'view_patient',
            'add_appointment', 'change_appointment', 'view_appointment',
            'add_invoice', 'change_invoice', 'view_invoice',
        ],
        'Patients': [
            'view_appointment', 'change_appointment',
            'view_medicalrecord',
        ],
        'Lab Technicians': [
            'view_patient',
            'add_medicalrecord', 'change_medicalrecord', 'view_medicalrecord',
        ],
        'Pharmacists': [
            'view_patient',
            'view_medicalrecord',
        ],
    }
    
    for group_name, permission_codenames in groups_permissions.items():
        group, created = Group.objects.get_or_create(name=group_name)
        
        if created:
            print(f"Created group: {group_name}")
        
        # Add permissions to group
        for codename in permission_codenames:
            try:
                permission = Permission.objects.get(codename=codename)
                group.permissions.add(permission)
            except Permission.DoesNotExist:
                print(f"Permission {codename} does not exist")
        
        group.save()


def assign_user_to_group(user):
    """
    Assign user to appropriate group based on user_type.
    """
    group_mapping = {
        'admin': 'Administrators',
        'doctor': 'Doctors',
        'nurse': 'Nurses',
        'receptionist': 'Receptionists',
        'patient': 'Patients',
        'lab_technician': 'Lab Technicians',
        'pharmacist': 'Pharmacists',
    }
    
    group_name = group_mapping.get(user.user_type)
    if group_name:
        try:
            group = Group.objects.get(name=group_name)
            user.groups.add(group)
            print(f"Added user {user.username} to group {group_name}")
        except Group.DoesNotExist:
            print(f"Group {group_name} does not exist")
    else:
        print(f"No group mapping for user_type: {user.user_type}")
