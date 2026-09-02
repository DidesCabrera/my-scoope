from __future__ import annotations

from collections import defaultdict
from math import ceil

from notas.domain.services.nutrition import macro_kcal_distribution

DAY_LABELS = (
    (1, "Lun"),
    (2, "Mar"),
    (3, "Mié"),
    (4, "Jue"),
    (5, "Vie"),
    (6, "Sáb"),
    (7, "Dom"),
)


def _number(value) -> float:
    return float(value or 0)


def _percentage(part: float, total: float) -> float:
    return (part / total) * 100 if total > 0 else 0


def _empty_totals() -> dict:
    return {
        "total_kcal": 0.0,
        "protein": 0.0,
        "carbs": 0.0,
        "fat": 0.0,
        "kcal_protein": 0.0,
        "kcal_carbs": 0.0,
        "kcal_fat": 0.0,
        "alloc": {"protein": 0.0, "carbs": 0.0, "fat": 0.0},
    }


def snapshot_nutrition_totals(snapshot: dict | None) -> dict:
    payload = (snapshot or {}).get("totals") or {}
    protein = _number(payload.get("protein_g"))
    carbs = _number(payload.get("carbs_g"))
    fat = _number(payload.get("fat_g"))
    kcal_protein = protein * 4
    kcal_carbs = carbs * 4
    kcal_fat = fat * 9
    calculated_kcal = kcal_protein + kcal_carbs + kcal_fat
    total_kcal = _number(payload.get("total_kcal")) or calculated_kcal
    return {
        "total_kcal": total_kcal,
        "protein": protein,
        "carbs": carbs,
        "fat": fat,
        "kcal_protein": kcal_protein,
        "kcal_carbs": kcal_carbs,
        "kcal_fat": kcal_fat,
        "alloc": {
            "protein": _percentage(kcal_protein, total_kcal),
            "carbs": _percentage(kcal_carbs, total_kcal),
            "fat": _percentage(kcal_fat, total_kcal),
        },
    }


def _add_totals(target: dict, source: dict) -> None:
    for key in (
        "total_kcal",
        "protein",
        "carbs",
        "fat",
        "kcal_protein",
        "kcal_carbs",
        "kcal_fat",
    ):
        target[key] += _number(source.get(key))


def _finalize_totals(totals: dict) -> dict:
    total_kcal = totals["total_kcal"]
    totals["alloc"] = {
        "protein": _percentage(totals["kcal_protein"], total_kcal),
        "carbs": _percentage(totals["kcal_carbs"], total_kcal),
        "fat": _percentage(totals["kcal_fat"], total_kcal),
    }
    return totals


def _average_totals(totals: dict, divisor: int = 7) -> dict:
    averaged = _empty_totals()
    for key in (
        "total_kcal",
        "protein",
        "carbs",
        "fat",
        "kcal_protein",
        "kcal_carbs",
        "kcal_fat",
    ):
        averaged[key] = totals[key] / max(divisor, 1)
    return _finalize_totals(averaged)


def _snapshot_foods(snapshots: list[dict], totals: dict) -> list[dict]:
    aggregation = defaultdict(
        lambda: {
            "name": "",
            "quantity": 0.0,
            "protein": 0.0,
            "carbs": 0.0,
            "fat": 0.0,
            "total_kcal": 0.0,
        }
    )
    for snapshot in snapshots:
        for meal in snapshot.get("meals", []):
            if not isinstance(meal, dict):
                continue
            for food in meal.get("foods", []):
                if not isinstance(food, dict):
                    continue
                name = str(food.get("name") or "Alimento").strip() or "Alimento"
                key = name.casefold()
                row = aggregation[key]
                row["name"] = row["name"] or name
                row["quantity"] += _number(food.get("quantity_g"))
                row["protein"] += _number(food.get("protein_g"))
                row["carbs"] += _number(food.get("carbs_g"))
                row["fat"] += _number(food.get("fat_g"))
                row["total_kcal"] += _number(food.get("total_kcal"))

    rows = []
    for key, food in sorted(
        aggregation.items(),
        key=lambda item: (-item[1]["quantity"], item[1]["name"]),
    ):
        kcal_protein = food["protein"] * 4
        kcal_carbs = food["carbs"] * 4
        kcal_fat = food["fat"] * 9
        total_kcal = food["total_kcal"] or kcal_protein + kcal_carbs + kcal_fat
        rows.append(
            {
                "child": {"id": key},
                "rel": {
                    "id": key,
                    "quantity": food["quantity"],
                    "quantity_unit": "g",
                    "name": food["name"],
                    "total_kcal": total_kcal,
                    "kcal_share": _percentage(total_kcal, totals["total_kcal"]),
                    "kcal_distribution": macro_kcal_distribution(
                        kcal_protein,
                        kcal_carbs,
                        kcal_fat,
                    ),
                    "g_protein": food["protein"],
                    "g_carbs": food["carbs"],
                    "g_fat": food["fat"],
                    "alloc_protein": _percentage(
                        kcal_protein,
                        totals["kcal_protein"],
                    ),
                    "alloc_carbs": _percentage(
                        kcal_carbs,
                        totals["kcal_carbs"],
                    ),
                    "alloc_fat": _percentage(kcal_fat, totals["kcal_fat"]),
                },
            }
        )
    return rows


def build_calendarization_snapshot_projection(calendarization) -> dict:
    days = list(calendarization.days.all())
    slots = {(day.week_number, day.day_number): day for day in days}
    duration_weeks = max(
        1,
        ceil(((calendarization.end_date - calendarization.start_date).days + 1) / 7),
        max((day.week_number for day in days), default=1),
    )
    weeks = []
    program_totals = _empty_totals()
    program_snapshots = []

    for week_number in range(1, duration_weeks + 1):
        week_totals = _empty_totals()
        week_snapshots = []
        week_days = []
        meals_count = 0

        for day_number, day_label in DAY_LABELS:
            day = slots.get((week_number, day_number))
            snapshot = day.plan_snapshot if day and isinstance(day.plan_snapshot, dict) else None
            if snapshot:
                totals = snapshot_nutrition_totals(snapshot)
                _add_totals(week_totals, totals)
                _add_totals(program_totals, totals)
                week_snapshots.append(snapshot)
                program_snapshots.append(snapshot)
                meals_count += sum(
                    1 for meal in snapshot.get("meals", []) if isinstance(meal, dict)
                )
            week_days.append(
                {
                    "calendarized_day_id": day.id if day else None,
                    "calendar_date": day.calendar_date if day else None,
                    "day_number": day_number,
                    "day_label": day_label,
                    "source_program_day_id": day.source_program_day_id if day else None,
                    "source_dailyplan_id": day.source_dailyplan_id if day else None,
                    "plan_name": snapshot.get("name", "") if snapshot else None,
                    "snapshot": snapshot,
                }
            )

        week_totals = _finalize_totals(week_totals)
        foods = _snapshot_foods(week_snapshots, week_totals)
        weeks.append(
            {
                "week_number": week_number,
                "days": week_days,
                "totals": week_totals,
                "averages": _average_totals(week_totals),
                "filled_days_count": len(week_snapshots),
                "meals_count": meals_count,
                "foods_count": len(foods),
                "foods_aggregation_table": foods,
                "foods_panel_id": f"calendarization-week-{calendarization.id}-{week_number}",
            }
        )

    program_totals = _finalize_totals(program_totals)
    program_foods = _snapshot_foods(program_snapshots, program_totals)
    return {
        "duration_weeks": duration_weeks,
        "duration_days": (calendarization.end_date - calendarization.start_date).days + 1,
        "weeks": weeks,
        "program_totals": program_totals,
        "filled_days_count": sum(week["filled_days_count"] for week in weeks),
        "program_meals_count": sum(week["meals_count"] for week in weeks),
        "program_foods_count": len(program_foods),
        "program_foods_aggregation_table": program_foods,
    }
