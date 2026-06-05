from django.db import migrations, models

ALLOWED_SUFFIXES = {"Jr.", "Sr.", "I", "II", "III", "IV", "V"}


def split_full_name(full_name):
    parts = (full_name or "").strip().split()
    if not parts:
        return "", "", ""

    suffix = ""
    if len(parts) > 1 and parts[-1] in ALLOWED_SUFFIXES:
        suffix = parts[-1]
        parts = parts[:-1]

    if not parts:
        return "", "", suffix
    if len(parts) == 1:
        return parts[0], "", suffix
    return parts[0], " ".join(parts[1:]), suffix


def migrate_full_name_to_parts(apps, schema_editor):
    DocumentRequisitioner = apps.get_model("documents", "DocumentRequisitioner")
    for requisitioner in DocumentRequisitioner.objects.all().iterator():
        first_name, last_name, suffix = split_full_name(requisitioner.full_name)
        requisitioner.first_name = first_name
        requisitioner.last_name = last_name
        requisitioner.suffix = suffix
        requisitioner.save(update_fields=["first_name", "last_name", "suffix"])


def restore_full_name_from_parts(apps, schema_editor):
    DocumentRequisitioner = apps.get_model("documents", "DocumentRequisitioner")
    for requisitioner in DocumentRequisitioner.objects.all().iterator():
        parts = [requisitioner.first_name, requisitioner.last_name]
        if requisitioner.suffix:
            parts.append(requisitioner.suffix)
        requisitioner.full_name = " ".join(part for part in parts if part).strip()
        requisitioner.save(update_fields=["full_name"])


class Migration(migrations.Migration):

    dependencies = [
        ("documents", "0002_documentrequisitioner"),
    ]

    operations = [
        migrations.AddField(
            model_name="documentrequisitioner",
            name="first_name",
            field=models.CharField(blank=True, default="", max_length=100),
        ),
        migrations.AddField(
            model_name="documentrequisitioner",
            name="last_name",
            field=models.CharField(blank=True, default="", max_length=100),
        ),
        migrations.AddField(
            model_name="documentrequisitioner",
            name="suffix",
            field=models.CharField(blank=True, default="", max_length=20),
        ),
        migrations.RunPython(migrate_full_name_to_parts, restore_full_name_from_parts),
        migrations.RemoveField(
            model_name="documentrequisitioner",
            name="full_name",
        ),
        migrations.AlterField(
            model_name="documentrequisitioner",
            name="first_name",
            field=models.CharField(max_length=100),
        ),
        migrations.AlterField(
            model_name="documentrequisitioner",
            name="last_name",
            field=models.CharField(max_length=100),
        ),
    ]
