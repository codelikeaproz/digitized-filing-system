from django.db import migrations, models


def seed_system_settings(apps, schema_editor):
    SystemSettings = apps.get_model("system", "SystemSettings")
    SystemSettings.objects.get_or_create(
        pk=1,
        defaults={
            "upload_limit_mb": 15,
            "storage_quota_mb": 500,
        },
    )


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="SystemSettings",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("upload_limit_mb", models.PositiveIntegerField(default=15)),
                ("storage_quota_mb", models.PositiveIntegerField(default=500)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "system_settings",
                "verbose_name": "System Settings",
                "verbose_name_plural": "System Settings",
            },
        ),
        migrations.RunPython(seed_system_settings, migrations.RunPython.noop),
    ]
