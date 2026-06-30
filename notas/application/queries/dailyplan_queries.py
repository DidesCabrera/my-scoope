from notas.application.queries.read_boundaries import (
    get_owned_dailyplan_queryset,
    get_readable_dailyplan_or_404,
    get_readable_dailyplan_queryset,
)

from notas.application.dto.dailyplan_dto import (
    DailyPlanDTO,
    DailyPlanFoodAggregationDTO,
    DailyPlanKpiDTO,
    DailyPlanListItemDTO,
    DailyPlanMealDTO,
)
from notas.application.queries.meal_queries import (
    build_meal_food_dto,
    build_meal_kpi_dto,
)

from notas.application.services.nutrition.nutrition_kpis import get_ppk_dailyplan
from notas.domain.models import DailyPlan

from notas.application.services.food_imports.localized_names import (
    resolve_food_display_name,
)


def _cached_or_computed(value, fallback):
    return value if value is not None else fallback


def build_dailyplan_kpi_dto(dailyplan: DailyPlan, user) -> DailyPlanKpiDTO:
    alloc = dailyplan.alloc

    ppk_data = get_ppk_dailyplan(dailyplan, user)
    ppk_value = ppk_data.get("ppk") or 0

    return DailyPlanKpiDTO(
        ppk=float(ppk_value),
        total_kcal=float(dailyplan.total_kcal),
        protein=float(dailyplan.protein),
        carbs=float(dailyplan.carbs),
        fat=float(dailyplan.fat),
        kcal_protein=float(dailyplan.kcal_protein),
        kcal_carbs=float(dailyplan.kcal_carbs),
        kcal_fat=float(dailyplan.kcal_fat),
        alloc_protein=float(alloc["protein"]),
        alloc_carbs=float(alloc["carbs"]),
        alloc_fat=float(alloc["fat"]),
    )


def build_dailyplan_meal_dto(dailyplan_meal, user) -> DailyPlanMealDTO:
    meal = dailyplan_meal.meal

    meal_foods = (
        meal.meal_food_set
        .select_related("food")
        .all()
        .order_by("order", "id")
    )

    foods = [
        build_meal_food_dto(meal_food)
        for meal_food in meal_foods
    ]

    return DailyPlanMealDTO(
        dailyplanmeal_id=dailyplan_meal.id,
        meal_id=meal.id,
        meal_name=meal.name,
        hour=str(dailyplan_meal.hour) if dailyplan_meal.hour else None,
        note=dailyplan_meal.note,
        order=dailyplan_meal.order or 0,
        foods_count=len(foods),
        kpis=build_meal_kpi_dto(meal, user),
        foods=foods,
    )


def build_dailyplan_foods_aggregation_dto(
    dailyplan_meals,
) -> list[DailyPlanFoodAggregationDTO]:
    aggregation = {}

    for dailyplan_meal in dailyplan_meals:
        meal = dailyplan_meal.meal

        meal_foods = (
            meal.meal_food_set
            .select_related("food")
            .all()
        )

        for meal_food in meal_foods:
            food = meal_food.food
            quantity = float(meal_food.quantity)
            factor = quantity / 100.0

            if food.id not in aggregation:
                aggregation[food.id] = {
                    "food_id": food.id,
                    "food_name": resolve_food_display_name(food),
                    "quantity": 0.0,
                    "protein": 0.0,
                    "carbs": 0.0,
                    "fat": 0.0,
                }

            aggregation[food.id]["quantity"] += quantity
            aggregation[food.id]["protein"] += float(food.protein) * factor
            aggregation[food.id]["carbs"] += float(food.carbs) * factor
            aggregation[food.id]["fat"] += float(food.fat) * factor

    result = []

    for item in aggregation.values():
        total_kcal = (
            item["protein"] * 4
            + item["carbs"] * 4
            + item["fat"] * 9
        )

        result.append(
            DailyPlanFoodAggregationDTO(
                food_id=item["food_id"],
                food_name=item["food_name"],
                quantity=item["quantity"],
                protein=item["protein"],
                carbs=item["carbs"],
                fat=item["fat"],
                total_kcal=total_kcal,
            )
        )

    return sorted(
        result,
        key=lambda item: (-item.quantity, item.food_name),
    )


def build_dailyplan_list_item_dto(
    dailyplan: DailyPlan,
    user,
) -> DailyPlanListItemDTO:
    dailyplan_meals = list(
        dailyplan.dailyplan_meals
        .select_related("meal")
        .all()
    )

    foods_aggregation = build_dailyplan_foods_aggregation_dto(
        dailyplan_meals,
    )

    return DailyPlanListItemDTO(
        id=dailyplan.id,
        name=dailyplan.name,
        category=dailyplan.category,
        created_by_id=dailyplan.created_by_id,
        original_author_id=dailyplan.original_author_id,
        meals_count=len(dailyplan_meals),
        foods_count=len(foods_aggregation),
        is_public=dailyplan.is_public,
        is_forkable=dailyplan.is_forkable,
        is_copiable=dailyplan.is_copiable,
        is_draft=dailyplan.is_draft,
        kpis=build_dailyplan_kpi_dto(dailyplan, user),
    )


def build_dailyplan_dto(
    dailyplan: DailyPlan,
    user,
) -> DailyPlanDTO:
    dailyplan_meals = list(
        dailyplan.dailyplan_meals
        .select_related("meal")
        .prefetch_related("meal__meal_food_set__food")
        .all()
        .order_by("order", "id")
    )

    meals = [
        build_dailyplan_meal_dto(dailyplan_meal, user)
        for dailyplan_meal in dailyplan_meals
    ]

    foods_aggregation = build_dailyplan_foods_aggregation_dto(
        dailyplan_meals,
    )

    return DailyPlanDTO(
        id=dailyplan.id,
        name=dailyplan.name,
        category=dailyplan.category,
        created_by_id=dailyplan.created_by_id,
        original_author_id=dailyplan.original_author_id,
        meals_count=len(meals),
        foods_count=len(foods_aggregation),
        is_public=dailyplan.is_public,
        is_forkable=dailyplan.is_forkable,
        is_copiable=dailyplan.is_copiable,
        is_draft=dailyplan.is_draft,
        kpis=build_dailyplan_kpi_dto(dailyplan, user),
        meals=meals,
        foods_aggregation=foods_aggregation,
    )


def get_available_dailyplan_queryset(user):
    """
    Alias de compatibilidad para el boundary explícito de lectura.
    Mantiene el contrato público existente de dailyplan_queries.
    """
    return get_readable_dailyplan_queryset(user)



def list_user_dailyplans(user) -> list[DailyPlanListItemDTO]:
    dailyplans = (
        get_owned_dailyplan_queryset(user)
        .prefetch_related("dailyplan_meals__meal")
    )

    return [
        build_dailyplan_list_item_dto(dailyplan, user)
        for dailyplan in dailyplans
    ]


def list_available_dailyplans(user) -> list[DailyPlanListItemDTO]:
    dailyplans = (
        get_available_dailyplan_queryset(user)
        .prefetch_related("dailyplan_meals__meal")
    )

    return [
        build_dailyplan_list_item_dto(dailyplan, user)
        for dailyplan in dailyplans
    ]


def search_dailyplans(user, query: str) -> list[DailyPlanListItemDTO]:
    clean_query = (query or "").strip()

    dailyplans = get_available_dailyplan_queryset(user)

    if clean_query:
        dailyplans = dailyplans.filter(
            name__icontains=clean_query,
        )

    dailyplans = dailyplans.prefetch_related("dailyplan_meals__meal")

    return [
        build_dailyplan_list_item_dto(dailyplan, user)
        for dailyplan in dailyplans
    ]


def get_dailyplan_detail(user, dailyplan_id: int) -> DailyPlanDTO:
    dailyplan = get_readable_dailyplan_or_404(
        user,
        dailyplan_id,
    )

    dailyplan = (
        DailyPlan.objects
        .prefetch_related(
            "dailyplan_meals__meal__meal_food_set__food",
        )
        .get(pk=dailyplan.id)
    )

    return build_dailyplan_dto(
        dailyplan,
        user,
    )