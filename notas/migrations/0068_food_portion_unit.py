from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("notas", "0067_profile_onboarding_v2"),
    ]

    operations = [
        migrations.AddField(
            model_name="food",
            name="portion_unit",
            field=models.CharField(
                choices=[("g", "Gramos"), ("ml", "Mililitros")],
                default="g",
                help_text="Unidad usada para las porciones y la base nutricional: por 100 g o por 100 ml.",
                max_length=2,
            ),
        ),
        migrations.AlterField(
            model_name="food",
            name="default_portion_g",
            field=models.DecimalField(
                blank=True,
                decimal_places=3,
                help_text="Suggested default portion in the food's configured portion unit.",
                max_digits=8,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="food",
            name="fiber_g_per_100g",
            field=models.DecimalField(
                blank=True,
                decimal_places=3,
                help_text="Fiber in grams per 100 of the food's configured portion unit.",
                max_digits=8,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="food",
            name="saturated_fat_g_per_100g",
            field=models.DecimalField(
                blank=True,
                decimal_places=3,
                help_text="Saturated fat in grams per 100 of the food's configured portion unit.",
                max_digits=8,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="food",
            name="sodium_mg_per_100g",
            field=models.DecimalField(
                blank=True,
                decimal_places=3,
                help_text="Sodium in milligrams per 100 of the food's configured portion unit.",
                max_digits=10,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="food",
            name="sugar_g_per_100g",
            field=models.DecimalField(
                blank=True,
                decimal_places=3,
                help_text="Sugar in grams per 100 of the food's configured portion unit.",
                max_digits=8,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="foodportion",
            name="grams",
            field=models.DecimalField(
                decimal_places=3,
                help_text="Portion amount in the food's configured portion unit.",
                max_digits=8,
                verbose_name="amount",
            ),
        ),
        migrations.AlterField(
            model_name="mealfood",
            name="quantity",
            field=models.FloatField(
                help_text="Amount in the food's configured portion unit",
            ),
        ),
    ]
