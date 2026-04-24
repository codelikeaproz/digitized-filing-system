from rest_framework import serializers

from .models import User


class UserSerializer(serializers.ModelSerializer):
    id = serializers.CharField(read_only=True)
    fullName = serializers.SerializerMethodField()
    orgUnitId = serializers.CharField(source="org_unit_id", required=False, allow_blank=True, allow_null=True)
    orgUnitName = serializers.CharField(source="org_unit.name", read_only=True)
    isActive = serializers.BooleanField(source="is_active_status", required=False)
    createdAt = serializers.DateTimeField(source="date_joined", read_only=True)

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
        ]
        extra_kwargs = {"password": {"write_only": True, "required": False}}

    def get_fullName(self, obj):
        return obj.get_full_name() or obj.email

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
