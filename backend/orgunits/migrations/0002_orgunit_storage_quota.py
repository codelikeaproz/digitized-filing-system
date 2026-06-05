from decimal import Decimal

from django.db import migrations, models
from django.db.models import Sum


def backfill_storage_used(apps, schema_editor):
    OrgUnit = apps.get_model("orgunits", "OrgUnit")
    Document = apps.get_model("documents", "Document")

    for org_unit in OrgUnit.objects.all():
        total_bytes = (
            Document.objects.filter(folder__org_unit_id=org_unit.id)
            .aggregate(total=Sum("file_size"))
            .get("total")
            or 0
        )
        org_unit.storage_used_mb = Decimal(total_bytes) / Decimal(1024 * 1024)
        org_unit.save(update_fields=["storage_used_mb"])


class Migration(migrations.Migration):

    dependencies = [
        ("documents", "0001_initial"),
        ("orgunits", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="orgunit",
            name="storage_quota_mb",
            field=models.PositiveIntegerField(default=1024),
        ),
        migrations.AddField(
            model_name="orgunit",
            name="storage_used_mb",
            field=models.DecimalField(decimal_places=2, default=Decimal("0"), max_digits=12),
        ),
        migrations.RunPython(backfill_storage_used, migrations.RunPython.noop),
    ]
