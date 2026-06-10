from dataclasses import dataclass
from typing import Optional

from django.db import transaction

from notas.domain.models import Meal, MealFood

# ==================================================
# MEAL HELPERS
# ==================================================

def get_meal_origin(meal: Meal) -> Meal:
    """
    Retorna la Meal raíz.
    Si meal es un fork → devuelve su original root.
    """
    return meal.forked_from or meal


def clone_meal_foods(source: Meal, target: Meal) -> None:
    """
    Snapshot completo de foods desde source hacia target.
    """
    MealFood.objects.bulk_create([
        MealFood(
            meal=target,
            food=mf.food,
            quantity=mf.quantity
        )
        for mf in source.meal_food_set.all()
    ])



# ==================================================

@dataclass(frozen=True)
class MealCreateResult:
    meal: Meal


@dataclass(frozen=True)
class MealRenameResult:
    meal: Meal


@dataclass(frozen=True)
class MealDeleteResult:
    meal_id: int


@transaction.atomic
def create_draft_meal(
    *,
    user,
    name: str,
    pending_dailyplan_id: Optional[int] = None,
) -> MealCreateResult:
    clean_name = (name or "").strip()

    if not clean_name:
        raise ValueError("meal_name_required")

    meal = Meal.objects.create(
        name=clean_name,
        created_by=user,
        is_draft=True,
    )

    if pending_dailyplan_id:
        meal.pending_dailyplan_id = pending_dailyplan_id
        meal.save(update_fields=["pending_dailyplan"])

    return MealCreateResult(meal=meal)


@transaction.atomic
def rename_meal(
    *,
    meal: Meal,
    name: str,
) -> MealRenameResult:
    clean_name = (name or "").strip()

    if not clean_name:
        raise ValueError("meal_name_required")

    meal.name = clean_name
    meal.save(update_fields=["name"])

    return MealRenameResult(meal=meal)


@transaction.atomic
def delete_meal(
    *,
    meal: Meal,
) -> MealDeleteResult:
    meal_id = meal.id
    meal.delete()

    return MealDeleteResult(meal_id=meal_id)


@transaction.atomic
def delete_draft_meal(
    *,
    meal: Meal,
) -> MealDeleteResult:
    if not meal.is_draft:
        raise ValueError("meal_is_not_draft")

    meal_id = meal.id
    meal.delete()

    return MealDeleteResult(meal_id=meal_id)




# ==================================================
# MEAL ACTIONS
# ==================================================

@transaction.atomic
def fork_meal(original: Meal, user) -> Meal:
    """
    Fork tipo GitHub:

    - forked_from apunta siempre al root
    - original_author siempre es el creador original
    - snapshot foods
    """

    origin = get_meal_origin(original)

    forked = Meal.objects.create(
        name=f"{original.name}",
        created_by=user,

        forked_from=origin,
        original_author=origin.created_by,

        is_public=False,
        is_forkable=True,
        is_copiable=False,
        is_draft=False,
    )

    clone_meal_foods(original, forked)

    return forked


def _clone_meal(original: Meal, user) -> Meal:
    from notas.application.services.nutrition.meal_nutrition import rebuild_meal_cached_state

    origin = get_meal_origin(original)

    forked = Meal.objects.create(
        name=original.name,
        created_by=user,
        forked_from=origin,
        original_author=origin.created_by,
        is_public=False,
        is_forkable=True,
        is_copiable=False,
        is_draft=False,
    )

    clone_meal_foods(original, forked)
    rebuild_meal_cached_state(forked)

    return forked


def fork_meal_for_library(original: Meal, user) -> Meal:

    forked = _clone_meal(original, user)

    forked.name = f"{original.name} (Copia)"
    forked.save(update_fields=["name"])

    return forked


def fork_meal_for_dailyplan(original: Meal, user) -> Meal:

    forked = _clone_meal(original, user)

    # mismo nombre
    return forked

@transaction.atomic
def copy_meal(original: Meal, user) -> Meal:
    """
    Copy limpio:

    - sin trazabilidad
    - forked_from=None
    - original_author=None
    """

    copy = Meal.objects.create(
        name=f"{original.name} (copy)",
        created_by=user,

        forked_from=None,
        original_author=None,

        is_public=False,
        is_forkable=True,
        is_copiable=False,
        is_draft=False,
    )

    clone_meal_foods(original, copy)

    return copy


def save_meal(original: Meal, user) -> Meal:
    """
    UX Alias:
    Explore / Shared → Guardar = fork para biblioteca personal.

    Mantiene un nombre semántico propio para que la UI, API o MCP
    puedan expresar la intención "guardar en mi biblioteca" sin acoplarse
    al concepto interno de fork.
    """
    return fork_meal_for_library(original, user)


def save_dailyplan_meal_to_library(dailyplan_meal, user) -> Meal:
    """
    Guarda en la biblioteca personal una copia independiente de la Meal
    que vive dentro de un DailyPlanMeal.

    El DPM conserva su Meal interna; la nueva Meal queda libre para usarse
    en otros planes desde Mi librería.
    """
    return fork_meal_for_library(dailyplan_meal.meal, user)



@dataclass(frozen=True)
class FinishMealForDailyPlanResult:
    meal: Meal
    dailyplan_id: int | None
    completed: bool


@dataclass(frozen=True)
class SaveFoodInMealResult:
    meal: Meal
    meal_food: MealFood
    created: bool


@dataclass(frozen=True)
class MealFoodUpdateResult:
    meal: Meal
    meal_food: MealFood


@dataclass(frozen=True)
class MealFoodDeleteResult:
    meal: Meal
    meal_food_id: int


@dataclass(frozen=True)
class MealFoodCreateResult:
    meal: Meal
    meal_food: MealFood


@dataclass(frozen=True)
class MealFoodReorderResult:
    meal: Meal
    updated_count: int



@dataclass(frozen=True)
class ConfigureMealResult:
    meal: Meal
    origin_dailyplan_id: int | None = None
    completed_from_pending_dailyplan: bool = False


@transaction.atomic
def finish_meal_for_pending_dailyplan(
    *,
    meal: Meal,
) -> FinishMealForDailyPlanResult:
    pending_dailyplan = meal.pending_dailyplan

    if not pending_dailyplan:
        return FinishMealForDailyPlanResult(
            meal=meal,
            dailyplan_id=None,
            completed=False,
        )

    dailyplan_id = pending_dailyplan.id

    meal.pending_dailyplan = None
    meal.save(update_fields=["pending_dailyplan"])

    return FinishMealForDailyPlanResult(
        meal=meal,
        dailyplan_id=dailyplan_id,
        completed=True,
    )


@transaction.atomic
def save_food_in_meal(
    *,
    meal: Meal,
    mealfood_id,
    food_id,
    quantity,
) -> SaveFoodInMealResult:
    if mealfood_id:
        meal_food = MealFood.objects.get(
            pk=mealfood_id,
            meal=meal,
        )
        meal_food.quantity = quantity
        meal_food.save(update_fields=["quantity"])

        created = False
    else:
        meal_food = MealFood.objects.create(
            meal=meal,
            food_id=food_id,
            quantity=quantity,
        )

        created = True

    meal = Meal.objects.get(pk=meal.pk)
    meal.update_draft_status()

    return SaveFoodInMealResult(
        meal=meal,
        meal_food=meal_food,
        created=created,
    )

@transaction.atomic
def configure_meal(
    *,
    meal: Meal,
    is_public: bool,
    is_forkable: bool,
    is_copiable: bool,
) -> ConfigureMealResult:
    origin_dailyplan = meal.pending_dailyplan
    origin_dailyplan_id = origin_dailyplan.id if origin_dailyplan else None

    meal.is_public = is_public
    meal.is_forkable = is_forkable
    meal.is_copiable = is_copiable

    update_fields = [
        "is_public",
        "is_forkable",
        "is_copiable",
    ]

    completed_from_pending_dailyplan = False

    if origin_dailyplan:
        meal.pending_dailyplan = None
        update_fields.append("pending_dailyplan")
        completed_from_pending_dailyplan = True

    meal.save(update_fields=update_fields)

    return ConfigureMealResult(
        meal=meal,
        origin_dailyplan_id=origin_dailyplan_id,
        completed_from_pending_dailyplan=completed_from_pending_dailyplan,
    )

@transaction.atomic
def update_meal_food(
    *,
    meal_food: MealFood,
    quantity,
    food_id=None,
) -> MealFoodUpdateResult:
    meal_food.quantity = quantity

    update_fields = ["quantity"]

    if food_id:
        meal_food.food_id = int(food_id)
        update_fields.append("food")

    meal_food.save(update_fields=update_fields)

    meal = meal_food.meal
    meal.update_draft_status()

    return MealFoodUpdateResult(
        meal=meal,
        meal_food=meal_food,
    )


@transaction.atomic
def delete_meal_food(
    *,
    meal_food: MealFood,
) -> MealFoodDeleteResult:
    meal = meal_food.meal
    meal_food_id = meal_food.id

    meal_food.delete()
    meal.update_draft_status()

    return MealFoodDeleteResult(
        meal=meal,
        meal_food_id=meal_food_id,
    )


@transaction.atomic
def create_meal_food(
    *,
    meal: Meal,
    food,
    quantity,
) -> MealFoodCreateResult:
    next_order = meal.meal_food_set.count() + 1

    meal_food = MealFood.objects.create(
        meal=meal,
        food=food,
        quantity=quantity,
        order=next_order,
    )

    meal.update_draft_status()

    return MealFoodCreateResult(
        meal=meal,
        meal_food=meal_food,
    )


@transaction.atomic
def reorder_meal_foods(
    *,
    meal: Meal,
    ordered_ids,
) -> MealFoodReorderResult:
    meal_foods = list(
        MealFood.objects.filter(
            meal=meal,
            id__in=ordered_ids,
        )
    )

    meal_food_by_id = {
        str(meal_food.id): meal_food
        for meal_food in meal_foods
    }

    if len(meal_food_by_id) != len(ordered_ids):
        raise ValueError("invalid_mealfood_ids")

    updated_count = 0

    for index, mealfood_id in enumerate(ordered_ids, start=1):
        meal_food = meal_food_by_id[str(mealfood_id)]
        meal_food.order = index
        meal_food.save(update_fields=["order"])
        updated_count += 1

    return MealFoodReorderResult(
        meal=meal,
        updated_count=updated_count,
    )