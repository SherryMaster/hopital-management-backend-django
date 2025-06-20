from functools import wraps
from django.http import JsonResponse
from django.core.exceptions import PermissionDenied
from rest_framework import status
from rest_framework.response import Response


def require_user_type(*allowed_types):
    """
    Decorator to require specific user types for view access.
    
    Usage:
        @require_user_type('admin', 'doctor')
        def my_view(request):
            # Only admins and doctors can access this view
            pass
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return JsonResponse(
                    {'error': 'Authentication required'}, 
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            if request.user.user_type not in allowed_types:
                return JsonResponse(
                    {'error': f'Access denied. Required user types: {", ".join(allowed_types)}'}, 
                    status=status.HTTP_403_FORBIDDEN
                )
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def require_permission(*permissions):
    """
    Decorator to require specific permissions for view access.
    
    Usage:
        @require_permission('accounts.view_user', 'accounts.change_user')
        def my_view(request):
            # Only users with these permissions can access this view
            pass
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return JsonResponse(
                    {'error': 'Authentication required'}, 
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            # Check if user has all required permissions
            missing_permissions = []
            for permission in permissions:
                if not request.user.has_perm(permission):
                    missing_permissions.append(permission)
            
            if missing_permissions:
                return JsonResponse(
                    {
                        'error': 'Insufficient permissions',
                        'missing_permissions': missing_permissions
                    }, 
                    status=status.HTTP_403_FORBIDDEN
                )
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def require_admin(view_func):
    """
    Decorator to require admin access.
    
    Usage:
        @require_admin
        def my_view(request):
            # Only admins can access this view
            pass
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse(
                {'error': 'Authentication required'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        if not (request.user.user_type == 'admin' or request.user.is_staff or request.user.is_superuser):
            return JsonResponse(
                {'error': 'Admin access required'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        return view_func(request, *args, **kwargs)
    return wrapper


def require_staff_or_admin(view_func):
    """
    Decorator to require staff or admin access.
    
    Usage:
        @require_staff_or_admin
        def my_view(request):
            # Only staff or admins can access this view
            pass
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse(
                {'error': 'Authentication required'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        staff_types = ['admin', 'doctor', 'nurse', 'receptionist', 'lab_technician', 'pharmacist']
        if not (request.user.user_type in staff_types or request.user.is_staff):
            return JsonResponse(
                {'error': 'Staff access required'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        return view_func(request, *args, **kwargs)
    return wrapper


class RoleBasedAccessMixin:
    """
    Mixin for DRF ViewSets to add role-based access control.
    
    Usage:
        class MyViewSet(RoleBasedAccessMixin, viewsets.ModelViewSet):
            allowed_user_types = ['admin', 'doctor']
            required_permissions = ['myapp.view_model']
    """
    allowed_user_types = None
    required_permissions = None
    
    def check_permissions(self, request):
        """
        Check if the user has the required permissions and user type.
        """
        super().check_permissions(request)
        
        # Check user type
        if self.allowed_user_types and request.user.is_authenticated:
            if request.user.user_type not in self.allowed_user_types:
                self.permission_denied(
                    request,
                    message=f'Access denied. Required user types: {", ".join(self.allowed_user_types)}'
                )
        
        # Check specific permissions
        if self.required_permissions and request.user.is_authenticated:
            missing_permissions = []
            for permission in self.required_permissions:
                if not request.user.has_perm(permission):
                    missing_permissions.append(permission)
            
            if missing_permissions:
                self.permission_denied(
                    request,
                    message=f'Insufficient permissions: {", ".join(missing_permissions)}'
                )


def check_object_permission(user, obj, permission_type='view'):
    """
    Helper function to check object-level permissions.
    
    Args:
        user: The user requesting access
        obj: The object being accessed
        permission_type: Type of permission ('view', 'change', 'delete')
    
    Returns:
        bool: True if user has permission, False otherwise
    """
    if not user.is_authenticated:
        return False
    
    # Admins have access to everything
    if user.user_type == 'admin' or user.is_superuser:
        return True
    
    # Check if object belongs to user
    if hasattr(obj, 'user') and obj.user == user:
        return True
    
    # Check if object is related to user's patient profile
    if hasattr(obj, 'patient') and hasattr(user, 'patient_profile'):
        if obj.patient == user.patient_profile:
            return True
    
    # Check if object is related to user's doctor profile
    if hasattr(obj, 'doctor') and hasattr(user, 'doctor_profile'):
        if obj.doctor == user.doctor_profile:
            return True
    
    # Additional role-specific checks can be added here
    
    return False
