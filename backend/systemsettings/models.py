from django.db import models


class SystemSetting(models.Model):
    nas_base_path = models.CharField(max_length=500, default="/mnt/nas/documents")
    max_file_size = models.PositiveIntegerField(default=20)
    auto_archive = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)
