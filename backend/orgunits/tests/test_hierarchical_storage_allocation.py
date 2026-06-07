from django.core.files.uploadedfile import SimpleUploadedFile

from django.test import TestCase
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIClient

from accounts.models import User
from auditlogs.models import AuditLog
from documents.models import Document, Folder
from orgunits.models import OrgType, OrgUnit
from orgunits.storage import (
    get_display_used_mb,
    get_parent_available_allocation_mb,
    get_system_available_allocation_mb,
    validate_org_unit_allocation_quota,
    validate_storage_quota,
)
from system.models import SystemSettings
from system.services import invalidate_system_settings_cache


class HierarchicalStorageAllocationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            email="admin-hier-storage@test.local",
            password="Admin@12345",
            role="admin",
        )
        self.client.force_authenticate(user=self.admin)
        self.org_type = OrgType.objects.create(name="College", code="college", is_active=True)
        settings = SystemSettings.load()
        settings.storage_quota_mb = 10000
        settings.save()
        invalidate_system_settings_cache()

        self.cisc = OrgUnit.objects.create(
            name="CISC",
            org_type=self.org_type,
            storage_quota_mb=8000,
        )
        self.sdd = OrgUnit.objects.create(
            name="SDD",
            org_type=self.org_type,
            parent=self.cisc,
            storage_quota_mb=3000,
        )

    def test_child_quota_not_counted_against_system_pool(self):
        self.assertEqual(get_system_available_allocation_mb(), 2000)
        self.assertEqual(get_system_available_allocation_mb(exclude_org_unit=self.cisc), 10000)

    def test_create_child_within_parent_allocation_succeeds(self):
        response = self.client.post(
            "/api/org-units/",
            {
                "name": "IT",
                "org_type_id": self.org_type.id,
                "parentId": str(self.cisc.id),
                "storageQuotaMb": 4096,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            get_parent_available_allocation_mb(self.cisc),
            8000 - 3000 - 4096,
        )

    def test_create_child_exceeding_parent_allocation_fails(self):
        response = self.client.post(
            "/api/org-units/",
            {
                "name": "IT",
                "org_type_id": self.org_type.id,
                "parentId": str(self.cisc.id),
                "storageQuotaMb": 12000,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn(
            "Child Office Unit allocations exceed the available Parent Office Unit storage",
            str(response.data),
        )
        audit = AuditLog.objects.filter(action="STORAGE_ALLOCATION_VALIDATION_FAILED").latest("id")
        self.assertIn("Parent Office Unit: CISC", audit.details)

    def test_siblings_cannot_exceed_parent_allocation(self):
        OrgUnit.objects.create(
            name="IT",
            org_type=self.org_type,
            parent=self.cisc,
            storage_quota_mb=4096,
        )
        response = self.client.post(
            "/api/org-units/",
            {
                "name": "CS",
                "org_type_id": self.org_type.id,
                "parentId": str(self.cisc.id),
                "storageQuotaMb": 7000,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_multilevel_child_validated_against_immediate_parent(self):
        records = OrgUnit.objects.create(
            name="Records",
            org_type=self.org_type,
            parent=self.sdd,
            storage_quota_mb=1024,
        )
        self.assertEqual(records.parent_id, self.sdd.id)

        response = self.client.post(
            "/api/org-units/",
            {
                "name": "Archive",
                "org_type_id": self.org_type.id,
                "parentId": str(self.sdd.id),
                "storageQuotaMb": 5000,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn(
            "Child Office Unit allocations exceed the available Parent Office Unit storage",
            str(response.data),
        )

    def test_parent_reduction_blocked_below_child_allocations(self):
        response = self.client.put(
            f"/api/org-units/{self.cisc.id}/",
            {
                "name": "CISC",
                "org_type_id": self.org_type.id,
                "storageQuotaMb": 2048,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn(
            "Parent allocation cannot be reduced below the total allocated child storage",
            str(response.data),
        )

    def test_edit_child_quota_revalidates_against_parent_headroom(self):
        response = self.client.put(
            f"/api/org-units/{self.sdd.id}/",
            {
                "name": "SDD",
                "org_type_id": self.org_type.id,
                "parentId": str(self.cisc.id),
                "storageQuotaMb": 12000,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_parent_display_used_includes_descendant_documents(self):
        cisc_folder = Folder.objects.create(name="CISC Root", org_unit=self.cisc)
        sdd_folder = Folder.objects.create(name="SDD Root", org_unit=self.sdd)
        pdf = SimpleUploadedFile("sample.pdf", b"%PDF-1.4 test", content_type="application/pdf")
        Document.objects.create(
            title="CISC Doc",
            folder=cisc_folder,
            file=pdf,
            file_size=1024 * 1024,
        )
        Document.objects.create(
            title="SDD Doc",
            folder=sdd_folder,
            file=SimpleUploadedFile("sdd.pdf", b"%PDF-1.4 sdd", content_type="application/pdf"),
            file_size=2 * 1024 * 1024,
        )

        self.assertEqual(get_display_used_mb(self.sdd), 2.0)
        self.assertEqual(get_display_used_mb(self.cisc), 3.0)

    def test_parent_upload_blocked_when_subtree_usage_exceeds_quota(self):
        self.cisc.storage_quota_mb = 1
        self.cisc.save(update_fields=["storage_quota_mb"])
        sdd_folder = Folder.objects.create(name="SDD Root", org_unit=self.sdd)
        Document.objects.create(
            title="SDD Doc",
            folder=sdd_folder,
            file=SimpleUploadedFile("sdd.pdf", b"%PDF-1.4 sdd", content_type="application/pdf"),
            file_size=2 * 1024 * 1024,
        )

        with self.assertRaises(ValidationError):
            validate_storage_quota(self.cisc, 1024)

    def test_child_allocation_update_logs_parent_context(self):
        response = self.client.put(
            f"/api/org-units/{self.sdd.id}/",
            {
                "name": "SDD",
                "org_type_id": self.org_type.id,
                "parentId": str(self.cisc.id),
                "storageQuotaMb": 6144,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        audit = AuditLog.objects.filter(
            action="STORAGE_ALLOCATION_UPDATED",
            target_name="SDD",
        ).latest("id")
        self.assertIn("Child allocation updated", audit.details)
        self.assertIn("Parent: CISC", audit.details)

    def test_list_response_includes_allocation_context(self):
        response = self.client.get("/api/org-units/")
        self.assertEqual(response.status_code, 200)
        sdd_row = next(row for row in response.data["results"] if row["name"] == "SDD")
        self.assertEqual(sdd_row["parentName"], "CISC")
        self.assertEqual(sdd_row["allocationContext"]["source"], "parent")
        self.assertEqual(sdd_row["allocationContext"]["parentName"], "CISC")

    def test_validate_org_unit_allocation_quota_with_explicit_parent(self):
        with self.assertRaises(ValidationError):
            validate_org_unit_allocation_quota(12000, parent=self.cisc)
