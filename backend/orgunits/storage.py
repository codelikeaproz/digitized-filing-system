"""
Storage quota helpers for OrgUnit-scoped PDF storage.

Tracks usage in megabytes (MB) and validates uploads against per-unit quotas.
Usage includes soft-deleted documents until they are permanently removed.
"""
from decimal import Decimal

from django.db.models import Sum

from documents.models import Document
from .models import OrgUnit


BYTES_PER_MB = 1024 * 1024
DEFAULT_STORAGE_QUOTA_MB = 1024


def bytes_to_mb(byte_count):
    if not byte_count:
        return Decimal("0")
    return (Decimal(byte_count) / Decimal(BYTES_PER_MB)).quantize(Decimal("0.01"))


def validate_storage_quota(org_unit, additional_bytes):
    """Raise ValidationError if upload would exceed the OrgUnit storage quota."""
    from rest_framework.exceptions import ValidationError

    if not org_unit:
        raise ValidationError({"file": "Target Office Unit is required for storage validation."})

    quota_mb = org_unit.storage_quota_mb or DEFAULT_STORAGE_QUOTA_MB
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


def get_total_allocated_quota_mb(exclude_org_unit=None):
    """Sum of storage_quota_mb across active (non-deleted) Office Units."""
    queryset = OrgUnit.objects.filter(is_deleted=False)
    if exclude_org_unit is not None:
        queryset = queryset.exclude(pk=exclude_org_unit.pk)
    total = queryset.aggregate(total=Sum("storage_quota_mb"))["total"]
    return int(total or 0)


def get_available_allocation_mb(org_unit=None):
    """Remaining system storage headroom for new or updated Office Unit quotas."""
    from system.services import get_storage_quota_mb

    system_mb = get_storage_quota_mb()
    others_mb = get_total_allocated_quota_mb(exclude_org_unit=org_unit)
    return max(0, int(system_mb) - others_mb)


def validate_org_unit_allocation_quota(requested_mb, org_unit=None):
    """
    Raise ValidationError if requested quota exceeds available allocation headroom.
    On update, org_unit is excluded from the allocated sum so its own quota can be reallocated.
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

    available_mb = get_available_allocation_mb(org_unit=org_unit)
    if requested_mb > available_mb:
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


def get_storage_summary(org_unit):
    quota_mb = org_unit.storage_quota_mb or DEFAULT_STORAGE_QUOTA_MB
    used_mb = org_unit.storage_used_mb or Decimal("0")
    remaining_mb = max(Decimal("0"), Decimal(quota_mb) - used_mb)
    percent_used = float((used_mb / Decimal(quota_mb) * Decimal("100")).quantize(Decimal("0.1"))) if quota_mb else 0.0
    return {
        "org_unit_id": str(org_unit.id),
        "org_unit_name": org_unit.name,
        "used_mb": float(used_mb),
        "quota_mb": int(quota_mb),
        "remaining_mb": float(remaining_mb),
        "percent_used": percent_used,
    }
