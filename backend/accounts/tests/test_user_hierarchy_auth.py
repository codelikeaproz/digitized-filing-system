from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import User
from orgunits.models import OrgType, OrgUnit


class UserHierarchyAuthTests(TestCase):
    """Dept Head user management scoped to accessible OrgUnit subtree."""

    def setUp(self):
        self.client = APIClient()
        self.org_type = OrgType.objects.create(name="Department", code="department", is_active=True)

        self.cisc = OrgUnit.objects.create(name="CISC", org_type=self.org_type)
        self.sdd = OrgUnit.objects.create(name="SDD", org_type=self.org_type, parent=self.cisc)
        self.it = OrgUnit.objects.create(name="IT", org_type=self.org_type, parent=self.cisc)
        self.other = OrgUnit.objects.create(name="OTHER", org_type=self.org_type)

        self.cisc_head = User.objects.create_user(
            email="cisc-head-users@test.local",
            password="Test@12345",
            role="dept_head",
            org_unit=self.cisc,
            employee_number="100001",
            first_name="Head",
            last_name="CISC",
        )
        self.sdd_head = User.objects.create_user(
            email="sdd-head-users@test.local",
            password="Test@12345",
            role="dept_head",
            org_unit=self.sdd,
            employee_number="100002",
            first_name="Head",
            last_name="SDD",
        )
        self.sdd_staff = User.objects.create_user(
            email="sdd-staff-users@test.local",
            password="Test@12345",
            role="staff",
            org_unit=self.sdd,
            employee_number="100003",
            first_name="Staff",
            last_name="SDD",
        )
        self.other_staff = User.objects.create_user(
            email="other-staff-users@test.local",
            password="Test@12345",
            role="staff",
            org_unit=self.other,
            employee_number="100004",
            first_name="Staff",
            last_name="OTHER",
        )

    def _user_emails(self, response):
        return {row["email"] for row in response.data["results"]}

    def test_cisc_head_lists_subtree_staff(self):
        self.client.force_authenticate(user=self.cisc_head)
        response = self.client.get("/api/users/", {"role": "staff"})
        self.assertEqual(response.status_code, 200)
        emails = self._user_emails(response)
        self.assertIn(self.sdd_staff.email, emails)
        self.assertNotIn(self.other_staff.email, emails)

    def test_cisc_head_retrieves_child_staff(self):
        self.client.force_authenticate(user=self.cisc_head)
        response = self.client.get(f"/api/users/{self.sdd_staff.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["canManage"])

    def test_cisc_head_creates_staff_in_child_unit(self):
        self.client.force_authenticate(user=self.cisc_head)
        response = self.client.post(
            "/api/users/",
            {
                "employeeNumber": "100010",
                "firstName": "New",
                "lastName": "SDD",
                "email": "new-sdd-staff@test.local",
                "role": "staff",
                "orgUnitId": str(self.sdd.id),
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        created = User.objects.get(email="new-sdd-staff@test.local")
        self.assertEqual(created.org_unit_id, self.sdd.id)

    def test_cisc_head_updates_child_staff(self):
        self.client.force_authenticate(user=self.cisc_head)
        response = self.client.put(
            f"/api/users/{self.sdd_staff.id}/",
            {
                "employeeNumber": self.sdd_staff.employee_number,
                "firstName": "Updated",
                "lastName": "SDD",
                "email": self.sdd_staff.email,
                "role": "staff",
                "orgUnitId": str(self.sdd.id),
                "isActive": True,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.sdd_staff.refresh_from_db()
        self.assertEqual(self.sdd_staff.first_name, "Updated")
        self.assertTrue(response.data["canManage"])

    def test_cisc_head_cannot_update_child_dept_head(self):
        self.client.force_authenticate(user=self.cisc_head)
        response = self.client.put(
            f"/api/users/{self.sdd_head.id}/",
            {
                "employeeNumber": self.sdd_head.employee_number,
                "firstName": "Blocked",
                "lastName": "SDD",
                "email": self.sdd_head.email,
                "role": "staff",
                "orgUnitId": str(self.sdd.id),
                "isActive": True,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    def test_sdd_head_cannot_access_cisc_staff(self):
        self.client.force_authenticate(user=self.sdd_head)
        cisc_staff = User.objects.create_user(
            email="cisc-staff-users@test.local",
            password="Test@12345",
            role="staff",
            org_unit=self.cisc,
            employee_number="100005",
            first_name="Staff",
            last_name="CISC",
        )
        response = self.client.get(f"/api/users/{cisc_staff.id}/")
        self.assertEqual(response.status_code, 403)

    def test_tampered_org_unit_filter_returns_403(self):
        self.client.force_authenticate(user=self.cisc_head)
        response = self.client.get("/api/users/", {"orgUnitId": self.other.id})
        self.assertEqual(response.status_code, 403)
