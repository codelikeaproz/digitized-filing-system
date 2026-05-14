# Phase 1: map existing OrgUnit.type strings into OrgUnit.org_type.

from django.db import migrations
from django.utils.text import slugify


DEFAULT_ORG_TYPES = [
    ("College", "college", 10),
    ("Department", "department", 20),
    ("Office", "office", 30),
    ("Unit", "unit", 40),
]


def backfill_org_type_from_old_type(apps, schema_editor):
    OrgType = apps.get_model("orgunits", "OrgType")
    OrgUnit = apps.get_model("orgunits", "OrgUnit")

    def available_code(name):
        base = (slugify(name) or "org-type")[:50]
        code = base
        suffix = 2
        while OrgType.objects.filter(code=code).exists():
            tail = f"-{suffix}"
            code = f"{base[:50 - len(tail)]}{tail}"
            suffix += 1
        return code

    by_name = {}
    for name, code, sort_order in DEFAULT_ORG_TYPES:
        org_type, created = OrgType.objects.get_or_create(
            name=name,
            defaults={
                "code": code,
                "is_active": True,
                "sort_order": sort_order,
            },
        )
        if not created:
            updates = []
            if not org_type.code:
                org_type.code = code
                updates.append("code")
            if org_type.sort_order != sort_order:
                org_type.sort_order = sort_order
                updates.append("sort_order")
            if not org_type.is_active:
                org_type.is_active = True
                updates.append("is_active")
            if updates:
                org_type.save(update_fields=updates)
        by_name[name.lower()] = org_type

    fallback = by_name["unit"]
    for org_unit in OrgUnit.objects.filter(org_type__isnull=True):
        old_type = (org_unit.type or "").strip()
        org_type = by_name.get(old_type.lower())
        if old_type and org_type is None:
            org_type, _ = OrgType.objects.get_or_create(
                name=old_type,
                defaults={
                    "code": available_code(old_type),
                    "is_active": True,
                    "sort_order": 100,
                },
            )
            by_name[old_type.lower()] = org_type
        org_unit.org_type = org_type or fallback
        org_unit.save(update_fields=["org_type"])


def clear_org_type_backfill(apps, schema_editor):
    OrgUnit = apps.get_model("orgunits", "OrgUnit")
    OrgUnit.objects.update(org_type=None)


class Migration(migrations.Migration):

    dependencies = [
        ("orgunits", "0004_add_org_type_to_orgunit"),
    ]

    operations = [
        migrations.RunPython(backfill_org_type_from_old_type, clear_org_type_backfill),
    ]
