from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("notas", "0085_alter_savedcomparison_kind"),
    ]

    operations = [
        migrations.AddField(
            model_name="weightlog",
            name="comment",
            field=models.CharField(blank=True, max_length=500),
        ),
    ]
