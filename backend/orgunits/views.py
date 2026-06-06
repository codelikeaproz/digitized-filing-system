"""
Organization unit and org type API.

OrgUnitViewSet:
    Hierarchical org structure; soft delete when no dependencies remain.

OrgTypeViewSet:
    Admin-only CRUD for database-driven org type labels used in OrgUnit forms.
"""
from django.db import transaction
from django.db.models import ProtectedError
from django.db.models import Q
from rest_framework import status, viewsets
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from accounts.models import User
from auditlogs.models import log_audit
from config.pagination import StandardResultsSetPagination
from documents.models import Document, Folder
from documents.permissions import get_scoped_org_units_queryset
from .models import OrgType, OrgUnit
from .serializers import OrgTypeSerializer, OrgUnitSerializer


def ensure_default_org_unit():
    org_type, _ = OrgType.objects.get_or_create(
        name="Office",
        defaults={"code": "office", "is_active": True, "sort_order": 30},
    )
    org_unit, _ = OrgUnit.objects.get_or_create(
        name="Headquarters",
        defaults={"type": org_type.name, "org_type": org_type},
    )
    if org_unit.org_type_id is None:
        org_unit.org_type = org_type
        org_unit.type = org_type.name
        org_unit.save(update_fields=["org_type", "type"])
    return org_unit


class OrgTypeViewSet(viewsets.ModelViewSet):
    serializer_class = OrgTypeSerializer
    pagination_class = None

    def get_queryset(self):
        queryset = OrgType.objects.all().order_by("name")
        include_inactive = self.request.query_params.get("includeInactive", "").lower() == "true"
        if self.action == "list" and not include_inactive:
            return queryset.filter(is_active=True)
        return queryset

    def _require_admin(self):
        if getattr(self.request.user, "role", None) != "admin":
            raise PermissionDenied("Only Admin users can manage Org Types.")

    def perform_create(self, serializer):
        self._require_admin()
        instance = serializer.save()
        log_audit(
            self.request.user,
            "CREATE_ORG_TYPE",
            f"Created OrgType: {instance.name}",
            target_type="org_type",
            target_name=instance.name,
        )

    def perform_update(self, serializer):
        self._require_admin()
        instance = serializer.save()
        action = "Enabled" if instance.is_active else "Disabled"
        log_audit(
            self.request.user,
            "UPDATE_ORG_TYPE",
            f"{action} OrgType: {instance.name}",
            target_type="org_type",
            target_name=instance.name,
        )

    def destroy(self, request, *args, **kwargs):
        self._require_admin()
        instance = self.get_object()
        if instance.org_units.exists():
            return Response(
                {"message": "Cannot delete Org Type while it is used by Org Units. Disable it instead."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            name = instance.name
            self.perform_destroy(instance)
        except ProtectedError:
            return Response(
                {"message": "Cannot delete Org Type while it is used by protected records."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        log_audit(
            request.user,
            "DELETE_ORG_TYPE",
            f"Deleted OrgType: {name}",
            target_type="org_type",
            target_name=name,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class OrgUnitViewSet(viewsets.ModelViewSet):
    serializer_class = OrgUnitSerializer
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        queryset = get_scoped_org_units_queryset(self.request.user).select_related(
            "org_type", "parent"
        ).order_by("name")
        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search)
                | Q(type__icontains=search)
                | Q(org_type__name__icontains=search)
            )
        return queryset

    def _require_admin(self):
        if getattr(self.request.user, "role", None) != "admin":
            raise PermissionDenied("Only Admin users can manage Office Units.")

    def _is_allocation_validation_error(self, exc):
        detail = getattr(exc, "detail", None)
        if not isinstance(detail, dict):
            return False
        if detail.get("message") == "Insufficient available system storage.":
            return True
        storage_err = detail.get("storageQuotaMb") or detail.get("storage_quota_mb")
        return storage_err is not None and "Insufficient available system storage" in str(storage_err)

    def _audit_allocation_failure(self, request, *, org_unit_name="", previous_quota=None, requested_quota=None):
        parts = ["Storage allocation validation failed."]
        if org_unit_name:
            parts.append(f"Office Unit: {org_unit_name}.")
        if previous_quota is not None:
            parts.append(f"Previous quota: {previous_quota} MB.")
        if requested_quota is not None:
            parts.append(f"Requested quota: {requested_quota} MB.")
        log_audit(
            request.user,
            "STORAGE_ALLOCATION_VALIDATION_FAILED",
            " ".join(parts),
            target_type="org_unit",
            target_name=org_unit_name or "Office Unit",
            target_org_unit=org_unit_name or None,
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except ValidationError as exc:
            if self._is_allocation_validation_error(exc):
                self._audit_allocation_failure(
                    request,
                    org_unit_name=(request.data.get("name") or "").strip(),
                    requested_quota=request.data.get("storageQuotaMb"),
                )
            raise
        self.perform_create(serializer)
        if "storage_quota_mb" in serializer.validated_data:
            from notifications.storage_alerts import check_allocation_thresholds

            check_allocation_thresholds(trigger_user=request.user)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        previous_quota = instance.storage_quota_mb
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        try:
            serializer.is_valid(raise_exception=True)
        except ValidationError as exc:
            if self._is_allocation_validation_error(exc):
                self._audit_allocation_failure(
                    request,
                    org_unit_name=instance.name,
                    previous_quota=previous_quota,
                    requested_quota=request.data.get("storageQuotaMb"),
                )
            raise
        self.perform_update(serializer)
        if "storage_quota_mb" in serializer.validated_data:
            from notifications.storage_alerts import check_allocation_thresholds

            check_allocation_thresholds(trigger_user=request.user)
        return Response(serializer.data)

    def _validate_hierarchy(self, *, instance=None, name=None, parent=None):
        org_unit_name = (name or "").strip()
        if not org_unit_name:
            raise ValidationError({"name": "Org Unit name cannot be empty."})

        if instance and parent:
            if parent.pk == instance.pk:
                raise ValidationError({"parentId": "Org Unit cannot be its own parent."})

            ancestor = parent
            while ancestor:
                if ancestor.pk == instance.pk:
                    raise ValidationError({"parentId": "Circular Org Unit parent relationship is not allowed."})
                ancestor = ancestor.parent

        duplicate_queryset = OrgUnit.objects.filter(
            is_deleted=False,
            parent=parent,
            name__iexact=org_unit_name,
        )
        if instance:
            duplicate_queryset = duplicate_queryset.exclude(pk=instance.pk)
        if duplicate_queryset.exists():
            raise ValidationError({"name": "An Org Unit with this name already exists under the same parent."})

    def _resolve_parent(self, serializer, instance=None):
        fallback_parent_id = instance.parent_id if instance else None
        parent_id = serializer.validated_data.get("parent_id", fallback_parent_id)
        if not parent_id:
            return None

        parent = OrgUnit.objects.filter(pk=parent_id, is_deleted=False).first()
        if not parent:
            raise ValidationError({"parentId": "Parent Org Unit does not exist."})
        return parent

    def perform_create(self, serializer):
        self._require_admin()
        parent = self._resolve_parent(serializer)
        name = serializer.validated_data.get("name")
        self._validate_hierarchy(name=name, parent=parent)
        instance = serializer.save(name=name.strip(), parent=parent)
        quota_note = ""
        if "storage_quota_mb" in serializer.validated_data:
            quota_note = f"; storage quota {instance.storage_quota_mb} MB"
        log_audit(
            self.request.user,
            "CREATE_ORG_UNIT",
            f"Created OrgUnit: {instance.name} ({instance.type_name or 'Unassigned'}){quota_note}",
            target_type="org_unit",
            target_name=instance.name,
            target_org_unit=instance.name,
        )

    def perform_update(self, serializer):
        self._require_admin()
        instance = serializer.instance
        previous_quota = instance.storage_quota_mb
        parent = self._resolve_parent(serializer, instance)
        name = serializer.validated_data.get("name", instance.name)
        self._validate_hierarchy(instance=instance, name=name, parent=parent)
        instance = serializer.save(name=name.strip(), parent=parent)
        if "storage_quota_mb" in serializer.validated_data:
            new_quota = instance.storage_quota_mb
            if previous_quota != new_quota:
                log_audit(
                    self.request.user,
                    "STORAGE_ALLOCATION_UPDATED",
                    (
                        f"Storage allocation updated for {instance.name}: "
                        f"{previous_quota} MB → {new_quota} MB"
                    ),
                    target_type="org_unit",
                    target_name=instance.name,
                    target_org_unit=instance.name,
                )
        quota_note = ""
        if "storage_quota_mb" in serializer.validated_data:
            quota_note = f"; storage quota set to {instance.storage_quota_mb} MB"
        log_audit(
            self.request.user,
            "UPDATE_ORG_UNIT",
            f"Updated OrgUnit: {instance.name} ({instance.type_name or 'Unassigned'}){quota_note}",
            target_type="org_unit",
            target_name=instance.name,
            target_org_unit=instance.name,
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        has_dependencies = (
            User.objects.filter(org_unit=instance).exists()
            or Folder.objects.filter(org_unit=instance, is_deleted=False).exists()
            or Document.objects.filter(folder__org_unit=instance, is_deleted=False).exists()
            or OrgUnit.objects.filter(parent=instance, is_deleted=False).exists()
        )

        if has_dependencies:
            return Response(
                {"message": "Cannot delete OrgUnit. It still contains users, folders, documents, or sub-units."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            instance.is_deleted = True
            instance.save(update_fields=["is_deleted"])
            log_audit(
                request.user,
                "DELETE_ORG_UNIT",
                f"Deleted OrgUnit: {instance.name} ({instance.type_name or 'Unassigned'})",
                target_type="org_unit",
                target_name=instance.name,
                target_org_unit=instance.name,
            )

        return Response({"message": "Org Unit deleted successfully"}, status=status.HTTP_200_OK)
