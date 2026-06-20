from datetime import datetime, timezone as datetime_timezone

from django.utils import timezone
from django.utils.dateparse import parse_datetime


DISPLAY_DATETIME_FORMAT = "%Y-%m-%d %I:%M:%S %p"
INPUT_DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
UTC = datetime_timezone.utc


def _parse_datetime_value(value):
    if not value:
        return None

    if isinstance(value, datetime):
        return value

    if isinstance(value, str):
        dt = parse_datetime(value)
        if dt:
            return dt
        try:
            return datetime.strptime(value, INPUT_DATETIME_FORMAT)
        except ValueError:
            return None

    return None


def _to_aware_utc(dt):
    if timezone.is_naive(dt):
        return timezone.make_aware(dt, UTC)
    return dt.astimezone(UTC)


def serialize_api_datetime(value):
    """Return an ISO 8601 UTC string for JSON API responses."""
    dt = _parse_datetime_value(value)
    if not dt:
        return None
    return _to_aware_utc(dt).isoformat().replace("+00:00", "Z")


def local_datetime(value):
    dt = _parse_datetime_value(value)
    if not dt:
        return None
    return timezone.localtime(_to_aware_utc(dt))


def format_local_datetime(value):
    """Human-readable Manila datetime for exports (audit XLSX, etc.)."""
    dt = local_datetime(value)
    return dt.strftime(DISPLAY_DATETIME_FORMAT) if dt else None
