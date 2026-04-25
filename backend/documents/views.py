import json
import posixpath
import re

from django.http import FileResponse
from django.db import transaction
from django.db.models import Count, Q
from django.core.files.storage import default_storage
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from auditlogs.models import log_audit

from .models import Category, Document, Folder
from .serializers import CategorySerializer, DocumentSerializer, FolderSerializer, RESERVED_FOLDER_NAMES
from .services import permanently_delete_folder, restore_folder, soft_delete_folder
from accounts.models import User
from config.pagination import StandardResultsSetPagination
from config.timezone_utils import format_local_datetime, local_datetime
from orgunits.models import OrgUnit


def ensure_default_folder(user=None):
    return None


def org_unit_scope_ids(user):
    org_unit = getattr(user, "org_unit", None)
    if not org_unit:
        return []
    if getattr(user, "role", None) == "dept_head":
        return [org_unit.id, *[child.id for child in org_unit.get_all_children()]]
    return [org_unit.id]


def assert_recycle_bin_access(user, folder_or_document):
    if getattr(user, "role", None) == "admin":
        return
    if getattr(user, "role", None) != "dept_head":
        raise PermissionDenied("Staff do not have Recycle Bin access.")

    folder = getattr(folder_or_document, "folder", folder_or_document)
    if folder.org_unit_id not in org_unit_scope_ids(user):
        raise PermissionDenied("You do not have access to this recycle bin item.")


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


def normalize_folder_name(value):
    folder_name = (value or "").strip()
    if not folder_name:
        raise ValidationError({"name": "Folder name cannot be empty."})
    if INVALID_FILENAME_CHARS.search(folder_name):
        raise ValidationError({"name": 'Folder name contains invalid characters: \\ / : * ? " < > |'})
    if folder_name.lower() in RESERVED_FOLDER_NAMES:
        raise ValidationError({"name": "Reserved folder name cannot be used."})
    return folder_name


def assert_folder_write_access(user, folder):
    role = getattr(user, "role", None)
    if role == "admin":
        return

    org_unit = getattr(user, "org_unit", None)
    if not org_unit:
        raise PermissionDenied("You do not have access to this folder.")

    if role == "dept_head":
        if folder.org_unit_id in org_unit_scope_ids(user):
            return
        raise PermissionDenied("You do not have access to this folder.")

    if role == "staff":
        if folder.org_unit_id == org_unit.id:
            return
        raise PermissionDenied("You do not have access to this folder.")

    raise PermissionDenied("You do not have access to this folder.")


def assert_document_write_access(user, document):
    role = getattr(user, "role", None)
    if role == "admin":
        return

    org_unit = getattr(user, "org_unit", None)
    if not org_unit:
        raise PermissionDenied("You do not have access to this document.")

    if role == "dept_head":
        if document.folder.org_unit_id in org_unit_scope_ids(user):
            return
        raise PermissionDenied("You do not have access to this document.")

    if role == "staff":
        if document.folder.org_unit_id == org_unit.id:
            return
        raise PermissionDenied("You do not have access to this document.")

    raise PermissionDenied("You do not have access to this document.")


def assert_category_delete_access(user, category):
    role = getattr(user, "role", None)
    if role == "admin":
        return

    org_unit = getattr(user, "org_unit", None)
    if not org_unit or not category.org_unit_id:
        raise PermissionDenied("You do not have access to this category.")

    if role == "dept_head":
        if category.org_unit_id in org_unit_scope_ids(user):
            return
        raise PermissionDenied("You do not have access to this category.")

    if role == "staff":
        if category.org_unit_id == org_unit.id:
            return
        raise PermissionDenied("You do not have access to this category.")

    raise PermissionDenied("You do not have access to this category.")


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
            if getattr(user, "role", None) == "dept_head":
                queryset = queryset.filter(org_unit_id__in=org_unit_scope_ids(user))
            else:
                queryset = queryset.filter(org_unit_id=org_unit.id)

        org_unit_id = self.request.query_params.get("orgUnitId")
        if org_unit_id:
            queryset = queryset.filter(org_unit_id=org_unit_id)
        return queryset

    def perform_create(self, serializer):
        serializer.save()
        log_audit(self.request.user, "CREATE_CATEGORY", f"Created category: {serializer.instance.name}")

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
        )
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
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search)
                | Q(code__icontains=search)
                | Q(description__icontains=search)
                | Q(requestor__icontains=search)
                | Q(keywords__icontains=search)
            )
        return queryset.order_by("-created_at")

    def perform_destroy(self, instance):
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
            title=new_name,
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


class DocumentUploadView(APIView):
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request):
        upload = request.FILES.get("file")
        if not upload:
            return Response({"error": "File is required."}, status=status.HTTP_400_BAD_REQUEST)

        folder = Folder.objects.filter(pk=request.data.get("folderId"), is_deleted=False).first()
        if not folder:
            return Response({"error": "Target folder is required."}, status=status.HTTP_400_BAD_REQUEST)

        category = Category.objects.filter(pk=request.data.get("categoryId")).first()
        if not category:
            return Response({"error": "Valid category is required."}, status=status.HTTP_400_BAD_REQUEST)
        if category.org_unit_id and category.org_unit_id != folder.org_unit_id:
            return Response(
                {"error": "Category must belong to the selected folder's Org Unit."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            keywords = json.loads(request.data.get("keywords", "[]"))
        except json.JSONDecodeError:
            keywords = []

        document = Document.objects.create(
            title=request.data.get("title") or upload.name,
            file=upload,
            file_path=request.data.get("filePath", folder.get_full_path()),
            folder=folder,
            category=category,
            uploader=request.user if request.user.is_authenticated else None,
            code=request.data.get("code") or None,
            requestor=request.data.get("requestor") or None,
            description=request.data.get("description") or None,
            keywords=keywords,
            filing_year=timezone.now().year,
            status="Received",
            source=request.data.get("source", "Uploaded"),
            mime_type=getattr(upload, "content_type", "") or "application/octet-stream",
            file_size=upload.size,
        )
        log_audit(request.user, "UPLOAD", f"Uploaded: {document.title} to {document.file_path}")
        return Response(DocumentSerializer(document, context={"request": request}).data, status=status.HTTP_201_CREATED)


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
        ).select_related("folder", "folder__org_unit", "deleted_by").order_by("-deleted_at")
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
            doc = Document.objects.get(pk=item_id)
            assert_recycle_bin_access(request.user, doc)
            if doc.file:
                doc.file.delete(save=False)
            doc.delete()
            return Response({"message": "Document permanently deleted"})
        return Response({"error": "Invalid type"}, status=400)


class DashboardStatsAPIView(APIView):
    def get(self, request):
        docs = Document.objects.filter(is_deleted=False)
        return Response(
            {
                "total_documents": docs.count(),
                "uploaded_files": docs.filter(source="Uploaded").count(),
                "scanned_files": docs.filter(source="Scanned").count(),
                "total_org_units": OrgUnit.objects.count(),
                "total_users": User.objects.count(),
            }
        )
