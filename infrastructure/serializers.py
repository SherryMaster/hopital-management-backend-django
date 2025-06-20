from rest_framework import serializers
from .models import Building, Room, Equipment, RoomType, EquipmentCategory


class BuildingSerializer(serializers.ModelSerializer):
    """
    Serializer for Building model
    """
    floor_count = serializers.SerializerMethodField()
    room_count = serializers.SerializerMethodField()

    class Meta:
        model = Building
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')

    def get_floor_count(self, obj):
        """Get number of floors in this building"""
        return obj.building_floors.count()

    def get_room_count(self, obj):
        """Get total number of rooms in this building"""
        return Room.objects.filter(floor__building=obj).count()


class RoomTypeSerializer(serializers.ModelSerializer):
    """
    Serializer for RoomType model
    """
    room_count = serializers.SerializerMethodField()

    class Meta:
        model = RoomType
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')

    def get_room_count(self, obj):
        """Get number of rooms of this type"""
        return obj.rooms.count()


class EquipmentCategorySerializer(serializers.ModelSerializer):
    """
    Serializer for EquipmentCategory model
    """
    equipment_count = serializers.SerializerMethodField()

    class Meta:
        model = EquipmentCategory
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')

    def get_equipment_count(self, obj):
        """Get number of equipment items in this category"""
        return obj.equipment.count()


class RoomSerializer(serializers.ModelSerializer):
    """
    Serializer for Room model
    """
    building_name = serializers.CharField(source='floor.building.name', read_only=True)
    floor_number = serializers.IntegerField(source='floor.floor_number', read_only=True)
    room_type_name = serializers.CharField(source='room_type.name', read_only=True)
    equipment_count = serializers.SerializerMethodField()

    class Meta:
        model = Room
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')

    def get_equipment_count(self, obj):
        """Get number of equipment items in this room"""
        return obj.equipment.count()


class EquipmentSerializer(serializers.ModelSerializer):
    """
    Serializer for Equipment model
    """
    category_name = serializers.CharField(source='category.name', read_only=True)
    room_number = serializers.CharField(source='current_room.room_number', read_only=True)
    building_name = serializers.CharField(source='current_room.floor.building.name', read_only=True)

    class Meta:
        model = Equipment
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')


class BuildingDetailSerializer(BuildingSerializer):
    """
    Detailed serializer for Building with related objects
    """
    building_floors = serializers.SerializerMethodField()

    class Meta(BuildingSerializer.Meta):
        fields = '__all__'

    def get_building_floors(self, obj):
        """Get floors in this building"""
        from .models import Floor
        floors = Floor.objects.filter(building=obj)
        return [{'floor_number': f.floor_number, 'name': f.name} for f in floors]


class RoomDetailSerializer(RoomSerializer):
    """
    Detailed serializer for Room with related equipment
    """
    equipment = EquipmentSerializer(many=True, read_only=True)

    class Meta(RoomSerializer.Meta):
        fields = '__all__'
