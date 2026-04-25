from rest_framework import serializers

from .models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    id = serializers.CharField(read_only=True)
    userId = serializers.CharField(source="user_id", read_only=True)
    userEmail = serializers.EmailField(source="user_email", required=False, allow_blank=True)
    ipAddress = serializers.IPAddressField(source="ip_address", required=False, allow_null=True)
    createdAt = serializers.DateTimeField(source="created_at", read_only=True)
    targetType = serializers.CharField(source="target_type", required=False, allow_blank=True, allow_null=True)
    targetName = serializers.CharField(source="target_name", required=False, allow_blank=True, allow_null=True)
    targetOrgUnit = serializers.CharField(source="target_org_unit", required=False, allow_blank=True, allow_null=True)
    userFullName = serializers.SerializerMethodField()
    userRole = serializers.SerializerMethodField()
    displayOrgUnit = serializers.SerializerMethodField()

    class Meta:
        model = AuditLog
        fields = [
            "id",
            "userId",
            "userEmail",
            "action",
            "details",
            "ipAddress",
            "createdAt",
            "targetType",
            "targetName",
            "targetOrgUnit",
            "userFullName",
            "userRole",
            "displayOrgUnit",
        ]

    def get_userFullName(self, obj):
        if obj.user:
            return obj.user.get_full_name() or obj.user.email
        return "System"

    def get_userRole(self, obj):
        return getattr(obj.user, "role", None) or "System"

    def get_displayOrgUnit(self, obj):
        if obj.target_org_unit:
            return obj.target_org_unit
        org_unit = getattr(getattr(obj, "user", None), "org_unit", None)
        if org_unit:
            return org_unit.name
        return "Global Access"
