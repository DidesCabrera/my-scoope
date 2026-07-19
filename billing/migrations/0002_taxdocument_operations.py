from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("billing", "0001_initial")]

    operations = [
        migrations.AddField(model_name="taxdocument", name="attempts", field=models.PositiveSmallIntegerField(default=0)),
        migrations.AddField(model_name="taxdocument", name="first_attempt_at", field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name="taxdocument", name="last_attempt_at", field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name="taxdocument", name="adjustment_required", field=models.BooleanField(db_index=True, default=False)),
        migrations.AddField(model_name="taxdocument", name="adjustment_reason", field=models.TextField(blank=True)),
    ]
