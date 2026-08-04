from notas.application.dto.meal_dto import (
    MealDTO,
    MealFoodDTO,
    MealKpiDTO,
    MealListItemDTO,
)
from notas.application.queries.read_boundaries import (
    get_owned_meal_queryset,
    get_readable_meal_or_404,
    get_readable_meal_queryset,
)
from notas.application.services.food_imports.localized_names import (
    resolve_food_display_name,
)
from notas.application.services.nutrition.nutrition_kpis import get_ppk_meal
from notas.domain.models import Meal


def _cached_or_computed(value, fallback):
    return value if value is not None else fallback


def build_meal_kpi_dto(meal: Meal, user) -> MealKpiDTO:
    meal_alloc = {
        "protein": _cached_or_computed(
            meal.alloc_protein_cached,
            meal.alloc["protein"],
        ),
        "carbs": _cached_or_computed(
            meal.alloc_carbs_cached,
            meal.alloc["carbs"],
        ),
        "fat": _cached_or_computed(
            meal.alloc_fat_cached,
            meal.alloc["fat"],
        ),
    }

    ppk_data = get_ppk_meal(meal, user)
    ppk_value = ppk_data.get("ppk") or 0

    return MealKpiDTO(
        ppk=float(ppk_value),
        total_kcal=float(
            _cached_or_computed(
                meal.total_kcal_cached,
                meal.total_kcal,
            )
        ),
        protein=float(
            _cached_or_computed(
                meal.protein_cached,
                meal.protein,
            )
        ),
        carbs=float(
            _cached_or_computed(
                meal.carbs_cached,
                meal.carbs,
            )
        ),
        fat=float(
            _cached_or_computed(
                meal.fat_cached,
                meal.fat,
            )
        ),
        kcal_protein=float(
            _cached_or_computed(
                meal.kcal_protein_cached,
                meal.kcal_protein,
            )
        ),
        kcal_carbs=float(
            _cached_or_computed(
                meal.kcal_carbs_cached,
                meal.kcal_carbs,
            )
        ),
        kcal_fat=float(
            _cached_or_computed(
                meal.kcal_fat_cached,
                meal.kcal_fat,
            )
        ),
        alloc_protein=float(meal_alloc["protein"]),
        alloc_carbs=float(meal_alloc["carbs"]),
        alloc_fat=float(meal_alloc["fat"]),
    )


def build_meal_food_dto(meal_food) -> MealFoodDTO:
    food = meal_food.food
    quantity = float(meal_food.quantity)
    factor = quantity / 100.0

    food_alloc = food.alloc

    protein = float(food.protein) * factor
    carbs = float(food.carbs) * factor
    fat = float(food.fat) * factor

    kcal_protein = protein * 4
    kcal_carbs = carbs * 4
    kcal_fat = fat * 9
    total_kcal = kcal_protein + kcal_carbs + kcal_fat

    return MealFoodDTO(
        mealfood_id=meal_food.id,
        food_id=food.id,
        food_name=resolve_food_display_name(food),
        quantity=quantity,
        protein=protein,
        carbs=carbs,
        fat=fat,
        total_kcal=total_kcal,
        kcal_protein=kcal_protein,
        kcal_carbs=kcal_carbs,
        kcal_fat=kcal_fat,
        alloc_protein=float(food_alloc["protein"]),
        alloc_carbs=float(food_alloc["carbs"]),
        alloc_fat=float(food_alloc["fat"]),
    )


def build_meal_list_item_dto(meal: Meal, user) -> MealListItemDTO:
    foods_count = meal.meal_food_set.count()

    return MealListItemDTO(
        id=meal.id,
        name=meal.name,
        category=meal.category,
        created_by_id=meal.created_by_id,
        original_author_id=meal.original_author_id,
        foods_count=foods_count,
        is_public=meal.is_public,
        is_forkable=meal.is_forkable,
        is_copiable=meal.is_copiable,
        is_draft=meal.is_draft,
        kpis=build_meal_kpi_dto(meal, user),
    )


def build_meal_dto(meal: Meal, user) -> MealDTO:
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

    return MealDTO(
        id=meal.id,
        name=meal.name,
        category=meal.category,
        created_by_id=meal.created_by_id,
        original_author_id=meal.original_author_id,
        foods_count=len(foods),
        is_public=meal.is_public,
        is_forkable=meal.is_forkable,
        is_copiable=meal.is_copiable,
        is_draft=meal.is_draft,
        kpis=build_meal_kpi_dto(meal, user),
        foods=foods,
    )


def get_available_meal_queryset(user):
    """
    Alias de compatibilidad para el boundary explícito de lectura.
    Mantiene el contrato público existente de meal_queries.
    """
    return get_readable_meal_queryset(user)


def list_user_meals(user) -> list[MealListItemDTO]:
    meals = (
        get_owned_meal_queryset(user)
        .prefetch_related("meal_food_set")
    )

    return [
        build_meal_list_item_dto(meal, user)
        for meal in meals
    ]


def list_available_meals(user) -> list[MealListItemDTO]:
    meals = (
        get_available_meal_queryset(user)
        .prefetch_related("meal_food_set")
    )

    return [
        build_meal_list_item_dto(meal, user)
        for meal in meals
    ]


def search_meals(user, query: str) -> list[MealListItemDTO]:
    clean_query = (query or "").strip()

    meals = get_available_meal_queryset(user)

    if clean_query:
        meals = meals.filter(
            name__icontains=clean_query,
        )

    meals = meals.prefetch_related("meal_food_set")

    return [
        build_meal_list_item_dto(meal, user)
        for meal in meals
    ]


def get_meal_detail(user, meal_id: int) -> MealDTO:
    meal = get_readable_meal_or_404(
        user,
        meal_id,
    )

    meal = (
        Meal.objects
        .prefetch_related(
            "meal_food_set__food",
        )
        .get(pk=meal.id)
    )

    return build_meal_dto(
        meal,
        user,
    )