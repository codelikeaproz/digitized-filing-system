from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import User
from orgunits.models import OrgType, OrgUnit


class UserPasswordManagementTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.org_type = OrgType.objects.create(name="Department", code="department", is_active=True)
        self.org_unit = OrgUnit.objects.create(name="SDD", org_type=self.org_type)

        self.admin = User.objects.create_user(
            email="admin-password@test.local",
            password="Admin@12345",
            role="admin",
            employee_number="100001",
            first_name="Admin",
            last_name="User",
        )
        self.dept_head = User.objects.create_user(
            email="head-password@test.local",
            password="Test@12345",
            role="dept_head",
            org_unit=self.org_unit,
            employee_number="100002",
            first_name="Head",
            last_name="User",
        )
        self.staff = User.objects.create_user(
            email="staff-password@test.local",
            password="Test@12345",
            role="staff",
            org_unit=self.org_unit,
            employee_number="100003",
            first_name="Staff",
            last_name="User",
        )

    def test_admin_create_with_password_activates_user(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(
            "/api/users/",
            {
                "employeeNumber": "100010",
                "firstName": "Activated",
                "lastName": "User",
                "email": "activated-user@test.local",
                "role": "staff",
                "orgUnitId": str(self.org_unit.id),
                "password": "SecurePass123!",
                "confirmPassword": "SecurePass123!",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        created = User.objects.get(email="activated-user@test.local")
        self.assertTrue(created.has_usable_password())
        self.assertTrue(created.is_active)
        self.assertTrue(created.is_active_status)
        self.assertTrue(created.check_password("SecurePass123!"))

    def test_admin_create_without_password_stays_pending(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(
            "/api/users/",
            {
                "employeeNumber": "100011",
                "firstName": "Pending",
                "lastName": "User",
                "email": "pending-user@test.local",
                "role": "staff",
                "orgUnitId": str(self.org_unit.id),
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        created = User.objects.get(email="pending-user@test.local")
        self.assertFalse(created.has_usable_password())
        self.assertFalse(created.is_active)
        self.assertFalse(created.is_active_status)

    def test_dept_head_create_staff_with_password(self):
        self.client.force_authenticate(user=self.dept_head)
        response = self.client.post(
            "/api/users/",
            {
                "employeeNumber": "100012",
                "firstName": "Head",
                "lastName": "Created",
                "email": "head-created@test.local",
                "role": "staff",
                "orgUnitId": str(self.org_unit.id),
                "password": "SecurePass123!",
                "confirmPassword": "SecurePass123!",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        created = User.objects.get(email="head-created@test.local")
        self.assertTrue(created.has_usable_password())
        self.assertTrue(created.is_active)

    def test_staff_cannot_create_user_with_password(self):
        self.client.force_authenticate(user=self.staff)
        response = self.client.post(
            "/api/users/",
            {
                "employeeNumber": "100013",
                "firstName": "Blocked",
                "lastName": "User",
                "email": "blocked-create@test.local",
                "role": "staff",
                "orgUnitId": str(self.org_unit.id),
                "password": "SecurePass123!",
                "confirmPassword": "SecurePass123!",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    def test_admin_edit_pending_user_with_password_activates_account(self):
        pending = User.objects.create(
            email="pending-edit@test.local",
            role="staff",
            org_unit=self.org_unit,
            employee_number="100014",
            first_name="Pending",
            last_name="Edit",
            is_active=False,
            is_active_status=False,
        )
        pending.set_unusable_password()
        pending.save()

        self.client.force_authenticate(user=self.admin)
        response = self.client.put(
            f"/api/users/{pending.id}/",
            {
                "employeeNumber": pending.employee_number,
                "firstName": pending.first_name,
                "lastName": pending.last_name,
                "email": pending.email,
                "role": "staff",
                "orgUnitId": str(self.org_unit.id),
                "isActive": False,
                "password": "SecurePass123!",
                "confirmPassword": "SecurePass123!",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        pending.refresh_from_db()
        self.assertTrue(pending.has_usable_password())
        self.assertTrue(pending.is_active)
        self.assertTrue(pending.is_active_status)

    def test_activate_succeeds_after_manager_set_password(self):
        pending = User.objects.create(
            email="pending-activate@test.local",
            role="staff",
            org_unit=self.org_unit,
            employee_number="100015",
            first_name="Pending",
            last_name="Activate",
            is_active=False,
            is_active_status=False,
        )
        pending.set_password("SecurePass123!")
        pending.save(update_fields=["password"])

        self.client.force_authenticate(user=self.admin)
        response = self.client.patch(f"/api/users/{pending.id}/activate/")
        self.assertEqual(response.status_code, 200)
        pending.refresh_from_db()
        self.assertTrue(pending.is_active)
        self.assertTrue(pending.is_active_status)
