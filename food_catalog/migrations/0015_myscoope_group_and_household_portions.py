from decimal import Decimal

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("food_catalog", "0014_catalogfood_normalized_identity"),
    ]

    operations = [
        migrations.AddField(
            model_name="catalogfood",
            name="myscoope_group",
            field=models.CharField(
                blank=True,
                choices=(("vegetables","Verduras y hortalizas"),("mushrooms","Hongos"),("algae","Algas"),("fruits","Frutas"),("cereals_and_pseudocereals","Cereales y pseudocereales"),("starchy_roots_and_tubers","Tubérculos y raíces feculentas"),("legumes_and_derivatives","Legumbres y derivados"),("nuts_and_seeds","Frutos secos y semillas"),("meats","Carnes"),("poultry","Aves"),("fish","Pescados"),("shellfish","Mariscos"),("eggs","Huevos"),("dairy","Lácteos"),("fats_and_oils","Grasas y aceites")),
                help_text=(
                    "Controlled My Scoope classification. Source food_group and "
                    "food_subgroup remain unchanged for traceability."
                ),
                max_length=40,
            ),
        ),
        migrations.AddField(
            model_name="catalogfoodportion",
            name="household_amount",
            field=models.DecimalField(
                blank=True,
                decimal_places=3,
                help_text="Everyday portion quantity, for example 1 or 0.5.",
                max_digits=8,
                null=True,
                validators=[django.core.validators.MinValueValidator(Decimal("0.001"))],
            ),
        ),
        migrations.AddField(
            model_name="catalogfoodportion",
            name="household_measure",
            field=models.CharField(
                blank=True,
                choices=(("unit","unidad"),("cup","taza"),("tablespoon","cucharada"),("slice","rodaja"),("can","lata"),("fillet","filete"),("leaf","hoja"),("strip","tira"),("g","g"),("ml","ml")),
                help_text="Controlled everyday measure such as unit, cup or tablespoon.",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="catalogfoodportion",
            name="household_detail",
            field=models.CharField(
                blank=True,
                help_text="Optional preparation or size detail for the everyday measure.",
                max_length=160,
            ),
        ),
        migrations.AddConstraint(
            model_name="catalogfoodportion",
            constraint=models.CheckConstraint(
                condition=(
                    models.Q(household_amount__isnull=True, household_measure="")
                    | (
                        models.Q(household_amount__isnull=False)
                        & ~models.Q(household_measure="")
                    )
                ),
                name="cat_portion_household_pair",
            ),
        ),
    ]
