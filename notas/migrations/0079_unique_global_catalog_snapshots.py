from django.db import migrations, models
from django.db.models import Q


def _linked_components(foods):
    parent = {food.pk: food.pk for food in foods}
    seen_ids = {}
    seen_refs = {}

    def root(pk):
        while parent[pk] != pk:
            parent[pk] = parent[parent[pk]]
            pk = parent[pk]
        return pk

    def join(left, right):
        parent[root(right)] = root(left)

    for food in foods:
        if food.catalog_food_id is not None:
            if food.catalog_food_id in seen_ids:
                join(food.pk, seen_ids[food.catalog_food_id])
            seen_ids[food.catalog_food_id] = food.pk
        if food.catalog_food_ref is not None:
            ref = str(food.catalog_food_ref)
            if ref in seen_refs:
                join(food.pk, seen_refs[ref])
            seen_refs[ref] = food.pk

    groups = {}
    for food in foods:
        groups.setdefault(root(food.pk), []).append(food)
    return list(groups.values())


def _retired_ids_from_group(members, CatalogFood, database):
    ids = {food.catalog_food_id for food in members if food.catalog_food_id is not None}
    refs = {str(food.catalog_food_ref) for food in members if food.catalog_food_ref is not None}
    member_ids = [food.pk for food in members]
    if len(ids) > 1 or len(refs) > 1:
        raise RuntimeError(f"Conflicting Food Catalog identities on notas.Food IDs {member_ids}")
    if ids and refs and not CatalogFood.objects.using(database).filter(
        pk=next(iter(ids)), catalog_ref=next(iter(refs))
    ).exists():
        raise RuntimeError(f"Mismatched Food Catalog ID/ref on notas.Food IDs {member_ids}")
    members.sort(
        key=lambda food: (
            not food.is_active,
            food.catalog_food_id is None or food.catalog_food_ref is None,
            food.catalog_sync_status != "snapshot",
            not food.is_verified,
            -food.data_quality_score,
            food.pk,
        )
    )
    return [food.pk for food in members[1:]]


def _check_partial_snapshots(Food, database):
    partial = (
        Food.objects.using(database)
        .filter(is_global=True, catalog_sync_status="snapshot")
        .filter(
            Q(catalog_food_id__isnull=True, catalog_food_ref__isnull=False)
            | Q(catalog_food_id__isnull=False, catalog_food_ref__isnull=True)
        )
        .values_list("pk", flat=True)
        .first()
    )
    if partial is not None:
        raise RuntimeError(
            f"Global notas.Food ID {partial} has an incomplete Food Catalog trace; resolve it before migration."
        )


def retire_duplicate_snapshots(apps, schema_editor):
    Food = apps.get_model("notas", "Food")
    CatalogFood = apps.get_model("food_catalog", "CatalogFood")
    database = schema_editor.connection.alias
    foods = list(
        Food.objects.using(database)
        .filter(is_global=True)
        .filter(Q(catalog_food_id__isnull=False) | Q(catalog_food_ref__isnull=False))
        .order_by("id")
    )

    retire_ids = []
    for members in _linked_components(foods):
        if len(members) > 1:
            retire_ids.extend(_retired_ids_from_group(members, CatalogFood, database))

    if retire_ids:
        Food.objects.using(database).filter(pk__in=retire_ids).update(
            is_active=False,
            catalog_food_id=None,
            catalog_food_ref=None,
            catalog_sync_status="unlinked",
        )
    _check_partial_snapshots(Food, database)


class Migration(migrations.Migration):
    dependencies = [
        ("notas", "0078_calendar_commitment_nutritionist"),
        ("food_catalog", "0014_catalogfood_normalized_identity"),
    ]

    operations = [
        migrations.RunPython(retire_duplicate_snapshots, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name="food",
            constraint=models.CheckConstraint(
                condition=(
                    Q(is_global=False)
                    | ~Q(catalog_sync_status="snapshot")
                    | Q(catalog_food_id__isnull=True, catalog_food_ref__isnull=True)
                    | Q(catalog_food_id__isnull=False, catalog_food_ref__isnull=False)
                ),
                name="global_food_catalog_trace_pair",
            ),
        ),
        migrations.AddConstraint(
            model_name="food",
            constraint=models.UniqueConstraint(
                fields=("catalog_food_ref",),
                condition=Q(is_global=True, catalog_food_ref__isnull=False),
                name="unique_global_food_catalog_ref",
            ),
        ),
        migrations.AddConstraint(
            model_name="food",
            constraint=models.UniqueConstraint(
                fields=("catalog_food_id",),
                condition=Q(is_global=True, catalog_food_id__isnull=False),
                name="unique_global_food_catalog_id",
            ),
        ),
    ]
