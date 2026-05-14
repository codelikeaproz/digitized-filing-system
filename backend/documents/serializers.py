from rest_framework import serializers
from django.utils import timezone

from config.timezone_utils import format_local_datetime
from .models import Category, Document, Folder, ScanJob, ScannerStation


RESERVED_FOLDER_NAMES = {"all files", "root", "trash", "recycle bin"}


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
