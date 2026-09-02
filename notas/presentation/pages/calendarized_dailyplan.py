from __future__ import annotations

from dataclasses import asdict

from django.urls import reverse

from notas.application.queries.calendarization_projection_queries import (
    snapshot_food_aggregation_rows,
    snapshot_nutrition_totals,
)
from notas.application.services.nutrition.weight import get_current_weight
from notas.domain.services.nutrition import macro_kcal_distribution
from notas.presentation.pages.calendarized_meal import snapshot_food_table_row
from notas.presentation.resolvers.title_resolvers import resolve_category_badge
from notas.presentation.viewmodels.content.dailyplan.detail_dailyplan_vm import (
    KPIUI,
    ChildCardUI,
    DailyPlanDetailVM,
    DpmRelatedDataUI,
    MainCardUI,
    MetadataUI,
    StructuralIndicatorsUI,
    TitleUI,
)


def _percentage(part: float, total: float) -> float:
    return (part / total) * 100 if total > 0 else 0


def _kpis(totals: dict, current_weight: float | None) -> KPIUI:
    protein = totals["protein"]
    return KPIUI(
        ppk=protein / current_weight if current_weight else 0,
        tot_kcal=totals["total_kcal"],
        g_protein=protein,
        g_carbs=totals["carbs"],
        g_fat=totals["fat"],
        kcal_protein=totals["kcal_protein"],
        kcal_carbs=totals["kcal_carbs"],
        kcal_fat=totals["kcal_fat"],
        alloc_protein=totals["alloc"]["protein"],
        alloc_carbs=totals["alloc"]["carbs"],
        alloc_fat=totals["alloc"]["fat"],
    )


def _meal_table_row(*, day_id: int, meal: dict, plan_totals: dict) -> dict:
    totals = snapshot_nutrition_totals(meal)
    return {
        "main_id": day_id,
        "child_id": meal.get("key", ""),
        "rel": {
            "id": meal.get("key", ""),
            "hour": meal.get("hour"),
            "note": meal.get("note", ""),
            "name": meal.get("name") or "Comida",
            "total_kcal": totals["total_kcal"],
            "kcal_share": _percentage(totals["total_kcal"], plan_totals["total_kcal"]),
            "kcal_distribution": macro_kcal_distribution(
                totals["kcal_protein"],
                totals["kcal_carbs"],
                totals["kcal_fat"],
            ),
            "g_protein": totals["protein"],
            "g_carbs": totals["carbs"],
            "g_fat": totals["fat"],
            "alloc_protein": _percentage(totals["kcal_protein"], plan_totals["kcal_protein"]),
            "alloc_carbs": _percentage(totals["kcal_carbs"], plan_totals["kcal_carbs"]),
            "alloc_fat": _percentage(totals["kcal_fat"], plan_totals["kcal_fat"]),
        },
    }


def build_calendarized_dailyplan_detail(*, day, user, header: dict) -> dict:
    """Project one active-plan snapshot onto the official DailyPlan detail VM."""

    snapshot = day.plan_snapshot or {}
    meals = [item for item in snapshot.get("meals", []) if isinstance(item, dict)]
    plan_totals = snapshot_nutrition_totals(snapshot)
    food_rows = snapshot_food_aggregation_rows([snapshot], plan_totals)
    current_weight = get_current_weight(user)
    owner = str(user)
    metadata = MetadataUI(owner=owner, author=owner, fork_from=None)
    meal_badge = resolve_category_badge("en plan")

    calendarized_meals = []
    child_cards = []
    for index, meal in enumerate(meals, start=1):
        meal_key = meal.get("key") or ""
        meal_totals = snapshot_nutrition_totals(meal)
        foods = [item for item in meal.get("foods", []) if isinstance(item, dict)]
        detail_url = reverse("calendarization_meal_detail", args=[day.id, meal_key]) if meal_key else ""
        calendarized_meals.append(
            {
                "key": meal_key,
                "name": meal.get("name") or "Comida",
                "hour": meal.get("hour"),
                "foods": [item.get("name") or "Alimento" for item in foods],
                "detail_url": detail_url,
            }
        )
        child_cards.append(
            ChildCardUI(
                main_id=day.id,
                child_id=meal_key,
                related_data=DpmRelatedDataUI(
                    rel_id=meal_key,
                    hour=meal.get("hour"),
                    note=meal.get("note", ""),
                    alloc_protein=meal_totals["alloc"]["protein"],
                    alloc_carbs=meal_totals["alloc"]["carbs"],
                    alloc_fat=meal_totals["alloc"]["fat"],
                ),
                titulo=TitleUI(
                    name=meal.get("name") or "Comida",
                    label="Meal",
                    icon="utensils",
                    category="en plan",
                    category_badge=meal_badge,
                    structural_indicators=StructuralIndicatorsUI(
                        foods_count=len(foods),
                        hour=meal.get("hour"),
                    ),
                    url=detail_url,
                ),
                kpis=_kpis(meal_totals, current_weight),
                table={"items": [snapshot_food_table_row(food, meal_totals["total_kcal"]) for food in foods]},
                foods_aggregation=[{"display_name": food.get("name") or "Alimento"} for food in foods],
                metadata=metadata,
                actions=[
                    {
                        "key": "detail",
                        "label": "Ver detalle",
                        "method": "get",
                        "icon": "chevron-right",
                        "desktop_position": "inline",
                        "mobile_position": "inline",
                        "url": detail_url,
                    }
                ]
                if detail_url
                else [],
                id=f"calendarized-meal-{day.id}-{index}",
                hide_overflow_actions=True,
            )
        )

    vm = DailyPlanDetailVM(
        header=header,
        main_card=MainCardUI(
            main_id=day.id,
            titulo=TitleUI(
                name=snapshot.get("name") or "Plan diario",
                label="DailyPlan",
                icon="clipboard-list",
                category="en plan",
                category_badge=meal_badge,
                structural_indicators=StructuralIndicatorsUI(
                    meals_count=len(meals),
                    foods_count=len(food_rows),
                ),
            ),
            kpis=_kpis(plan_totals, current_weight),
            table={"items": [_meal_table_row(day_id=day.id, meal=meal, plan_totals=plan_totals) for meal in meals]},
            menu={"meals": calendarized_meals, "uses_detail_links": True},
            metadata=metadata,
            show_kpis=bool(meals),
            show_table=bool(meals),
        ),
        structural_indicators=StructuralIndicatorsUI(
            meals_count=len(meals),
            foods_count=len(food_rows),
        ),
        foods_aggregation=[{"display_name": row["rel"]["name"]} for row in food_rows],
        foods_aggregation_table=food_rows,
        child_cards=child_cards,
    )
    return {
        **asdict(vm),
        "calendarized_meals": calendarized_meals,
    }
