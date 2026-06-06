from django.db import models

SINGLETON_PK = 1


class Notification(models.Model):
    AUDIENCE_ALL = "all"
    AUDIENCE_ADMIN = "admin"
    AUDIENCE_CHOICES = [
        (AUDIENCE_ALL, "All Users"),
        (AUDIENCE_ADMIN, "Administrators"),
    ]

    LEVEL_WARNING = "warning"
    LEVEL_ALERT = "alert"
    LEVEL_CRITICAL = "critical"
    LEVEL_EXCEEDED = "exceeded"
    LEVEL_CHOICES = [
        (LEVEL_WARNING, "Warning"),
        (LEVEL_ALERT, "Alert"),
        (LEVEL_CRITICAL, "Critical"),
        (LEVEL_EXCEEDED, "Exceeded"),
    ]

    title = models.CharField(max_length=120)
    message = models.TextField()
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES, default=LEVEL_WARNING)
    threshold_percent = models.PositiveSmallIntegerField(null=True, blank=True)
    audience = models.CharField(max_length=20, choices=AUDIENCE_CHOICES, default=AUDIENCE_ALL)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class StorageThresholdState(models.Model):
    fired_80 = models.BooleanField(default=False)
    fired_90 = models.BooleanField(default=False)
    fired_95 = models.BooleanField(default=False)
    fired_100 = models.BooleanField(default=False)
    quota_mb_at_last_reset = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Storage Threshold State"
        verbose_name_plural = "Storage Threshold State"

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=SINGLETON_PK)
        return obj

    def save(self, *args, **kwargs):
        self.pk = SINGLETON_PK
        super().save(*args, **kwargs)
