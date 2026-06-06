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
