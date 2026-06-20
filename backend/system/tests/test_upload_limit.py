from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIClient

from accounts.models import User
from documents.models import Category, Document, Folder
from documents.views import validate_pdf_upload
from orgunits.models import OrgType, OrgUnit
from system.models import MAX_SYSTEM_STORAGE_QUOTA_MB, SystemSettings
from system.services import get_upload_limit_bytes, invalidate_system_settings_cache


class UploadLimitTests(TestCase):
    def setUp(self):
        settings = SystemSettings.load()
        settings.upload_limit_mb = 15
        settings.save()
        invalidate_system_settings_cache()

    def test_get_upload_limit_bytes_uses_system_settings(self):
        self.assertEqual(get_upload_limit_bytes(), 15 * 1024 * 1024)

    def test_validate_pdf_upload_rejects_oversized_file(self):
        upload = SimpleUploadedFile("large.pdf", b"%PDF" + b"0" * 100, content_type="application/pdf")
        upload.size = 16 * 1024 * 1024
        with self.assertRaises(ValidationError) as ctx:
            validate_pdf_upload(upload)
        self.assertIn("15 MB", str(ctx.exception.detail))

    def test_validate_pdf_upload_accepts_file_within_limit(self):
        upload = SimpleUploadedFile("small.pdf", b"%PDF-test", content_type="application/pdf")
        validate_pdf_upload(upload)


class SystemSettingsAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            email="admin-settings@test.local",
            password="Admin@12345",
            role="admin",
        )
        self.staff = User.objects.create_user(
            email="staff-settings@test.local",
            password="Staff@12345",
            role="staff",
        )
        SystemSettings.load()

    def test_staff_can_read_public_settings_fields(self):
        self.client.force_authenticate(user=self.staff)
        response = self.client.get("/api/system/settings/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("upload_limit_mb", response.data)
        self.assertIn("storage_quota_exceeded", response.data)
        self.assertNotIn("updated_at", response.data)

    def test_admin_can_update_settings(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.patch(
            "/api/system/settings/",
            {"upload_limit_mb": 20, "storage_quota_mb": 750},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["upload_limit_mb"], 20)
        self.assertEqual(response.data["storage_quota_mb"], 750)

    def test_staff_cannot_update_settings(self):
        self.client.force_authenticate(user=self.staff)
        response = self.client.patch(
            "/api/system/settings/",
            {"upload_limit_mb": 99},
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    def _set_system_quota_mb(self, quota_mb):
        settings = SystemSettings.load()
        settings.storage_quota_mb = quota_mb
        settings.save()
        invalidate_system_settings_cache()

    def _create_document_with_size_mb(self, org_unit, used_mb):
        folder = Folder.objects.create(name="Storage", org_unit=org_unit)
        category = Category.objects.create(name="General", org_unit=org_unit)
        upload = SimpleUploadedFile("sample.pdf", b"%PDF-test", content_type="application/pdf")
        Document.objects.create(
            title="sample.pdf",
            file=upload,
            folder=folder,
            category=category,
            file_size=int(used_mb * 1024 * 1024),
            mime_type="application/pdf",
        )

    def test_admin_cannot_reduce_quota_below_file_usage(self):
        org_unit = OrgUnit.objects.create(name="HQ")
        self._set_system_quota_mb(30000)
        self._create_document_with_size_mb(org_unit, 20480)

        self.client.force_authenticate(user=self.admin)
        response = self.client.patch(
            "/api/system/settings/",
            {"storage_quota_mb": 15360},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("storage_quota_mb", response.data)
        self.assertIn("file usage", str(response.data["storage_quota_mb"][0]).lower())

    def test_admin_cannot_reduce_quota_below_top_level_allocation(self):
        org_type = OrgType.objects.create(name="College")
        OrgUnit.objects.create(name="CISC", org_type=org_type, storage_quota_mb=15360)
        self._set_system_quota_mb(30000)

        self.client.force_authenticate(user=self.admin)
        response = self.client.patch(
            "/api/system/settings/",
            {"storage_quota_mb": 10240},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("storage_quota_mb", response.data)
        self.assertIn("office unit", str(response.data["storage_quota_mb"][0]).lower())

    def test_admin_can_set_quota_at_or_above_floor(self):
        org_type = OrgType.objects.create(name="College")
        org_unit = OrgUnit.objects.create(name="CISC", org_type=org_type, storage_quota_mb=15360)
        self._set_system_quota_mb(30000)
        self._create_document_with_size_mb(org_unit, 100)

        self.client.force_authenticate(user=self.admin)
        response = self.client.patch(
            "/api/system/settings/",
            {"storage_quota_mb": 15360},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["storage_quota_mb"], 15360)

    def test_admin_can_set_quota_up_to_5tb(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.patch(
            "/api/system/settings/",
            {"storage_quota_mb": MAX_SYSTEM_STORAGE_QUOTA_MB},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["storage_quota_mb"], MAX_SYSTEM_STORAGE_QUOTA_MB)

    def test_admin_cannot_set_quota_above_5tb(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.patch(
            "/api/system/settings/",
            {"storage_quota_mb": MAX_SYSTEM_STORAGE_QUOTA_MB + 1},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("storage_quota_mb", response.data)
        self.assertIn("5 TB", str(response.data["storage_quota_mb"][0]))
