"""Build a served preparation component for one calendarized meal."""

from decimal import Decimal, InvalidOperation


def build_calendarized_preparation_snapshot(preparation, *, units):
    version = preparation.current_version
    if not preparation.is_active or version is None:
        raise ValueError("preparation_not_found")
    try:
        count = Decimal(str(units))
    except (TypeError, InvalidOperation):
        raise ValueError("preparation_portion_invalid") from None
    if not count.is_finite() or count < Decimal("0.5") or count > 10 or count * 2 != (count * 2).to_integral_value():
        raise ValueError("preparation_portion_invalid")
    quantity = count * version.default_portion_g
    factor = quantity / version.yield_g
    ingredients = list(version.ingredients.order_by("order", "id"))
    return {
        "component_type": "preparation",
        "source_preparation_id": preparation.id,
        "source_preparation_version": version.version,
        "name": preparation.name,
        "quantity_g": float(quantity),
        "quantity_unit": "g",
        "portion_display_quantity": float(count),
        "portion_display_measure": version.household_label,
        "ingredients": [
            {
                "source_food_id": row.food_id,
                "name": version.ingredients_snapshot[index]["name"],
                "quantity_g": round(float(row.quantity_g * factor), 3),
                "preparation_state": row.preparation_state,
                "is_condiment": row.is_condiment,
            }
            for index, row in enumerate(ingredients)
        ],
        "source_evidence": version.evidence,
        "allergens": version.allergens,
        "sodium_mg": round(float(version.sodium_mg * factor), 3) if version.sodium_mg is not None else None,
        "protein_g": round(float(version.protein_g * factor), 3),
        "carbs_g": round(float(version.carbs_g * factor), 3),
        "fat_g": round(float(version.fat_g * factor), 3),
        "total_kcal": round(float((version.protein_g * 4 + version.carbs_g * 4 + version.fat_g * 9) * factor), 3),
    }
