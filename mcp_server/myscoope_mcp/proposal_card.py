"""Allowlisted projection for the MCP proposal card.

The proposal DTO contains profile snapshots and audit data. The card receives
only its identity, status, and the simulated DailyPlan already authorized for
the creating user.
"""

from __future__ import annotations

import math
import re
from typing import Any

_KPI_FIELDS = (
    "total_kcal",
    "protein",
    "carbs",
    "fat",
    "ppk",
    "alloc_protein",
    "alloc_carbs",
    "alloc_fat",
)
_PUBLIC_IMAGE_PATH = re.compile(r"/api/v1/foods/visual-assets/[0-9a-f-]{36}/[0-9a-f]{64}\.png\Z")


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    return number if math.isfinite(number) else None


def _kpis(value: Any) -> dict[str, float | None]:
    source = value if isinstance(value, dict) else {}
    return {name: _number(source.get(name)) for name in _KPI_FIELDS}


def _project_food(food: Any) -> dict[str, Any] | None:
    if not isinstance(food, dict) or not isinstance(food.get("food_name"), str) or not food["food_name"].strip():
        return None
    item = {"food_name": food["food_name"]}
    identifier = food.get("food_id")
    if isinstance(identifier, int) and not isinstance(identifier, bool) and identifier > 0:
        item["food_id"] = identifier
    image_path = food.get("image_path")
    if isinstance(image_path, str) and _PUBLIC_IMAGE_PATH.fullmatch(image_path):
        item["image_path"] = image_path
    quantity = _number(food.get("quantity"))
    if quantity is not None and quantity > 0:
        item["quantity"] = quantity
        item["quantity_unit"] = "ml" if (food.get("unit") or food.get("quantity_unit")) == "ml" else "g"
    for key in ("total_kcal", "protein", "carbs", "fat"):
        value = _number(food.get(key))
        if value is not None:
            item[key] = value
    return item


def _add_aggregate(aggregated_foods: dict, item: dict[str, Any]) -> None:
    unit = item.get("quantity_unit", "g")
    key = (item.get("food_id", item["food_name"].casefold()), unit)
    aggregate = aggregated_foods.setdefault(key, {"food_name": item["food_name"], "quantity_unit": unit})
    for field in ("food_id", "image_path"):
        if field in item:
            aggregate[field] = item[field]
    for field in ("quantity", "total_kcal", "protein", "carbs", "fat"):
        if field in item:
            aggregate[field] = aggregate.get(field, 0.0) + item[field]


def _project_meal(raw_item: Any, aggregated_foods: dict) -> dict[str, Any] | None:
    if not isinstance(raw_item, dict):
        return None
    meal = raw_item.get("meal")
    if not isinstance(meal, dict):
        return None
    name = meal.get("name")
    raw_foods = meal.get("foods")
    if not isinstance(name, str) or not name.strip() or not isinstance(raw_foods, list):
        return None
    foods = []
    for raw_food in raw_foods:
        item = _project_food(raw_food)
        if item is not None:
            foods.append(item)
            _add_aggregate(aggregated_foods, item)
    hour = raw_item.get("hour")
    return {
        "meal_name": name,
        "hour": hour if isinstance(hour, str) else None,
        "kpis": _kpis(meal.get("kpis")),
        "foods": foods,
    }


def build_proposal_card_data(proposal: Any) -> dict[str, Any] | None:
    """Return only fields needed by the existing DailyPlan card renderer."""
    if not isinstance(proposal, dict):
        return None
    proposal_id = proposal.get("id")
    if isinstance(proposal_id, bool) or not isinstance(proposal_id, int) or proposal_id < 1:
        return None
    if proposal.get("status") != "pending_review":
        return None
    validation = proposal.get("validation_summary")
    simulation = validation.get("simulation") if isinstance(validation, dict) else None
    dailyplan = simulation.get("dailyplan") if isinstance(simulation, dict) else None
    if not isinstance(dailyplan, dict) or not isinstance(dailyplan.get("name"), str):
        return None
    raw_meals = dailyplan.get("meals")
    if not isinstance(raw_meals, list) or not raw_meals:
        return None
    plan_kpis = dailyplan.get("kpis")
    if not isinstance(plan_kpis, dict) or _number(plan_kpis.get("total_kcal")) is None:
        return None

    meals: list[dict[str, Any]] = []
    aggregated_foods: dict[tuple[Any, str], dict[str, Any]] = {}
    for raw_item in raw_meals:
        meal = _project_meal(raw_item, aggregated_foods)
        if meal is None:
            return None
        meals.append(meal)

    return {
        "proposal_card": {
            "id": proposal_id,
            "title": "Minuta diaria para revisión",
            "status": "pending_review",
            "status_label": "Pendiente de revisión",
            "summary": "Revisa las comidas y los valores nutricionales antes de aprobar en My Scoope.",
        },
        "dailyplan": {
            "id": 0,  # A proposal is not a final DailyPlan.
            "name": dailyplan["name"],
            "meals_count": len(meals),
            "foods_count": len(aggregated_foods),
            "kpis": _kpis(dailyplan.get("kpis")),
            "meals": meals,
            "foods_aggregation": list(aggregated_foods.values()),
        },
    }
