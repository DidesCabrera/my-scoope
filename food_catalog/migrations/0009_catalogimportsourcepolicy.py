import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("food_catalog", "0008_usda_source_type"),
    ]
    operations = [
        migrations.CreateModel(
            name="CatalogImportSourcePolicy",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("source_type", models.CharField(choices=[("natural_verified", "Natural verified"), ("usda", "USDA FoodData Central"), ("brand_submitted", "Brand submitted"), ("user_created", "User created"), ("external_temporary", "External temporary"), ("fatsecret", "FatSecret"), ("open_food_facts", "Open Food Facts"), ("admin_import", "Admin import")], max_length=40)),
                ("source_name", models.CharField(max_length=160)),
                ("is_enabled", models.BooleanField(default=True)),
                ("scale_approved", models.BooleanField(default=False)),
                ("kill_switch", models.BooleanField(default=False)),
                ("max_batch_rows", models.PositiveIntegerField(default=10)),
                ("approval_reason", models.TextField(blank=True)),
                ("approved_at", models.DateTimeField(blank=True, null=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("approved_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="approved_catalog_import_source_policies", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["source_type", "source_name"]},
        ),
        migrations.AddConstraint(
            model_name="catalogimportsourcepolicy",
            constraint=models.UniqueConstraint(fields=("source_type", "source_name"), name="unique_catalog_import_source_policy"),
        ),
    ]
