from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import User
from documents.models import Category, Document, DocumentRequisitioner, Folder
from employees.duplicate_detection import SIMILAR_NAME_EXISTS_MESSAGE
from employees.models import Employee
from employees.sync import link_document_requisitioners, upsert_employee_and_cascade
from orgunits.models import OrgUnit


class RequisitionerSyncTests(TestCase):
    def setUp(self):
        self.org_unit = OrgUnit.objects.create(name="CISC")
        self.category = Category.objects.create(name="Reports", org_unit=self.org_unit)
        self.folder = Folder.objects.create(name="Inbox", org_unit=self.org_unit)
        self.admin = User.objects.create_user(
            email="admin-sync@test.local",
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

    def _create_document(self, title="Doc", code="RPT-SYNC-001"):
        return Document.objects.create(
            title=title,
            file="documents/sample.pdf",
            folder=self.folder,
            category=self.category,
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

    def test_upsert_with_employee_number_updates_directory_and_cascades(self):
        doc_one = self._create_document("Doc One", code="RPT-SYNC-A1")
        doc_two = self._create_document("Doc Two", code="RPT-SYNC-A2")
        DocumentRequisitioner.objects.create(
            document=doc_one,
            employee=self.employee,
            source=DocumentRequisitioner.SOURCE_DIRECTORY,
            employee_number="D-2022-ADDD",
            first_name="Ralph",
            last_name="Jumao-As",
            suffix="",
        )
        DocumentRequisitioner.objects.create(
            document=doc_two,
            employee=self.employee,
            source=DocumentRequisitioner.SOURCE_DIRECTORY,
            employee_number="D-2022-ADDD",
            first_name="Ralph",
            last_name="Jumao-As",
            suffix="",
        )

        upsert_employee_and_cascade(
            first_name="Ralph",
            last_name="Updated-Name",
            suffix="",
            employee_number="D-2022-ADDD",
        )

        self.employee.refresh_from_db()
        self.assertEqual(self.employee.last_name, "Updated-Name")

        for document in (doc_one, doc_two):
            requisitioner = DocumentRequisitioner.objects.get(document=document)
            self.assertEqual(requisitioner.last_name, "Updated-Name")

    def test_document_edit_with_directory_link_does_not_update_master(self):
        document = self._create_document()
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
        self.assertEqual(requisitioner.last_name, "Jumao-As")

    def test_document_edit_does_not_cascade_to_other_documents(self):
        doc_one = self._create_document("Doc One", code="RPT-SYNC-B1")
        doc_two = self._create_document("Doc Two", code="RPT-SYNC-B2")
        for document in (doc_one, doc_two):
            DocumentRequisitioner.objects.create(
                document=document,
                employee=self.employee,
                source=DocumentRequisitioner.SOURCE_DIRECTORY,
                employee_number="D-2022-ADDD",
                first_name="Ralph",
                last_name="Jumao-As",
                suffix="",
            )

        response = self.client.patch(
            f"/api/documents/{doc_one.id}/edit",
            self._edit_payload(
                doc_one,
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
        for document in (doc_one, doc_two):
            requisitioner = DocumentRequisitioner.objects.get(document=document)
            self.assertEqual(requisitioner.last_name, "Jumao-As")

    def test_upsert_without_employee_number_keeps_number_blank(self):
        employee = upsert_employee_and_cascade(
            first_name="Jane",
            last_name="Guest",
            suffix="",
            employee_number=None,
        )
        self.assertIsNone(employee.employee_number)
        self.assertTrue(
            Employee.objects.filter(
                employee_number__isnull=True,
                first_name="Jane",
                last_name="Guest",
            ).exists()
        )

    def test_upsert_api_accepts_blank_employee_number(self):
        response = self.client.post(
            "/api/employees/upsert",
            {
                "employeeNumber": "",
                "firstName": "External",
                "lastName": "Person",
                "suffix": "",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["employeeNumber"], "")

    def test_name_only_document_edit_creates_directory_record_when_unique(self):
        document = self._create_document(code="RPT-SYNC-002")
        response = self.client.patch(
            f"/api/documents/{document.id}/edit",
            self._edit_payload(
                document,
                [
                    {
                        "source": "manual",
                        "employeeNumber": "",
                        "firstName": "External",
                        "lastName": "Guest",
                        "suffix": "",
                    }
                ],
            ),
            format="json",
        )
        self.assertEqual(response.status_code, 200)

        requisitioner = DocumentRequisitioner.objects.get(document=document)
        self.assertIsNone(requisitioner.employee_number)
        self.assertIsNotNone(requisitioner.employee_id)
        self.assertTrue(
            Employee.objects.filter(
                employee_number__isnull=True,
                first_name="External",
                last_name="Guest",
            ).exists()
        )

    def test_name_only_document_edit_blocks_when_similar_name_exists(self):
        Employee.objects.create(
            employee_number=None,
            first_name="External",
            last_name="Guest",
            suffix="",
        )
        document = self._create_document(code="RPT-SYNC-003")
        response = self.client.patch(
            f"/api/documents/{document.id}/edit",
            self._edit_payload(
                document,
                [
                    {
                        "source": "manual",
                        "employeeNumber": "",
                        "firstName": "External",
                        "lastName": "Guest",
                        "suffix": "",
                    }
                ],
            ),
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn(SIMILAR_NAME_EXISTS_MESSAGE, str(response.data))

    def test_link_document_requisitioners_links_name_only_rows(self):
        document = self._create_document()
        DocumentRequisitioner.objects.create(
            document=document,
            employee_number=None,
            first_name="External",
            last_name="Guest",
            suffix="",
        )
        items = link_document_requisitioners(
            [
                {
                    "employee_id": None,
                    "source": DocumentRequisitioner.SOURCE_MANUAL,
                    "employee_number": None,
                    "first_name": "External",
                    "last_name": "Guest",
                    "suffix": "",
                }
            ],
            document=document,
        )
        self.assertEqual(len(items), 1)
        self.assertIsNone(items[0]["employee_number"])
        self.assertIsNotNone(items[0]["employee_id"])
