import django.core.validators
from decimal import Decimal

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("food_catalog", "0011_catalogfood_imported_release_version_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="catalogfood",
            name="portion_unit",
            field=models.CharField(
                choices=[("g", "Grams"), ("ml", "Milliliters")],
                default="g",
                help_text="Unit used for portions and the nutritional basis: per 100 g or per 100 ml.",
                max_length=2,
            ),
        ),
        migrations.AlterField(
            model_name="catalogfood",
            name="calories_kcal_per_100g",
            field=models.DecimalField(
                blank=True,
                decimal_places=3,
                help_text="Optional label/source kcal per 100 of the configured portion unit.",
                max_digits=10,
                null=True,
                validators=[django.core.validators.MinValueValidator(Decimal("0"))],
            ),
        ),
        migrations.AlterField(
            model_name="catalogfoodportion",
            name="grams",
            field=models.DecimalField(
                decimal_places=3,
                help_text="Portion amount in the catalog food's configured portion unit.",
                max_digits=8,
                validators=[django.core.validators.MinValueValidator(Decimal("0.001"))],
                verbose_name="amount",
            ),
        ),
    ]
