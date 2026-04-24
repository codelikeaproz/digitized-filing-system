from rest_framework import serializers

from .models import OrgUnit


class OrgUnitSerializer(serializers.ModelSerializer):
    id = serializers.CharField(read_only=True)
    parentId = serializers.CharField(source="parent_id", required=False, allow_null=True)
    createdAt = serializers.DateTimeField(source="created_at", read_only=True)

    class Meta:
        model = OrgUnit
        fields = ["id", "name", "parentId", "type", "is_deleted", "createdAt"]

    def validate_parentId(self, value):
        return value or None
