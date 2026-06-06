"""
Dashboard statistics and storage analytics.

Computes storage usage dynamically from Document.file_size and
OfficeUnit.storage_quota_mb (quota only is stored in DB).
"""
from django.db.models import Sum
from django.db.models.functions import Coalesce
from rest_framework.exceptions import NotFound, PermissionDenied

from accounts.models import User
from documents.models import Document
from documents.permissions import get_accessible_org_unit_ids, org_unit_scope_ids
from orgunits.models import OrgUnit
from orgunits.storage import DEFAULT_STORAGE_QUOTA_MB, bytes_to_mb


class DashboardService:
    """Reusable dashboard aggregation for global and per-Office-Unit views."""

    @staticmethod
    def _usage_bytes_by_org_unit():
        return {
            row["folder__org_unit_id"]: int(row["used_bytes"] or 0)
            for row in Document.objects.values("folder__org_unit_id").annotate(
                used_bytes=Coalesce(Sum("file_size"), 0)
            )
        }

    @staticmethod
    def _active_documents(org_unit_ids=None):
        queryset = Document.objects.filter(is_deleted=False)
        if org_unit_ids is not None:
            queryset = queryset.filter(folder__org_unit_id__in=org_unit_ids)
        return queryset

    @staticmethod
    def _deleted_documents(org_unit_ids=None):
        queryset = Document.objects.filter(is_deleted=True)
        if org_unit_ids is not None:
            queryset = queryset.filter(folder__org_unit_id__in=org_unit_ids)
        return queryset

    @classmethod
    def compute_used_bytes(cls, org_unit_id):
        """Sum file sizes for all documents in an Office Unit (includes soft-deleted)."""
        return (
            Document.objects.filter(folder__org_unit_id=org_unit_id)
            .aggregate(total=Coalesce(Sum("file_size"), 0))
            .get("total")
            or 0
        )

    @classmethod
    def get_storage_summary(cls, org_unit, used_bytes=None):
        """Build storage summary for one Office Unit from live document sizes."""
        quota_mb = org_unit.storage_quota_mb or DEFAULT_STORAGE_QUOTA_MB
        if used_bytes is None:
            used_bytes = cls.compute_used_bytes(org_unit.id)
        used_mb = float(bytes_to_mb(used_bytes))
        remaining_mb = round(max(0.0, quota_mb - used_mb), 2)
        usage_percentage = round((used_mb / quota_mb) * 100, 1) if quota_mb else 0.0
        return {
            "org_unit_id": str(org_unit.id),
            "org_unit_name": org_unit.name,
            "quota_mb": int(quota_mb),
            "used_mb": round(used_mb, 2),
            "remaining_mb": remaining_mb,
            "usage_percentage": usage_percentage,
            "percent_used": usage_percentage,
        }

    @classmethod
    def get_storage_usage_by_office_unit(cls, usage_map=None, org_unit_ids=None):
        """Bar chart data: used vs quota per Office Unit."""
        if usage_map is None:
            usage_map = cls._usage_bytes_by_org_unit()

        queryset = OrgUnit.objects.filter(is_deleted=False).order_by("name")
        if org_unit_ids is not None:
            queryset = queryset.filter(id__in=org_unit_ids)

        results = []
        for org_unit in queryset:
            used_bytes = usage_map.get(org_unit.id, 0)
            summary = cls.get_storage_summary(org_unit, used_bytes=used_bytes)
            results.append(
                {
                    "org_unit_id": summary["org_unit_id"],
                    "org_unit_name": summary["org_unit_name"],
                    "quota_mb": summary["quota_mb"],
                    "used_mb": summary["used_mb"],
                    "remaining_mb": summary["remaining_mb"],
                    "usage_percentage": summary["usage_percentage"],
                }
            )
        return sorted(results, key=lambda row: row["used_mb"], reverse=True)

    @classmethod
    def get_global_dashboard_stats(cls):
        """Admin view: all Office Units combined."""
        from system.services import get_storage_quota_mb

        org_units = list(OrgUnit.objects.filter(is_deleted=False))
        usage_map = cls._usage_bytes_by_org_unit()

        system_quota_mb = get_storage_quota_mb()
        org_units_quota_mb = sum(unit.storage_quota_mb or DEFAULT_STORAGE_QUOTA_MB for unit in org_units)
        total_used_bytes = sum(usage_map.values())
        total_used_mb = float(bytes_to_mb(total_used_bytes))
        remaining_mb = round(max(0.0, system_quota_mb - total_used_mb), 2)
        usage_percentage = round((total_used_mb / system_quota_mb) * 100, 1) if system_quota_mb else 0.0

        docs = cls._active_documents()
        return {
            "scope": "global",
            "office_unit_id": None,
            "office_unit_name": "All Office Units",
            "office_unit_filter": "all",
            "can_filter_office_units": True,
            "total_documents": docs.count(),
            "uploaded_files": docs.count(),
            "total_org_units": len(org_units),
            "total_users": User.objects.count(),
            "deleted_files": None,
            "storage": {
                "org_unit_id": None,
                "org_unit_name": "All Office Units",
                "quota_mb": int(system_quota_mb),
                "org_units_quota_mb": int(org_units_quota_mb),
                "used_mb": round(total_used_mb, 2),
                "remaining_mb": remaining_mb,
                "usage_percentage": usage_percentage,
                "percent_used": usage_percentage,
            },
            "storage_by_office_unit": cls.get_storage_usage_by_office_unit(usage_map),
        }

    @classmethod
    def get_office_unit_dashboard_stats(cls, org_unit):
        """Scoped view for one Office Unit."""
        org_unit_ids = [org_unit.id]
        docs = cls._active_documents(org_unit_ids)
        deleted = cls._deleted_documents(org_unit_ids)

        return {
            "scope": "office_unit",
            "office_unit_id": str(org_unit.id),
            "office_unit_name": org_unit.name,
            "office_unit_filter": str(org_unit.id),
            "can_filter_office_units": False,
            "total_documents": docs.count(),
            "uploaded_files": docs.count(),
            "total_org_units": None,
            "total_users": User.objects.filter(org_unit=org_unit).count(),
            "deleted_files": deleted.count(),
            "storage": cls.get_storage_summary(org_unit),
            "storage_by_office_unit": [],
        }

    @classmethod
    def get_subtree_dashboard_stats(cls, root_org_unit, scope_ids):
        """Aggregated dashboard for a dept_head's assigned unit and descendants."""
        usage_map = cls._usage_bytes_by_org_unit()
        docs = cls._active_documents(scope_ids)
        deleted = cls._deleted_documents(scope_ids)

        total_used_bytes = sum(usage_map.get(unit_id, 0) for unit_id in scope_ids)
        total_quota_mb = sum(
            (OrgUnit.objects.filter(pk=unit_id).values_list("storage_quota_mb", flat=True).first()
             or DEFAULT_STORAGE_QUOTA_MB)
            for unit_id in scope_ids
        )
        used_mb = float(bytes_to_mb(total_used_bytes))
        remaining_mb = round(max(0.0, total_quota_mb - used_mb), 2)
        usage_percentage = round((used_mb / total_quota_mb) * 100, 1) if total_quota_mb else 0.0

        descendant_count = max(0, len(scope_ids) - 1)
        has_children = descendant_count > 0

        return {
            "scope": "office_unit",
            "office_unit_id": str(root_org_unit.id),
            "office_unit_name": root_org_unit.name,
            "office_unit_filter": str(root_org_unit.id),
            "can_filter_office_units": has_children,
            "total_documents": docs.count(),
            "uploaded_files": docs.count(),
            "total_org_units": len(scope_ids),
            "total_users": User.objects.filter(org_unit_id__in=scope_ids).count(),
            "deleted_files": deleted.count(),
            "storage": {
                "org_unit_id": str(root_org_unit.id),
                "org_unit_name": root_org_unit.name,
                "quota_mb": int(total_quota_mb),
                "used_mb": round(used_mb, 2),
                "remaining_mb": remaining_mb,
                "usage_percentage": usage_percentage,
                "percent_used": usage_percentage,
            },
            "storage_by_office_unit": cls.get_storage_usage_by_office_unit(usage_map, scope_ids),
        }

    @classmethod
    def resolve_office_unit_for_user(cls, user, office_unit_param=None):
        """Enforce role-based dashboard scope on the backend."""
        role = getattr(user, "role", None)

        if role == "admin":
            if not office_unit_param or str(office_unit_param).lower() in {"all", ""}:
                return None
            org_unit = OrgUnit.objects.filter(pk=office_unit_param, is_deleted=False).first()
            if not org_unit:
                raise NotFound("Office Unit not found.")
            return org_unit

        org_unit = getattr(user, "org_unit", None)
        if not org_unit or org_unit.is_deleted:
            raise PermissionDenied("Your account must be assigned to an Office Unit to view the dashboard.")

        if role == "staff":
            if office_unit_param and str(office_unit_param) not in {"", "all", str(org_unit.id)}:
                raise PermissionDenied("You can only view dashboard data for your assigned Office Unit.")
            return org_unit

        if role == "dept_head":
            scope_ids = get_accessible_org_unit_ids(user)
            if office_unit_param and str(office_unit_param).lower() not in {"", "all"}:
                try:
                    requested_id = int(office_unit_param)
                except (TypeError, ValueError) as exc:
                    raise PermissionDenied("Invalid Office Unit filter.") from exc
                if requested_id not in scope_ids:
                    raise PermissionDenied("You do not have access to this Office Unit.")
                requested = OrgUnit.objects.filter(pk=requested_id, is_deleted=False).first()
                if not requested:
                    raise NotFound("Office Unit not found.")
                return requested
            return org_unit

        raise PermissionDenied("You do not have access to the dashboard.")

    @classmethod
    def get_dashboard_for_user(cls, user, office_unit_param=None):
        org_unit = cls.resolve_office_unit_for_user(user, office_unit_param)
        role = getattr(user, "role", None)
        is_admin = role == "admin"

        if org_unit is None:
            payload = cls.get_global_dashboard_stats()
            payload["can_filter_office_units"] = is_admin
            return payload

        if role == "dept_head":
            scope_ids = org_unit_scope_ids(user)
            root = getattr(user, "org_unit", org_unit)
            if len(scope_ids) > 1 and str(org_unit.id) == str(root.id):
                payload = cls.get_subtree_dashboard_stats(root, scope_ids)
            else:
                payload = cls.get_office_unit_dashboard_stats(org_unit)
                if len(scope_ids) > 1:
                    usage_map = cls._usage_bytes_by_org_unit()
                    payload["storage_by_office_unit"] = cls.get_storage_usage_by_office_unit(
                        usage_map, scope_ids
                    )
                    payload["can_filter_office_units"] = True
                else:
                    payload["can_filter_office_units"] = False
            return payload

        payload = cls.get_office_unit_dashboard_stats(org_unit)
        payload["can_filter_office_units"] = is_admin
        return payload
