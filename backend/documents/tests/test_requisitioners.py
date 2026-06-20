from django.test import TestCase
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIClient

from accounts.models import User
from config.employee_number import EMPLOYEE_NUMBER_FORMAT_ERROR
from config.tests.test_timezone_utils import ISO_UTC_PATTERN
from documents.models import Category, Document, DocumentRequisitioner, Folder
from documents.requisitioners import (
    format_requisitioners_display,
    normalize_requisitioner_item,
    validate_requisitioners_list,
)
from orgunits.models import OrgUnit


class RequisitionerValidationTests(TestCase):
    def test_empty_employee_number_is_allowed(self):
        item = normalize_requisitioner_item(
            {
                "employeeNumber": "",
                "firstName": "Jane",
                "lastName": "Doe",
                "suffix": "",
            }
        )
        self.assertIsNone(item["employee_number"])

    def test_invalid_employee_number_rejected(self):
        with self.assertRaises(ValidationError) as ctx:
            normalize_requisitioner_item(
                {
                    "employeeNumber": "ABC123",
                    "firstName": "Jane",
                    "lastName": "Doe",
                    "suffix": "",
                }
            )
        self.assertIn(EMPLOYEE_NUMBER_FORMAT_ERROR, str(ctx.exception))

    def test_duplicate_non_empty_employee_numbers_rejected(self):
        with self.assertRaises(ValidationError) as ctx:
            validate_requisitioners_list(
                [
                    {
                        "employeeNumber": "202400123",
                        "firstName": "Jane",
                        "lastName": "Doe",
                        "suffix": "",
                    },
                    {
                        "employeeNumber": "202400123",
                        "firstName": "John",
                        "lastName": "Smith",
                        "suffix": "",
                    },
                ]
            )
        self.assertIn("Duplicate Employee Numbers", str(ctx.exception))

    def test_multiple_requisitioners_without_employee_number_allowed(self):
        normalized = validate_requisitioners_list(
            [
                {
                    "employeeNumber": "",
                    "firstName": "Jane",
                    "lastName": "Doe",
                    "suffix": "",
                },
                {
                    "employeeNumber": "",
                    "firstName": "John",
                    "lastName": "Guest",
                    "suffix": "",
                },
            ]
        )
        self.assertEqual(len(normalized), 2)
        self.assertIsNone(normalized[0]["employee_number"])
        self.assertIsNone(normalized[1]["employee_number"])


class FormatRequisitionersDisplayTests(TestCase):
    def setUp(self):
        self.org_unit = OrgUnit.objects.create(name="CISC")
        self.category = Category.objects.create(name="Reports", org_unit=self.org_unit)
        self.folder = Folder.objects.create(name="Inbox", org_unit=self.org_unit)
        self.document = Document.objects.create(
            title="sample.pdf",
            file="documents/sample.pdf",
            folder=self.folder,
            category=self.category,
        )

    def test_model_instance_without_employee_number(self):
        requisitioner = DocumentRequisitioner.objects.create(
            document=self.document,
            employee_number=None,
            first_name="Jane",
            last_name="Guest",
            suffix="",
        )
        self.assertEqual(format_requisitioners_display([requisitioner]), "Jane Guest")

    def test_model_instance_with_employee_number(self):
        requisitioner = DocumentRequisitioner.objects.create(
            document=self.document,
            employee_number="D-2022-ADDD",
            first_name="Ralph",
            last_name="Jumao-As",
            suffix="",
        )
        self.assertEqual(
            format_requisitioners_display([requisitioner]),
            "D-2022-ADDD - Ralph Jumao-As",
        )


class RequisitionerAPITests(TestCase):
    def setUp(self):
        self.org_unit = OrgUnit.objects.create(name="CISC")
        self.category = Category.objects.create(name="Reports", org_unit=self.org_unit)
        self.folder = Folder.objects.create(name="Inbox", org_unit=self.org_unit)
        self.admin = User.objects.create_user(
            email="admin@test.local",
            password="Admin@12345",
            role="admin",
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin)
        self.document = Document.objects.create(
            title="sample.pdf",
            file="documents/sample.pdf",
            folder=self.folder,
            category=self.category,
            keywords=["test"],
            code="RPT-TEST-001",
        )

    def _edit_payload(self, requisitioners):
        return {
            "folderId": str(self.folder.id),
            "categoryId": str(self.category.id),
            "code": self.document.code,
            "requisitioners": requisitioners,
            "description": "Updated",
            "keywords": ["updated"],
            "file_name": "sample",
        }

    def test_edit_allows_requisitioner_without_employee_number(self):
        response = self.client.patch(
            f"/api/documents/{self.document.id}/edit",
            self._edit_payload(
                [
                    {
                        "employeeNumber": "",
                        "firstName": "External",
                        "lastName": "Guest",
                        "suffix": "",
                    }
                ]
            ),
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        requisitioner = DocumentRequisitioner.objects.get(document=self.document)
        self.assertEqual(requisitioner.first_name, "External")
        self.assertIsNone(requisitioner.employee_number)

    def test_edit_rejects_invalid_employee_number(self):
        response = self.client.patch(
            f"/api/documents/{self.document.id}/edit",
            self._edit_payload(
                [
                    {
                        "employeeNumber": "ABC123",
                        "firstName": "Jane",
                        "lastName": "Doe",
                        "suffix": "",
                    }
                ]
            ),
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_edit_rejects_duplicate_employee_numbers(self):
        response = self.client.patch(
            f"/api/documents/{self.document.id}/edit",
            self._edit_payload(
                [
                    {
                        "employeeNumber": "202400123",
                        "firstName": "Jane",
                        "lastName": "Doe",
                        "suffix": "",
                    },
                    {
                        "employeeNumber": "202400123",
                        "firstName": "John",
                        "lastName": "Smith",
                        "suffix": "",
                    },
                ]
            ),
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_edit_allows_two_requisitioners_without_employee_number(self):
        response = self.client.patch(
            f"/api/documents/{self.document.id}/edit",
            self._edit_payload(
                [
                    {
                        "employeeNumber": "",
                        "firstName": "External",
                        "lastName": "Guest",
                        "suffix": "",
                    },
                    {
                        "employeeNumber": "",
                        "firstName": "Another",
                        "lastName": "Visitor",
                        "suffix": "",
                    },
                ]
            ),
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(DocumentRequisitioner.objects.filter(document=self.document).count(), 2)

    def test_document_detail_returns_iso_created_at(self):
        response = self.client.get(f"/api/documents/{self.document.id}")
        self.assertEqual(response.status_code, 200)
        self.assertRegex(response.data["createdAt"], ISO_UTC_PATTERN)
