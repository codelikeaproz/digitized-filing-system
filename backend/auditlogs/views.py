from rest_framework import viewsets

from .models import AuditLog
from .serializers import AuditLogSerializer


class AuditLogViewSet(viewsets.ModelViewSet):
    serializer_class = AuditLogSerializer

    def get_queryset(self):
        return AuditLog.objects.all().order_by("-created_at")

    def perform_create(self, serializer):
        user = self.request.user if self.request.user.is_authenticated else None
        serializer.save(
            user=user,
            user_email=getattr(user, "email", "") or "system",
            ip_address=self.request.META.get("REMOTE_ADDR"),
        )
