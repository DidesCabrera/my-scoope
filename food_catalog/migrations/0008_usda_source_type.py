from django.db import migrations, models

SOURCE_CHOICES = [
    ("natural_verified", "Natural verified"),
    ("usda", "USDA FoodData Central"),
    ("brand_submitted", "Brand submitted"),
    ("user_created", "User created"),
    ("external_temporary", "External temporary"),
    ("fatsecret", "FatSecret"),
    ("open_food_facts", "Open Food Facts"),
    ("admin_import", "Admin import"),
]


class Migration(migrations.Migration):
    dependencies = [("food_catalog", "0007_catalogimportbatch_governance")]
    operations = [
        migrations.AlterField(
            model_name="catalogfood",
            name="source_type",
            field=models.CharField(choices=SOURCE_CHOICES, default="admin_import", help_text="High-level origin category for curation and governance.", max_length=40),
        ),
        migrations.AlterField(
            model_name="catalogfoodsource",
            name="source_type",
            field=models.CharField(choices=SOURCE_CHOICES, max_length=40),
        ),
        migrations.AlterField(
            model_name="catalogimportbatch",
            name="source_type",
            field=models.CharField(choices=SOURCE_CHOICES, max_length=40),
        ),
    ]
