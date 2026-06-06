from rest_framework import serializers

from .models import SystemSettings


class SystemSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemSettings
        fields = ["upload_limit_mb", "storage_quota_mb", "updated_at"]
        read_only_fields = ["updated_at"]

    def validate_upload_limit_mb(self, value):
        if value < 1 or value > 500:
            raise serializers.ValidationError("Upload limit must be between 1 and 500 MB.")
        return value

    def validate_storage_quota_mb(self, value):
        if value < 1:
            raise serializers.ValidationError("Storage quota must be at least 1 MB.")
        max_quota_mb = 1048576  # 1 TB
        if value > max_quota_mb:
            raise serializers.ValidationError("Storage quota cannot exceed 1 TB (1048576 MB).")
        return value


class SystemSettingsPublicSerializer(serializers.ModelSerializer):
    """Read-only subset for all authenticated users."""

    storage_quota_exceeded = serializers.SerializerMethodField()
    storage_used_mb = serializers.SerializerMethodField()
    storage_remaining_mb = serializers.SerializerMethodField()
    storage_usage_percentage = serializers.SerializerMethodField()

    class Meta:
        model = SystemSettings
        fields = [
            "upload_limit_mb",
            "storage_quota_mb",
            "storage_quota_exceeded",
            "storage_used_mb",
            "storage_remaining_mb",
            "storage_usage_percentage",
        ]

    def _summary(self, obj):
        if not hasattr(self, "_storage_summary"):
            from notifications.storage_alerts import get_global_storage_summary

            self._storage_summary = get_global_storage_summary()
        return self._storage_summary

    def get_storage_quota_exceeded(self, obj):
        return self._summary(obj)["quota_exceeded"]

    def get_storage_used_mb(self, obj):
        return self._summary(obj)["used_mb"]

    def get_storage_remaining_mb(self, obj):
        return self._summary(obj)["remaining_mb"]

    def get_storage_usage_percentage(self, obj):
        return self._summary(obj)["usage_percentage"]
