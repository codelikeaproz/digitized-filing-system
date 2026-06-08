from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import User
from auditlogs.models import AuditLog
from documents.confirmation import build_permanent_delete_confirmation
from documents.models import Document, Folder
from orgunits.models import OrgType, OrgUnit


class RecycleBinPermanentDeleteTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.org_type = OrgType.objects.create(name="Department", code="department", is_active=True)
        self.cisc = OrgUnit.objects.create(name="CISC", org_type=self.org_type)
        self.sdd = OrgUnit.objects.create(name="SDD", org_type=self.org_type, parent=self.cisc)

        self.admin = User.objects.create_user(
            email="admin-recycle@test.local",
            password="Test@12345",
            role="admin",
        )
        self.cisc_head = User.objects.create_user(
            email="cisc-head-recycle@test.local",
            password="Test@12345",
            role="dept_head",
            org_unit=self.cisc,
        )
        self.sdd_staff = User.objects.create_user(
            email="sdd-staff-recycle@test.local",
            password="Test@12345",
            role="staff",
            org_unit=self.sdd,
        )

        self.sdd_folder = Folder.objects.create(name="SDD Root", org_unit=self.sdd)
        pdf = SimpleUploadedFile("sample.pdf", b"%PDF-1.4 test", content_type="application/pdf")
        self.deleted_doc = Document.objects.create(
            title="SampleData.pdf",
            file=pdf,
            folder=self.sdd_folder,
            file_size=2048,
            is_deleted=True,
            deleted_by=self.admin,
        )
        self.deleted_folder = Folder.objects.create(
            name="Archive Folder",
            org_unit=self.sdd,
            is_deleted=True,
            deleted_by=self.admin,
        )

    def test_admin_permanent_delete_document_with_valid_confirmation(self):
        confirmation = build_permanent_delete_confirmation(self.deleted_doc.title)
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(
            "/api/recycle-bin/delete",
            {
                "type": "document",
                "id": self.deleted_doc.id,
                "confirmation": confirmation,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Document.objects.filter(pk=self.deleted_doc.id).exists())
        self.assertTrue(
            AuditLog.objects.filter(
                action="PERMANENT_DELETE_DOCUMENT",
                target_name="SampleData.pdf",
            ).exists()
        )

    def test_wrong_confirmation_returns_400_and_keeps_document(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(
            "/api/recycle-bin/delete",
            {
                "type": "document",
                "id": self.deleted_doc.id,
                "confirmation": "delete sampledata.pdf",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["message"], "Invalid deletion confirmation.")
        self.assertTrue(Document.objects.filter(pk=self.deleted_doc.id).exists())
        self.assertTrue(
            AuditLog.objects.filter(action="PERMANENT_DELETE_FAILED").exists()
        )

    def test_missing_confirmation_on_post_returns_400(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(
            "/api/recycle-bin/delete",
            {"type": "document", "id": self.deleted_doc.id},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["message"], "Invalid deletion confirmation.")

    def test_raw_delete_without_confirmation_returns_400(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.delete(
            f"/api/recycle-bin/delete?type=document&id={self.deleted_doc.id}"
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["message"], "Invalid deletion confirmation.")
        self.assertTrue(Document.objects.filter(pk=self.deleted_doc.id).exists())
        self.assertTrue(
            AuditLog.objects.filter(action="PERMANENT_DELETE_FAILED").exists()
        )

    def test_staff_cannot_permanent_delete(self):
        confirmation = build_permanent_delete_confirmation(self.deleted_doc.title)
        self.client.force_authenticate(user=self.sdd_staff)
        response = self.client.post(
            "/api/recycle-bin/delete",
            {
                "type": "document",
                "id": self.deleted_doc.id,
                "confirmation": confirmation,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Document.objects.filter(pk=self.deleted_doc.id).exists())

    def test_folder_permanent_delete_with_valid_confirmation(self):
        confirmation = build_permanent_delete_confirmation(self.deleted_folder.name)
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(
            "/api/recycle-bin/delete",
            {
                "type": "folder",
                "id": self.deleted_folder.id,
                "confirmation": confirmation,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Folder.objects.filter(pk=self.deleted_folder.id).exists())
        self.assertTrue(
            AuditLog.objects.filter(
                action="PERMANENT_DELETE_FOLDER",
                target_name="Archive Folder",
            ).exists()
        )

    def test_dept_head_scoped_permanent_delete_with_valid_confirmation(self):
        confirmation = build_permanent_delete_confirmation(self.deleted_doc.title)
        self.client.force_authenticate(user=self.cisc_head)
        response = self.client.post(
            "/api/recycle-bin/delete",
            {
                "type": "document",
                "id": self.deleted_doc.id,
                "confirmation": confirmation,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Document.objects.filter(pk=self.deleted_doc.id).exists())
