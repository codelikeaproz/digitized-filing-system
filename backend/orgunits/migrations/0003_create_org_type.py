# Phase 1: create database-backed organization types.

from django.db import migrations, models


DEFAULT_ORG_TYPES = [
    ("College", "college", 10),
    ("Department", "department", 20),
    ("Office", "office", 30),
    ("Unit", "unit", 40),
]


def seed_default_org_types(apps, schema_editor):
    OrgType = apps.get_model("orgunits", "OrgType")
    for name, code, sort_order in DEFAULT_ORG_TYPES:
        org_type, created = OrgType.objects.get_or_create(
            name=name,
            defaults={
                "code": code,
                "is_active": True,
                "sort_order": sort_order,
            },
        )
        if created:
            continue

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


def unseed_default_org_types(apps, schema_editor):
    OrgType = apps.get_model("orgunits", "OrgType")
    OrgType.objects.filter(code__in=[code for _, code, _ in DEFAULT_ORG_TYPES]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("orgunits", "0002_orgunit_is_deleted"),
    ]

    operations = [
        migrations.CreateModel(
            name="OrgType",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=100, unique=True)),
                ("code", models.SlugField(blank=True, max_length=50, null=True, unique=True)),
                ("is_active", models.BooleanField(default=True)),
                ("sort_order", models.PositiveIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "ordering": ["sort_order", "name"],
            },
        ),
        migrations.RunPython(seed_default_org_types, unseed_default_org_types),
    ]
