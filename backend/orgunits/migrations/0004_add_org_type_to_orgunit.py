# Phase 1: add nullable OrgType relation while keeping the old type field.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("orgunits", "0003_create_org_type"),
    ]

    operations = [
        migrations.AddField(
            model_name="orgunit",
            name="org_type",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="org_units",
                to="orgunits.orgtype",
            ),
        ),
    ]
