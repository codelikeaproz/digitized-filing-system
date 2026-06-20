from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import User
from auditlogs.models import AuditLog
from documents.models import Category, Document, DocumentRequisitioner, Folder
from employees.models import Employee
from employees.validation import EMPLOYEE_NUMBER_TAGGED_LOCK_MESSAGE
from orgunits.models import OrgUnit


class EmployeeNumberLockTests(TestCase):
    def setUp(self):
        self.org_unit = OrgUnit.objects.create(name="CISC")
        self.category = Category.objects.create(name="Reports", org_unit=self.org_unit)
        self.folder = Folder.objects.create(name="Inbox", org_unit=self.org_unit)
        self.admin = User.objects.create_user(
            email="admin-lock@test.local",
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
        self.document = Document.objects.create(
            title="sample.pdf",
            file="documents/sample.pdf",
            folder=self.folder,
            category=self.category,
            code="RPT-LOCK-001",
            keywords=["test"],
        )
        DocumentRequisitioner.objects.create(
            document=self.document,
            employee=self.employee,
            source=DocumentRequisitioner.SOURCE_DIRECTORY,
            employee_number=self.employee.employee_number,
            first_name=self.employee.first_name,
            last_name=self.employee.last_name,
            suffix="",
        )

    def test_serializer_exposes_lock_when_tagged(self):
        response = self.client.get(f"/api/employees/{self.employee.id}")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["canChangeEmployeeNumber"])
        self.assertEqual(response.data["employeeNumberBlockReason"], EMPLOYEE_NUMBER_TAGGED_LOCK_MESSAGE)
        self.assertEqual(response.data["referencedDocumentCount"], 1)

    def test_name_only_edit_allowed_when_tagged(self):
        response = self.client.put(
            f"/api/employees/{self.employee.id}",
            {
                "employeeNumber": "D-2022-ADDD",
                "firstName": "Ralph",
                "lastName": "Updated-Name",
                "suffix": "",
                "isActive": True,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)

        self.employee.refresh_from_db()
        self.assertEqual(self.employee.last_name, "Updated-Name")
        self.assertEqual(self.employee.employee_number, "D-2022-ADDD")

        requisitioner = DocumentRequisitioner.objects.get(document=self.document)
        self.assertEqual(requisitioner.last_name, "Updated-Name")

        self.assertTrue(
            AuditLog.objects.filter(
                user=self.admin,
                action="UPDATE_EMPLOYEE",
            ).exists()
        )

    def test_change_number_allowed_when_untagged(self):
        untagged = Employee.objects.create(
            employee_number="D-2099-OPEN",
            first_name="Open",
            last_name="Record",
            suffix="",
        )
        response = self.client.put(
            f"/api/employees/{untagged.id}",
            {
                "employeeNumber": "D-2099-NEWID",
                "firstName": "Open",
                "lastName": "Record",
                "suffix": "",
                "isActive": True,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)

        untagged.refresh_from_db()
        self.assertEqual(untagged.employee_number, "D-2099-NEWID")

        audit = AuditLog.objects.filter(user=self.admin, action="UPDATE_EMPLOYEE_NUMBER").latest("created_at")
        self.assertIn(f"Requisitioner ID: {untagged.id}", audit.details)
        self.assertIn("Old: D-2099-OPEN", audit.details)
        self.assertIn("New: D-2099-NEWID", audit.details)

    def test_change_number_blocked_when_tagged_without_override(self):
        response = self.client.put(
            f"/api/employees/{self.employee.id}",
            {
                "employeeNumber": "D-2099-BLOCK",
                "firstName": "Ralph",
                "lastName": "Jumao-As",
                "suffix": "",
                "isActive": True,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn(EMPLOYEE_NUMBER_TAGGED_LOCK_MESSAGE, str(response.data))

        self.employee.refresh_from_db()
        self.assertEqual(self.employee.employee_number, "D-2022-ADDD")

    def test_change_number_blocked_when_tagged_without_reason(self):
        response = self.client.put(
            f"/api/employees/{self.employee.id}",
            {
                "employeeNumber": "D-2099-BLOCK",
                "firstName": "Ralph",
                "lastName": "Jumao-As",
                "suffix": "",
                "isActive": True,
                "employeeNumberOverrideReason": "",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)

        self.employee.refresh_from_db()
        self.assertEqual(self.employee.employee_number, "D-2022-ADDD")

    def test_admin_override_allows_number_change_when_tagged(self):
        response = self.client.put(
            f"/api/employees/{self.employee.id}",
            {
                "employeeNumber": "D-2099-OVERRIDE",
                "firstName": "Ralph",
                "lastName": "Jumao-As",
                "suffix": "",
                "isActive": True,
                "employeeNumberOverrideReason": "Correcting institutional ID after HR verification.",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)

        self.employee.refresh_from_db()
        self.assertEqual(self.employee.employee_number, "D-2099-OVERRIDE")

        requisitioner = DocumentRequisitioner.objects.get(document=self.document)
        self.assertEqual(requisitioner.employee_number, "D-2099-OVERRIDE")

        audit = AuditLog.objects.filter(
            user=self.admin,
            action="UPDATE_EMPLOYEE_NUMBER_OVERRIDE",
        ).latest("created_at")
        self.assertIn(f"Requisitioner ID: {self.employee.id}", audit.details)
        self.assertIn("Old: D-2022-ADDD", audit.details)
        self.assertIn("New: D-2099-OVERRIDE", audit.details)
        self.assertIn("Reason: Correcting institutional ID after HR verification.", audit.details)
