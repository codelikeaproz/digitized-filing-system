from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Notification",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=120)),
                ("message", models.TextField()),
                (
                    "level",
                    models.CharField(
                        choices=[
                            ("warning", "Warning"),
                            ("alert", "Alert"),
                            ("critical", "Critical"),
                            ("exceeded", "Exceeded"),
                        ],
                        default="warning",
                        max_length=20,
                    ),
                ),
                ("threshold_percent", models.PositiveSmallIntegerField(blank=True, null=True)),
                (
                    "audience",
                    models.CharField(
                        choices=[("all", "All Users"), ("admin", "Administrators")],
                        default="all",
                        max_length=20,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "db_table": "notifications",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="StorageThresholdState",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("fired_80", models.BooleanField(default=False)),
                ("fired_90", models.BooleanField(default=False)),
                ("fired_95", models.BooleanField(default=False)),
                ("fired_100", models.BooleanField(default=False)),
                ("alloc_fired_90", models.BooleanField(default=False)),
                ("alloc_fired_100", models.BooleanField(default=False)),
                ("quota_mb_at_last_reset", models.PositiveIntegerField(default=0)),
            ],
            options={
                "db_table": "storage_threshold_states",
                "verbose_name": "Storage Threshold State",
                "verbose_name_plural": "Storage Threshold State",
            },
        ),
    ]
