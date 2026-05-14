from django.conf import settings
from django.db import models
from django.utils import timezone

from orgunits.models import OrgUnit


class Category(models.Model):
    name = models.CharField(max_length=100)
    org_unit = models.ForeignKey(OrgUnit, on_delete=models.CASCADE, null=True, blank=True, related_name="categories")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        unique_together = ("name", "org_unit")
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name


class Folder(models.Model):
    name = models.CharField(max_length=255)
    parent = models.ForeignKey("self", on_delete=models.CASCADE, null=True, blank=True, related_name="children")
    org_unit = models.ForeignKey(OrgUnit, on_delete=models.CASCADE, null=True, blank=True, related_name="folders")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="deleted_folders",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def get_full_path(self):
        if self.parent_id:
            return f"{self.parent.get_full_path()} > {self.name}"
        return self.name

    def soft_delete(self, user=None):
        now = timezone.now()
        folder_ids = [self.id]
        stack = list(self.children.all())
        while stack:
            child = stack.pop()
            folder_ids.append(child.id)
            stack.extend(child.children.all())

        self.__class__.objects.filter(id__in=folder_ids).update(
            is_deleted=True,
            deleted_at=now,
            deleted_by=user,
        )
        Document.objects.filter(folder_id__in=folder_ids, is_deleted=False).update(
            is_deleted=True,
            deleted_at=now,
            deleted_by=user,
        )


class Document(models.Model):
    STATUS_CHOICES = [("Received", "Received")]
    SOURCE_CHOICES = [("Scanned", "Scanned"), ("Uploaded", "Uploaded")]

    title = models.CharField(max_length=255)
    file = models.FileField(upload_to="documents/%Y/%m/%d/")
    file_path = models.CharField(max_length=500, blank=True, default="")
    folder = models.ForeignKey(Folder, on_delete=models.CASCADE, related_name="documents")
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name="documents")
    uploader = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    code = models.CharField(max_length=100, unique=True, null=True, blank=True)
    requestor = models.CharField(max_length=255, null=True, blank=True)
    description = models.CharField(max_length=50, null=True, blank=True)
    keywords = models.JSONField(default=list, blank=True)
    filing_year = models.PositiveIntegerField(default=timezone.now().year)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="Received")
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default="Uploaded")
    mime_type = models.CharField(max_length=100, blank=True)
    file_size = models.BigIntegerField(null=True, blank=True)
    extracted_text = models.TextField(blank=True)
    ai_summary = models.TextField(blank=True)
    content_hash = models.CharField(max_length=64, blank=True, db_index=True)
    last_indexed_at = models.DateTimeField(null=True, blank=True)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="deleted_documents",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

    def soft_delete(self, user=None):
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.deleted_by = user
        self.save(update_fields=["is_deleted", "deleted_at", "deleted_by"])


class ScannerStation(models.Model):
    STATUS_CHOICES = [
        ("CONNECTED", "Connected"),
        ("NOT_DETECTED", "Not Detected"),
        ("ERROR", "Error"),
    ]

    station_id = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="NOT_DETECTED")
    watched_folder = models.CharField(max_length=500, blank=True)
    last_seen_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["station_id"]

    def __str__(self):
        return self.name or self.station_id


class ScanJob(models.Model):
    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("WAITING_FOR_SCAN", "Waiting for Scan"),
        ("UPLOADING", "Uploading"),
        ("COMPLETED", "Completed"),
        ("FAILED", "Failed"),
        ("CANCELLED", "Cancelled"),
    ]

    station_id = models.CharField(max_length=100)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    folder = models.ForeignKey(Folder, on_delete=models.PROTECT, related_name="scan_jobs")
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="scan_jobs")
    uploaded_document = models.OneToOneField(
        Document,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="scan_job",
    )
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="PENDING")
    code = models.CharField(max_length=100)
    title = models.CharField(max_length=255, blank=True)
    requestor = models.CharField(max_length=255, blank=True)
    description = models.CharField(max_length=50, blank=True)
    keywords = models.JSONField(default=list, blank=True)
    original_filename = models.CharField(max_length=255, blank=True)
    sha256 = models.CharField(max_length=64, blank=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["station_id", "status", "created_at"], name="documents_s_station_25d655_idx"),
            models.Index(fields=["sha256"], name="documents_s_sha256_409f25_idx"),
        ]

    def __str__(self):
        return f"{self.station_id} - {self.code} - {self.status}"
