import threading
from unittest import skipIf
from unittest.mock import patch

from django.db import connection
from django.test import TestCase
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIClient

from accounts.models import User
from documents.document_code import (
    derive_category_code,
    generate_document_code,
    preview_next_document_code,
)
from documents.models import Category, Document, DocumentSequence, Folder
from orgunits.models import OrgUnit


class DocumentCodeServiceTests(TestCase):
    def setUp(self):
        self.org_unit = OrgUnit.objects.create(name="CISC")
        self.category = Category.objects.create(name="Reports", code="RPT", org_unit=self.org_unit)
        self.folder = Folder.objects.create(name="Inbox", org_unit=self.org_unit)
        self.admin = User.objects.create_user(
            email="admin@test.local",
            password="Admin@12345",
            role="admin",
        )

    def test_preview_shows_next_sequence_without_incrementing(self):
        DocumentSequence.objects.create(category_code="RPT", current_year=timezone.now().year, current_number=3)
        preview = preview_next_document_code(self.category)
        self.assertEqual(preview, f"RPT-{timezone.now().year}-000004")
        seq = DocumentSequence.objects.get(category_code="RPT", current_year=timezone.now().year)
        self.assertEqual(seq.current_number, 3)

    def test_generate_increments_sequence(self):
        first = generate_document_code(self.category)
        second = generate_document_code(self.category)
        self.assertEqual(first, f"RPT-{timezone.now().year}-000001")
        self.assertEqual(second, f"RPT-{timezone.now().year}-000002")

    def test_generate_requires_category_code(self):
        category = Category.objects.create(name="Empty", code="", org_unit=self.org_unit)
        with self.assertRaises(ValidationError):
            generate_document_code(category)

    @patch("documents.document_code.timezone.now")
    def test_sequence_resets_when_year_changes(self, mock_now):
        mock_now.return_value = timezone.datetime(2025, 6, 1, tzinfo=timezone.get_current_timezone())
        code_2025 = generate_document_code(self.category)
        self.assertTrue(code_2025.startswith("RPT-2025-"))

        mock_now.return_value = timezone.datetime(2026, 1, 2, tzinfo=timezone.get_current_timezone())
        code_2026 = generate_document_code(self.category)
        self.assertEqual(code_2026, "RPT-2026-000001")

    @skipIf(connection.vendor == "sqlite", "SQLite serializes writers; concurrency tested on MySQL.")
    def test_concurrent_generation_produces_unique_codes(self):
        results = []
        errors = []

        def worker():
            try:
                results.append(generate_document_code(self.category))
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=worker) for _ in range(5)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        self.assertEqual(errors, [])
        self.assertEqual(len(results), len(set(results)))
        self.assertEqual(len(results), 5)

    def test_derive_category_code_from_name(self):
        self.assertEqual(derive_category_code("Legal"), "LEG")
        self.assertEqual(derive_category_code("Audit Reports"), "AUD")
        self.assertEqual(derive_category_code(""), "CAT")

    def test_derive_category_code_dedupes_within_org_unit(self):
        Category.objects.create(name="Alpha", code="REP", org_unit=self.org_unit)
        self.assertEqual(derive_category_code("Report", self.org_unit.id), "REP2")


class DocumentCodeAPITests(TestCase):
    def setUp(self):
        self.org_unit = OrgUnit.objects.create(name="CISC")
        self.category = Category.objects.create(name="Reports", code="RPT", org_unit=self.org_unit)
        self.folder = Folder.objects.create(name="Inbox", org_unit=self.org_unit)
        self.admin = User.objects.create_user(
            email="admin@test.local",
            password="Admin@12345",
            role="admin",
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin)

    def test_next_code_preview_endpoint(self):
        response = self.client.get("/api/documents/next-code", {"categoryId": self.category.id})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["code"], f"RPT-{timezone.now().year}-000001")

    def test_edit_does_not_change_document_code(self):
        document = Document.objects.create(
            title="sample.pdf",
            file="documents/sample.pdf",
            folder=self.folder,
            category=self.category,
            code="LEGACY-001",
            keywords=["test"],
        )
        response = self.client.patch(
            f"/api/documents/{document.id}/edit",
            {
                "folderId": str(self.folder.id),
                "categoryId": str(self.category.id),
                "requisitioners": [
                    {
                        "employeeNumber": "202400123",
                        "firstName": "Jane",
                        "lastName": "Doe",
                        "suffix": "",
                    }
                ],
                "description": "Updated",
                "keywords": ["updated"],
                "file_name": "sample",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        document.refresh_from_db()
        self.assertEqual(document.code, "LEGACY-001")

    def test_category_create_auto_generates_code(self):
        response = self.client.post(
            "/api/categories",
            {"name": "Legal", "orgUnitId": str(self.org_unit.id)},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["code"], "LEG")

    def test_category_code_dedupes_within_org_unit(self):
        Category.objects.create(name="Alpha", code="REP", org_unit=self.org_unit)
        response = self.client.post(
            "/api/categories",
            {"name": "Report", "orgUnitId": str(self.org_unit.id)},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["code"], "REP2")

    def test_category_rename_regenerates_code(self):
        category = Category.objects.create(name="Report", code="REP", org_unit=self.org_unit)
        response = self.client.put(
            f"/api/categories/{category.id}",
            {"name": "Code"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], "Code")
        self.assertEqual(response.data["code"], "COD")
        category.refresh_from_db()
        self.assertEqual(category.code, "COD")

    def test_category_rename_dedupes_code(self):
        Category.objects.create(name="Codes", code="COD", org_unit=self.org_unit)
        category = Category.objects.create(name="Report", code="REP", org_unit=self.org_unit)
        response = self.client.put(
            f"/api/categories/{category.id}",
            {"name": "Code"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["code"], "COD2")

    def test_category_rename_keeps_existing_document_codes(self):
        category = Category.objects.create(name="Report", code="REP", org_unit=self.org_unit)
        document = Document.objects.create(
            title="sample.pdf",
            file="documents/sample.pdf",
            folder=self.folder,
            category=category,
            code="REP-2026-000001",
            keywords=["test"],
        )
        response = self.client.put(
            f"/api/categories/{category.id}",
            {"name": "Code"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["code"], "COD")
        document.refresh_from_db()
        self.assertEqual(document.code, "COD-2026-000001")

        preview = self.client.get("/api/documents/next-code", {"categoryId": category.id})
        self.assertEqual(preview.status_code, 200)
        self.assertEqual(preview.data["code"], f"COD-{timezone.now().year}-000001")

    def test_category_rename_same_name_keeps_code(self):
        category = Category.objects.create(name="Report", code="REP", org_unit=self.org_unit)
        response = self.client.put(
            f"/api/categories/{category.id}",
            {"name": "Report"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["code"], "REP")

    def test_category_update_backfills_missing_code(self):
        category = Category.objects.create(name="Report", code="", org_unit=self.org_unit)
        response = self.client.put(
            f"/api/categories/{category.id}",
            {"name": "Report"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["code"], "REP")

    def test_category_manual_code_update_only(self):
        category = Category.objects.create(name="Report", code="REP", org_unit=self.org_unit)
        response = self.client.put(
            f"/api/categories/{category.id}",
            {"name": "Report", "code": "AUD"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], "Report")
        self.assertEqual(response.data["code"], "AUD")

    def test_category_manual_code_overrides_rename_auto(self):
        category = Category.objects.create(name="Report", code="REP", org_unit=self.org_unit)
        response = self.client.put(
            f"/api/categories/{category.id}",
            {"name": "Monthly", "code": "CUSTOM"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], "Monthly")
        self.assertEqual(response.data["code"], "CUSTOM")

    def test_category_duplicate_code_rejected(self):
        Category.objects.create(name="Audit", code="AUD", org_unit=self.org_unit)
        category = Category.objects.create(name="Report", code="REP", org_unit=self.org_unit)
        response = self.client.put(
            f"/api/categories/{category.id}",
            {"name": "Report", "code": "AUD"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("code", response.data)

    def test_category_manual_code_keeps_document_codes(self):
        category = Category.objects.create(name="Report", code="REP", org_unit=self.org_unit)
        document = Document.objects.create(
            title="sample.pdf",
            file="documents/sample.pdf",
            folder=self.folder,
            category=category,
            code="REP-2026-000001",
            keywords=["test"],
        )
        response = self.client.put(
            f"/api/categories/{category.id}",
            {"name": "Report", "code": "AUD"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        document.refresh_from_db()
        self.assertEqual(document.code, "AUD-2026-000001")
        preview = self.client.get("/api/documents/next-code", {"categoryId": category.id})
        self.assertEqual(preview.data["code"], f"AUD-{timezone.now().year}-000001")

    def test_category_rename_recodes_multiple_documents(self):
        category = Category.objects.create(name="Memo", code="MEM", org_unit=self.org_unit)
        Document.objects.create(
            title="a.pdf",
            file="documents/a.pdf",
            folder=self.folder,
            category=category,
            code="MEM-2026-000001",
            keywords=["a"],
        )
        Document.objects.create(
            title="b.pdf",
            file="documents/b.pdf",
            folder=self.folder,
            category=category,
            code="MEM-2026-000002",
            keywords=["b"],
        )
        response = self.client.put(
            f"/api/categories/{category.id}",
            {"name": "test", "code": "TES"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        codes = list(
            Document.objects.filter(category=category, is_deleted=False)
            .order_by("code")
            .values_list("code", flat=True)
        )
        self.assertEqual(codes, ["TES-2026-000001", "TES-2026-000002"])

    def test_edit_document_category_swaps_code_prefix(self):
        source = Category.objects.create(name="Memo", code="MEM", org_unit=self.org_unit)
        target = Category.objects.create(name="Report", code="REP", org_unit=self.org_unit)
        document = Document.objects.create(
            title="sample.pdf",
            file="documents/sample.pdf",
            folder=self.folder,
            category=source,
            code="MEM-2026-000001",
            keywords=["test"],
        )
        response = self.client.patch(
            f"/api/documents/{document.id}/edit",
            {
                "folderId": str(self.folder.id),
                "categoryId": str(target.id),
                "requisitioners": [
                    {
                        "employeeNumber": "202400123",
                        "firstName": "Jane",
                        "lastName": "Doe",
                        "suffix": "",
                    }
                ],
                "description": "Updated",
                "keywords": ["updated"],
                "file_name": "sample",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        document.refresh_from_db()
        self.assertEqual(document.code, "REP-2026-000001")
        self.assertEqual(document.category_id, target.id)

    def test_recode_duplicate_target_blocked(self):
        category = Category.objects.create(name="Memo", code="MEM", org_unit=self.org_unit)
        Document.objects.create(
            title="a.pdf",
            file="documents/a.pdf",
            folder=self.folder,
            category=category,
            code="MEM-2026-000001",
            keywords=["a"],
        )
        Document.objects.create(
            title="b.pdf",
            file="documents/b.pdf",
            folder=self.folder,
            category=category,
            code="MEM-2026-000002",
            keywords=["b"],
        )
        Document.objects.create(
            title="other.pdf",
            file="documents/other.pdf",
            folder=self.folder,
            category=category,
            code="TES-2026-000001",
            keywords=["c"],
        )
        response = self.client.put(
            f"/api/categories/{category.id}",
            {"name": "Memo", "code": "TES"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_legacy_document_code_unchanged_on_category_change(self):
        source = Category.objects.create(name="Memo", code="MEM", org_unit=self.org_unit)
        target = Category.objects.create(name="Report", code="REP", org_unit=self.org_unit)
        document = Document.objects.create(
            title="legacy.pdf",
            file="documents/legacy.pdf",
            folder=self.folder,
            category=source,
            code="LEGACY-001",
            keywords=["test"],
        )
        response = self.client.patch(
            f"/api/documents/{document.id}/edit",
            {
                "folderId": str(self.folder.id),
                "categoryId": str(target.id),
                "requisitioners": [
                    {
                        "employeeNumber": "202400123",
                        "firstName": "Jane",
                        "lastName": "Doe",
                        "suffix": "",
                    }
                ],
                "description": "Updated",
                "keywords": ["updated"],
                "file_name": "legacy",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        document.refresh_from_db()
        self.assertEqual(document.code, "LEGACY-001")
        self.assertEqual(document.category_id, target.id)

    def test_category_code_normalizes_lowercase(self):
        category = Category.objects.create(name="Report", code="REP", org_unit=self.org_unit)
        response = self.client.put(
            f"/api/categories/{category.id}",
            {"name": "Report", "code": "aud"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["code"], "AUD")
