"""Singleton system-wide configuration (upload limits, global storage quota)."""
from django.db import models

DEFAULT_UPLOAD_LIMIT_MB = 15
DEFAULT_STORAGE_QUOTA_MB = 500
MAX_SYSTEM_STORAGE_QUOTA_MB = 5_242_880  # 5 TB
SINGLETON_PK = 1


class SystemSettings(models.Model):
    upload_limit_mb = models.PositiveIntegerField(default=DEFAULT_UPLOAD_LIMIT_MB)
    storage_quota_mb = models.PositiveIntegerField(default=DEFAULT_STORAGE_QUOTA_MB)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "system_settings"
        verbose_name = "System Settings"
        verbose_name_plural = "System Settings"

    def __str__(self):
        return f"SystemSettings(upload={self.upload_limit_mb}MB, quota={self.storage_quota_mb}MB)"

    def save(self, *args, **kwargs):
        self.pk = SINGLETON_PK
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(
            pk=SINGLETON_PK,
            defaults={
                "upload_limit_mb": DEFAULT_UPLOAD_LIMIT_MB,
                "storage_quota_mb": DEFAULT_STORAGE_QUOTA_MB,
            },
        )
        return obj
