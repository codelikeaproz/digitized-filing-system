# Generated for local scanner bridge integration.

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("documents", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ScannerStation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("station_id", models.CharField(max_length=100, unique=True)),
                ("name", models.CharField(blank=True, max_length=255)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("CONNECTED", "Connected"),
                            ("NOT_DETECTED", "Not Detected"),
                            ("ERROR", "Error"),
                        ],
                        default="NOT_DETECTED",
                        max_length=20,
                    ),
                ),
                ("watched_folder", models.CharField(blank=True, max_length=500)),
                ("last_seen_at", models.DateTimeField(blank=True, null=True)),
                ("error_message", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "ordering": ["station_id"],
            },
        ),
        migrations.CreateModel(
            name="ScanJob",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("station_id", models.CharField(max_length=100)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("PENDING", "Pending"),
                            ("WAITING_FOR_SCAN", "Waiting for Scan"),
                            ("UPLOADING", "Uploading"),
                            ("COMPLETED", "Completed"),
                            ("FAILED", "Failed"),
                            ("CANCELLED", "Cancelled"),
                        ],
                        default="PENDING",
                        max_length=30,
                    ),
                ),
                ("code", models.CharField(max_length=100)),
                ("title", models.CharField(blank=True, max_length=255)),
                ("requestor", models.CharField(blank=True, max_length=255)),
                ("description", models.CharField(blank=True, max_length=50)),
                ("keywords", models.JSONField(blank=True, default=list)),
                ("original_filename", models.CharField(blank=True, max_length=255)),
                ("sha256", models.CharField(blank=True, max_length=64)),
                ("error_message", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                (
                    "category",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="scan_jobs",
                        to="documents.category",
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "folder",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="scan_jobs",
                        to="documents.folder",
                    ),
                ),
                (
                    "uploaded_document",
                    models.OneToOneField(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="scan_job",
                        to="documents.document",
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="scanjob",
            index=models.Index(fields=["station_id", "status", "created_at"], name="documents_s_station_25d655_idx"),
        ),
        migrations.AddIndex(
            model_name="scanjob",
            index=models.Index(fields=["sha256"], name="documents_s_sha256_409f25_idx"),
        ),
    ]
