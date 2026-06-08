from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import User
from auditlogs.models import AuditLog
from documents.confirmation import build_bulk_permanent_delete_confirmation
from documents.models import Document, Folder
from orgunits.models import OrgType, OrgUnit


class RecycleBinBulkActionsTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.org_type = OrgType.objects.create(name="Department", code="department", is_active=True)
        self.cisc = OrgUnit.objects.create(name="CISC", org_type=self.org_type)
        self.sdd = OrgUnit.objects.create(name="SDD", org_type=self.org_type, parent=self.cisc)

        self.admin = User.objects.create_user(
            email="admin-bulk-recycle@test.local",
            password="Test@12345",
            role="admin",
        )
        self.cisc_head = User.objects.create_user(
            email="cisc-head-bulk-recycle@test.local",
            password="Test@12345",
            role="dept_head",
            org_unit=self.cisc,
        )
        self.sdd_staff = User.objects.create_user(
            email="sdd-staff-bulk-recycle@test.local",
            password="Test@12345",
            role="staff",
            org_unit=self.sdd,
        )

        self.parent_folder = Folder.objects.create(name="Research Folder", org_unit=self.sdd)
        self.child_folder = Folder.objects.create(
            name="Images",
            org_unit=self.sdd,
            parent=self.parent_folder,
        )
        pdf_parent = SimpleUploadedFile("report.pdf", b"%PDF-1.4 parent", content_type="application/pdf")
        pdf_child = SimpleUploadedFile("budget.pdf", b"%PDF-1.4 child", content_type="application/pdf")
        pdf_standalone = SimpleUploadedFile("standalone.pdf", b"%PDF-1.4 standalone", content_type="application/pdf")

        self.parent_doc = Document.objects.create(
            title="Report.docx",
            file=pdf_parent,
            folder=self.parent_folder,
            file_size=1024,
            is_deleted=True,
            deleted_by=self.admin,
        )
        self.child_doc = Document.objects.create(
            title="Budget.xlsx",
            file=pdf_child,
            folder=self.child_folder,
            file_size=2048,
            is_deleted=True,
            deleted_by=self.admin,
        )
        self.active_folder = Folder.objects.create(name="Active Parent", org_unit=self.sdd)
        self.standalone_folder = Folder.objects.create(
            name="Archive Folder",
            org_unit=self.sdd,
            is_deleted=True,
            deleted_by=self.admin,
        )
        self.standalone_doc = Document.objects.create(
            title="Procurement.docx",
            file=pdf_standalone,
            folder=self.active_folder,
            file_size=4096,
            is_deleted=True,
            deleted_by=self.admin,
        )

        Folder.objects.filter(id=self.parent_folder.id).update(is_deleted=True, deleted_by=self.admin)
        Folder.objects.filter(id=self.child_folder.id).update(is_deleted=True, deleted_by=self.admin)

    def test_bulk_restore_mixed_items(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(
            "/api/recycle-bin/bulk-restore",
            {
                "items": [
                    {"type": "document", "id": self.standalone_doc.id},
                    {"type": "folder", "id": self.standalone_folder.id},
                ]
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["total_restored"], 2)
        self.standalone_doc.refresh_from_db()
        self.standalone_folder.refresh_from_db()
        self.assertFalse(self.standalone_doc.is_deleted)
        self.assertFalse(self.standalone_folder.is_deleted)
        self.assertTrue(AuditLog.objects.filter(action="BULK_ITEM_RESTORE").exists())

    def test_bulk_delete_valid_confirmation(self):
        self.client.force_authenticate(user=self.admin)
        items = [
            {"type": "document", "id": self.standalone_doc.id},
            {"type": "folder", "id": self.standalone_folder.id},
        ]
        confirmation = build_bulk_permanent_delete_confirmation(len(items))
        response = self.client.post(
            "/api/recycle-bin/bulk-delete",
            {"items": items, "confirmation": confirmation},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["total_deleted"], 2)
        self.assertFalse(Document.objects.filter(pk=self.standalone_doc.id).exists())
        self.assertFalse(Folder.objects.filter(pk=self.standalone_folder.id).exists())
        self.assertTrue(AuditLog.objects.filter(action="BULK_ITEM_DELETION").exists())

    def test_bulk_delete_wrong_confirmation(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(
            "/api/recycle-bin/bulk-delete",
            {
                "items": [{"type": "document", "id": self.standalone_doc.id}],
                "confirmation": "delete 1 item",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertTrue(Document.objects.filter(pk=self.standalone_doc.id).exists())
        self.assertTrue(AuditLog.objects.filter(action="PERMANENT_DELETE_FAILED").exists())

    def test_bulk_delete_dedupes_folder_and_child_document(self):
        self.client.force_authenticate(user=self.admin)
        items = [
            {"type": "folder", "id": self.parent_folder.id},
            {"type": "document", "id": self.parent_doc.id},
        ]
        confirmation = build_bulk_permanent_delete_confirmation(len(items))
        response = self.client.post(
            "/api/recycle-bin/bulk-delete",
            {"items": items, "confirmation": confirmation},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Folder.objects.filter(pk=self.parent_folder.id).exists())
        self.assertFalse(Document.objects.filter(pk=self.parent_doc.id).exists())

    def test_staff_blocked_from_bulk_restore(self):
        self.client.force_authenticate(user=self.sdd_staff)
        response = self.client.post(
            "/api/recycle-bin/bulk-restore",
            {"items": [{"type": "document", "id": self.standalone_doc.id}]},
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    def test_dept_head_bulk_delete_in_scope(self):
        self.client.force_authenticate(user=self.cisc_head)
        items = [{"type": "document", "id": self.standalone_doc.id}]
        confirmation = build_bulk_permanent_delete_confirmation(len(items))
        response = self.client.post(
            "/api/recycle-bin/bulk-delete",
            {"items": items, "confirmation": confirmation},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Document.objects.filter(pk=self.standalone_doc.id).exists())

    def test_bulk_summary_returns_storage_for_folder_tree(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(
            "/api/recycle-bin/bulk-summary",
            {"items": [{"type": "folder", "id": self.parent_folder.id}]},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["folder_count"], 1)
        self.assertEqual(response.data["total_items"], 1)
        self.assertEqual(response.data["total_bytes"], 1024 + 2048)

    def test_bulk_summary_returns_200_with_storage_mb(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(
            "/api/recycle-bin/bulk-summary",
            {
                "items": [
                    {"type": "document", "id": self.standalone_doc.id},
                    {"type": "folder", "id": self.standalone_folder.id},
                ]
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("total_storage_mb", response.data)
        self.assertGreater(response.data["total_storage_mb"], 0)

    def test_bulk_restore_document_without_parent_folder_returns_400(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(
            "/api/recycle-bin/bulk-restore",
            {"items": [{"type": "document", "id": self.parent_doc.id}]},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("message", response.data)
        self.assertIn("Parent folder", str(response.data["message"]))
        self.parent_doc.refresh_from_db()
        self.assertTrue(self.parent_doc.is_deleted)

    def test_bulk_restore_document_with_parent_folder_selected_succeeds(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(
            "/api/recycle-bin/bulk-restore",
            {
                "items": [
                    {"type": "folder", "id": self.parent_folder.id},
                    {"type": "document", "id": self.parent_doc.id},
                ]
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.parent_doc.refresh_from_db()
        self.parent_folder.refresh_from_db()
        self.assertFalse(self.parent_doc.is_deleted)
        self.assertFalse(self.parent_folder.is_deleted)
