from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    user_email = models.EmailField(blank=True)
    action = models.CharField(max_length=100)
    details = models.TextField()
    target_type = models.CharField(max_length=50, null=True, blank=True)
    target_name = models.CharField(max_length=255, null=True, blank=True)
    target_org_unit = models.CharField(max_length=255, null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.action} - {self.user_email or 'system'}"


def log_audit(user, action, details, target_type=None, target_name=None, target_org_unit=None, ip_address=None):
    return AuditLog.objects.create(
        user=user if getattr(user, "is_authenticated", False) else None,
        user_email=getattr(user, "email", "") or "system",
        action=action,
        details=details,
        target_type=target_type,
        target_name=target_name,
        target_org_unit=target_org_unit,
        ip_address=ip_address,
    )
