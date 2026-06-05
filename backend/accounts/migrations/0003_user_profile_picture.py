from django.db import migrations, models

import accounts.models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0002_user_employee_number_suffix"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="profile_picture",
            field=models.ImageField(
                blank=True,
                null=True,
                upload_to=accounts.models.profile_picture_upload_to,
            ),
        ),
    ]
