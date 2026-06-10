# Generated manually for list panel ordering.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("notas", "0024_foodlocalizedname"),
    ]

    operations = [
        migrations.AddField(
            model_name="dailyplan",
            name="list_order",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="meal",
            name="list_order",
            field=models.PositiveIntegerField(default=0),
        ),
    ]
