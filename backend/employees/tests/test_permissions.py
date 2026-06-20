import json

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import User
from auditlogs.models import AuditLog
from documents.models import Category, Document, DocumentRequisitioner, Folder
from employees.duplicate_detection import EMPLOYEE_NUMBER_EXISTS_MESSAGE
from employees.models import Employee
from orgunits.models import OrgType, OrgUnit


class RequisitionerPermissionTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.org_type, _ = OrgType.objects.get_or_create(
            name="Department",
            defaults={"code": "department", "is_active": True},
        )
        self.org_unit = OrgUnit.objects.create(name="SDD", org_type=self.org_type)
        self.category = Category.objects.create(name="Reports", org_unit=self.org_unit)
        self.folder = Folder.objects.create(name="Inbox", org_unit=self.org_unit)

        self.admin = User.objects.create_user(
            email="admin-perms@test.local",
            password="Admin@12345",
            role="admin",
        )
        self.dept_head = User.objects.create_user(
            email="head-perms@test.local",
            password="Test@12345",
            role="dept_head",
            org_unit=self.org_unit,
        )
        self.staff = User.objects.create_user(
            email="staff-perms@test.local",
            password="Test@12345",
            role="staff",
            org_unit=self.org_unit,
        )

        self.employee = Employee.objects.create(
            employee_number="D-2022-ADDD",
            first_name="Ralph",
            last_name="Jumao-As",
            suffix="",
        )

    def _create_document(self, *, title, folder, category, code, file_path="documents/sample.pdf"):
        return Document.objects.create(
            title=title,
            file=file_path,
            folder=folder,
            category=category,
            code=code,
            keywords=["test"],
        )

    def _tag_employee(self, document, employee, *, source=DocumentRequisitioner.SOURCE_DIRECTORY):
        return DocumentRequisitioner.objects.create(
            document=document,
            employee=employee,
            source=source,
            employee_number=employee.employee_number,
            first_name=employee.first_name,
            last_name=employee.last_name,
            suffix=employee.suffix or "",
        )

    def _edit_payload(self, document, requisitioners):
        return {
            "folderId": str(document.folder_id),
            "categoryId": str(document.category_id),
            "code": document.code,
            "requisitioners": requisitioners,
            "description": "Updated",
            "keywords": ["updated"],
            "file_name": "sample",
        }

    def test_admin_can_list_directory(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.get("/api/employees", {"activeOnly": "false", "page": 1, "page_size": 10})
        self.assertEqual(response.status_code, 200)
        self.assertIn("referencedDocumentCount", response.data["results"][0])
        self.assertIn("canChangeEmployeeNumber", response.data["results"][0])

    def test_staff_cannot_browse_directory_without_search(self):
        self.client.force_authenticate(user=self.staff)
        response = self.client.get("/api/employees", {"activeOnly": "false", "page": 1, "page_size": 10})
        self.assertEqual(response.status_code, 403)

    def test_dept_head_can_list_directory(self):
        self.client.force_authenticate(user=self.dept_head)
        response = self.client.get("/api/employees", {"activeOnly": "false", "page": 1, "page_size": 10})
        self.assertEqual(response.status_code, 200)
        self.assertIn("scopedReferencedDocumentCount", response.data["results"][0])

    def test_dept_head_can_view_tagged_documents_scoped(self):
        other_org = OrgUnit.objects.create(name="VPAA", org_type=self.org_type)
        other_category = Category.objects.create(name="Memo", org_unit=other_org)
        other_folder = Folder.objects.create(name="VPAA Inbox", org_unit=other_org)

        sdd_document = self._create_document(
            title="SDD Doc",
            folder=self.folder,
            category=self.category,
            code="RPT-SDD-001",
        )
        self._tag_employee(sdd_document, self.employee)
        vpaa_document = self._create_document(
            title="VPAA Doc",
            folder=other_folder,
            category=other_category,
            code="RPT-VPAA-001",
        )
        self._tag_employee(vpaa_document, self.employee)

        self.client.force_authenticate(user=self.dept_head)
        response = self.client.get(f"/api/employees/{self.employee.id}/documents")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["totalTaggedDocuments"], 1)
        self.assertEqual(response.data["results"][0]["title"], "SDD Doc")

    def test_dept_head_sees_scoped_count_for_cross_org_tags(self):
        other_org = OrgUnit.objects.create(name="VPAA", org_type=self.org_type)
        other_category = Category.objects.create(name="Memo", org_unit=other_org)
        other_folder = Folder.objects.create(name="VPAA Inbox", org_unit=other_org)

        self._tag_employee(
            self._create_document(
                title="SDD Doc",
                folder=self.folder,
                category=self.category,
                code="RPT-SDD-002",
            ),
            self.employee,
        )
        self._tag_employee(
            self._create_document(
                title="VPAA Doc",
                folder=other_folder,
                category=other_category,
                code="RPT-VPAA-002",
            ),
            self.employee,
        )

        self.client.force_authenticate(user=self.dept_head)
        response = self.client.get("/api/employees", {"activeOnly": "false", "search": "Ralph"})
        self.assertEqual(response.status_code, 200)
        row = response.data["results"][0]
        self.assertEqual(row["scopedReferencedDocumentCount"], 1)
        self.assertEqual(row["referencedDocumentCount"], 1)

        self.client.force_authenticate(user=self.admin)
        admin_response = self.client.get("/api/employees", {"activeOnly": "false", "search": "Ralph"})
        self.assertEqual(admin_response.status_code, 200)
        admin_row = admin_response.data["results"][0]
        self.assertEqual(admin_row["referencedDocumentCount"], 2)

    def test_dept_head_cannot_update_directory_record(self):
        self.client.force_authenticate(user=self.dept_head)
        response = self.client.put(
            f"/api/employees/{self.employee.id}",
            {
                "employeeNumber": "D-2022-ADDD",
                "firstName": "Ralph",
                "lastName": "Updated",
                "suffix": "",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    def test_dept_head_cannot_delete_requisitioner(self):
        self.client.force_authenticate(user=self.dept_head)
        response = self.client.delete(f"/api/employees/{self.employee.id}")
        self.assertEqual(response.status_code, 403)

    def test_staff_directory_browse_is_audited(self):
        self.client.force_authenticate(user=self.staff)
        response = self.client.get("/api/employees", {"activeOnly": "false", "page": 1, "page_size": 10})
        self.assertEqual(response.status_code, 403)
        self.assertTrue(
            AuditLog.objects.filter(action="REQUISITIONER_DIRECTORY_ACCESS_DENIED").exists()
        )

    def test_staff_can_search_directory_for_documents(self):
        self.client.force_authenticate(user=self.staff)
        response = self.client.get("/api/employees", {"search": "Ralph", "page_size": 50})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        result = response.data["results"][0]
        self.assertEqual(result["firstName"], "Ralph")
        self.assertNotIn("referencedDocumentCount", result)
        self.assertNotIn("scopedReferencedDocumentCount", result)

    def test_staff_cannot_retrieve_directory_record(self):
        self.client.force_authenticate(user=self.staff)
        response = self.client.get(f"/api/employees/{self.employee.id}")
        self.assertEqual(response.status_code, 403)

    def test_staff_cannot_view_tagged_documents(self):
        self.client.force_authenticate(user=self.staff)
        response = self.client.get(f"/api/employees/{self.employee.id}/documents")
        self.assertEqual(response.status_code, 403)

    def test_staff_cannot_upsert_directory_record(self):
        self.client.force_authenticate(user=self.staff)
        response = self.client.post(
            "/api/employees/upsert",
            {
                "employeeNumber": "D-2022-NEWW",
                "firstName": "New",
                "lastName": "Person",
                "suffix": "",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(Employee.objects.filter(employee_number="D-2022-NEWW").exists())

    def test_staff_cannot_update_directory_record(self):
        self.client.force_authenticate(user=self.staff)
        response = self.client.put(
            f"/api/employees/{self.employee.id}",
            {
                "employeeNumber": "D-2022-ADDD",
                "firstName": "Ralph",
                "lastName": "Updated",
                "suffix": "",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.employee.refresh_from_db()
        self.assertEqual(self.employee.last_name, "Jumao-As")

    def test_staff_cannot_delete_requisitioner(self):
        self.client.force_authenticate(user=self.staff)
        response = self.client.delete(f"/api/employees/{self.employee.id}")
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Employee.objects.filter(pk=self.employee.pk).exists())

    def test_dept_head_cannot_upsert_directory_record(self):
        self.client.force_authenticate(user=self.dept_head)
        response = self.client.post(
            "/api/employees/upsert",
            {
                "employeeNumber": "D-2022-NEWW",
                "firstName": "New",
                "lastName": "Person",
                "suffix": "",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    def test_staff_upload_links_manual_requisitioner_to_directory_without_upsert_api(self):
        self.client.force_authenticate(user=self.staff)
        upload = SimpleUploadedFile("report.pdf", b"%PDF-1.4 test", content_type="application/pdf")
        response = self.client.post(
            "/api/documents/upload",
            {
                "file": upload,
                "folderId": str(self.folder.id),
                "categoryId": str(self.category.id),
                "code": "RPT-SYNC-001",
                "description": "Upload test",
                "keywords": json.dumps(["sync"]),
                "requisitioners": json.dumps(
                    [
                        {
                            "source": "manual",
                            "employeeNumber": "D-2022-SYNC",
                            "firstName": "Sync",
                            "lastName": "Person",
                            "suffix": "",
                        }
                    ]
                ),
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, 201)
        self.assertTrue(Employee.objects.filter(employee_number="D-2022-SYNC").exists())

    def test_staff_cannot_edit_document_requisitioners(self):
        document = self._create_document(
            title="sample.pdf",
            folder=self.folder,
            category=self.category,
            code="RPT-STAFF-001",
        )
        self._tag_employee(document, self.employee)

        self.client.force_authenticate(user=self.staff)
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
                        "lastName": "Jumao-As",
                        "suffix": "",
                    }
                ],
            ),
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    def test_dept_head_directory_linked_tag_name_edit_keeps_master_snapshot(self):
        document = self._create_document(
            title="sample.pdf",
            folder=self.folder,
            category=self.category,
            code="RPT-HEAD-001",
        )
        self._tag_employee(document, self.employee)

        self.client.force_authenticate(user=self.dept_head)
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
                        "lastName": "Updated-Name",
                        "suffix": "",
                    }
                ],
            ),
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        requisitioner = DocumentRequisitioner.objects.get(document=document)
        self.assertEqual(requisitioner.last_name, "Jumao-As")
        self.employee.refresh_from_db()
        self.assertEqual(self.employee.last_name, "Jumao-As")

    def test_dept_head_manual_tag_duplicate_employee_number_blocked(self):
        Employee.objects.create(
            employee_number="D-2022-CHNG",
            first_name="Other",
            last_name="Person",
            suffix="",
        )
        document = self._create_document(
            title="sample.pdf",
            folder=self.folder,
            category=self.category,
            code="RPT-HEAD-002",
        )

        self.client.force_authenticate(user=self.dept_head)
        response = self.client.patch(
            f"/api/documents/{document.id}/edit",
            self._edit_payload(
                document,
                [
                    {
                        "source": "manual",
                        "employeeNumber": "D-2022-CHNG",
                        "firstName": "Ralph",
                        "lastName": "Jumao-As",
                        "suffix": "",
                    }
                ],
            ),
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn(EMPLOYEE_NUMBER_EXISTS_MESSAGE, str(response.data))
