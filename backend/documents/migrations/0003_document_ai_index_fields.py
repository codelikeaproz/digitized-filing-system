from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("documents", "0002_scannerstation_scanjob"),
    ]

    operations = [
        migrations.AddField(
            model_name="document",
            name="ai_summary",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="document",
            name="content_hash",
            field=models.CharField(blank=True, db_index=True, max_length=64),
        ),
        migrations.AddField(
            model_name="document",
            name="extracted_text",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="document",
            name="last_indexed_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
