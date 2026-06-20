from django.test import TestCase

from accounts.models import User
from ai.services.intent_service import answer_direct_intent
from documents.models import Category, Document, DocumentRequisitioner, Folder
from employees.models import Employee
from orgunits.models import OrgType, OrgUnit


class RequisitionerDirectoryIntentTests(TestCase):
    def setUp(self):
        self.org_type = OrgType.objects.create(name="Department", code="department", is_active=True)
        self.cisc = OrgUnit.objects.create(name="CISC", org_type=self.org_type)
        self.sdd = OrgUnit.objects.create(name="SDD", org_type=self.org_type, parent=self.cisc)

        self.cisc_folder = Folder.objects.create(name="CISC Inbox", org_unit=self.cisc)
        self.sdd_folder = Folder.objects.create(name="SDD Inbox", org_unit=self.sdd)

        self.cisc_category = Category.objects.create(name="Memo", org_unit=self.cisc)
        self.sdd_category = Category.objects.create(name="Report", org_unit=self.sdd)

        self.admin = User.objects.create_user(
            email="admin-chatbot-dir@test.local",
            password="Admin@12345",
            role="admin",
        )
        self.staff = User.objects.create_user(
            email="staff-chatbot-dir@test.local",
            password="Test@12345",
            role="staff",
            org_unit=self.sdd,
            employee_number="100001",
            first_name="Staff",
            last_name="SDD",
        )
        self.dept_head = User.objects.create_user(
            email="head-chatbot-dir@test.local",
            password="Test@12345",
            role="dept_head",
            org_unit=self.sdd,
        )

        self.employee = Employee.objects.create(
            employee_number="D-2022-ADDD",
            first_name="Ralph",
            last_name="Jumao-As",
            suffix="",
        )

    def _create_tagged_document(self, folder, category, title):
        document = Document.objects.create(
            title=title,
            file="documents/sample.pdf",
            folder=folder,
            category=category,
        )
        DocumentRequisitioner.objects.create(
            document=document,
            employee_number=self.employee.employee_number,
            first_name="Ralph",
            last_name="Jumao-As",
            suffix="",
        )
        return document

    def test_tagged_count_for_admin(self):
        self._create_tagged_document(self.cisc_folder, self.cisc_category, "Doc A")
        self._create_tagged_document(self.sdd_folder, self.sdd_category, "Doc B")

        result = answer_direct_intent(self.admin, "How many documents is Ralph tagged on?")
        self.assertIsNotNone(result)
        self.assertIn("tagged on 2 documents", result["answer"])

    def test_tagged_count_scoped_for_staff_is_refused(self):
        self._create_tagged_document(self.cisc_folder, self.cisc_category, "Doc A")
        self._create_tagged_document(self.sdd_folder, self.sdd_category, "Doc B")

        result = answer_direct_intent(self.staff, "How many documents is Ralph tagged on?")
        self.assertIsNotNone(result)
        self.assertIn("department heads", result["answer"].lower())

    def test_tagged_count_scoped_for_dept_head(self):
        self._create_tagged_document(self.cisc_folder, self.cisc_category, "Doc A")
        self._create_tagged_document(self.sdd_folder, self.sdd_category, "Doc B")

        result = answer_direct_intent(self.dept_head, "How many documents is Ralph tagged on?")
        self.assertIsNotNone(result)
        self.assertIn("tagged on 1 document", result["answer"])
        self.assertIn("accessible scope", result["answer"])

    def test_list_tagged_documents_for_dept_head(self):
        self._create_tagged_document(self.sdd_folder, self.sdd_category, "Scoped Doc")

        result = answer_direct_intent(self.dept_head, "List documents tagged to Ralph")
        self.assertIsNotNone(result)
        self.assertIn("Scoped Doc", result["answer"])
        self.assertEqual(len(result["matches"]), 1)

    def test_list_tagged_documents_for_staff_is_refused(self):
        self._create_tagged_document(self.sdd_folder, self.sdd_category, "Scoped Doc")

        result = answer_direct_intent(self.staff, "List documents tagged to Ralph")
        self.assertIsNotNone(result)
        self.assertIn("department heads", result["answer"].lower())
    def test_find_requisitioner_by_employee_number(self):
        self._create_tagged_document(self.sdd_folder, self.sdd_category, "Scoped Doc")

        result = answer_direct_intent(self.admin, "Find requisitioner D-2022-ADDD")
        self.assertIsNotNone(result)
        self.assertIn("Ralph Jumao-As", result["answer"])
        self.assertIn("Tagged Documents: 1", result["answer"])

    def test_catalog_requisitioners_with_tagged_documents(self):
        self._create_tagged_document(self.sdd_folder, self.sdd_category, "Scoped Doc")

        result = answer_direct_intent(self.admin, "Which requisitioners have tagged documents?")
        self.assertIsNotNone(result)
        self.assertIn("Ralph Jumao-As", result["answer"])
        self.assertIn("1 tagged document", result["answer"])

    def test_most_tagged_requisitioner(self):
        self._create_tagged_document(self.sdd_folder, self.sdd_category, "Scoped Doc")

        result = answer_direct_intent(self.admin, "Who has the most tagged documents?")
        self.assertIsNotNone(result)
        self.assertIn("Ralph Jumao-As", result["answer"])
        self.assertIn("most tagged documents", result["answer"])

    def test_document_requestor_query_still_uses_document_search(self):
        self._create_tagged_document(self.sdd_folder, self.sdd_category, "Scoped Doc")

        result = answer_direct_intent(self.staff, "How many files were requested by Ralph?")
        self.assertIsNotNone(result)
        self.assertIn("1 accessible document", result["answer"])

    def test_unknown_requisitioner_returns_no_result(self):
        result = answer_direct_intent(self.admin, "How many documents is Unknown Person tagged on?")
        self.assertIsNotNone(result)
        self.assertEqual(result["audit_action"], "CHATBOT_NO_RESULT")
