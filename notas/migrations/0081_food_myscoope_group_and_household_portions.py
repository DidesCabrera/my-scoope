from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("notas", "0080_unique_active_global_food_names"),
    ]

    operations = [
        migrations.AddField(
            model_name="food",
            name="myscoope_group",
            field=models.CharField(
                blank=True,
                choices=(("vegetables","Verduras y hortalizas"),("mushrooms","Hongos"),("algae","Algas"),("fruits","Frutas"),("cereals_and_pseudocereals","Cereales y pseudocereales"),("starchy_roots_and_tubers","Tubérculos y raíces feculentas"),("legumes_and_derivatives","Legumbres y derivados"),("nuts_and_seeds","Frutos secos y semillas"),("meats","Carnes"),("poultry","Aves"),("fish","Pescados"),("shellfish","Mariscos"),("eggs","Huevos"),("dairy","Lácteos"),("fats_and_oils","Grasas y aceites")),
                help_text=(
                    "Controlled My Scoope classification copied from Food Catalog. "
                    "Source food_group and food_subgroup remain available for traceability."
                ),
                max_length=40,
            ),
        ),
        migrations.AddField(
            model_name="foodportion",
            name="household_amount",
            field=models.DecimalField(
                blank=True,
                decimal_places=3,
                help_text="Everyday portion quantity copied from Food Catalog.",
                max_digits=8,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="foodportion",
            name="household_measure",
            field=models.CharField(
                blank=True,
                choices=(("unit","unidad"),("cup","taza"),("tablespoon","cucharada"),("slice","rodaja"),("can","lata"),("fillet","filete"),("leaf","hoja"),("strip","tira"),("g","g"),("ml","ml")),
                help_text="Controlled everyday measure copied from Food Catalog.",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="foodportion",
            name="household_detail",
            field=models.CharField(
                blank=True,
                help_text="Optional preparation or size detail for the everyday measure.",
                max_length=160,
            ),
        ),
        migrations.AddConstraint(
            model_name="foodportion",
            constraint=models.CheckConstraint(
                condition=(
                    models.Q(household_amount__isnull=True, household_measure="")
                    | (
                        models.Q(household_amount__isnull=False)
                        & ~models.Q(household_measure="")
                    )
                ),
                name="food_portion_household_pair",
            ),
        ),
    ]
