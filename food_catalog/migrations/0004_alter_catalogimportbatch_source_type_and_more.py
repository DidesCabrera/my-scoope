# Generated for Food Catalog Launch Readiness FC-06.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("food_catalog", "0003_external_provider_source_choices"),
    ]

    operations = [
        migrations.AlterField(
            model_name="catalogimportbatch",
            name="source_type",
            field=models.CharField(choices=[("natural_verified", "Natural verified"), ("brand_submitted", "Brand submitted"), ("user_created", "User created"), ("external_temporary", "External temporary"), ("fatsecret", "FatSecret"), ("open_food_facts", "Open Food Facts"), ("admin_import", "Admin import")], max_length=40),
        ),
        migrations.CreateModel(
            name="ExternalFoodReference",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("provider", models.CharField(choices=[('fatsecret', 'FatSecret'), ('open_food_facts', 'Open Food Facts')], help_text="External provider key, for example fatsecret.", max_length=40)),
                ("external_food_id", models.CharField(max_length=160)),
                ("external_serving_id", models.CharField(blank=True, max_length=160)),
                ("display_name", models.CharField(max_length=255)),
                ("brand_name", models.CharField(blank=True, max_length=160)),
                ("source_url", models.URLField(blank=True)),
                ("attribution_text", models.TextField(blank=True)),
                ("raw_payload_hash", models.CharField(blank=True, help_text="Hash of the latest provider payload used for traceability. Raw payload is not stored here.", max_length=128)),
                ("detail_payload_hash", models.CharField(blank=True, help_text="Optional hash of the latest detail payload. Raw payload is not stored here.", max_length=128)),
                ("seen_count", models.PositiveIntegerField(default=0)),
                ("selected_count", models.PositiveIntegerField(default=0)),
                ("first_seen_at", models.DateTimeField(auto_now_add=True)),
                ("last_seen_at", models.DateTimeField(auto_now=True)),
                ("last_fetched_at", models.DateTimeField(blank=True, null=True)),
                ("expires_at", models.DateTimeField(blank=True, help_text="When provider data must be refreshed before display/calculation.", null=True)),
                ("is_active", models.BooleanField(default=True)),
                ("notes", models.TextField(blank=True)),
            ],
            options={
                "verbose_name": "External food reference",
                "verbose_name_plural": "External food references",
                "ordering": ["provider", "display_name", "external_food_id", "external_serving_id"],
                "indexes": [
                    models.Index(fields=["provider", "external_food_id"], name="ext_food_ref_provider_food_idx"),
                    models.Index(fields=["provider", "expires_at"], name="ext_food_ref_provider_exp_idx"),
                ],
                "constraints": [
                    models.UniqueConstraint(fields=("provider", "external_food_id", "external_serving_id"), name="unique_external_food_reference"),
                ],
            },
        ),
        migrations.CreateModel(
            name="ExternalProviderFetchLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("provider", models.CharField(choices=[('fatsecret', 'FatSecret'), ('open_food_facts', 'Open Food Facts')], max_length=40)),
                ("lookup_type", models.CharField(choices=[("search", "Search"), ("detail", "Detail"), ("serving", "Serving")], max_length=30)),
                ("status", models.CharField(choices=[("success", "Success"), ("failed", "Failed")], max_length=30)),
                ("query", models.CharField(blank=True, max_length=255)),
                ("external_food_id", models.CharField(blank=True, max_length=160)),
                ("external_serving_id", models.CharField(blank=True, max_length=160)),
                ("status_code", models.PositiveIntegerField(blank=True, null=True)),
                ("error_message", models.TextField(blank=True)),
                ("raw_payload_hash", models.CharField(blank=True, max_length=128)),
                ("fetched_at", models.DateTimeField(auto_now_add=True)),
                ("expires_at", models.DateTimeField(blank=True, null=True)),
            ],
            options={
                "verbose_name": "External provider fetch log",
                "verbose_name_plural": "External provider fetch logs",
                "ordering": ["-fetched_at"],
                "indexes": [
                    models.Index(fields=["provider", "lookup_type", "status"], name="ext_fetch_provider_type_idx"),
                    models.Index(fields=["provider", "fetched_at"], name="ext_fetch_provider_time_idx"),
                ],
            },
        ),
    ]
