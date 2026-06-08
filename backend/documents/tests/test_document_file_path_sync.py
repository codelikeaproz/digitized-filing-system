import json

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase
from io import StringIO
from rest_framework.test import APIClient

from accounts.models import User
from documents.models import Category, Document, Folder
from documents.serializers import DocumentSerializer
from documents.services import resolve_document_file_path
from orgunits.models import OrgType, OrgUnit


class DocumentFilePathSyncTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.org_type = OrgType.objects.create(name="Department", code="department", is_active=True)
        self.sdd = OrgUnit.objects.create(name="SDD", org_type=self.org_type)
        self.admin = User.objects.create_user(
            email="admin-path-sync@test.local",
            password="Test@12345",
            role="admin",
        )

        self.parent_folder = Folder.objects.create(name="Systems", org_unit=self.sdd)
        self.child_folder = Folder.objects.create(
            name="Audits",
            org_unit=self.sdd,
            parent=self.parent_folder,
        )
        self.category = Category.objects.create(
            name="Reports",
            code="REP",
            org_unit=self.sdd,
        )
        pdf = SimpleUploadedFile("report.pdf", b"%PDF-1.4 test", content_type="application/pdf")
        self.document = Document.objects.create(
            title="report.pdf",
            file=pdf,
            folder=self.child_folder,
            category=self.category,
            file_path="Stale > Old > Path",
            description="Test document",
        )

    def test_resolve_document_file_path_prefers_live_folder_path(self):
        self.assertEqual(resolve_document_file_path(self.document), "Systems > Audits")

    def test_serializer_file_path_ignores_stale_cache(self):
        data = DocumentSerializer(self.document).data
        self.assertEqual(data["filePath"], "Systems > Audits")

    def test_folder_rename_cascades_file_path_to_documents(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.patch(
            f"/api/folders/{self.child_folder.id}/rename",
            {"name": "Audits Renamed"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)

        self.document.refresh_from_db()
        self.assertEqual(self.document.file_path, "Systems > Audits Renamed")
        self.assertEqual(
            DocumentSerializer(self.document).data["filePath"],
            "Systems > Audits Renamed",
        )

    def test_upload_sets_server_side_file_path(self):
        self.client.force_authenticate(user=self.admin)
        upload = SimpleUploadedFile("uploaded.pdf", b"%PDF-1.4 upload", content_type="application/pdf")
        response = self.client.post(
            "/api/documents/upload",
            {
                "file": upload,
                "folderId": str(self.child_folder.id),
                "categoryId": str(self.category.id),
                "description": "Upload test",
                "requisitioners": json.dumps(
                    [{"firstName": "Jane", "lastName": "Doe", "employeeNumber": "", "suffix": ""}]
                ),
                "filePath": "Client > Wrong > Path",
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["filePath"], "Systems > Audits")

        created = Document.objects.get(pk=response.data["id"])
        self.assertEqual(created.file_path, "Systems > Audits")

    def test_recycle_bin_location_path_uses_live_folder_path(self):
        self.document.is_deleted = True
        self.document.save(update_fields=["is_deleted"])

        self.client.force_authenticate(user=self.admin)
        response = self.client.get("/api/recycle-bin", {"type": "documents"})
        self.assertEqual(response.status_code, 200)
        row = next(item for item in response.data["results"] if item["id"] == str(self.document.id))
        self.assertEqual(row["locationPath"], "Systems > Audits")

    def test_recompute_document_file_paths_command_fixes_stale_rows(self):
        out = StringIO()
        call_command("recompute_document_file_paths", stdout=out)
        self.document.refresh_from_db()
        self.assertEqual(self.document.file_path, "Systems > Audits")
        self.assertIn("Updated 1 document(s).", out.getvalue())
