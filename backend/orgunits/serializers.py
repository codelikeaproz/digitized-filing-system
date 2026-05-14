from django.db.models import Max
from django.utils.text import slugify
from rest_framework import serializers

from config.timezone_utils import format_local_datetime
from .models import OrgType, OrgUnit


class OrgTypeSerializer(serializers.ModelSerializer):
    id = serializers.CharField(read_only=True)
    createdAt = serializers.SerializerMethodField()
    updatedAt = serializers.SerializerMethodField()

    class Meta:
        model = OrgType
        fields = ["id", "name", "code", "is_active", "sort_order", "createdAt", "updatedAt"]
        read_only_fields = ["code", "sort_order", "createdAt", "updatedAt"]

    def validate_name(self, value):
        name = (value or "").strip()
        if not name:
            raise serializers.ValidationError("Org Type name cannot be empty.")

        queryset = OrgType.objects.filter(name__iexact=name)
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise serializers.ValidationError("An Org Type with this name already exists.")
        return name

    def _next_code(self, name):
        base = slugify(name)[:50] or "org-type"
        code = base
        suffix = 2
        while OrgType.objects.filter(code=code).exists():
            tail = f"-{suffix}"
            code = f"{base[:50 - len(tail)]}{tail}"
            suffix += 1
        return code

    def create(self, validated_data):
        validated_data["name"] = validated_data["name"].strip()
        validated_data["code"] = self._next_code(validated_data["name"])
        max_order = OrgType.objects.aggregate(max_order=Max("sort_order"))["max_order"] or 0
        validated_data["sort_order"] = max_order + 10
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if "name" in validated_data:
            validated_data["name"] = validated_data["name"].strip()
            if not instance.code:
                validated_data["code"] = self._next_code(validated_data["name"])
        return super().update(instance, validated_data)

    def get_createdAt(self, obj):
        return format_local_datetime(obj.created_at)

    def get_updatedAt(self, obj):
        return format_local_datetime(obj.updated_at)


class OrgUnitSerializer(serializers.ModelSerializer):
    id = serializers.CharField(read_only=True)
    parentId = serializers.CharField(source="parent_id", required=False, allow_null=True)
    org_type_id = serializers.PrimaryKeyRelatedField(
        source="org_type",
        queryset=OrgType.objects.filter(is_active=True),
        required=False,
        allow_null=True,
    )
    org_type_name = serializers.CharField(source="org_type.name", read_only=True)
    orgTypeId = serializers.SerializerMethodField()
    orgTypeName = serializers.SerializerMethodField()
    createdAt = serializers.SerializerMethodField()

    class Meta:
        model = OrgUnit
        fields = [
            "id",
            "name",
            "parentId",
            "type",
            "org_type_id",
            "org_type_name",
            "orgTypeId",
            "orgTypeName",
            "is_deleted",
            "createdAt",
        ]

    def validate_parentId(self, value):
        return value or None

    def validate(self, attrs):
        instance = getattr(self, "instance", None)
        org_type = attrs.get("org_type")
        legacy_type = (attrs.get("type") or "").strip()

        if not org_type and legacy_type:
            org_type = OrgType.objects.filter(name__iexact=legacy_type, is_active=True).first()
            if not org_type:
                raise serializers.ValidationError({"org_type_id": "Select a valid active Org Type."})
            attrs["org_type"] = org_type

        if not org_type and instance and instance.org_type_id:
            org_type = instance.org_type

        if not org_type:
            raise serializers.ValidationError({"org_type_id": "Org Type is required."})

        attrs["type"] = org_type.name
        return attrs

    def get_orgTypeId(self, obj):
        return str(obj.org_type_id) if obj.org_type_id else None

    def get_orgTypeName(self, obj):
        return obj.type_name

    def get_createdAt(self, obj):
        return format_local_datetime(obj.created_at)
