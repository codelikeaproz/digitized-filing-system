from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import User
from documents.models import Category, Document, DocumentRequisitioner, Folder
from employees.duplicate_detection import EMPLOYEE_NUMBER_EXISTS_MESSAGE
from employees.models import Employee
from employees.references import get_reference_count_for_employee
from orgunits.models import OrgUnit


class RequisitionerIntegrityTests(TestCase):
    def setUp(self):
        self.org_unit = OrgUnit.objects.create(name="CISC")
        self.category = Category.objects.create(name="Reports", org_unit=self.org_unit)
        self.folder = Folder.objects.create(name="Inbox", org_unit=self.org_unit)
        self.admin = User.objects.create_user(
            email="admin-integrity@test.local",
            password="Admin@12345",
            role="admin",
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin)

        self.employee = Employee.objects.create(
            employee_number="D-2022-ADDD",
            first_name="Ralph",
            last_name="Jumao-As",
            suffix="",
        )

    def _create_document(self, title="Doc", code="RPT-INT-001"):
        return Document.objects.create(
            title=title,
            file="documents/sample.pdf",
            folder=self.folder,
            category=self.category,
            keywords=["test"],
            code=code,
        )

    def _edit_payload(self, document, requisitioners):
        return {
            "folderId": str(self.folder.id),
            "categoryId": str(self.category.id),
            "code": document.code,
            "requisitioners": requisitioners,
            "description": "Updated",
            "keywords": ["updated"],
            "file_name": "sample",
        }

    def test_directory_linked_edit_does_not_mutate_master(self):
        document = self._create_document(code="RPT-INT-001")
        response = self.client.patch(
            f"/api/documents/{document.id}/edit",
            self._edit_payload(
                document,
                [
                    {
                        "employeeId": str(self.employee.id),
                        "source": "directory",
                        "employeeNumber": "D-2022-ADDD",
                        "firstName": "Ralph",
                        "lastName": "Renamed",
                        "suffix": "",
                    }
                ],
            ),
            format="json",
        )
        self.assertEqual(response.status_code, 200)

        self.employee.refresh_from_db()
        self.assertEqual(self.employee.last_name, "Jumao-As")

        requisitioner = DocumentRequisitioner.objects.get(document=document)
        self.assertEqual(requisitioner.employee_id, self.employee.id)
        self.assertEqual(requisitioner.source, DocumentRequisitioner.SOURCE_DIRECTORY)
        self.assertEqual(requisitioner.last_name, "Jumao-As")

    def test_manual_tag_with_existing_employee_number_is_blocked(self):
        document = self._create_document(code="RPT-INT-002")
        response = self.client.patch(
            f"/api/documents/{document.id}/edit",
            self._edit_payload(
                document,
                [
                    {
                        "source": "manual",
                        "employeeNumber": "D-2022-ADDD",
                        "firstName": "Other",
                        "lastName": "Person",
                        "suffix": "",
                    }
                ],
            ),
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn(EMPLOYEE_NUMBER_EXISTS_MESSAGE, str(response.data))

    def test_manual_tag_with_unique_number_creates_one_employee(self):
        document = self._create_document(code="RPT-INT-003")
        response = self.client.patch(
            f"/api/documents/{document.id}/edit",
            self._edit_payload(
                document,
                [
                    {
                        "source": "manual",
                        "employeeNumber": "D-2099-NEWID",
                        "firstName": "New",
                        "lastName": "Requisitioner",
                        "suffix": "",
                    }
                ],
            ),
            format="json",
        )
        self.assertEqual(response.status_code, 200)

        requisitioner = DocumentRequisitioner.objects.get(document=document)
        self.assertIsNotNone(requisitioner.employee_id)
        self.assertEqual(requisitioner.source, DocumentRequisitioner.SOURCE_MANUAL)
        self.assertEqual(
            Employee.objects.filter(employee_number__iexact="D-2099-NEWID").count(),
            1,
        )

    def test_reference_counts_use_employee_fk(self):
        document = self._create_document()
        DocumentRequisitioner.objects.create(
            document=document,
            employee=self.employee,
            source=DocumentRequisitioner.SOURCE_DIRECTORY,
            employee_number=self.employee.employee_number,
            first_name=self.employee.first_name,
            last_name=self.employee.last_name,
            suffix="",
        )

        self.assertEqual(get_reference_count_for_employee(self.employee), 1)

    def test_check_duplicate_endpoint_blocks_existing_number(self):
        response = self.client.post(
            "/api/employees/check-duplicate",
            {
                "employeeNumber": "D-2022-ADDD",
                "firstName": "Someone",
                "lastName": "Else",
                "suffix": "",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["blocked"])
        self.assertEqual(response.data["message"], EMPLOYEE_NUMBER_EXISTS_MESSAGE)
