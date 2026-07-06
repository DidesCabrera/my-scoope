# Generated manually for Food Catalog Launch Readiness FC-05.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("food_catalog", "0002_solver_readiness_fields"),
    ]

    operations = [
        migrations.AlterField(
            model_name="catalogfood",
            name="source_type",
            field=models.CharField(
                choices=[
                    ("natural_verified", "Natural verified"),
                    ("brand_submitted", "Brand submitted"),
                    ("user_created", "User created"),
                    ("external_temporary", "External temporary"),
                    ("fatsecret", "FatSecret"),
                    ("open_food_facts", "Open Food Facts"),
                    ("admin_import", "Admin import"),
                ],
                default="admin_import",
                help_text="High-level origin category for curation and governance.",
                max_length=40,
            ),
        ),
        migrations.AlterField(
            model_name="catalogfoodsource",
            name="source_type",
            field=models.CharField(
                choices=[
                    ("natural_verified", "Natural verified"),
                    ("brand_submitted", "Brand submitted"),
                    ("user_created", "User created"),
                    ("external_temporary", "External temporary"),
                    ("fatsecret", "FatSecret"),
                    ("open_food_facts", "Open Food Facts"),
                    ("admin_import", "Admin import"),
                ],
                max_length=40,
            ),
        ),
    ]
