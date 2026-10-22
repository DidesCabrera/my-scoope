from django.db import migrations, models
from django.db.models import Count
from django.db.models.functions import Lower, Trim


def check_existing_identites(apps, schema_editor):
    CatalogFood = apps.get_model("food_catalog", "CatalogFood")
    duplicates = (
        CatalogFood.objects.using(schema_editor.connection.alias)
        .exclude(canonical_name="")
        .annotate(
            normalized_name=Lower(Trim("canonical_name")),
            normalized_brand=Lower(Trim("brand_name")),
            normalized_country=Lower(Trim("country")),
        )
        .values("normalized_name", "normalized_brand", "normalized_country")
        .annotate(count=Count("pk"))
        .filter(count__gt=1)
        .order_by("normalized_name", "normalized_brand", "normalized_country")
        .first()
    )
    if duplicates:
        raise RuntimeError(
            "Duplicate Food Catalog identities require curation before adding the normalized uniqueness constraint: "
            f"{duplicates['normalized_name']!r}, {duplicates['normalized_brand']!r}, "
            f"{duplicates['normalized_country']!r}"
        )


class Migration(migrations.Migration):
    dependencies = [("food_catalog", "0013_catalogfood_visual_identity")]

    operations = [
        migrations.RunPython(check_existing_identites, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name="catalogfood",
            constraint=models.UniqueConstraint(
                Lower(Trim("canonical_name")),
                Lower(Trim("brand_name")),
                Lower(Trim("country")),
                condition=~models.Q(canonical_name=""),
                name="unique_catalog_food_normalized_identity",
            ),
        ),
    ]
