from django.db.models import Prefetch

from notas.application.queries.calendarization_projection_queries import snapshot_nutrition_totals
from notas.domain.models import FoodLocalizedName, MealFood
from notas.domain.services.nutrition import macro_kcal_distribution


def _number(value) -> float:
    return round(float(value or 0), 1)


def _percentage(part, total) -> float:
    if not total or float(total) <= 0:
        return 0.0
    return float(part or 0) / float(total) * 100


def _distribution(protein_kcal, carbs_kcal, fat_kcal) -> dict:
    return {
        key: _number(value)
        for key, value in macro_kcal_distribution(protein_kcal, carbs_kcal, fat_kcal).items()
    }


def meal_foods_for_library_projection():
    primary_names = FoodLocalizedName.objects.filter(
        language="es", country__in=["CL", ""], is_primary=True
    ).order_by("country", "name")
    return (
        MealFood.objects.select_related("food")
        .prefetch_related(
            Prefetch(
                "food__localized_names",
                queryset=primary_names,
                to_attr="_prefetched_primary_display_names",
            )
        )
        .order_by("order", "id")
    )


def snapshot_nutrition_payload(snapshot, current_weight=None) -> dict:
    totals = snapshot_nutrition_totals(snapshot)
    protein = _number(totals["protein"])
    return {
        "calories": _number(totals["total_kcal"]),
        "protein": {
            "grams": protein,
            "allocation": _number(totals["alloc"]["protein"]),
            "per_kilogram": _number(protein / current_weight) if current_weight and protein else None,
        },
        "carbs": {
            "grams": _number(totals["carbs"]),
            "allocation": _number(totals["alloc"]["carbs"]),
        },
        "fat": {
            "grams": _number(totals["fat"]),
            "allocation": _number(totals["alloc"]["fat"]),
        },
    }


def prepare_program_card_summary(program) -> dict:
    summary = program.summary_cache or {}
    if summary.get("weeks") is not None and summary.get("program_totals") is not None:
        return summary

    def empty_totals():
        return {
            "total_kcal": 0,
            "protein": 0,
            "carbs": 0,
            "fat": 0,
            "kcal_protein": 0,
            "kcal_carbs": 0,
            "kcal_fat": 0,
            "alloc": {"protein": 0, "carbs": 0, "fat": 0},
        }

    slots = {
        (item.week_number, item.day_number): item
        for item in getattr(program, "_card_program_days", ())
    }
    weeks = []
    for week_number in range(1, program.normalized_duration_weeks + 1):
        week_totals = empty_totals()
        days = []
        filled_days_count = 0
        for day_number, label in enumerate(("Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"), start=1):
            slot = slots.get((week_number, day_number))
            dailyplan = slot.dailyplan if slot else None
            snapshot = (dailyplan.summary_cache or {}).get("totals") if dailyplan else None
            if snapshot:
                for key in ("total_kcal", "protein", "carbs", "fat"):
                    week_totals[key] += float(snapshot.get(key) or 0)
                for macro, factor in (("protein", 4), ("carbs", 4), ("fat", 9)):
                    week_totals[f"kcal_{macro}"] += float(
                        snapshot.get(f"kcal_{macro}") or float(snapshot.get(macro) or 0) * factor
                    )
            if slot:
                filled_days_count += 1
            days.append(
                {
                    "day_number": day_number,
                    "day_label": label,
                    "program_day": {"id": slot.id} if slot else None,
                    "dailyplan": {"id": dailyplan.id, "name": dailyplan.name} if dailyplan else None,
                    "snapshot": snapshot,
                }
            )
        total_kcal = week_totals["total_kcal"]
        week_totals["alloc"] = {
            key: _percentage(week_totals[f"kcal_{key}"], total_kcal)
            for key in ("protein", "carbs", "fat")
        }
        weeks.append(
            {
                "week_number": week_number,
                "days": days,
                "totals": week_totals,
                "averages": {key: value / 7 if key != "alloc" else value for key, value in week_totals.items()},
                "filled_days_count": filled_days_count,
                "meals_count": 0,
                "foods_count": 0,
            }
        )
    program_totals = {**empty_totals(), **(summary.get("program_totals") or {})}
    if not program_totals.get("total_kcal"):
        program_totals["total_kcal"] = sum(
            float(program_totals.get(key) or 0) for key in ("kcal_protein", "kcal_carbs", "kcal_fat")
        )
    summary = {
        "weeks": weeks,
        "program_totals": program_totals,
        "program_foods_count": summary.get("program_foods_count", 0),
    }
    program.summary_cache = summary
    return summary


def program_card_week_panel_items(program, current_weight=None) -> list[dict]:
    """Build card charts from cached summaries without hydrating composition rows."""
    summary = prepare_program_card_summary(program)
    program_totals = summary["program_totals"]
    program_total_kcal = program_totals["total_kcal"]

    def day_item(week_number, day):
        snapshot = day.get("snapshot")
        dailyplan = day.get("dailyplan") or {}
        program_day = day.get("program_day") or {}
        nutrition = None
        if snapshot:
            protein = _number(snapshot["protein"])
            nutrition = {
                "calories": _number(snapshot["total_kcal"]),
                "protein": {
                    "grams": protein,
                    "allocation": _number(snapshot["alloc"]["protein"]),
                    "per_kilogram": (
                        _number(protein / current_weight) if current_weight and protein else None
                    ),
                },
                "carbs": {
                    "grams": _number(snapshot["carbs"]),
                    "allocation": _number(snapshot["alloc"]["carbs"]),
                },
                "fat": {
                    "grams": _number(snapshot["fat"]),
                    "allocation": _number(snapshot["alloc"]["fat"]),
                },
            }
        return {
            "id": f"program-card-week:{program.id}:{week_number}:day:{day['day_number']}",
            "program_day_id": program_day.get("id"),
            "day_number": day["day_number"],
            "day_label": day["day_label"],
            "dailyplan_id": dailyplan.get("id"),
            "plan_name": dailyplan.get("name"),
            "nutrition": nutrition,
            "meals": [],
        }

    return [
        {
            "id": f"program-card-week:{program.id}:{week['week_number']}",
            "week_number": week["week_number"],
            "days": [day_item(week["week_number"], day) for day in week["days"]],
            "filled_days_count": week["filled_days_count"],
            "meals_count": week["meals_count"],
            "foods_count": week["foods_count"],
            "average_calories": _number(week["averages"]["total_kcal"]),
            "foods": [],
            "calories": _number(week["totals"]["total_kcal"]),
            "calorie_share": _number(_percentage(week["totals"]["total_kcal"], program_total_kcal)),
            "calorie_distribution": _distribution(
                week["totals"]["kcal_protein"], week["totals"]["kcal_carbs"], week["totals"]["kcal_fat"]
            ),
            "protein_grams": _number(week["totals"]["protein"]),
            "carbs_grams": _number(week["totals"]["carbs"]),
            "fat_grams": _number(week["totals"]["fat"]),
            "protein_allocation": _number(
                _percentage(week["totals"]["kcal_protein"], program_totals["kcal_protein"])
            ),
            "carbs_allocation": _number(
                _percentage(week["totals"]["kcal_carbs"], program_totals["kcal_carbs"])
            ),
            "fat_allocation": _number(
                _percentage(week["totals"]["kcal_fat"], program_totals["kcal_fat"])
            ),
        }
        for week in summary["weeks"]
    ]
