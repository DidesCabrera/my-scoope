from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("notas", "0054_food_label_ai_analysis_and_retained_image"),
    ]

    operations = [
        migrations.AlterField(
            model_name="foodlabelcapturereceipt",
            name="detected_basis",
            field=models.CharField(
                choices=[
                    ("per_100g", "Per 100 g"),
                    ("per_serving", "Per serving"),
                    ("per_100ml", "Per 100 ml"),
                    ("manual", "Manual review"),
                ],
                max_length=24,
            ),
        ),
        migrations.AddField(
            model_name="foodlabelcapturereceipt",
            name="volume_weight_g_per_100ml",
            field=models.DecimalField(blank=True, decimal_places=3, max_digits=8, null=True),
        ),
    ]
