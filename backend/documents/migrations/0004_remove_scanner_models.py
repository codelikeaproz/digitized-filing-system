from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("documents", "0003_documentrequisitioner_name_parts"),
    ]

    operations = [
        migrations.DeleteModel(
            name="ScanJob",
        ),
        migrations.DeleteModel(
            name="ScannerStation",
        ),
    ]
