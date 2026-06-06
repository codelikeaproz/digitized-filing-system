from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import User
from auditlogs.models import AuditLog
from documents.models import Document, Folder
from orgunits.models import OrgType, OrgUnit


class OrgUnitHierarchyAuthTests(TestCase):
    """Hierarchical Office Unit authorization for dept_head vs staff."""

    def setUp(self):
        self.client = APIClient()
        self.org_type = OrgType.objects.create(name="Department", code="department", is_active=True)

        self.cisc = OrgUnit.objects.create(name="CISC", org_type=self.org_type)
        self.sdd = OrgUnit.objects.create(name="SDD", org_type=self.org_type, parent=self.cisc)
        self.it = OrgUnit.objects.create(name="IT", org_type=self.org_type, parent=self.cisc)
        self.other = OrgUnit.objects.create(name="OTHER", org_type=self.org_type)

        self.cisc_head = User.objects.create_user(
            email="cisc-head@test.local",
            password="Test@12345",
            role="dept_head",
            org_unit=self.cisc,
        )
        self.sdd_head = User.objects.create_user(
            email="sdd-head@test.local",
            password="Test@12345",
            role="dept_head",
            org_unit=self.sdd,
        )
        self.sdd_staff = User.objects.create_user(
            email="sdd-staff@test.local",
            password="Test@12345",
            role="staff",
            org_unit=self.sdd,
        )
        self.admin = User.objects.create_user(
            email="admin-hierarchy@test.local",
            password="Test@12345",
            role="admin",
        )

        self.cisc_folder = Folder.objects.create(name="CISC Root", org_unit=self.cisc)
        self.sdd_folder = Folder.objects.create(name="SDD Root", org_unit=self.sdd)
        self.it_folder = Folder.objects.create(name="IT Root", org_unit=self.it)
        self.other_folder = Folder.objects.create(name="OTHER Root", org_unit=self.other)

        pdf = SimpleUploadedFile("sample.pdf", b"%PDF-1.4 test", content_type="application/pdf")
        self.cisc_doc = Document.objects.create(
            title="CISC Document",
            file=pdf,
            folder=self.cisc_folder,
            file_size=1024,
        )
        self.sdd_doc = Document.objects.create(
            title="SDD Document",
            file=SimpleUploadedFile("sdd.pdf", b"%PDF-1.4 sdd", content_type="application/pdf"),
            folder=self.sdd_folder,
            file_size=2048,
        )
        self.it_doc = Document.objects.create(
            title="IT Document",
            file=SimpleUploadedFile("it.pdf", b"%PDF-1.4 it", content_type="application/pdf"),
            folder=self.it_folder,
            file_size=4096,
        )

    def _document_titles(self, response):
        if isinstance(response.data, dict) and "results" in response.data:
            return {row["title"] for row in response.data["results"]}
        return {row["title"] for row in response.data}

    def test_cisc_head_sees_descendant_documents(self):
        self.client.force_authenticate(user=self.cisc_head)
        response = self.client.get("/api/documents/")
        self.assertEqual(response.status_code, 200)
        titles = self._document_titles(response)
        self.assertIn("CISC Document", titles)
        self.assertIn("SDD Document", titles)
        self.assertIn("IT Document", titles)
        self.assertNotIn("OTHER Document", titles)

    def test_sdd_head_cannot_access_parent_org_unit_param(self):
        self.client.force_authenticate(user=self.sdd_head)
        response = self.client.get("/api/documents/", {"orgUnitId": self.cisc.id})
        self.assertEqual(response.status_code, 403)

    def test_sdd_head_cannot_access_sibling_org_unit_param(self):
        self.client.force_authenticate(user=self.sdd_head)
        response = self.client.get("/api/documents/", {"orgUnitId": self.it.id})
        self.assertEqual(response.status_code, 403)

    def test_sdd_head_sees_only_own_unit_documents_by_default(self):
        self.client.force_authenticate(user=self.sdd_head)
        response = self.client.get("/api/documents/")
        self.assertEqual(response.status_code, 200)
        titles = self._document_titles(response)
        self.assertEqual(titles, {"SDD Document"})

    def test_sdd_staff_sees_only_own_unit(self):
        self.client.force_authenticate(user=self.sdd_staff)
        response = self.client.get("/api/documents/")
        self.assertEqual(response.status_code, 200)
        titles = self._document_titles(response)
        self.assertEqual(titles, {"SDD Document"})

    def test_org_units_list_scoped_for_dept_heads(self):
        self.client.force_authenticate(user=self.cisc_head)
        response = self.client.get("/api/org-units/")
        self.assertEqual(response.status_code, 200)
        names = {row["name"] for row in response.data["results"]}
        self.assertEqual(names, {"CISC", "SDD", "IT"})

        self.client.force_authenticate(user=self.sdd_head)
        response = self.client.get("/api/org-units/")
        names = {row["name"] for row in response.data["results"]}
        self.assertEqual(names, {"SDD"})

    def test_folder_tree_shows_subtree_for_parent_dept_head(self):
        self.client.force_authenticate(user=self.cisc_head)
        response = self.client.get("/api/folders/tree/")
        self.assertEqual(response.status_code, 200)
        tree = response.data
        self.assertEqual(len(tree), 2)
        root = tree[1]
        self.assertEqual(root["type"], "org_unit")
        self.assertEqual(root["name"], "CISC")
        child_names = {node["name"] for node in root.get("children", []) if node.get("type") == "org_unit"}
        self.assertEqual(child_names, {"SDD", "IT"})

    def test_folder_tree_staff_shows_single_org_unit(self):
        self.client.force_authenticate(user=self.sdd_staff)
        response = self.client.get("/api/folders/tree/")
        self.assertEqual(response.status_code, 200)
        org_nodes = [node for node in response.data if node.get("type") == "org_unit"]
        self.assertEqual(len(org_nodes), 1)
        self.assertEqual(org_nodes[0]["name"], "SDD")

    def test_document_search_audited(self):
        self.client.force_authenticate(user=self.sdd_head)
        response = self.client.get("/api/documents/", {"search": "SDD"})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            AuditLog.objects.filter(action="SEARCH_DOCUMENTS", user=self.sdd_head).exists()
        )

    def test_document_view_audited(self):
        self.client.force_authenticate(user=self.sdd_head)
        response = self.client.get(f"/api/documents/{self.sdd_doc.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            AuditLog.objects.filter(action="VIEW_DOCUMENT", user=self.sdd_head).exists()
        )

    def test_dashboard_subtree_aggregation_for_parent_dept_head(self):
        self.client.force_authenticate(user=self.cisc_head)
        response = self.client.get("/api/dashboard/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["scope"], "office_unit")
        self.assertGreaterEqual(response.data["total_documents"], 3)
        self.assertTrue(response.data["can_filter_office_units"])
        self.assertGreaterEqual(len(response.data["storage_by_office_unit"]), 3)

    def test_dashboard_child_filter_within_scope(self):
        self.client.force_authenticate(user=self.cisc_head)
        response = self.client.get("/api/dashboard/", {"office_unit": self.sdd.id})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["office_unit_id"], str(self.sdd.id))

    def test_dashboard_child_filter_out_of_scope_for_sdd_head(self):
        self.client.force_authenticate(user=self.sdd_head)
        response = self.client.get("/api/dashboard/", {"office_unit": self.cisc.id})
        self.assertEqual(response.status_code, 403)

    def test_ai_search_preview_audited(self):
        self.client.force_authenticate(user=self.sdd_head)
        response = self.client.get("/api/ai/search-preview/", {"q": "SDD"})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            AuditLog.objects.filter(action="SEARCH_DOCUMENTS", user=self.sdd_head).exists()
        )
