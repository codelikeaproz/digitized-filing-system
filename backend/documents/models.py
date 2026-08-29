"""
Document domain models.

Defines the core filing hierarchy:
    OrgUnit → Folder (parent/child) → Document (PDF + metadata)

Soft delete fields (is_deleted, deleted_at, deleted_by) support Recycle Bin.
"""
from django.conf import settings
from django.db import models
from django.utils import timezone

from orgunits.models import OrgUnit


class Category(models.Model):
    name = models.CharField(max_length=100)
    org_unit = models.ForeignKey(OrgUnit, on_delete=models.CASCADE, null=True, blank=True, related_name="categories")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "categories"
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
        db_table = "folders"
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
    SOURCE_CHOICES = [("Scanned", "Scanned"), ("Uploaded", "Uploaded")]

    title = models.CharField(max_length=255)
    file = models.FileField(upload_to="documents/%Y/%m/%d/", blank=True, null=True)
    google_drive_link = models.URLField(max_length=500, blank=True, default="")
    file_path = models.CharField(max_length=500, blank=True, default="")
    folder = models.ForeignKey(Folder, on_delete=models.CASCADE, related_name="documents")
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name="documents")
    uploader = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    code = models.CharField(max_length=100, unique=True, null=True, blank=True)
    requestor = models.CharField(max_length=255, null=True, blank=True)
    description = models.CharField(max_length=50, null=True, blank=True)
    keywords = models.JSONField(default=list, blank=True)
    filing_year = models.PositiveIntegerField(default=timezone.now().year)
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
        db_table = "documents"
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

    def soft_delete(self, user=None):
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.deleted_by = user
        self.save(update_fields=["is_deleted", "deleted_at", "deleted_by"])


class DocumentRequisitioner(models.Model):
    SOURCE_DIRECTORY = "directory"
    SOURCE_MANUAL = "manual"
    SOURCE_CHOICES = [
        (SOURCE_DIRECTORY, "Directory"),
        (SOURCE_MANUAL, "Manual"),
    ]

    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name="requisitioners",
    )
    employee = models.ForeignKey(
        "employees.Employee",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="document_tags",
    )
    source = models.CharField(
        max_length=20,
        choices=SOURCE_CHOICES,
        default=SOURCE_MANUAL,
    )
    employee_number = models.CharField(max_length=50, blank=True, null=True, default=None)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    suffix = models.CharField(max_length=20, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "document_requisitioners"
        ordering = ["created_at", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["document", "employee_number"],
                name="unique_requisitioner_per_document",
            ),
            models.UniqueConstraint(
                fields=["document", "employee"],
                condition=models.Q(employee__isnull=False),
                name="unique_directory_requisitioner_per_document",
            ),
        ]

    def get_full_name(self):
        parts = [self.first_name, self.last_name]
        if self.suffix:
            parts.append(self.suffix)
        return " ".join(part for part in parts if part).strip()

    def __str__(self):
        full_name = self.get_full_name()
        if self.employee_number:
            return f"{self.employee_number} - {full_name}"
        return full_name
