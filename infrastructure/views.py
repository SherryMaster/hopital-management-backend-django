from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from drf_spectacular.utils import extend_schema, extend_schema_view
from .models import Building, Room, Equipment, RoomType, EquipmentCategory
from .serializers import BuildingSerializer, RoomSerializer, EquipmentSerializer, RoomTypeSerializer, EquipmentCategorySerializer


@extend_schema_view(
    list=extend_schema(
        summary="List buildings",
        description="Get a list of all hospital buildings",
        tags=['Hospital Infrastructure']
    ),
    create=extend_schema(
        summary="Create building",
        description="Create a new hospital building",
        tags=['Hospital Infrastructure']
    ),
    retrieve=extend_schema(
        summary="Get building details",
        description="Get detailed information about a specific building",
        tags=['Hospital Infrastructure']
    ),
    update=extend_schema(
        summary="Update building",
        description="Update building information",
        tags=['Hospital Infrastructure']
    ),
    partial_update=extend_schema(
        summary="Partially update building",
        description="Partially update building information",
        tags=['Hospital Infrastructure']
    ),
    destroy=extend_schema(
        summary="Delete building",
        description="Delete a building",
        tags=['Hospital Infrastructure']
    )
)
class BuildingViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing hospital buildings
    """
    queryset = Building.objects.all()
    serializer_class = BuildingSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['is_active']
    search_fields = ['name', 'code', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']


@extend_schema_view(
    list=extend_schema(
        summary="List rooms",
        description="Get a list of all hospital rooms",
        tags=['Hospital Infrastructure']
    ),
    create=extend_schema(
        summary="Create room",
        description="Create a new hospital room",
        tags=['Hospital Infrastructure']
    ),
    retrieve=extend_schema(
        summary="Get room details",
        description="Get detailed information about a specific room",
        tags=['Hospital Infrastructure']
    ),
    update=extend_schema(
        summary="Update room",
        description="Update room information",
        tags=['Hospital Infrastructure']
    ),
    partial_update=extend_schema(
        summary="Partially update room",
        description="Partially update room information",
        tags=['Hospital Infrastructure']
    ),
    destroy=extend_schema(
        summary="Delete room",
        description="Delete a room",
        tags=['Hospital Infrastructure']
    )
)
class RoomViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing hospital rooms
    """
    queryset = Room.objects.all()
    serializer_class = RoomSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['floor', 'room_type', 'status', 'is_active']
    search_fields = ['room_number', 'description']
    ordering_fields = ['room_number', 'created_at']
    ordering = ['room_number']


@extend_schema_view(
    list=extend_schema(
        summary="List equipment",
        description="Get a list of all hospital equipment",
        tags=['Hospital Infrastructure']
    ),
    create=extend_schema(
        summary="Create equipment",
        description="Add new hospital equipment",
        tags=['Hospital Infrastructure']
    ),
    retrieve=extend_schema(
        summary="Get equipment details",
        description="Get detailed information about specific equipment",
        tags=['Hospital Infrastructure']
    ),
    update=extend_schema(
        summary="Update equipment",
        description="Update equipment information",
        tags=['Hospital Infrastructure']
    ),
    partial_update=extend_schema(
        summary="Partially update equipment",
        description="Partially update equipment information",
        tags=['Hospital Infrastructure']
    ),
    destroy=extend_schema(
        summary="Delete equipment",
        description="Remove equipment from inventory",
        tags=['Hospital Infrastructure']
    )
)
class EquipmentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing hospital equipment
    """
    queryset = Equipment.objects.all()
    serializer_class = EquipmentSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['category', 'current_room', 'status', 'condition']
    search_fields = ['name', 'model', 'serial_number']
    ordering_fields = ['name', 'purchase_date', 'created_at']
    ordering = ['name']
