"""Portable snapshot of global preparations without private ownership data."""

from notas.application.sharing.services import ShareUnavailable


def preparation_share_item(relation) -> dict:
    if not relation.preparation.is_global:
        raise ShareUnavailable("private_preparation_sharing_unavailable")
    version = relation.version
    return {
        "catalog_ref": str(relation.preparation.catalog_ref),
        "name": relation.preparation.name,
        "version": version.version,
        "quantity_grams": round(float(relation.quantity_g), 2),
        "selected_units": float(relation.selected_units) if relation.selected_units is not None else None,
        "selection_mode": relation.selection_mode,
        "household_label": version.household_label,
        "nutrition": {
            "protein_grams": round(relation.protein, 2),
            "carbs_grams": round(relation.carbs, 2),
            "fat_grams": round(relation.fat, 2),
            "calories": round(relation.total_kcal, 2),
            "sodium_mg": round(float(version.sodium_mg) * relation.factor, 2) if version.sodium_mg is not None else None,
        },
        "allergens": version.allergens,
        "ingredients": [
            {
                "name": row["name"],
                "quantity_g": round(float(row["quantity_g"]) * relation.factor, 2),
                "preparation_state": row["preparation_state"],
                "is_condiment": row["is_condiment"],
            }
            for row in version.ingredients_snapshot
        ],
    }
