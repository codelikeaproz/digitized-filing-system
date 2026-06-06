from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import User
from auditlogs.models import AuditLog
from orgunits.models import OrgType, OrgUnit
from orgunits.storage import get_available_allocation_mb, validate_org_unit_allocation_quota
from system.models import SystemSettings
from system.services import invalidate_system_settings_cache


class OrgUnitAllocationStorageTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            email="admin-orgunit-alloc@test.local",
            password="Admin@12345",
            role="admin",
        )
        self.client.force_authenticate(user=self.admin)
        self.org_type = OrgType.objects.create(name="Department", code="department", is_active=True)
        settings = SystemSettings.load()
        settings.storage_quota_mb = 5000
        settings.save()
        invalidate_system_settings_cache()
        OrgUnit.objects.create(name="CBM", org_type=self.org_type, storage_quota_mb=2400)
        OrgUnit.objects.create(name="SDD", org_type=self.org_type, storage_quota_mb=2400)

    def test_available_allocation_mb_after_existing_units(self):
        self.assertEqual(get_available_allocation_mb(), 200)

    def test_create_org_unit_exceeding_allocation_fails(self):
        response = self.client.post(
            "/api/org-units/",
            {
                "name": "New Unit",
                "org_type_id": self.org_type.id,
                "storageQuotaMb": 500,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Insufficient available system storage", str(response.data))
        self.assertTrue(
            AuditLog.objects.filter(action="STORAGE_ALLOCATION_VALIDATION_FAILED").exists()
        )

    def test_create_org_unit_within_allocation_succeeds(self):
        response = self.client.post(
            "/api/org-units/",
            {
                "name": "Small Unit",
                "org_type_id": self.org_type.id,
                "storageQuotaMb": 200,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(OrgUnit.objects.filter(name="Small Unit").count(), 1)

    def test_update_org_unit_exceeding_allocation_fails(self):
        cbm = OrgUnit.objects.get(name="CBM")
        cbm.storage_quota_mb = 500
        cbm.save(update_fields=["storage_quota_mb"])
        OrgUnit.objects.filter(name="SDD").update(storage_quota_mb=4300)

        response = self.client.put(
            f"/api/org-units/{cbm.id}/",
            {
                "name": "CBM",
                "org_type_id": self.org_type.id,
                "storageQuotaMb": 800,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Insufficient available system storage", str(response.data))

    def test_update_org_unit_quota_logs_allocation_updated(self):
        cbm = OrgUnit.objects.get(name="CBM")
        cbm.storage_quota_mb = 500
        cbm.save(update_fields=["storage_quota_mb"])
        OrgUnit.objects.filter(name="SDD").update(storage_quota_mb=2000)

        response = self.client.put(
            f"/api/org-units/{cbm.id}/",
            {
                "name": "CBM",
                "org_type_id": self.org_type.id,
                "storageQuotaMb": 600,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            AuditLog.objects.filter(
                action="STORAGE_ALLOCATION_UPDATED",
                target_name="CBM",
            ).exists()
        )

    def test_validate_rejects_quota_below_current_usage(self):
        cbm = OrgUnit.objects.get(name="CBM")
        cbm.storage_used_mb = 800
        cbm.storage_quota_mb = 1000
        cbm.save(update_fields=["storage_used_mb", "storage_quota_mb"])
        OrgUnit.objects.filter(name="SDD").delete()

        from rest_framework.exceptions import ValidationError

        with self.assertRaises(ValidationError) as ctx:
            validate_org_unit_allocation_quota(500, org_unit=cbm)
        self.assertIn("current usage", str(ctx.exception.detail))
