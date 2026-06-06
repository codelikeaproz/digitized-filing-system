"""Global storage threshold monitoring and notification generation."""
from decimal import Decimal

from django.db.models import Sum
from django.db.models.functions import Coalesce
from rest_framework.exceptions import ValidationError

from auditlogs.models import log_audit
from documents.models import Document
from orgunits.storage import bytes_to_mb
from system.services import get_storage_quota_mb

from .models import Notification, StorageThresholdState

THRESHOLDS = [
    (80, "fired_80", Notification.LEVEL_WARNING, "STORAGE_WARNING_GENERATED"),
    (90, "fired_90", Notification.LEVEL_ALERT, "STORAGE_ALERT_GENERATED"),
    (95, "fired_95", Notification.LEVEL_CRITICAL, "STORAGE_CRITICAL_ALERT_GENERATED"),
    (100, "fired_100", Notification.LEVEL_EXCEEDED, "STORAGE_QUOTA_EXCEEDED"),
]

ALLOCATION_THRESHOLDS = [
    (90, "alloc_fired_90", Notification.LEVEL_ALERT, "STORAGE_ALLOCATION_ALERT_GENERATED"),
    (100, "alloc_fired_100", Notification.LEVEL_EXCEEDED, "STORAGE_ALLOCATION_EXCEEDED"),
]

ADMIN_90_TITLE = "Storage Administration Notice"
ADMIN_90_MESSAGE = (
    "Storage capacity has reached 90%.\n\n"
    "Consider increasing the allocated storage quota."
)


def get_total_used_bytes():
    return (
        Document.objects.aggregate(total=Coalesce(Sum("file_size"), 0)).get("total") or 0
    )


def get_global_storage_summary():
    quota_mb = get_storage_quota_mb()
    used_bytes = get_total_used_bytes()
    used_mb = float(bytes_to_mb(used_bytes))
    remaining_mb = round(max(0.0, quota_mb - used_mb), 2)
    usage_percentage = round((used_mb / quota_mb) * 100, 1) if quota_mb else 0.0
    quota_exceeded = used_mb >= quota_mb if quota_mb else False
    return {
        "quota_mb": int(quota_mb),
        "used_mb": round(used_mb, 2),
        "remaining_mb": remaining_mb,
        "usage_percentage": usage_percentage,
        "quota_exceeded": quota_exceeded,
        "used_bytes": int(used_bytes),
    }


def get_allocation_summary():
    from orgunits.storage import get_total_allocated_quota_mb

    quota_mb = get_storage_quota_mb()
    allocated_mb = get_total_allocated_quota_mb()
    remaining_mb = max(0, int(quota_mb) - allocated_mb)
    allocation_percentage = round((allocated_mb / quota_mb) * 100, 1) if quota_mb else 0.0
    allocation_exceeded = allocated_mb >= quota_mb if quota_mb else False
    return {
        "quota_mb": int(quota_mb),
        "allocated_mb": int(allocated_mb),
        "remaining_mb": remaining_mb,
        "allocation_percentage": allocation_percentage,
        "allocation_exceeded": allocation_exceeded,
    }


def validate_global_storage_quota(additional_bytes):
    summary = get_global_storage_summary()
    quota_mb = summary["quota_mb"]
    if not quota_mb:
        return

    incoming_mb = float(bytes_to_mb(additional_bytes or 0))
    used_mb = summary["used_mb"]
    if used_mb + incoming_mb > quota_mb:
        raise ValidationError(
            {
                "file": (
                    "Storage quota exceeded. Please contact your system administrator."
                )
            }
        )


def _format_mb(value):
    if isinstance(value, float) and value == int(value):
        return str(int(value))
    return str(round(float(value), 2)).rstrip("0").rstrip(".")


def _build_notification_content(threshold, used_mb, remaining_mb):
    used_label = _format_mb(used_mb)
    remaining_label = _format_mb(remaining_mb)

    if threshold == 80:
        return (
            "Storage Warning",
            (
                "System storage has reached 80% capacity.\n\n"
                f"Used Storage: {used_label} MB\n"
                f"Remaining Storage: {remaining_label} MB"
            ),
        )
    if threshold == 90:
        return (
            "Storage Alert",
            (
                "System storage has reached 90% capacity.\n\n"
                f"Used Storage: {used_label} MB\n"
                f"Remaining Storage: {remaining_label} MB\n\n"
                "New office unit storage allocations may be limited.\n\n"
                "Please coordinate with your administrator regarding additional storage."
            ),
        )
    if threshold == 95:
        return (
            "Critical Storage Alert",
            (
                f"Only {remaining_label} MB of storage remains.\n\n"
                "Uploads may be restricted once storage capacity is reached."
            ),
        )
    return (
        "Storage Quota Exceeded",
        (
            "No additional office unit storage allocations can be created until "
            "storage capacity is increased."
        ),
    )


def _build_allocation_notification_content(threshold, allocated_mb, remaining_mb, quota_mb):
    allocated_label = _format_mb(allocated_mb)
    remaining_label = _format_mb(remaining_mb)
    quota_label = _format_mb(quota_mb)

    if threshold == 90:
        return (
            "Storage Alert",
            (
                "System storage has reached 90% capacity.\n\n"
                f"Allocated Storage: {allocated_label} MB of {quota_label} MB\n"
                f"Remaining Allocation: {remaining_label} MB\n\n"
                "New office unit storage allocations may be limited."
            ),
        )
    return (
        "Storage Quota Exceeded",
        (
            "No additional office unit storage allocations can be created until "
            "storage capacity is increased."
        ),
    )


def reset_thresholds_if_quota_increased(new_quota_mb):
    state = StorageThresholdState.load()
    summary = get_global_storage_summary()
    used_mb = summary["used_mb"]
    usage_pct = (used_mb / new_quota_mb * 100) if new_quota_mb else 0

    state.fired_80 = usage_pct >= 80
    state.fired_90 = usage_pct >= 90
    state.fired_95 = usage_pct >= 95
    state.fired_100 = usage_pct >= 100

    allocation_summary = get_allocation_summary()
    alloc_pct = allocation_summary["allocation_percentage"]
    state.alloc_fired_90 = alloc_pct >= 90
    state.alloc_fired_100 = alloc_pct >= 100
    state.quota_mb_at_last_reset = int(new_quota_mb)
    state.save()


def check_storage_thresholds(trigger_user=None):
    summary = get_global_storage_summary()
    quota_mb = summary["quota_mb"]
    if not quota_mb:
        return []

    used_mb = summary["used_mb"]
    remaining_mb = summary["remaining_mb"]
    usage_pct = summary["usage_percentage"]
    state = StorageThresholdState.load()
    created = []

    for threshold, flag_name, level, audit_action in THRESHOLDS:
        if usage_pct < threshold:
            continue
        if getattr(state, flag_name):
            continue

        title, message = _build_notification_content(threshold, used_mb, remaining_mb)
        notification = Notification.objects.create(
            title=title,
            message=message,
            level=level,
            threshold_percent=threshold,
            audience=Notification.AUDIENCE_ALL,
        )
        created.append(notification)
        setattr(state, flag_name, True)

        log_audit(
            trigger_user,
            audit_action,
            f"{title} — used {used_mb} MB of {quota_mb} MB ({usage_pct}%)",
            target_type="system_storage",
            target_name=title,
        )

        if threshold == 90:
            admin_notification = Notification.objects.create(
                title=ADMIN_90_TITLE,
                message=ADMIN_90_MESSAGE,
                level=Notification.LEVEL_ALERT,
                threshold_percent=90,
                audience=Notification.AUDIENCE_ADMIN,
            )
            created.append(admin_notification)

    if created:
        state.quota_mb_at_last_reset = int(quota_mb)
        state.save()

    return created


def check_allocation_thresholds(trigger_user=None):
    summary = get_allocation_summary()
    quota_mb = summary["quota_mb"]
    if not quota_mb:
        return []

    allocated_mb = summary["allocated_mb"]
    remaining_mb = summary["remaining_mb"]
    allocation_pct = summary["allocation_percentage"]
    state = StorageThresholdState.load()
    created = []

    for threshold, flag_name, level, audit_action in ALLOCATION_THRESHOLDS:
        if allocation_pct < threshold:
            continue
        if getattr(state, flag_name):
            continue

        title, message = _build_allocation_notification_content(
            threshold, allocated_mb, remaining_mb, quota_mb
        )
        notification = Notification.objects.create(
            title=title,
            message=message,
            level=level,
            threshold_percent=threshold,
            audience=Notification.AUDIENCE_ADMIN,
        )
        created.append(notification)
        setattr(state, flag_name, True)

        log_audit(
            trigger_user,
            audit_action,
            (
                f"{title} — allocated {allocated_mb} MB of {quota_mb} MB "
                f"({allocation_pct}%)"
            ),
            target_type="system_storage",
            target_name=title,
        )

    if created:
        state.quota_mb_at_last_reset = int(quota_mb)
        state.save()

    return created
