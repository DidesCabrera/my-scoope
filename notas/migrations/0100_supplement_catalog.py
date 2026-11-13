from datetime import date

import django.db.models.deletion
from django.db import migrations, models


def seed_example(apps, schema_editor):
    Catalog = apps.get_model("notas", "SupplementCatalogEntry")
    Catalog.objects.get_or_create(
        slug="vitamina-d3-generica",
        defaults={
            "name": "Vitamina D3",
            "description": "Forma D3 de vitamina D (colecalciferol). La dosis, presentación y composición dependen del producto; revisa la etiqueta del fabricante.",
            "source_name": "NIH Office of Dietary Supplements — Vitamin D",
            "source_url": "https://ods.od.nih.gov/factsheets/VitaminD-Consumer/",
            "reviewed_at": date(2026, 11, 12),
            "is_published": True,
        },
    )


class Migration(migrations.Migration):
    dependencies = [("notas", "0099_calendar_commitment_evaluation_label")]

    operations = [
        migrations.CreateModel(
            name="SupplementCatalogEntry",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("slug", models.SlugField(unique=True)),
                ("name", models.CharField(max_length=100)),
                ("brand", models.CharField(blank=True, max_length=100)),
                ("form", models.CharField(blank=True, max_length=32)),
                ("description", models.TextField(blank=True)),
                ("components", models.JSONField(blank=True, default=list)),
                ("nutrition", models.JSONField(blank=True, default=dict)),
                ("default_quantity", models.DecimalField(blank=True, decimal_places=3, max_digits=9, null=True)),
                ("default_unit", models.CharField(blank=True, max_length=20)),
                ("source_name", models.CharField(max_length=120)),
                ("source_url", models.URLField()),
                ("reviewed_at", models.DateField()),
                ("is_published", models.BooleanField(default=False)),
            ],
            options={"ordering": ["name", "id"]},
        ),
        migrations.AddField(
            model_name="supplement",
            name="catalog_entry",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="saved_supplements", to="notas.supplementcatalogentry"),
        ),
        migrations.AddConstraint(
            model_name="supplement",
            constraint=models.UniqueConstraint(fields=["created_by", "catalog_entry"], condition=models.Q(catalog_entry__isnull=False), name="supp_one_catalog_copy_per_user"),
        ),
        migrations.RunPython(seed_example, migrations.RunPython.noop),
    ]
