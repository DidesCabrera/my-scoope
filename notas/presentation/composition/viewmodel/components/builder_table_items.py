from notas.application.services.food_imports.localized_names import (
    resolve_food_display_name,
)


def _cached_or_live(obj, cached_attr, live_attr):
    cached_value = getattr(obj, cached_attr, None)
    return cached_value if cached_value is not None else getattr(obj, live_attr)


def _safe_percentage(part, total):
    if not total or total <= 0:
        return 0.0
    return part / total * 100


def _dailyplanmeal_snapshot_metrics(meal, dailyplan_snapshot):
    meal_kcal_protein = _cached_or_live(
        meal,
        "kcal_protein_cached",
        "kcal_protein",
    )
    meal_kcal_carbs = _cached_or_live(
        meal,
        "kcal_carbs_cached",
        "kcal_carbs",
    )
    meal_kcal_fat = _cached_or_live(
        meal,
        "kcal_fat_cached",
        "kcal_fat",
    )
    meal_total_kcal = _cached_or_live(
        meal,
        "total_kcal_cached",
        "total_kcal",
    )

    dailyplan_kcal_protein = dailyplan_snapshot.get("kcal_protein", 0)
    dailyplan_kcal_carbs = dailyplan_snapshot.get("kcal_carbs", 0)
    dailyplan_kcal_fat = dailyplan_snapshot.get("kcal_fat", 0)
    dailyplan_total_kcal = dailyplan_snapshot.get("total_kcal", 0)

    return {
        "kcal_share": _safe_percentage(
            meal_total_kcal,
            dailyplan_total_kcal,
        ),
        "alloc": {
            "protein": _safe_percentage(
                meal_kcal_protein,
                dailyplan_kcal_protein,
            ),
            "carbs": _safe_percentage(
                meal_kcal_carbs,
                dailyplan_kcal_carbs,
            ),
            "fat": _safe_percentage(
                meal_kcal_fat,
                dailyplan_kcal_fat,
            ),
        },
    }


def build_dailyplanmeal_table_item(dpm, dailyplan_snapshot=None):
    dailyplan = dpm.dailyplan
    meal = dpm.meal

    # ==================================================
    # Freeze MEAL aggregates (cached if available)
    # ==================================================

    meal_total_kcal = _cached_or_live(meal, "total_kcal_cached", "total_kcal")
    meal_protein = _cached_or_live(meal, "protein_cached", "protein")
    meal_carbs = _cached_or_live(meal, "carbs_cached", "carbs")
    meal_fat = _cached_or_live(meal, "fat_cached", "fat")

    if dailyplan_snapshot is None:
        # Fallback para detail screens o callers antiguos.
        # Las propiedades del modelo son correctas, pero en listas/Home pueden
        # ser caras porque vuelven a recorrer relaciones del DailyPlan.
        dpm_alloc = dpm.alloc
        kcal_share = dpm.kcal_share
    else:
        snapshot_metrics = _dailyplanmeal_snapshot_metrics(
            meal,
            dailyplan_snapshot,
        )
        dpm_alloc = snapshot_metrics["alloc"]
        kcal_share = snapshot_metrics["kcal_share"]

    return {
        # entidad principal
        "main_id": dailyplan.id,
        "child_id": meal.id,

        # RELACIÓN EXPLÍCITA
        "rel": {
            "id": dpm.id,
            "hour": dpm.hour,
            "note": dpm.note,

            "name": meal.name,

            "total_kcal": meal_total_kcal,
            "kcal_share": kcal_share,

            "g_protein": meal_protein,
            "g_carbs": meal_carbs,
            "g_fat": meal_fat,

            "alloc_protein": dpm_alloc["protein"],
            "alloc_carbs": dpm_alloc["carbs"],
            "alloc_fat": dpm_alloc["fat"],
        },
    }


def build_mealfood_table_item(mf):
    food = mf.food

    # ==================================================
    # Freeze MF aggregates (mf ya es “materializado”)
    # ==================================================

    mf_total_kcal = mf.total_kcal
    mf_protein = mf.protein
    mf_carbs = mf.carbs
    mf_fat = mf.fat

    mf_alloc = mf.alloc

    return {
        # entidad principal
        "child": food,

        # RELACIÓN EXPLÍCITA
        "rel": {
            "id": mf.id,
            "quantity": mf.quantity,
            "quantity_unit": "g",

            "name": resolve_food_display_name(food),

            "total_kcal": mf_total_kcal,
            "kcal_share": mf.kcal_share,

            "g_protein": mf_protein,
            "g_carbs": mf_carbs,
            "g_fat": mf_fat,

            "alloc_protein": mf_alloc["protein"],
            "alloc_carbs": mf_alloc["carbs"],
            "alloc_fat": mf_alloc["fat"],
        }
    }