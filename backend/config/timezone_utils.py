from datetime import datetime

from django.utils import timezone
from django.utils.dateparse import parse_datetime


DISPLAY_DATETIME_FORMAT = "%Y-%m-%d %I:%M:%S %p"
INPUT_DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"


def local_datetime(value):
    if not value:
        return None

    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, str):
        dt = parse_datetime(value)
        if not dt:
            try:
                dt = datetime.strptime(value, INPUT_DATETIME_FORMAT)
            except ValueError:
                return None
    else:
        return None

    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt, timezone.get_current_timezone())
    return timezone.localtime(dt)


def format_local_datetime(value):
    dt = local_datetime(value)
    return dt.strftime(DISPLAY_DATETIME_FORMAT) if dt else None
