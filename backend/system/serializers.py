from rest_framework import serializers

from .models import SystemSettings


from rest_framework import serializers

from .models import SystemSettings


class SystemStorageAllocationMixin(serializers.Serializer):
    allocated_storage_mb = serializers.SerializerMethodField()
    allocation_remaining_mb = serializers.SerializerMethodField()
    allocation_percentage = serializers.SerializerMethodField()

    def _allocation_summary(self, obj):
        if not hasattr(self, "_allocation_summary_cache"):
            from notifications.storage_alerts import get_allocation_summary

            self._allocation_summary_cache = get_allocation_summary()
        return self._allocation_summary_cache

    def get_allocated_storage_mb(self, obj):
        return self._allocation_summary(obj)["allocated_mb"]

    def get_allocation_remaining_mb(self, obj):
        return self._allocation_summary(obj)["remaining_mb"]

    def get_allocation_percentage(self, obj):
        return self._allocation_summary(obj)["allocation_percentage"]


class SystemSettingsSerializer(SystemStorageAllocationMixin, serializers.ModelSerializer):
    class Meta:
        model = SystemSettings
        fields = [
            "upload_limit_mb",
            "storage_quota_mb",
            "updated_at",
            "allocated_storage_mb",
            "allocation_remaining_mb",
            "allocation_percentage",
        ]
        read_only_fields = [
            "updated_at",
            "allocated_storage_mb",
            "allocation_remaining_mb",
            "allocation_percentage",
        ]

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


class SystemSettingsPublicSerializer(SystemStorageAllocationMixin, serializers.ModelSerializer):
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
            "allocated_storage_mb",
            "allocation_remaining_mb",
            "allocation_percentage",
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
