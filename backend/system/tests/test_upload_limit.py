from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIClient

from accounts.models import User
from documents.views import validate_pdf_upload
from system.models import SystemSettings
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
