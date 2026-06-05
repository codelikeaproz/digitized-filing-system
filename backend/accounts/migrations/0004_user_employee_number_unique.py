from django.db import migrations, models


def blank_employee_numbers_to_null(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    User.objects.filter(employee_number="").update(employee_number=None)


def null_employee_numbers_to_blank(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    User.objects.filter(employee_number__isnull=True).update(employee_number="")


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0003_user_profile_picture"),
    ]

    operations = [
        migrations.RunPython(blank_employee_numbers_to_null, null_employee_numbers_to_blank),
        migrations.AlterField(
            model_name="user",
            name="employee_number",
            field=models.CharField(blank=True, max_length=50, null=True, unique=True),
        ),
    ]
