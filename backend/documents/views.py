"""
Document Management API Views

Purpose:
    REST endpoints for categories, folders, documents, uploads, recycle bin,
    dashboard statistics, and recycle bin.

Main responsibilities:
    - OrgUnit-scoped queryset filtering for all document resources
    - PDF upload validation (type, size, header)
    - Soft delete / restore / permanent delete for folders and documents
    - Role-based write and recycle-bin access checks
    - Audit logging for mutations and downloads

Access control helpers (defined in this module):
    org_unit_scope_ids, assert_folder_write_access, assert_document_write_access,
    assert_recycle_bin_access, assert_category_delete_access

Used by frontend:
    DocumentsPage, FolderNavigation, UploadDialog, RecycleBinPage,
    DashboardPage, CategoryContext

See also:
    documents/services.py — folder tree soft delete / restore
    docs/API_DOCUMENTATION.md — endpoint reference
"""
import json
import posixpath
import re
from datetime import datetime, time, timedelta

from django.conf import settings
from django.http import FileResponse
from django.db import IntegrityError, transaction
from django.db.models import Count, Q
from django.core.files.storage import default_storage
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from auditlogs.models import log_audit
from ai.services.extraction_service import index_document_text

from .document_code import generate_document_code, preview_next_document_code
from .models import Category, Document, Folder
from .requisitioners import (
    format_requisitioners_display,
    parse_requisitioners,
    sync_document_requisitioners,
    validate_requisitioners_list,
)
from .serializers import (
    normalize_requestor_name,
    CategorySerializer,
    DocumentEditSerializer,
    DocumentSerializer,
    FolderSerializer,
    RESERVED_FOLDER_NAMES,
)
from .permissions import (
    assert_category_delete_access,
    assert_document_edit_access,
    assert_document_write_access,
    assert_folder_write_access,
    assert_recycle_bin_access,
    org_unit_scope_ids,
)
from .services import permanently_delete_folder, restore_folder, soft_delete_folder
from accounts.models import User
from config.pagination import StandardResultsSetPagination
from config.timezone_utils import format_local_datetime, local_datetime
from orgunits.models import OrgUnit
from orgunits.storage import add_storage_usage, validate_storage_quota
from notifications.storage_alerts import check_storage_thresholds, validate_global_storage_quota
from system.services import get_upload_limit_bytes
from .dashboard_service import DashboardService
from .pdf_compression import compress_pdf_upload
from .serializers import DashboardStatsSerializer


def ensure_default_folder(user=None):
    return None


INVALID_FILENAME_CHARS = re.compile(r'[\\/:*?"<>|]')


def normalize_pdf_filename(value):
    raw_name = (value or "").strip()
    if not raw_name:
        raise ValidationError({"file_name": "File name cannot be empty."})
    if INVALID_FILENAME_CHARS.search(raw_name):
        raise ValidationError({"file_name": 'File name contains invalid characters: \\ / : * ? " < > |'})

    if raw_name.lower().endswith(".pdf"):
        raw_name = raw_name[:-4].strip()
    elif "." in raw_name.rsplit("/", 1)[-1]:
        raise ValidationError({"file_name": "File extension cannot be changed. Only PDF files are supported."})

    if not raw_name:
        raise ValidationError({"file_name": "File name cannot be empty."})
    return f"{raw_name}.pdf"


def parse_keywords(value):
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if not value:
        return []
    try:
        parsed = json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return []
    if not isinstance(parsed, list):
        return []
    return [str(item).strip() for item in parsed if str(item).strip()]


def keywords_validation_error(keywords):
    if not keywords:
        return "At least one keyword is required."
    return None


def validate_pdf_upload(upload):
    """Enforce PDF-only uploads with size and magic-byte checks."""
    if not upload:
        raise ValidationError({"file": "PDF file is required."})
    if not upload.name.lower().endswith(".pdf"):
        raise ValidationError({"file": "Only PDF files are supported."})
    if getattr(upload, "size", 0) <= 0:
        raise ValidationError({"file": "PDF file is empty."})
    max_bytes = get_upload_limit_bytes()
    if upload.size > max_bytes:
        limit_mb = max_bytes // (1024 * 1024)
        raise ValidationError(
            {
                "file": (
                    f"File exceeds the maximum allowed size of {limit_mb} MB. "
                    "Please compress the file and try again."
                )
            }
        )

    position = upload.tell() if hasattr(upload, "tell") else None
    header = upload.read(4)
    if hasattr(upload, "seek"):
        upload.seek(position or 0)
    if header != b"%PDF":
        raise ValidationError({"file": "Uploaded file is not a valid PDF."})


def normalize_folder_name(value):
    folder_name = (value or "").strip()
    if not folder_name:
        raise ValidationError({"name": "Folder name cannot be empty."})
    if INVALID_FILENAME_CHARS.search(folder_name):
        raise ValidationError({"name": 'Folder name contains invalid characters: \\ / : * ? " < > |'})
    if folder_name.lower() in RESERVED_FOLDER_NAMES:
        raise ValidationError({"name": "Reserved folder name cannot be used."})
    return folder_name


# ---------------------------------------------------------------------------
# Categories — scoped by OrgUnit; delete blocked when documents reference category
# ---------------------------------------------------------------------------
class CategoryViewSet(viewsets.ModelViewSet):
    serializer_class = CategorySerializer

    def get_queryset(self):
        queryset = Category.objects.select_related("org_unit").annotate(
            active_document_count=Count("documents", filter=Q(documents__is_deleted=False))
        ).order_by("name")
        user = self.request.user
        if getattr(user, "role", None) != "admin":
            org_unit = getattr(user, "org_unit", None)
            if not org_unit:
                return queryset.none()
            queryset = queryset.exclude(org_unit__isnull=True)
            if getattr(user, "role", None) == "dept_head":
                queryset = queryset.filter(org_unit_id__in=org_unit_scope_ids(user))
            else:
                queryset = queryset.filter(org_unit_id=org_unit.id)

        org_unit_id = self.request.query_params.get("orgUnitId")
        if org_unit_id:
            queryset = queryset.filter(org_unit_id=org_unit_id)
        return queryset

    def perform_create(self, serializer):
        try:
            serializer.save()
        except IntegrityError:
            raise ValidationError(
                {"name": "A category with this name already exists in this Org Unit."}
            ) from None
        log_audit(self.request.user, "CREATE_CATEGORY", f"Created category: {serializer.instance.name}")

    def perform_update(self, serializer):
        old_name = serializer.instance.name
        category = serializer.save()
        if old_name != category.name:
            log_audit(
                self.request.user,
                "UPDATE_CATEGORY",
                f"Renamed category: {old_name} to {category.name}",
                target_type="category",
                target_name=category.name,
                target_org_unit=category.org_unit.name if category.org_unit else None,
            )

    def destroy(self, request, *args, **kwargs):
        category = self.get_object()
        assert_category_delete_access(request.user, category)

        if Document.objects.filter(category=category, is_deleted=False).exists():
            return Response(
                {
                    "error": "Cannot delete category because it is currently used by existing documents.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        category_name = category.name
        category_org_unit = category.org_unit.name if category.org_unit else None
        with transaction.atomic():
            category.delete()
            log_audit(
                request.user,
                "DELETE_CATEGORY",
                f"Deleted category: {category_name}",
                target_type="category",
                target_name=category_name,
                target_org_unit=category_org_unit,
            )

        return Response({"message": "Category deleted successfully"}, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# Folders — hierarchy, tree endpoint, soft delete (Staff: empty folders only)
# ---------------------------------------------------------------------------
class FolderViewSet(viewsets.ModelViewSet):
    serializer_class = FolderSerializer

    def get_queryset(self):
        queryset = Folder.objects.filter(is_deleted=False, org_unit__is_deleted=False).select_related(
            "org_unit",
            "parent",
        ).order_by("name")
        user = self.request.user
        if getattr(user, "role", None) == "admin":
            return queryset

        org_unit = getattr(user, "org_unit", None)
        if not org_unit:
            return queryset.none()

        if getattr(user, "role", None) == "dept_head":
            org_unit_ids = org_unit_scope_ids(user)
            return queryset.filter(org_unit_id__in=org_unit_ids)

        return queryset.filter(org_unit=org_unit)

    def perform_create(self, serializer):
        parent = serializer.validated_data.get("parent")
        org_unit_id = self.request.data.get("orgUnitId")
        org_unit = parent.org_unit if parent else OrgUnit.objects.filter(pk=org_unit_id).first()
        if not org_unit:
            org_unit = getattr(self.request.user, "org_unit", None)
        if not org_unit:
            raise ValidationError({"orgUnitId": "Target OrgUnit is required."})
        serializer.save(created_by=self.request.user, org_unit=org_unit)

    def perform_destroy(self, instance):
        instance.soft_delete(self.request.user)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        # Staff may delete only empty folders; Admin/Dept Head may delete with contents.
        if getattr(request.user, "role", None) == "staff":
            is_non_empty = (
                instance.documents.filter(is_deleted=False).exists()
                or instance.children.filter(is_deleted=False).exists()
            )
            if is_non_empty:
                raise PermissionDenied("Staff cannot delete non-empty folders.")

        with transaction.atomic():
            document_count = soft_delete_folder(instance, request.user)
            log_audit(
                request.user,
                "DELETE_FOLDER",
                f"Deleted folder: {instance.name} and {document_count} document(s)",
                target_type="folder",
                target_name=instance.name,
                target_org_unit=instance.org_unit.name if instance.org_unit else None,
            )
        return Response(
            {
                "message": "Folder deleted successfully",
                "documents_deleted": document_count,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["patch"], url_path="rename")
    def rename(self, request, pk=None):
        folder = self.get_object()
        assert_folder_write_access(request.user, folder)

        old_name = folder.name
        new_name = normalize_folder_name(request.data.get("name"))

        duplicate_exists = Folder.objects.filter(
            parent=folder.parent,
            org_unit=folder.org_unit,
            is_deleted=False,
            name__iexact=new_name,
        ).exclude(pk=folder.pk).exists()
        if duplicate_exists:
            raise ValidationError({"name": "A folder with this name already exists in this location."})

        with transaction.atomic():
            folder.name = new_name
            folder.save(update_fields=["name"])
            log_audit(
                request.user,
                "RENAME_FOLDER",
                f"Renamed folder: {old_name} → {new_name}",
                target_type="folder",
                target_name=new_name,
                target_org_unit=folder.org_unit.name if folder.org_unit else None,
            )

        return Response(FolderSerializer(folder).data)

    def _folder_node(self, folder, children_by_parent):
        return {
            "id": str(folder.id),
            "name": folder.name,
            "type": "folder",
            "parentId": str(folder.parent_id) if folder.parent_id else None,
            "orgUnitId": str(folder.org_unit_id) if folder.org_unit_id else None,
            "org_unit": folder.org_unit.name if folder.org_unit else None,
            "createdBy": str(folder.created_by_id) if folder.created_by_id else None,
            "createdAt": format_local_datetime(folder.created_at),
            "documentCount": folder.documents.filter(is_deleted=False).count(),
            "subfolderCount": folder.children.filter(is_deleted=False).count(),
            "location": folder.get_full_path(),
            "children": [
                self._folder_node(child, children_by_parent)
                for child in children_by_parent.get(folder.id, [])
            ],
        }

    def _folder_tree(self, folders):
        children_by_parent = {}
        for folder in folders:
            children_by_parent.setdefault(folder.parent_id, []).append(folder)
        return [self._folder_node(folder, children_by_parent) for folder in children_by_parent.get(None, [])]

    def _org_unit_node(self, org_unit, org_units_by_parent, folders_by_org_unit):
        folder_tree = self._folder_tree(folders_by_org_unit.get(org_unit.id, []))
        child_org_units = [
            self._org_unit_node(child, org_units_by_parent, folders_by_org_unit)
            for child in org_units_by_parent.get(org_unit.id, [])
        ]
        return {
            "id": f"org-unit-{org_unit.id}",
            "orgUnitId": str(org_unit.id),
            "parentOrgUnitId": str(org_unit.parent_id) if org_unit.parent_id else None,
            "name": org_unit.name,
            "type": "org_unit",
            "isOrgUnit": True,
            "folders": folder_tree,
            "children": [*child_org_units, *folder_tree],
        }

    def _org_unit_tree(self, org_units, folders):
        org_units_by_parent = {}
        for org_unit in org_units:
            org_units_by_parent.setdefault(org_unit.parent_id, []).append(org_unit)

        folders_by_org_unit = {}
        for folder in folders:
            folders_by_org_unit.setdefault(folder.org_unit_id, []).append(folder)

        return [
            self._org_unit_node(org_unit, org_units_by_parent, folders_by_org_unit)
            for org_unit in org_units_by_parent.get(None, [])
        ]

    @action(detail=False, methods=["get"], url_path="tree")
    def tree(self, request):
        all_files = {
            "id": "all-files",
            "name": "All Files",
            "type": "virtual",
            "is_virtual": True,
            "isVirtual": True,
        }
        user = request.user
        folders = list(self.get_queryset())

        if getattr(user, "role", None) == "admin":
            org_units = OrgUnit.objects.filter(is_deleted=False).order_by("name")
            return Response([all_files, *self._org_unit_tree(org_units, folders)])

        return Response([all_files, *self._folder_tree(folders)])


# ---------------------------------------------------------------------------
# Documents — list/filter, download, rename; Staff cannot DELETE
# ---------------------------------------------------------------------------
def parse_document_date_boundary(value, *, end_of_day=False):
    parsed_date = parse_date(value or "")
    if not parsed_date:
        raise ValidationError({"date_range": "Date must use YYYY-MM-DD format."})
    boundary_time = time.max if end_of_day else time.min
    parsed_datetime = datetime.combine(parsed_date, boundary_time)
    return timezone.make_aware(parsed_datetime, timezone.get_current_timezone())


class DocumentViewSet(viewsets.ModelViewSet):
    serializer_class = DocumentSerializer
    pagination_class = StandardResultsSetPagination
    parser_classes = (JSONParser, MultiPartParser, FormParser)

    def get_serializer_context(self):
        return {"request": self.request}

    def get_queryset(self):
        queryset = Document.objects.filter(
            is_deleted=False,
            folder__is_deleted=False,
            folder__org_unit__is_deleted=False,
        ).select_related(
            "folder",
            "folder__org_unit",
        ).prefetch_related("requisitioners")
        user = self.request.user
        if getattr(user, "role", None) != "admin":
            org_unit = getattr(user, "org_unit", None)
            if org_unit:
                org_unit_ids = org_unit_scope_ids(user)
                queryset = queryset.filter(Q(folder__org_unit_id__in=org_unit_ids) | Q(folder__org_unit__isnull=True))
            else:
                queryset = queryset.filter(folder__org_unit__isnull=True)
        folder_id = self.request.query_params.get("folderId")
        org_unit_id = self.request.query_params.get("orgUnitId")
        category_id = self.request.query_params.get("category")
        start_date = self.request.query_params.get("start_date")
        end_date = self.request.query_params.get("end_date")
        search = self.request.query_params.get("search")
        if org_unit_id:
            include_children = self.request.query_params.get("includeChildOrgUnits", "true").lower() != "false"
            org_unit = OrgUnit.objects.filter(pk=org_unit_id, is_deleted=False).first()
            if include_children and org_unit:
                org_unit_ids = [org_unit.id, *[child.id for child in org_unit.get_all_children()]]
                queryset = queryset.filter(folder__org_unit_id__in=org_unit_ids)
            else:
                queryset = queryset.filter(folder__org_unit_id=org_unit_id)
        if folder_id:
            queryset = queryset.filter(folder_id=folder_id)
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        if start_date:
            queryset = queryset.filter(created_at__gte=parse_document_date_boundary(start_date))
        if end_date:
            queryset = queryset.filter(created_at__lte=parse_document_date_boundary(end_date, end_of_day=True))
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search)
                | Q(code__icontains=search)
                | Q(description__icontains=search)
                | Q(requestor__icontains=search)
                | Q(requisitioners__employee_number__icontains=search)
                | Q(requisitioners__first_name__icontains=search)
                | Q(requisitioners__last_name__icontains=search)
                | Q(requisitioners__suffix__icontains=search)
                | Q(keywords__icontains=search)
            ).distinct()
        return queryset.order_by("-created_at")

    def perform_destroy(self, instance):
        # Soft delete — item moves to Recycle Bin for Admin / Dept Head restore.
        if getattr(self.request.user, "role", None) == "staff":
            raise PermissionDenied("Staff cannot delete documents.")
        instance.soft_delete(self.request.user)

    @action(detail=True, methods=["get"], url_path="download")
    def download(self, request, pk=None):
        document = self.get_object()
        assert_document_write_access(request.user, document)

        if not document.file or not default_storage.exists(document.file.name):
            return Response({"error": "File not found"}, status=status.HTTP_404_NOT_FOUND)

        file_name = document.file.name.rsplit("/", 1)[-1] or document.title or "document.pdf"
        org_unit_name = document.folder.org_unit.name if document.folder and document.folder.org_unit else None

        log_audit(
            request.user,
            "DOWNLOAD_DOCUMENT",
            f"Downloaded document: {file_name}",
            target_type="Document",
            target_name=file_name,
            target_org_unit=org_unit_name,
            ip_address=request.META.get("REMOTE_ADDR"),
        )

        return FileResponse(
            document.file.open("rb"),
            as_attachment=True,
            filename=file_name,
        )

    @action(detail=True, methods=["patch"], url_path="rename")
    def rename(self, request, pk=None):
        document = self.get_object()
        assert_document_write_access(request.user, document)

        old_name = document.file.name.rsplit("/", 1)[-1] if document.file else document.title
        new_name = normalize_pdf_filename(request.data.get("file_name"))

        duplicate_exists = Document.objects.filter(
            folder=document.folder,
            is_deleted=False,
            title__iexact=new_name,
        ).exclude(pk=document.pk).exists()
        if duplicate_exists:
            raise ValidationError({"file_name": "A document with this file name already exists in this folder."})

        with transaction.atomic():
            if document.file:
                old_storage_name = document.file.name
                directory = posixpath.dirname(old_storage_name)
                new_storage_name = posixpath.join(directory, new_name) if directory else new_name

                if old_storage_name != new_storage_name:
                    if default_storage.exists(new_storage_name):
                        raise ValidationError({"file_name": "A file with this name already exists."})
                    with default_storage.open(old_storage_name, "rb") as old_file:
                        default_storage.save(new_storage_name, old_file)
                    default_storage.delete(old_storage_name)
                    document.file.name = new_storage_name

            document.title = new_name
            document.save(update_fields=["title", "file"])
            log_audit(
                request.user,
                "RENAME_DOCUMENT",
                f"Renamed document: {old_name} → {new_name}",
                target_type="document",
                target_name=new_name,
                target_org_unit=document.folder.org_unit.name if document.folder and document.folder.org_unit else None,
            )

        return Response(DocumentSerializer(document, context={"request": request}).data)

    @action(detail=True, methods=["patch"], url_path="edit")
    def edit_details(self, request, pk=None):
        document = self.get_object()
        assert_document_edit_access(request.user, document)

        serializer = DocumentEditSerializer(
            data=request.data,
            context={"document": document, "request": request},
        )
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        folder = Folder.objects.filter(pk=data["folderId"], is_deleted=False).first()
        if not folder:
            raise ValidationError({"folderId": "Target folder is required."})
        assert_folder_write_access(request.user, folder)

        category = Category.objects.filter(pk=data["categoryId"]).first()
        if not category:
            raise ValidationError({"categoryId": "Valid category is required."})
        if category.org_unit_id and category.org_unit_id != folder.org_unit_id:
            raise ValidationError({"categoryId": "Category must belong to the selected folder's Org Unit."})

        new_name = document.title
        if data.get("file_name"):
            new_name = normalize_pdf_filename(data["file_name"])

        duplicate_exists = Document.objects.filter(
            folder=folder,
            is_deleted=False,
            title__iexact=new_name,
        ).exclude(pk=document.pk).exists()
        if duplicate_exists:
            raise ValidationError({"file_name": "A document with this file name already exists in this folder."})

        old_folder_path = document.file_path or (document.folder.get_full_path() if document.folder else "")
        old_name = document.file.name.rsplit("/", 1)[-1] if document.file else document.title
        changes = []

        with transaction.atomic():
            if document.file and (new_name != document.title or old_name != new_name):
                old_storage_name = document.file.name
                directory = posixpath.dirname(old_storage_name)
                new_storage_name = posixpath.join(directory, new_name) if directory else new_name

                if old_storage_name != new_storage_name:
                    if default_storage.exists(new_storage_name):
                        raise ValidationError({"file_name": "A file with this name already exists."})
                    with default_storage.open(old_storage_name, "rb") as old_file:
                        default_storage.save(new_storage_name, old_file)
                    default_storage.delete(old_storage_name)
                    document.file.name = new_storage_name
                document.title = new_name
                if old_name != new_name:
                    changes.append(f"name: {old_name} → {new_name}")

            if document.folder_id != folder.id:
                changes.append(
                    f"folder: {document.folder.get_full_path() if document.folder else old_folder_path} → {folder.get_full_path()}"
                )
                document.folder = folder
                document.file_path = folder.get_full_path()

            if document.category_id != category.id:
                old_category = document.category.name if document.category else "None"
                changes.append(f"category: {old_category} → {category.name}")
                document.category = category

            new_requisitioners = data["requisitioners"]
            old_display = document.requestor or ""
            new_display = format_requisitioners_display(new_requisitioners) or ""
            if old_display != new_display:
                changes.append("requisitioners updated")

            new_description = data.get("description") or None
            if (document.description or None) != new_description:
                changes.append("description updated")
                document.description = new_description

            if (document.keywords or []) != data["keywords"]:
                changes.append("keywords updated")
                document.keywords = data["keywords"]

            document.save(
                update_fields=[
                    "title",
                    "file",
                    "folder",
                    "file_path",
                    "category",
                    "description",
                    "keywords",
                    "updated_at",
                ]
            )
            sync_document_requisitioners(document, new_requisitioners)

        change_summary = "; ".join(changes) if changes else "metadata refreshed"
        log_audit(
            request.user,
            "EDIT_DOCUMENT",
            f"Edited document: {document.title} ({change_summary})",
            target_type="document",
            target_name=document.title,
            target_org_unit=document.folder.org_unit.name if document.folder and document.folder.org_unit else None,
        )

        return Response(DocumentSerializer(document, context={"request": request}).data)


# ---------------------------------------------------------------------------
# Document upload — multipart PDF + metadata (primary upload path for frontend)
# ---------------------------------------------------------------------------
class DocumentUploadView(APIView):
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request):
        upload = request.FILES.get("file")
        if not upload:
            return Response({"error": "File is required."}, status=status.HTTP_400_BAD_REQUEST)
        validate_pdf_upload(upload)

        folder = Folder.objects.filter(pk=request.data.get("folderId"), is_deleted=False).first()
        if not folder:
            return Response({"error": "Target folder is required."}, status=status.HTTP_400_BAD_REQUEST)
        assert_folder_write_access(request.user, folder)

        category = Category.objects.filter(pk=request.data.get("categoryId")).first()
        if not category:
            return Response({"error": "Valid category is required."}, status=status.HTTP_400_BAD_REQUEST)
        if category.org_unit_id and category.org_unit_id != folder.org_unit_id:
            return Response(
                {"error": "Category must belong to the selected folder's Office Unit."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        keywords = parse_keywords(request.data.get("keywords", "[]"))
        keywords_error = keywords_validation_error(keywords)
        if keywords_error:
            return Response({"error": keywords_error}, status=status.HTTP_400_BAD_REQUEST)

        try:
            raw_requisitioners = parse_requisitioners(request.data.get("requisitioners", "[]"))
            validated_requisitioners = validate_requisitioners_list(raw_requisitioners)
        except ValidationError as exc:
            detail = exc.detail
            message = detail[0] if isinstance(detail, list) else str(detail)
            if isinstance(detail, dict):
                message = next(iter(detail.values()), message)
                if isinstance(message, list):
                    message = message[0]
            return Response({"message": str(message), "errors": detail}, status=status.HTTP_400_BAD_REQUEST)

        source = "Uploaded"
        upload = compress_pdf_upload(upload)
        try:
            validate_global_storage_quota(upload.size)
        except ValidationError as exc:
            log_audit(
                request.user,
                "UPLOAD_BLOCKED_STORAGE_QUOTA",
                "Upload blocked: global storage quota exceeded.",
                target_type="system_storage",
                target_name="Upload",
            )
            detail = exc.detail
            message = detail.get("file", detail) if isinstance(detail, dict) else str(detail)
            if isinstance(message, list):
                message = message[0]
            return Response({"message": str(message), "errors": detail}, status=status.HTTP_400_BAD_REQUEST)

        try:
            validate_storage_quota(folder.org_unit, upload.size)
        except ValidationError as exc:
            log_audit(
                request.user,
                "UPLOAD_BLOCKED_STORAGE_QUOTA",
                f"Upload blocked: Office Unit storage quota exceeded ({folder.org_unit.name}).",
                target_type="org_unit",
                target_name=folder.org_unit.name if folder.org_unit else None,
            )
            detail = exc.detail
            message = detail.get("file", detail) if isinstance(detail, dict) else str(detail)
            if isinstance(message, list):
                message = message[0]
            return Response({"message": str(message), "errors": detail}, status=status.HTTP_400_BAD_REQUEST)

        try:
            title = normalize_pdf_filename(request.data.get("title") or upload.name)
        except ValidationError as exc:
            return Response(exc.detail, status=status.HTTP_400_BAD_REQUEST)

        if Document.objects.filter(folder=folder, is_deleted=False, title__iexact=title).exists():
            return Response(
                {"file_name": "A document with this file name already exists in this folder."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        upload.name = title

        try:
            with transaction.atomic():
                code = generate_document_code(category)
                document = Document.objects.create(
                    title=title,
                    file=upload,
                    file_path=request.data.get("filePath", folder.get_full_path()),
                    folder=folder,
                    category=category,
                    uploader=request.user if request.user.is_authenticated else None,
                    code=code,
                    requestor=format_requisitioners_display(validated_requisitioners) or None,
                    description=request.data.get("description") or None,
                    keywords=keywords,
                    filing_year=timezone.now().year,
                    status="Received",
                    source=source,
                    mime_type=getattr(upload, "content_type", "") or "application/octet-stream",
                    file_size=upload.size,
                )
                sync_document_requisitioners(document, validated_requisitioners)
        except ValidationError as exc:
            detail = exc.detail
            if isinstance(detail, list) and detail:
                message = str(detail[0])
            elif isinstance(detail, dict):
                message = str(next(iter(detail.values())))
            else:
                message = str(detail)
            return Response({"message": message, "errors": detail}, status=status.HTTP_400_BAD_REQUEST)
        except IntegrityError:
            return Response({"message": "Document Code is already used."}, status=status.HTTP_409_CONFLICT)
        index_document_text(document)
        add_storage_usage(folder.org_unit, upload.size)
        check_storage_thresholds(request.user)
        log_audit(
            request.user,
            "UPLOAD",
            f"Uploaded document: {document.title} [Code: {document.code}] to {document.file_path}",
            target_type="document",
            target_name=document.title,
            target_org_unit=folder.org_unit.name if folder.org_unit else None,
        )
        return Response(DocumentSerializer(document, context={"request": request}).data, status=status.HTTP_201_CREATED)


class DocumentNextCodeAPIView(APIView):
    def get(self, request):
        category_id = request.query_params.get("categoryId")
        if not category_id:
            return Response({"error": "categoryId is required."}, status=status.HTTP_400_BAD_REQUEST)

        category = Category.objects.filter(pk=category_id).first()
        if not category:
            return Response({"error": "Valid category is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            code = preview_next_document_code(category)
        except ValidationError as exc:
            detail = exc.detail
            message = detail[0] if isinstance(detail, list) else str(detail)
            return Response({"message": str(message)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({"code": code})


# ---------------------------------------------------------------------------
# Recycle bin — merged paginated list of soft-deleted folders and documents
# ---------------------------------------------------------------------------
class RecycleBinAPIView(APIView):
    pagination_class = StandardResultsSetPagination

    def _deleted_at_sort_value(self, value):
        return local_datetime(value) or timezone.make_aware(
            timezone.datetime.min,
            timezone.get_current_timezone(),
        )

    def _format_deleted_at(self, value):
        return format_local_datetime(value)

    def _scope_deleted_folders(self, request):
        queryset = Folder.objects.filter(is_deleted=True, org_unit__is_deleted=False).select_related(
            "org_unit",
            "deleted_by",
        )
        user = request.user
        if getattr(user, "role", None) == "admin":
            return queryset
        if getattr(user, "role", None) == "dept_head":
            org_unit = getattr(user, "org_unit", None)
            if not org_unit:
                return queryset.none()
            org_unit_ids = org_unit_scope_ids(user)
            return queryset.filter(org_unit_id__in=org_unit_ids)
        raise PermissionDenied("Staff do not have Recycle Bin access.")

    def _scope_deleted_documents(self, request):
        queryset = Document.objects.filter(
            is_deleted=True,
            folder__org_unit__is_deleted=False,
        ).select_related("folder", "folder__org_unit", "deleted_by").prefetch_related(
            "requisitioners"
        ).order_by("-deleted_at")
        user = request.user
        if getattr(user, "role", None) == "admin":
            return queryset
        if getattr(user, "role", None) == "dept_head":
            org_unit = getattr(user, "org_unit", None)
            if not org_unit:
                return queryset.none()
            org_unit_ids = [org_unit.id, *[child.id for child in org_unit.get_all_children()]]
            return queryset.filter(folder__org_unit_id__in=org_unit_ids)
        raise PermissionDenied("Staff do not have Recycle Bin access.")

    def get(self, request):
        try:
            documents = self._scope_deleted_documents(request)
            folders = self._scope_deleted_folders(request).order_by("-deleted_at")
            item_type = (request.query_params.get("type") or "all").lower()
            doc_items = [
                {
                    **DocumentSerializer(doc, context={"request": request}).data,
                    "type": "document",
                    "deletedByRole": getattr(doc.deleted_by, "role", "System") if doc.deleted_by else "System",
                    "deletedByFullName": doc.deleted_by.get_full_name() if doc.deleted_by else "System",
                    "orgUnitName": doc.folder.org_unit.name if doc.folder and doc.folder.org_unit else "Global Access",
                    "deletedAt": self._format_deleted_at(doc.deleted_at),
                    "deleted_at": self._format_deleted_at(doc.deleted_at),
                    "deleted_at_sort": self._deleted_at_sort_value(doc.deleted_at),
                }
                for doc in documents
            ] if item_type in {"all", "documents", "document"} else []
            folder_items = [
                {
                    **FolderSerializer(folder).data,
                    "type": "folder",
                    "deletedByRole": getattr(folder.deleted_by, "role", "System") if folder.deleted_by else "System",
                    "deletedByFullName": folder.deleted_by.get_full_name() if folder.deleted_by else "System",
                    "orgUnitName": folder.org_unit.name if folder.org_unit else "Global Access",
                    "deletedAt": self._format_deleted_at(folder.deleted_at),
                    "deleted_at": self._format_deleted_at(folder.deleted_at),
                    "deleted_at_sort": self._deleted_at_sort_value(folder.deleted_at),
                }
                for folder in folders
            ] if item_type in {"all", "folders", "folder"} else []
            items = sorted(
                [*doc_items, *folder_items],
                key=lambda item: item["deleted_at_sort"],
                reverse=True,
            )
            for item in items:
                item.pop("deleted_at_sort", None)

            paginator = self.pagination_class()
            page = paginator.paginate_queryset(items, request, view=self)
            return paginator.get_paginated_response(page)
        except PermissionDenied:
            raise
        except Exception as exc:
            log_audit(
                request.user,
                "SYSTEM_ERROR",
                f"Failed to load recycle bin items: {exc}",
                target_type="RecycleBin",
                target_name="Recycle Bin",
                ip_address=request.META.get("REMOTE_ADDR"),
            )
            return Response({"message": "Failed to load recycle bin items."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class RecycleBinRestoreAPIView(APIView):
    @transaction.atomic
    def post(self, request):
        item_type = (request.data.get("type") or "").lower()
        item_id = request.data.get("id")
        if item_type == "folder":
            folder = Folder.objects.get(pk=item_id)
            assert_recycle_bin_access(request.user, folder)
            document_count = restore_folder(folder, request.user)
            log_audit(
                request.user,
                "RESTORE_FOLDER",
                f"Restored folder: {folder.name} and {document_count} document(s)",
                target_type="folder",
                target_name=folder.name,
                target_org_unit=folder.org_unit.name if folder.org_unit else None,
            )
            return Response({"message": "Folder restored", "documents_restored": document_count})
        if item_type == "document":
            document = Document.objects.get(pk=item_id)
            assert_recycle_bin_access(request.user, document)
            if document.folder.is_deleted:
                return Response({"error": "Cannot restore document. Parent folder is deleted."}, status=400)
            document.is_deleted = False
            document.deleted_at = None
            document.deleted_by = None
            document.save()
            return Response({"message": "Document restored"})
        return Response({"error": "Invalid type"}, status=400)


class RecycleBinDeleteAPIView(APIView):
    @transaction.atomic
    def delete(self, request):
        item_type = (request.query_params.get("type") or "").lower()
        item_id = request.query_params.get("id")
        if item_type == "folder":
            folder = Folder.objects.get(pk=item_id)
            assert_recycle_bin_access(request.user, folder)
            folder_name = folder.name
            org_unit_name = folder.org_unit.name if folder.org_unit else None
            document_count = permanently_delete_folder(folder, request.user)
            log_audit(
                request.user,
                "PERMANENT_DELETE_FOLDER",
                f"Permanently deleted folder: {folder_name} and {document_count} document(s)",
                target_type="folder",
                target_name=folder_name,
                target_org_unit=org_unit_name,
            )
            return Response(
                {
                    "message": "Folder permanently deleted",
                    "documents_deleted": document_count,
                }
            )
        if item_type == "document":
            doc = Document.objects.select_related("folder__org_unit").get(pk=item_id)
            assert_recycle_bin_access(request.user, doc)
            org_unit = doc.folder.org_unit if doc.folder else None
            file_size = doc.file_size or 0
            doc_title = doc.title
            org_unit_name = org_unit.name if org_unit else None
            if doc.file:
                doc.file.delete(save=False)
            doc.delete()
            if org_unit and file_size:
                from orgunits.storage import subtract_storage_usage

                subtract_storage_usage(org_unit, file_size)
            check_storage_thresholds(request.user)
            log_audit(
                request.user,
                "PERMANENT_DELETE_DOCUMENT",
                f"Permanently deleted document: {doc_title}",
                target_type="document",
                target_name=doc_title,
                target_org_unit=org_unit_name,
            )
            return Response({"message": "Document permanently deleted"})
        return Response({"error": "Invalid type"}, status=400)


class DashboardStatsAPIView(APIView):
    """
    Dashboard statistics with optional Office Unit filter.

    GET /api/dashboard/?office_unit=all
    GET /api/dashboard/?office_unit=5
    GET /api/dashboard/stats  (legacy alias)
    """

    def get(self, request):
        office_unit_param = (
            request.query_params.get("office_unit")
            or request.query_params.get("officeUnit")
            or request.query_params.get("org_unit")
        )
        payload = DashboardService.get_dashboard_for_user(request.user, office_unit_param)
        serializer = DashboardStatsSerializer(payload)
        return Response(serializer.data)
