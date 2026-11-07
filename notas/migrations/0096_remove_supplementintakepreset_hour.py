from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("notas", "0095_supplement_intake_presets"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="supplementintakepreset",
            name="hour",
        ),
    ]
