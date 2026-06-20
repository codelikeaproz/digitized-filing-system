from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import User
from auditlogs.models import AuditLog
from config.tests.test_timezone_utils import ISO_UTC_PATTERN
from documents.models import Category, Document, DocumentRequisitioner, Folder
from employees.models import Employee
from employees.references import get_reference_count_for_employee
from orgunits.models import OrgType, OrgUnit


class RequisitionerReferenceTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.org_type, _ = OrgType.objects.get_or_create(
            name="Department",
            defaults={"code": "department", "is_active": True},
        )
        self.cisc = OrgUnit.objects.create(name="CISC", org_type=self.org_type)
        self.sdd = OrgUnit.objects.create(name="SDD", org_type=self.org_type, parent=self.cisc)
        self.other = OrgUnit.objects.create(name="OTHER", org_type=self.org_type)

        self.cisc_folder = Folder.objects.create(name="CISC Inbox", org_unit=self.cisc)
        self.sdd_folder = Folder.objects.create(name="SDD Inbox", org_unit=self.sdd)
        self.other_folder = Folder.objects.create(name="OTHER Inbox", org_unit=self.other)

        self.cisc_category = Category.objects.create(name="Memo", org_unit=self.cisc)
        self.sdd_category = Category.objects.create(name="Report", org_unit=self.sdd)
        self.other_category = Category.objects.create(name="Report", org_unit=self.other)

        self.admin = User.objects.create_user(
            email="admin-refs@test.local",
            password="Admin@12345",
            role="admin",
        )
        self.staff = User.objects.create_user(
            email="staff-refs@test.local",
            password="Test@12345",
            role="staff",
            org_unit=self.sdd,
            employee_number="100001",
            first_name="Staff",
            last_name="SDD",
        )

        self.employee = Employee.objects.create(
            employee_number="D-2022-ADDD",
            first_name="Ralph",
            last_name="Jumao-As",
            suffix="",
        )
        self._doc_counter = 0

    def _create_tagged_document(self, folder, category, title, employee=None):
        employee = employee or self.employee
        self._doc_counter += 1
        document = Document.objects.create(
            title=title,
            file="documents/sample.pdf",
            folder=folder,
            category=category,
            code=f"RPT-REF-{self._doc_counter:03d}",
            keywords=["test"],
        )
        DocumentRequisitioner.objects.create(
            document=document,
            employee=employee,
            source=DocumentRequisitioner.SOURCE_DIRECTORY,
            employee_number=employee.employee_number,
            first_name=employee.first_name,
            last_name=employee.last_name,
            suffix=employee.suffix or "",
        )
        return document

    def test_reference_count_matches_distinct_documents(self):
        self._create_tagged_document(self.cisc_folder, self.cisc_category, "Doc A")
        self._create_tagged_document(self.sdd_folder, self.sdd_category, "Doc B")

        self.assertEqual(get_reference_count_for_employee(self.employee), 2)

    def test_list_includes_reference_counts(self):
        self._create_tagged_document(self.cisc_folder, self.cisc_category, "Doc A")
        self.client.force_authenticate(user=self.admin)
        response = self.client.get("/api/employees", {"activeOnly": "false"})
        self.assertEqual(response.status_code, 200)
        row = next(
            item for item in response.data["results"] if item["employeeNumber"] == "D-2022-ADDD"
        )
        self.assertEqual(row["referencedDocumentCount"], 1)
        self.assertFalse(row["canChangeEmployeeNumber"])
        self.assertTrue(row["canDelete"])
        self.assertEqual(row["deleteBlockReason"], "")

    def test_delete_blocked_when_more_than_three_references(self):
        for index in range(4):
            self._create_tagged_document(
                self.cisc_folder,
                self.cisc_category,
                f"Doc {index}",
            )

        self.client.force_authenticate(user=self.admin)
        response = self.client.delete(f"/api/employees/{self.employee.id}")
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.data["success"])
        self.assertIn("Tagged on 4 documents", response.data["message"])
        self.assertTrue(
            AuditLog.objects.filter(
                action="REQUISITIONER_DELETE_BLOCKED",
                target_name=self.employee.get_full_name(),
            ).exists()
        )
        self.assertTrue(Employee.objects.filter(pk=self.employee.pk).exists())

    def test_delete_allowed_with_three_references(self):
        for index in range(3):
            self._create_tagged_document(
                self.cisc_folder,
                self.cisc_category,
                f"Doc {index}",
            )

        self.client.force_authenticate(user=self.admin)
        response = self.client.delete(f"/api/employees/{self.employee.id}")
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Employee.objects.filter(pk=self.employee.pk).exists())
        audit = AuditLog.objects.filter(action="DELETE_EMPLOYEE").latest("created_at")
        self.assertIn("Tagged on 3 documents", audit.details)

    def test_documents_endpoint_paginates_and_audits(self):
        self._create_tagged_document(self.cisc_folder, self.cisc_category, "Memorandum 2026")
        self._create_tagged_document(self.sdd_folder, self.sdd_category, "Annual Report")

        self.client.force_authenticate(user=self.admin)
        response = self.client.get(
            f"/api/employees/{self.employee.id}/documents",
            {"page_size": 1},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 2)
        self.assertEqual(response.data["totalTaggedDocuments"], 2)
        self.assertEqual(len(response.data["results"]), 1)
        uploaded_at = response.data["results"][0]["uploadedAt"]
        self.assertRegex(uploaded_at, ISO_UTC_PATTERN)
        self.assertTrue(
            AuditLog.objects.filter(action="VIEW_REQUISITIONER_DOCUMENT_REFERENCES").exists()
        )

    def test_documents_endpoint_scopes_dept_head_to_accessible_org_units(self):
        cisc = OrgUnit.objects.create(name="CISC-Scoped", org_type=self.org_type)
        cisc_folder = Folder.objects.create(name="CISC Inbox Scoped", org_unit=cisc)
        cisc_category = Category.objects.create(name="Memo Scoped", org_unit=cisc)

        self._create_tagged_document(cisc_folder, cisc_category, "CISC Doc")
        self._create_tagged_document(self.sdd_folder, self.sdd_category, "SDD Doc")

        dept_head = User.objects.create_user(
            email="head-refs@test.local",
            password="Test@12345",
            role="dept_head",
            org_unit=self.sdd,
        )
        self.client.force_authenticate(user=dept_head)
        response = self.client.get(f"/api/employees/{self.employee.id}/documents")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["totalTaggedDocuments"], 1)
        self.assertEqual(response.data["results"][0]["title"], "SDD Doc")
        self.assertEqual(response.data["results"][0]["orgUnit"], "SDD")

    def test_documents_endpoint_denies_staff(self):
        self._create_tagged_document(self.cisc_folder, self.cisc_category, "CISC Doc")
        self._create_tagged_document(self.sdd_folder, self.sdd_category, "SDD Doc")

        self.client.force_authenticate(user=self.staff)
        response = self.client.get(f"/api/employees/{self.employee.id}/documents")
        self.assertEqual(response.status_code, 403)

    def test_documents_endpoint_filters_by_search_and_category(self):
        self._create_tagged_document(self.cisc_folder, self.cisc_category, "Memorandum 2026")
        self._create_tagged_document(self.sdd_folder, self.sdd_category, "Annual Report")

        self.client.force_authenticate(user=self.admin)
        response = self.client.get(
            f"/api/employees/{self.employee.id}/documents",
            {"search": "Annual", "category": "Report"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["title"], "Annual Report")
