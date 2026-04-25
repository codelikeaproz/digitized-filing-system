from rest_framework import serializers

from config.timezone_utils import format_local_datetime
from .models import OrgUnit


class OrgUnitSerializer(serializers.ModelSerializer):
    id = serializers.CharField(read_only=True)
    parentId = serializers.CharField(source="parent_id", required=False, allow_null=True)
    createdAt = serializers.SerializerMethodField()

    class Meta:
        model = OrgUnit
        fields = ["id", "name", "parentId", "type", "is_deleted", "createdAt"]

    def validate_parentId(self, value):
        return value or None

    def get_createdAt(self, obj):
        return format_local_datetime(obj.created_at)
