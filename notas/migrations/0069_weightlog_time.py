from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("notas", "0068_food_portion_unit"),
    ]

    operations = [
        migrations.AddField(
            model_name="weightlog",
            name="time",
            field=models.TimeField(blank=True, null=True),
        ),
    ]
