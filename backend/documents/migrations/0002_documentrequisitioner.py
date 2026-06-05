from django.db import migrations, models
import django.db.models.deletion


def backfill_requisitioners_from_requestor(apps, schema_editor):
    Document = apps.get_model("documents", "Document")
    DocumentRequisitioner = apps.get_model("documents", "DocumentRequisitioner")

    for document in Document.objects.exclude(requestor__isnull=True).exclude(requestor=""):
        requestor = (document.requestor or "").strip()
        if not requestor:
            continue
        DocumentRequisitioner.objects.get_or_create(
            document_id=document.id,
            employee_number="",
            defaults={"full_name": requestor},
        )


def remove_backfilled_requisitioners(apps, schema_editor):
    DocumentRequisitioner = apps.get_model("documents", "DocumentRequisitioner")
    DocumentRequisitioner.objects.filter(employee_number="").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("documents", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="DocumentRequisitioner",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("employee_number", models.CharField(max_length=50)),
                ("full_name", models.CharField(max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "document",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="requisitioners",
                        to="documents.document",
                    ),
                ),
            ],
            options={
                "ordering": ["created_at", "id"],
            },
        ),
        migrations.AddConstraint(
            model_name="documentrequisitioner",
            constraint=models.UniqueConstraint(
                fields=("document", "employee_number"),
                name="unique_requisitioner_per_document",
            ),
        ),
        migrations.RunPython(backfill_requisitioners_from_requestor, remove_backfilled_requisitioners),
    ]
