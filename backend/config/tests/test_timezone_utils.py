import re
from datetime import datetime, timezone as datetime_timezone

from django.test import TestCase
from django.utils import timezone

from config.timezone_utils import format_local_datetime, serialize_api_datetime

UTC = datetime_timezone.utc


ISO_UTC_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z$")


class TimezoneUtilsTests(TestCase):
    def test_serialize_api_datetime_from_aware_utc(self):
        dt = timezone.make_aware(datetime(2026, 6, 20, 9, 37, 9), UTC)
        self.assertEqual(serialize_api_datetime(dt), "2026-06-20T09:37:09Z")

    def test_serialize_api_datetime_from_naive_utc(self):
        dt = datetime(2026, 6, 20, 9, 37, 9)
        self.assertEqual(serialize_api_datetime(dt), "2026-06-20T09:37:09Z")

    def test_format_local_datetime_converts_utc_to_manila(self):
        dt = timezone.make_aware(datetime(2026, 6, 20, 9, 37, 9), UTC)
        formatted = format_local_datetime(dt)
        self.assertEqual(formatted, "2026-06-20 05:37:09 PM")

    def test_serialize_api_datetime_returns_none_for_empty(self):
        self.assertIsNone(serialize_api_datetime(None))
        self.assertIsNone(serialize_api_datetime(""))
