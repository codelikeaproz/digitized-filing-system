"""
Storage quota helpers for OrgUnit-scoped PDF storage.

Tracks usage in megabytes (MB) and validates uploads against per-unit quotas.
Usage includes soft-deleted documents until they are permanently removed.

Allocation model (hierarchical):
- Top-level Office Units draw from the system storage pool.
- Child Office Units draw from their immediate parent's allocated quota.
"""
from decimal import Decimal

from django.db.models import Sum

from documents.models import Document
from .models import OrgUnit


BYTES_PER_MB = 1024 * 1024
DEFAULT_STORAGE_QUOTA_MB = 1024

ALLOCATION_ERROR_MESSAGES = (
    "Insufficient available system storage.",
    "Insufficient available parent storage.",
    "Child Office Unit allocations exceed the available Parent Office Unit storage.",
    "Parent allocation cannot be reduced below the total allocated child storage.",
)


def bytes_to_mb(byte_count):
    if not byte_count:
        return Decimal("0")
    return (Decimal(byte_count) / Decimal(BYTES_PER_MB)).quantize(Decimal("0.01"))


def is_top_level(org_unit):
    return org_unit is None or org_unit.parent_id is None


def org_unit_has_active_children(org_unit):
    if not org_unit:
        return False
    return OrgUnit.objects.filter(parent=org_unit, is_deleted=False).exists()


def get_subtree_org_unit_ids(org_unit):
    """Return org_unit id plus all descendant ids."""
    ids = [org_unit.id]
    for child in org_unit.get_all_children():
        ids.append(child.id)
    return ids


def get_subtree_used_bytes(org_unit):
    """Sum file sizes for org_unit and all descendants (includes soft-deleted)."""
    if not org_unit:
        return 0
    org_unit_ids = get_subtree_org_unit_ids(org_unit)
    return (
        Document.objects.filter(folder__org_unit_id__in=org_unit_ids)
        .aggregate(total=Sum("file_size"))
        .get("total")
        or 0
    )


def get_own_used_bytes(org_unit):
    if not org_unit:
        return 0
    return (
        Document.objects.filter(folder__org_unit=org_unit)
        .aggregate(total=Sum("file_size"))
        .get("total")
        or 0
    )


def get_display_used_mb(org_unit):
    """
    Used storage for display and parent upload validation.
    Parents with children: rollup of own + descendant documents.
    Leaf/child units: own documents only.
    """
    if org_unit_has_active_children(org_unit):
        return float(bytes_to_mb(get_subtree_used_bytes(org_unit)))
    return float(bytes_to_mb(get_own_used_bytes(org_unit)))


def get_direct_children_quota_mb(parent, exclude_org_unit=None):
    """Sum storage_quota_mb for direct active children of parent."""
    if parent is None:
        return 0
    queryset = OrgUnit.objects.filter(parent=parent, is_deleted=False)
    if exclude_org_unit is not None:
        queryset = queryset.exclude(pk=exclude_org_unit.pk)
    total = queryset.aggregate(total=Sum("storage_quota_mb"))["total"]
    return int(total or 0)


def get_top_level_allocated_quota_mb(exclude_org_unit=None):
    """Sum storage_quota_mb for active top-level (root) Office Units."""
    queryset = OrgUnit.objects.filter(is_deleted=False, parent__isnull=True)
    if exclude_org_unit is not None and is_top_level(exclude_org_unit):
        queryset = queryset.exclude(pk=exclude_org_unit.pk)
    total = queryset.aggregate(total=Sum("storage_quota_mb"))["total"]
    return int(total or 0)


def get_total_allocated_quota_mb(exclude_org_unit=None):
    """Sum of top-level allocations (system pool consumption)."""
    return get_top_level_allocated_quota_mb(exclude_org_unit=exclude_org_unit)


def get_system_available_allocation_mb(exclude_org_unit=None):
    """Remaining system storage headroom for top-level Office Unit quotas."""
    from system.services import get_storage_quota_mb

    system_mb = get_storage_quota_mb()
    others_mb = get_top_level_allocated_quota_mb(exclude_org_unit=exclude_org_unit)
    return max(0, int(system_mb) - others_mb)


def get_parent_available_allocation_mb(parent, exclude_org_unit=None):
    """Remaining parent quota headroom for child Office Unit allocations."""
    if parent is None:
        return 0
    parent_quota = parent.storage_quota_mb or DEFAULT_STORAGE_QUOTA_MB
    children_mb = get_direct_children_quota_mb(parent, exclude_org_unit=exclude_org_unit)
    return max(0, int(parent_quota) - children_mb)


def get_available_allocation_mb(org_unit=None, parent=None):
    """
    Remaining allocation headroom for new or updated Office Unit quotas.
    Top-level units use system pool; child units use immediate parent pool.
    """
    if parent is not None:
        return get_parent_available_allocation_mb(parent, exclude_org_unit=org_unit)
    return get_system_available_allocation_mb(exclude_org_unit=org_unit)


def validate_parent_reduction(org_unit, new_quota_mb):
    """Block reducing a parent quota below the sum of direct child allocations."""
    from rest_framework.exceptions import ValidationError

    if org_unit is None or new_quota_mb is None:
        return

    children_allocated_mb = get_direct_children_quota_mb(org_unit)
    if children_allocated_mb <= new_quota_mb:
        return

    raise ValidationError(
        {
            "storageQuotaMb": (
                "Parent allocation cannot be reduced below the total allocated child storage.\n\n"
                f"Current Child Allocation: {children_allocated_mb} MB\n"
                f"Requested Parent Allocation: {new_quota_mb} MB"
            ),
            "message": "Parent allocation cannot be reduced below the total allocated child storage.",
        }
    )


def validate_org_unit_allocation_quota(requested_mb, org_unit=None, parent=None):
    """
    Raise ValidationError if requested quota exceeds available allocation headroom.
    Top-level units validate against system pool; child units against parent pool.
    """
    from rest_framework.exceptions import ValidationError

    if requested_mb is None:
        return

    if org_unit is not None:
        used_mb = float(org_unit.storage_used_mb or 0)
        if requested_mb < used_mb:
            raise ValidationError(
                {
                    "storageQuotaMb": (
                        f"Storage quota cannot be less than current usage ({used_mb} MB)."
                    )
                }
            )

        if org_unit_has_active_children(org_unit):
            validate_parent_reduction(org_unit, requested_mb)

    resolved_parent = parent
    if resolved_parent is None and org_unit is not None and org_unit.parent_id:
        resolved_parent = org_unit.parent

    available_mb = get_available_allocation_mb(org_unit=org_unit, parent=resolved_parent)

    if requested_mb > available_mb:
        if resolved_parent is not None:
            parent_quota = resolved_parent.storage_quota_mb or DEFAULT_STORAGE_QUOTA_MB
            children_allocated_mb = get_direct_children_quota_mb(
                resolved_parent, exclude_org_unit=org_unit
            )
            raise ValidationError(
                {
                    "storageQuotaMb": (
                        "Child Office Unit allocations exceed the available Parent Office Unit storage.\n\n"
                        f"Parent Allocation: {parent_quota} MB\n"
                        f"Allocated to Children: {children_allocated_mb + requested_mb} MB\n"
                        f"Available: {available_mb} MB\n\n"
                        f"Requested: {requested_mb} MB"
                    ),
                    "message": (
                        "Child Office Unit allocations exceed the available Parent Office Unit storage."
                    ),
                }
            )

        raise ValidationError(
            {
                "storageQuotaMb": (
                    "Insufficient available system storage.\n\n"
                    f"Requested: {requested_mb} MB\n"
                    f"Available: {available_mb} MB\n\n"
                    "Please reduce the storage allocation or increase the system storage quota."
                ),
                "message": "Insufficient available system storage.",
            }
        )


def validate_storage_quota(org_unit, additional_bytes):
    """Raise ValidationError if upload would exceed the OrgUnit storage quota."""
    from rest_framework.exceptions import ValidationError

    if not org_unit:
        raise ValidationError({"file": "Target Office Unit is required for storage validation."})

    quota_mb = org_unit.storage_quota_mb or DEFAULT_STORAGE_QUOTA_MB
    if org_unit_has_active_children(org_unit):
        used_mb = Decimal(str(get_display_used_mb(org_unit)))
    else:
        used_mb = org_unit.storage_used_mb or Decimal("0")
    incoming_mb = bytes_to_mb(additional_bytes)

    if used_mb + incoming_mb > Decimal(quota_mb):
        remaining_mb = max(Decimal("0"), Decimal(quota_mb) - used_mb)
        raise ValidationError(
            {
                "file": (
                    f"Storage quota exceeded for {org_unit.name}. "
                    f"Used {used_mb} MB of {quota_mb} MB. "
                    f"Remaining: {remaining_mb} MB. "
                    f"Upload requires {incoming_mb} MB."
                )
            }
        )


def add_storage_usage(org_unit, byte_count):
    if not org_unit or not byte_count:
        return
    org_unit.storage_used_mb = (org_unit.storage_used_mb or Decimal("0")) + bytes_to_mb(byte_count)
    org_unit.save(update_fields=["storage_used_mb"])


def subtract_storage_usage(org_unit, byte_count):
    if not org_unit or not byte_count:
        return
    next_used = (org_unit.storage_used_mb or Decimal("0")) - bytes_to_mb(byte_count)
    org_unit.storage_used_mb = max(Decimal("0"), next_used)
    org_unit.save(update_fields=["storage_used_mb"])


def recalculate_org_unit_storage(org_unit):
    """Recompute storage_used_mb from active and soft-deleted documents."""
    total_bytes = (
        Document.objects.filter(folder__org_unit=org_unit)
        .aggregate(total=Sum("file_size"))
        .get("total")
        or 0
    )
    org_unit.storage_used_mb = bytes_to_mb(total_bytes)
    org_unit.save(update_fields=["storage_used_mb"])
    return org_unit.storage_used_mb


def build_allocation_context(org_unit):
    """Build allocation context dict for API responses."""
    if org_unit.parent_id:
        parent = org_unit.parent
        parent_allocation_mb = int(parent.storage_quota_mb or DEFAULT_STORAGE_QUOTA_MB)
        children_allocated_mb = get_direct_children_quota_mb(parent, exclude_org_unit=org_unit)
        available_mb = get_parent_available_allocation_mb(parent, exclude_org_unit=org_unit)
        return {
            "source": "parent",
            "parentName": parent.name,
            "parentAllocationMb": parent_allocation_mb,
            "childrenAllocatedMb": children_allocated_mb,
            "availableForAllocationMb": available_mb,
        }

    from system.services import get_storage_quota_mb

    system_mb = get_storage_quota_mb()
    top_level_allocated_mb = get_top_level_allocated_quota_mb(exclude_org_unit=org_unit)
    available_mb = get_system_available_allocation_mb(exclude_org_unit=org_unit)
    return {
        "source": "system",
        "parentName": None,
        "parentAllocationMb": int(system_mb),
        "childrenAllocatedMb": top_level_allocated_mb,
        "availableForAllocationMb": available_mb,
    }


def get_storage_summary(org_unit):
    quota_mb = org_unit.storage_quota_mb or DEFAULT_STORAGE_QUOTA_MB
    used_mb = get_display_used_mb(org_unit)
    remaining_mb = max(0.0, float(quota_mb) - used_mb)
    percent_used = float((Decimal(str(used_mb)) / Decimal(quota_mb) * Decimal("100")).quantize(Decimal("0.1"))) if quota_mb else 0.0
    return {
        "org_unit_id": str(org_unit.id),
        "org_unit_name": org_unit.name,
        "used_mb": round(used_mb, 2),
        "quota_mb": int(quota_mb),
        "remaining_mb": round(remaining_mb, 2),
        "percent_used": percent_used,
    }
