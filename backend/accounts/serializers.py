from rest_framework import serializers
from django.contrib.auth.password_validation import password_changed
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError

from config.timezone_utils import format_local_datetime
from orgunits.models import OrgUnit
from .models import User


class UserSerializer(serializers.ModelSerializer):
    id = serializers.CharField(read_only=True)
    fullName = serializers.SerializerMethodField()
    orgUnitId = serializers.CharField(source="org_unit_id", required=False, allow_blank=True, allow_null=True)
    orgUnitName = serializers.CharField(source="org_unit.name", read_only=True)
    isActive = serializers.BooleanField(source="is_active_status", required=False)
    createdAt = serializers.SerializerMethodField()
    isLastActiveAdmin = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "password",
            "fullName",
            "role",
            "orgUnitId",
            "orgUnitName",
            "isActive",
            "createdAt",
            "isLastActiveAdmin",
        ]
        extra_kwargs = {"password": {"write_only": True, "required": False}}

    def get_fullName(self, obj):
        return obj.get_full_name() or obj.email

    def get_createdAt(self, obj):
        return format_local_datetime(obj.date_joined)

    def get_isLastActiveAdmin(self, obj):
        if obj.role != "admin" or not obj.is_active_status:
            return False
        return User.objects.filter(role="admin", is_active_status=True).count() == 1

    def validate(self, attrs):
        role = attrs.get("role", getattr(self.instance, "role", "staff"))

        if role == "admin":
            attrs["org_unit_id"] = None
            return attrs

        org_unit_id = attrs.get("org_unit_id", serializers.empty)
        if org_unit_id is serializers.empty:
            if self.instance and self.instance.org_unit_id:
                return attrs
            raise serializers.ValidationError({"message": "Organization unit is required for Dept Head and Staff."})

        if org_unit_id in ("", None):
            raise serializers.ValidationError({"message": "Organization unit is required for Dept Head and Staff."})

        try:
            org_unit = OrgUnit.objects.get(pk=org_unit_id, is_deleted=False)
        except (OrgUnit.DoesNotExist, TypeError, ValueError):
            raise serializers.ValidationError({"message": "Invalid organization unit."})

        attrs["org_unit_id"] = org_unit.pk
        return attrs

    def _apply_full_name(self, user, full_name):
        if not full_name:
            return
        parts = full_name.strip().split(" ", 1)
        user.first_name = parts[0]
        user.last_name = parts[1] if len(parts) > 1 else ""

    def create(self, validated_data):
        full_name = self.initial_data.get("fullName")
        password = validated_data.pop("password", None)
        user = User(**validated_data)
        self._apply_full_name(user, full_name)
        user.set_password(password)
        user.save()
        return user

    def update(self, instance, validated_data):
        full_name = self.initial_data.get("fullName")
        password = validated_data.pop("password", None)
        for key, value in validated_data.items():
            setattr(instance, key, value)
        self._apply_full_name(instance, full_name)
        if password:
            instance.set_password(password)
        instance.save()
        return instance


class PasswordChangeSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True, trim_whitespace=False)
    new_password = serializers.CharField(write_only=True, trim_whitespace=False)
    confirm_password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate(self, attrs):
        user = self.context["request"].user

        if not user.check_password(attrs["current_password"]):
            raise serializers.ValidationError({"message": "Current password is incorrect."})

        if attrs["new_password"] != attrs["confirm_password"]:
            raise serializers.ValidationError({"message": "New password and confirm password do not match."})

        if attrs["current_password"] == attrs["new_password"]:
            raise serializers.ValidationError({"message": "New password must be different from current password."})

        try:
            validate_password(attrs["new_password"], user)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(
                {
                    "message": "Password does not meet security requirements.",
                    "errors": list(exc.messages),
                }
            ) from exc
        return attrs

    def save(self, **kwargs):
        user = self.context["request"].user
        user.set_password(self.validated_data["new_password"])
        user.save(update_fields=["password"])
        password_changed(self.validated_data["new_password"], user)
        return user
