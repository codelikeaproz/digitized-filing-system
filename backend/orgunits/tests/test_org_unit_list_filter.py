from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import User
from documents.models import Category, Document, Folder
from orgunits.models import OrgType, OrgUnit


class OrgUnitListFilterTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            email="admin-orgunit-filter@test.local",
            password="Admin@12345",
            role="admin",
        )
        self.client.force_authenticate(user=self.admin)

        self.college_type = OrgType.objects.create(name="College", code="college", is_active=True)
        self.department_type = OrgType.objects.create(
            name="Department", code="department", is_active=True
        )

        self.cisc = OrgUnit.objects.create(
            name="CISC",
            org_type=self.college_type,
            type=self.college_type.name,
            storage_quota_mb=1024,
        )
        self.sdd = OrgUnit.objects.create(
            name="SDD",
            org_type=self.department_type,
            type=self.department_type.name,
            parent=self.cisc,
            storage_quota_mb=512,
        )

        folder = Folder.objects.create(name="Records", org_unit=self.sdd)
        category = Category.objects.create(name="General", org_unit=self.sdd)
        upload = SimpleUploadedFile("sample.pdf", b"%PDF-test", content_type="application/pdf")
        Document.objects.create(
            title="sample.pdf",
            file=upload,
            folder=folder,
            category=category,
            file_size=1024,
            mime_type="application/pdf",
        )

    def test_list_without_org_type_filter_returns_all_units(self):
        response = self.client.get("/api/org-units/", {"page_size": 100})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 2)
        self.assertEqual(response.data["summary"]["unit_count"], 2)
        self.assertEqual(response.data["summary"]["document_count"], 1)

    def test_list_with_org_type_id_filters_units(self):
        response = self.client.get(
            "/api/org-units/",
            {"org_type_id": self.college_type.id, "page_size": 100},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["name"], "CISC")
        self.assertEqual(response.data["summary"]["unit_count"], 1)
        self.assertEqual(response.data["summary"]["document_count"], 0)

    def test_list_department_type_includes_documents_in_summary(self):
        response = self.client.get(
            "/api/org-units/",
            {"org_type_id": self.department_type.id, "page_size": 100},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["name"], "SDD")
        self.assertEqual(response.data["summary"]["document_count"], 1)
        self.assertEqual(response.data["summary"]["folder_count"], 1)

    def test_list_org_type_all_returns_full_set(self):
        response = self.client.get(
            "/api/org-units/",
            {"org_type_id": "all", "page_size": 100},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 2)
