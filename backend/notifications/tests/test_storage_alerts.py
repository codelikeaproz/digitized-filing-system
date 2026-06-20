from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.exceptions import ValidationError

from notifications.models import Notification, StorageThresholdState
from notifications.storage_alerts import (
    check_allocation_thresholds,
    check_storage_thresholds,
    get_allocation_summary,
    get_global_storage_summary,
    reset_thresholds_if_quota_increased,
    validate_global_storage_quota,
)
from orgunits.models import OrgUnit
from system.models import SystemSettings
from system.services import invalidate_system_settings_cache


class StorageAlertsTests(TestCase):
    def setUp(self):
        self.org_unit = OrgUnit.objects.create(name="HQ")
        settings = SystemSettings.load()
        settings.storage_quota_mb = 500
        settings.save()
        invalidate_system_settings_cache()
        StorageThresholdState.objects.all().delete()

    def _set_used_mb(self, used_mb):
        from documents.models import Category, Document, Folder

        folder = Folder.objects.create(name="Storage", org_unit=self.org_unit)
        category = Category.objects.create(name="General", org_unit=self.org_unit)
        upload = SimpleUploadedFile("sample.pdf", b"%PDF-test", content_type="application/pdf")
        Document.objects.create(
            title="sample.pdf",
            file=upload,
            folder=folder,
            category=category,
            file_size=int(used_mb * 1024 * 1024),
            mime_type="application/pdf",
        )

    def test_threshold_notification_fires_once(self):
        self._set_used_mb(400)
        first = check_storage_thresholds()
        second = check_storage_thresholds()
        self.assertEqual(len(first), 1)
        self.assertEqual(second, [])
        self.assertEqual(Notification.objects.filter(threshold_percent=80).count(), 1)
        self.assertTrue(StorageThresholdState.load().fired_80)

    def test_multiple_thresholds_fire_in_one_pass(self):
        self._set_used_mb(500)
        created = check_storage_thresholds()
        titles = {item.title for item in created}
        self.assertIn("Storage Warning", titles)
        self.assertIn("Storage Alert", titles)
        self.assertIn("Critical Storage Alert", titles)
        self.assertIn("Storage Quota Exceeded", titles)
        self.assertEqual(
            Notification.objects.filter(audience=Notification.AUDIENCE_ADMIN, threshold_percent=90).count(),
            1,
        )

    def test_validate_global_storage_quota_blocks_at_capacity(self):
        self._set_used_mb(500)
        with self.assertRaises(ValidationError) as ctx:
            validate_global_storage_quota(1024)
        self.assertIn("Storage quota exceeded", str(ctx.exception.detail))

    def test_reset_thresholds_when_quota_increased(self):
        self._set_used_mb(500)
        check_storage_thresholds()
        state = StorageThresholdState.load()
        self.assertTrue(state.fired_100)

        settings = SystemSettings.load()
        settings.storage_quota_mb = 1000
        settings.save()
        invalidate_system_settings_cache()
        reset_thresholds_if_quota_increased(1000)

        state.refresh_from_db()
        self.assertFalse(state.fired_100)
        summary = get_global_storage_summary()
        self.assertEqual(summary["quota_mb"], 1000)

    def test_allocation_summary_tracks_allocated_quotas(self):
        OrgUnit.objects.all().delete()
        OrgUnit.objects.create(name="Unit A", storage_quota_mb=2000)
        OrgUnit.objects.create(name="Unit B", storage_quota_mb=1500)
        summary = get_allocation_summary()
        self.assertEqual(summary["quota_mb"], 500)
        self.assertEqual(summary["allocated_mb"], 3500)
        self.assertEqual(summary["remaining_mb"], 0)
        self.assertTrue(summary["allocation_exceeded"])

    def test_allocation_threshold_fires_once_at_ninety_percent(self):
        OrgUnit.objects.all().delete()
        StorageThresholdState.objects.all().delete()
        OrgUnit.objects.create(name="Unit A", storage_quota_mb=450)
        first = check_allocation_thresholds()
        second = check_allocation_thresholds()
        self.assertEqual(len(first), 1)
        self.assertEqual(second, [])
        self.assertEqual(first[0].title, "Storage Alert")
        self.assertEqual(first[0].audience, Notification.AUDIENCE_ADMIN)
        self.assertTrue(StorageThresholdState.load().alloc_fired_90)

    def test_allocation_threshold_fires_at_one_hundred_percent(self):
        OrgUnit.objects.all().delete()
        StorageThresholdState.objects.all().delete()
        OrgUnit.objects.create(name="Unit A", storage_quota_mb=500)
        created = check_allocation_thresholds()
        titles = {item.title for item in created}
        self.assertIn("Storage Alert", titles)
        self.assertIn("Storage Quota Exceeded", titles)
        self.assertTrue(StorageThresholdState.load().alloc_fired_100)
