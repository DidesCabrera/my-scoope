from __future__ import annotations

from notas.domain.models import FoodPortion


def proposed_portion_display(*, food, metric_quantity) -> tuple[float | None, str]:
    """Return the catalog's preferred household equivalent for a metric amount."""
    prefetched = getattr(food, "_prefetched_default_household_portions", None)
    portion = prefetched[0] if prefetched else None
    if portion is None and prefetched is None:
        portion = (
            food.portions.filter(
                is_default=True,
                household_amount__isnull=False,
            )
            .exclude(household_measure="")
            .only("grams", "household_amount", "household_measure")
            .first()
        )
    if portion is None:
        return None, ""

    return proposed_portion_from_values(
        metric_quantity=metric_quantity,
        grams=portion.grams,
        household_amount=portion.household_amount,
        household_measure=portion.household_measure,
    )


def proposed_or_selected_portion(*, food, metric_quantity, selected_quantity, selected_measure):
    quantity, measure = proposed_portion_display(food=food, metric_quantity=metric_quantity)
    return (quantity, measure) if quantity is not None else (selected_quantity, selected_measure)


def proposed_portion_from_values(
    *, metric_quantity, grams, household_amount, household_measure
) -> tuple[float | None, str]:
    metric = float(metric_quantity or 0)
    portion_metric = float(grams or 0)
    portion_household = float(household_amount or 0)
    measure = str(household_measure or "").strip()
    if metric <= 0 or portion_metric <= 0 or portion_household <= 0 or not measure:
        return None, ""
    return round(metric * portion_household / portion_metric, 3), measure


def enrich_snapshot_food_portions(*, foods_by_source_id, readable_food_ids) -> None:
    default_portions = {
        food_id: (grams, amount, measure)
        for food_id, grams, amount, measure in FoodPortion.objects.filter(
            food_id__in=readable_food_ids,
            is_default=True,
            household_amount__isnull=False,
        ).exclude(household_measure="").values_list(
            "food_id", "grams", "household_amount", "household_measure"
        )
    }
    for food_id in readable_food_ids:
        for food in foods_by_source_id[food_id]:
            food["detail_id"] = food_id
            portion = default_portions.get(food_id)
            if portion is None:
                continue
            quantity, measure = proposed_portion_from_values(
                metric_quantity=food.get("quantity_g"),
                grams=portion[0],
                household_amount=portion[1],
                household_measure=portion[2],
            )
            if quantity is not None:
                food["portion_display_quantity"] = quantity
                food["portion_display_measure"] = measure
