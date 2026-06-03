from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied
from django.utils import timezone
import re

from config.timezone_utils import format_local_datetime
from .models import Category, Document, Folder, ScanJob, ScannerStation
from .permissions import resolve_category_org_unit_for_create


RESERVED_FOLDER_NAMES = {"all files", "root", "trash", "recycle bin"}
DOCUMENT_CODE_PATTERN = re.compile(r"^[A-Za-z0-9-]+$")


def normalize_document_code(value):
    code = (value or "").strip().upper()
    if not code:
        raise serializers.ValidationError("Document Code is required.")
    if not DOCUMENT_CODE_PATTERN.fullmatch(code):
        raise serializers.ValidationError("Document Code can contain letters, numbers, and hyphens only.")
    return code


def ensure_unique_document_code(code, *, document_id=None):
    queryset = Document.objects.filter(code__iexact=code)
    if document_id:
        queryset = queryset.exclude(pk=document_id)
    if queryset.exists():
        raise serializers.ValidationError("Document Code is already used.")

    active_scan_job_exists = ScanJob.objects.filter(
        code__iexact=code,
        status__in=["PENDING", "WAITING_FOR_SCAN", "UPLOADING"],
    ).exists()
    if active_scan_job_exists:
        raise serializers.ValidationError("Document Code is already used by an active scan job.")


class CategorySerializer(serializers.ModelSerializer):
    id = serializers.CharField(read_only=True)
    org_unit = serializers.IntegerField(source="org_unit_id", read_only=True, allow_null=True)
    orgUnitId = serializers.CharField(source="org_unit_id", required=False, allow_null=True)
    createdAt = serializers.SerializerMethodField()
    document_count = serializers.SerializerMethodField()
    documentCount = serializers.SerializerMethodField()
    inUse = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ["id", "name", "org_unit", "orgUnitId", "createdAt", "document_count", "documentCount", "inUse"]

    def get_document_count(self, obj):
        return self.get_documentCount(obj)

    def get_documentCount(self, obj):
        annotated_count = getattr(obj, "active_document_count", None)
        if annotated_count is not None:
            return annotated_count
        return obj.documents.filter(is_deleted=False).count()

    def get_inUse(self, obj):
        return self.get_documentCount(obj) > 0

    def get_createdAt(self, obj):
        return format_local_datetime(obj.created_at)

    def validate_orgUnitId(self, value):
        return value or None

    def validate_name(self, value):
        name = (value or "").strip()
        if not name:
            raise serializers.ValidationError("Category name cannot be empty.")
        return name

    def _assign_category_org_unit(self, attrs):
        request = self.context.get("request")
        user = getattr(request, "user", None) if request else None
        if not user or not getattr(user, "is_authenticated", False):
            return attrs

        requested = attrs.get("org_unit_id")
        try:
            resolved_org_unit_id = resolve_category_org_unit_for_create(user, requested)
        except PermissionDenied as exc:
            detail = exc.detail
            if isinstance(detail, (list, tuple)):
                detail = detail[0] if detail else "Permission denied."
            raise serializers.ValidationError({"orgUnitId": str(detail)}) from exc

        attrs["org_unit_id"] = resolved_org_unit_id
        return attrs

    def validate(self, attrs):
        name = attrs.get("name")
        if name is None and self.instance:
            name = self.instance.name

        if not self.instance:
            attrs = self._assign_category_org_unit(attrs)
            org_unit_id = attrs.get("org_unit_id")
        else:
            attrs.pop("org_unit_id", None)
            org_unit_id = self.instance.org_unit_id

        if not name:
            return attrs

        duplicate_queryset = Category.objects.filter(name__iexact=name.strip())
        if org_unit_id:
            duplicate_queryset = duplicate_queryset.filter(org_unit_id=org_unit_id)
        else:
            duplicate_queryset = duplicate_queryset.filter(org_unit__isnull=True)

        if self.instance:
            duplicate_queryset = duplicate_queryset.exclude(pk=self.instance.pk)

        if duplicate_queryset.exists():
            if org_unit_id:
                raise serializers.ValidationError(
                    {"name": "A category with this name already exists in this Org Unit."}
                )
            raise serializers.ValidationError(
                {
                    "name": (
                        "A category with this name already exists as an unassigned (Global) category. "
                        "An Admin can remove it from Manage Categories."
                    )
                }
            )

        return attrs


class FolderSerializer(serializers.ModelSerializer):
    id = serializers.CharField(read_only=True)
    parentId = serializers.CharField(source="parent_id", required=False, allow_null=True)
    orgUnitId = serializers.CharField(source="org_unit_id", required=False, allow_null=True)
    createdBy = serializers.CharField(source="created_by_id", read_only=True)
    createdAt = serializers.SerializerMethodField()
    documentCount = serializers.SerializerMethodField()
    subfolderCount = serializers.SerializerMethodField()
    location = serializers.CharField(source="get_full_path", read_only=True)

    class Meta:
        model = Folder
        fields = [
            "id",
            "name",
            "parentId",
            "orgUnitId",
            "createdBy",
            "createdAt",
            "documentCount",
            "subfolderCount",
            "location",
        ]

    def get_documentCount(self, obj):
        return obj.documents.filter(is_deleted=False).count()

    def get_subfolderCount(self, obj):
        return obj.children.filter(is_deleted=False).count()

    def get_createdAt(self, obj):
        return format_local_datetime(obj.created_at)

    def validate_name(self, value):
        if value.strip().lower() in RESERVED_FOLDER_NAMES:
            raise serializers.ValidationError("Reserved folder name cannot be used.")
        return value.strip()

    def validate_parentId(self, value):
        return value or None

    def validate_orgUnitId(self, value):
        return value or None


class DocumentSerializer(serializers.ModelSerializer):
    id = serializers.CharField(read_only=True)
    file_name = serializers.SerializerMethodField()
    filePath = serializers.SerializerMethodField()
    file_url = serializers.SerializerMethodField()
    folderId = serializers.CharField(source="folder_id", read_only=True)
    categoryId = serializers.CharField(source="category_id", read_only=True)
    uploaderId = serializers.CharField(source="uploader_id", read_only=True)
    category = serializers.CharField(source="category.name", read_only=True)
    filingYear = serializers.IntegerField(source="filing_year")
    mimeType = serializers.CharField(source="mime_type")
    isDeleted = serializers.BooleanField(source="is_deleted")
    deletedAt = serializers.SerializerMethodField()
    deletedBy = serializers.CharField(source="deleted_by_id", read_only=True)
    createdAt = serializers.SerializerMethodField()
    created_at = serializers.SerializerMethodField()
    mime_type = serializers.CharField(read_only=True)
    file_size = serializers.IntegerField(read_only=True)

    class Meta:
        model = Document
        fields = [
            "id",
            "title",
            "file_name",
            "filePath",
            "file_url",
            "folderId",
            "categoryId",
            "uploaderId",
            "category",
            "code",
            "requestor",
            "description",
            "keywords",
            "filingYear",
            "status",
            "source",
            "mimeType",
            "mime_type",
            "file_size",
            "isDeleted",
            "deletedAt",
            "deletedBy",
            "createdAt",
            "created_at",
        ]

    def get_filePath(self, obj):
        return obj.file_path or obj.folder.get_full_path()

    def get_file_name(self, obj):
        if obj.file:
            return obj.file.name.rsplit("/", 1)[-1]
        return obj.title

    def get_file_url(self, obj):
        request = self.context.get("request")
        if not obj.file:
            return None
        url = obj.file.url
        return request.build_absolute_uri(url) if request else url

    def get_deletedAt(self, obj):
        return format_local_datetime(obj.deleted_at)

    def get_createdAt(self, obj):
        return format_local_datetime(obj.created_at)

    def get_created_at(self, obj):
        return self.get_createdAt(obj)

    def validate_code(self, value):
        code = normalize_document_code(value)
        ensure_unique_document_code(code, document_id=getattr(self.instance, "pk", None))
        return code


def normalize_requestor_name(value):
    cleaned = (value or "").strip()
    if not cleaned:
        return None

    def capitalize_part(part):
        return part[:1].upper() + part[1:].lower() if part else ""

    words = []
    for word in cleaned.split():
        words.append("-".join(capitalize_part(piece) for piece in word.split("-") if piece is not None))
    return " ".join(words)


class DocumentEditSerializer(serializers.Serializer):
    folderId = serializers.CharField()
    categoryId = serializers.CharField()
    code = serializers.CharField()
    requestor = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    description = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=50)
    keywords = serializers.ListField(child=serializers.CharField(), allow_empty=False)
    file_name = serializers.CharField(required=False, allow_blank=True)

    def validate_code(self, value):
        document = self.context.get("document")
        code = normalize_document_code(value)
        ensure_unique_document_code(code, document_id=getattr(document, "pk", None))
        return code

    def validate_keywords(self, value):
        cleaned = [str(item).strip() for item in (value or []) if str(item).strip()]
        if not cleaned:
            raise serializers.ValidationError("At least one keyword is required.")
        return cleaned

    def validate_description(self, value):
        return (value or "").strip()[:50]

    def validate_requestor(self, value):
        return normalize_requestor_name(value)


class ScannerStationSerializer(serializers.ModelSerializer):
    id = serializers.CharField(read_only=True)
    stationId = serializers.CharField(source="station_id")
    watchedFolder = serializers.CharField(source="watched_folder", required=False, allow_blank=True)
    lastSeenAt = serializers.SerializerMethodField()
    errorMessage = serializers.CharField(source="error_message", required=False, allow_blank=True)
    isOnline = serializers.SerializerMethodField()

    class Meta:
        model = ScannerStation
        fields = [
            "id",
            "stationId",
            "name",
            "status",
            "watchedFolder",
            "lastSeenAt",
            "errorMessage",
            "isOnline",
        ]

    def get_lastSeenAt(self, obj):
        return format_local_datetime(obj.last_seen_at)

    def get_isOnline(self, obj):
        if not obj.last_seen_at:
            return False
        return (timezone.now() - obj.last_seen_at).total_seconds() <= 30 and obj.status == "CONNECTED"


class ScanJobSerializer(serializers.ModelSerializer):
    id = serializers.CharField(read_only=True)
    stationId = serializers.CharField(source="station_id")
    folderId = serializers.CharField(source="folder_id")
    categoryId = serializers.CharField(source="category_id")
    documentId = serializers.CharField(source="uploaded_document_id", read_only=True)
    folderName = serializers.CharField(source="folder.name", read_only=True)
    categoryName = serializers.CharField(source="category.name", read_only=True)
    originalFilename = serializers.CharField(source="original_filename", read_only=True)
    errorMessage = serializers.CharField(source="error_message", read_only=True)
    createdAt = serializers.SerializerMethodField()
    updatedAt = serializers.SerializerMethodField()
    completedAt = serializers.SerializerMethodField()
    document = serializers.SerializerMethodField()

    class Meta:
        model = ScanJob
        fields = [
            "id",
            "stationId",
            "folderId",
            "folderName",
            "categoryId",
            "categoryName",
            "documentId",
            "document",
            "status",
            "code",
            "title",
            "requestor",
            "description",
            "keywords",
            "originalFilename",
            "sha256",
            "errorMessage",
            "createdAt",
            "updatedAt",
            "completedAt",
        ]
        read_only_fields = [
            "status",
            "documentId",
            "document",
            "originalFilename",
            "sha256",
            "errorMessage",
            "createdAt",
            "updatedAt",
            "completedAt",
        ]

    def get_createdAt(self, obj):
        return format_local_datetime(obj.created_at)

    def get_updatedAt(self, obj):
        return format_local_datetime(obj.updated_at)

    def get_completedAt(self, obj):
        return format_local_datetime(obj.completed_at)

    def get_document(self, obj):
        if not obj.uploaded_document:
            return None
        return DocumentSerializer(obj.uploaded_document, context=self.context).data
