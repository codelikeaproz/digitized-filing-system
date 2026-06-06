from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from auditlogs.models import log_audit

from .models import SystemSettings
from .serializers import SystemSettingsPublicSerializer, SystemSettingsSerializer
from .services import get_system_settings, invalidate_system_settings_cache


class SystemSettingsAPIView(APIView):
    """GET for all authenticated users; PATCH admin-only."""

    def get(self, request):
        settings = get_system_settings()
        if getattr(request.user, "role", None) == "admin":
            return Response(SystemSettingsSerializer(settings).data)
        return Response(SystemSettingsPublicSerializer(settings).data)

    def patch(self, request):
        if getattr(request.user, "role", None) != "admin":
            raise PermissionDenied("Only Admin users can update system settings.")

        settings = get_system_settings()
        old_quota = settings.storage_quota_mb
        serializer = SystemSettingsSerializer(settings, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        invalidate_system_settings_cache()

        new_quota = serializer.instance.storage_quota_mb
        if new_quota > old_quota:
            from notifications.storage_alerts import reset_thresholds_if_quota_increased

            reset_thresholds_if_quota_increased(new_quota)

        log_audit(
            request.user,
            "UPDATE_SYSTEM_SETTINGS",
            (
                f"Updated system settings: upload_limit_mb={serializer.instance.upload_limit_mb}, "
                f"storage_quota_mb={serializer.instance.storage_quota_mb}"
            ),
            target_type="system_settings",
            target_name="SystemSettings",
        )
        return Response(SystemSettingsSerializer(serializer.instance).data)
