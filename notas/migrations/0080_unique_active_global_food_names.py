from django.db import migrations, models
from django.db.models.functions import Lower, Trim


def retire_duplicate_global_names(apps, schema_editor):
    Food = apps.get_model("notas", "Food")
    database = schema_editor.connection.alias
    by_name = {}
    for food in (
        Food.objects.using(database)
        .filter(is_global=True, is_active=True)
        .annotate(normalized_name=Lower(Trim("name")))
        .order_by("pk")
    ):
        by_name.setdefault(food.normalized_name, []).append(food)

    retired_ids = []
    for name, members in by_name.items():
        if len(members) < 2:
            continue
        linked = [food for food in members if food.catalog_food_id is not None]
        if len(linked) > 1:
            raise RuntimeError(
                f"Multiple CatalogFood snapshots share public name {name!r}: "
                f"notas.Food IDs {[food.pk for food in linked]}; curate their names before migration."
            )
        members.sort(
            key=lambda food: (
                food.catalog_food_id is None,
                not food.is_verified,
                food.pk,
            )
        )
        retired_ids.extend(food.pk for food in members[1:])

    if retired_ids:
        # Historical MealFood rows keep their Food IDs and nutrient values.
        Food.objects.using(database).filter(pk__in=retired_ids).update(is_active=False)


class Migration(migrations.Migration):
    dependencies = [("notas", "0079_unique_global_catalog_snapshots")]

    operations = [
        migrations.RunPython(retire_duplicate_global_names, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name="food",
            constraint=models.UniqueConstraint(
                Lower(Trim("name")),
                condition=models.Q(is_global=True, is_active=True),
                name="unique_active_global_food_normalized_name",
            ),
        ),
    ]
