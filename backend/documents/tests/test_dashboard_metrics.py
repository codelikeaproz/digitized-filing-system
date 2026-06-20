from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import User
from documents.models import Document, Folder
from orgunits.models import OrgType, OrgUnit


class DashboardGoogleDriveMetricTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.org_type = OrgType.objects.create(name="Department", code="department", is_active=True)
        self.org_unit = OrgUnit.objects.create(name="Engineering", org_type=self.org_type)
        self.folder = Folder.objects.create(name="Inbox", org_unit=self.org_unit)

        self.admin = User.objects.create_user(
            email="admin-dashboard-gdrive@test.local",
            password="Admin@12345",
            role="admin",
        )

        Document.objects.create(
            title="uploaded.pdf",
            file=SimpleUploadedFile("uploaded.pdf", b"%PDF-1.4 test", content_type="application/pdf"),
            folder=self.folder,
            file_size=1024,
        )
        Document.objects.create(
            title="drive-only",
            folder=self.folder,
            google_drive_link="https://drive.google.com/file/d/example/view",
        )

    def test_dashboard_counts_google_drive_only_documents_separately(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.get("/api/dashboard/", {"office_unit": self.org_unit.id})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["total_documents"], 2)
        self.assertEqual(response.data["google_drive_files"], 1)
