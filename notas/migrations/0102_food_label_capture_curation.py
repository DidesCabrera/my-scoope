from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("notas", "0101_alter_foodportion_household_measure")]

    operations = [
        migrations.AddField(model_name="foodlabelcapturereceipt", name="shared_for_curation", field=models.BooleanField(default=False)),
        migrations.AddField(model_name="foodlabelcapturereceipt", name="curation_payload", field=models.JSONField(blank=True, default=dict)),
        migrations.AddField(model_name="foodlabelcapturereceipt", name="curation_label_image", field=models.BinaryField(blank=True, editable=False, null=True)),
        migrations.AddField(model_name="foodlabelcapturereceipt", name="curation_label_image_sha256", field=models.CharField(blank=True, max_length=64)),
        migrations.AddField(model_name="foodlabelcapturereceipt", name="curation_label_image_size", field=models.PositiveIntegerField(default=0)),
        migrations.AddField(model_name="foodlabelcapturereceipt", name="curation_shared_at", field=models.DateTimeField(blank=True, null=True)),
    ]
