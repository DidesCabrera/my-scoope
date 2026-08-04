from dataclasses import dataclass

from django.db import transaction

from notas.application.services.cache.dailyplan_summary import (
    refresh_dailyplan_and_related_program_caches,
    refresh_dailyplan_summary_cache,
)
from notas.domain.models import DailyPlan, DailyPlanMeal, Meal


@dataclass(frozen=True)
class DailyPlanCreateResult:
    dailyplan: DailyPlan


@dataclass(frozen=True)
class DailyPlanRenameResult:
    dailyplan: DailyPlan


@dataclass(frozen=True)
class DailyPlanDeleteResult:
    dailyplan_id: int


@dataclass(frozen=True)
class DailyPlanConfigureResult:
    dailyplan: DailyPlan


@dataclass(frozen=True)
class DailyPlanMealCreateResult:
    dailyplan: DailyPlan
    dailyplan_meal: DailyPlanMeal
    meal: Meal


@dataclass(frozen=True)
class DailyPlanMealDeleteResult:
    dailyplan: DailyPlan
    dailyplan_meal_id: int
    meal_id: int

@dataclass(frozen=True)
class DailyPlanMealUpdateResult:
    dailyplan_meal: DailyPlanMeal
    dailyplan: DailyPlan
    replaced_meal: bool = False
    old_meal_id: int | None = None
    new_meal_id: int | None = None


@dataclass(frozen=True)
class DailyPlanMealReorderResult:
    dailyplan: DailyPlan
    updated_count: int


@dataclass(frozen=True)
class DailyPlanMealSnapshotReplaceResult:
    dailyplan_meal: DailyPlanMeal
    dailyplan: DailyPlan
    replaced_meal: bool
    old_meal_id: int | None = None
    new_meal_id: int | None = None


@dataclass(frozen=True)
class DailyPlanMealCreateEmptyMealResult:
    dailyplan_meal: DailyPlanMeal
    dailyplan: DailyPlan
    meal: Meal
    old_meal_id: int | None = None


@dataclass(frozen=True)
class DailyPlanPendingMealCreateResult:
    dailyplan: DailyPlan
    meal: Meal


# ==================================================
# DAILYPLAN HELPERS
# ==================================================


def _refresh_dailyplan_cache(dailyplan: DailyPlan) -> None:
    refresh_dailyplan_and_related_program_caches(dailyplan)


def _refresh_new_dailyplan_cache(dailyplan: DailyPlan) -> None:
    refresh_dailyplan_summary_cache(dailyplan)


def get_dailyplan_origin(dp: DailyPlan) -> DailyPlan:
    """
    Retorna el DailyPlan raíz.

    - Si dp es un fork → devuelve el original root
    - Si dp es original → devuelve dp
    """
    return dp.forked_from or dp


def clone_dailyplan_meals(source: DailyPlan, target: DailyPlan) -> None:
    """
    Copia todas las meals desde source hacia target creando snapshots
    independientes para cada slot del DailyPlan.
    """
    from notas.application.services.commands.meal_commands import (
        fork_meal_for_dailyplan,
    )

    prefetched = getattr(source, "_prefetched_objects_cache", {}).get("dailyplan_meals")
    source_meals = (
        sorted(prefetched, key=lambda dpm: (dpm.order, dpm.id))
        if prefetched is not None
        else source.dailyplan_meals.all().order_by("order", "id")
    )

    dailyplan_meals_to_create = []
    for dpm in source_meals:
        forked_meal = fork_meal_for_dailyplan(
            dpm.meal,
            target.created_by,
        )

        dailyplan_meals_to_create.append(DailyPlanMeal(
            dailyplan=target,
            meal=forked_meal,
            note=dpm.note,
            hour=dpm.hour,
            order=dpm.order,
        ))

    if dailyplan_meals_to_create:
        DailyPlanMeal.objects.bulk_create(dailyplan_meals_to_create)

# ==================================================
# DAILYPLAN ACTIONS
# ==================================================


@transaction.atomic
def create_draft_dailyplan(
    *,
    user,
    name: str,
) -> DailyPlanCreateResult:
    clean_name = (name or "").strip()

    if not clean_name:
        raise ValueError("dailyplan_name_required")

    dailyplan = DailyPlan.objects.create(
        name=clean_name,
        created_by=user,
        is_draft=True,
    )

    return DailyPlanCreateResult(
        dailyplan=dailyplan,
    )


@transaction.atomic
def rename_dailyplan(
    *,
    dailyplan: DailyPlan,
    name: str,
) -> DailyPlanRenameResult:
    clean_name = (name or "").strip()

    if not clean_name:
        raise ValueError("dailyplan_name_required")

    dailyplan.name = clean_name
    dailyplan.save(update_fields=["name"])

    return DailyPlanRenameResult(
        dailyplan=dailyplan,
    )


@transaction.atomic
def delete_dailyplan(
    *,
    dailyplan: DailyPlan,
) -> DailyPlanDeleteResult:
    if dailyplan.is_public:
        raise ValueError("dailyplan_is_public")

    dailyplan_id = dailyplan.id
    dailyplan.delete()

    return DailyPlanDeleteResult(
        dailyplan_id=dailyplan_id,
    )


@transaction.atomic
def configure_dailyplan(
    *,
    dailyplan: DailyPlan,
    is_public: bool,
    is_forkable: bool,
    is_copiable: bool,
) -> DailyPlanConfigureResult:
    dailyplan.is_public = is_public
    dailyplan.is_forkable = is_forkable
    dailyplan.is_copiable = is_copiable

    dailyplan.save(
        update_fields=[
            "is_public",
            "is_forkable",
            "is_copiable",
        ]
    )

    return DailyPlanConfigureResult(
        dailyplan=dailyplan,
    )


@transaction.atomic
def fork_dailyplan(original: DailyPlan, user) -> DailyPlan:
    """
    Fork tipo GitHub:
    - forked_from siempre apunta al root original
    - original_author siempre es el creador original
    - snapshot completo de meals
    """

    origin = get_dailyplan_origin(original)

    forked = DailyPlan.objects.create(
        name=f"{original.name}",
        created_by=user,

        forked_from=origin,
        original_author=origin.created_by,

        is_public=False,
        is_forkable=True,
        is_copiable=False,
        is_draft=False,
    )

    clone_dailyplan_meals(original, forked)
    _refresh_new_dailyplan_cache(forked)

    return forked


@transaction.atomic
def copy_dailyplan(original: DailyPlan, user) -> DailyPlan:
    """
    Copy limpio:
    - NO mantiene trazabilidad
    - forked_from = None
    - original_author = None
    """

    copy = DailyPlan.objects.create(
        name=f"{original.name} (copy)",
        created_by=user,

        forked_from=None,
        original_author=None,

        is_public=False,
        is_forkable=True,
        is_copiable=False,
        is_draft=False,
    )

    clone_dailyplan_meals(original, copy)
    _refresh_new_dailyplan_cache(copy)

    return copy


def save_dailyplan(original: DailyPlan, user) -> DailyPlan:
    """
    UX Alias:
    Explore → Guardar = Fork
    Esto permite que en resolvers/UI digas "save"
    pero internamente siempre sea fork.
    """
    return fork_dailyplan(original, user)


@transaction.atomic
def add_existing_meal_to_dailyplan(
    *,
    dailyplan: DailyPlan,
    meal: Meal,
    user,
    hour=None,
    note=None,
) -> DailyPlanMealCreateResult:
    from notas.application.services.commands.meal_commands import (
        fork_meal_for_dailyplan,
    )

    clean_note = (note or "").strip() or None

    forked_meal = fork_meal_for_dailyplan(
        meal,
        user,
    )

    next_order = dailyplan.dailyplan_meals.count() + 1

    dailyplan_meal = DailyPlanMeal.objects.create(
        dailyplan=dailyplan,
        meal=forked_meal,
        hour=hour or None,
        note=clean_note,
        order=next_order,
    )

    dailyplan.update_draft_status()
    _refresh_dailyplan_cache(dailyplan)

    return DailyPlanMealCreateResult(
        dailyplan=dailyplan,
        dailyplan_meal=dailyplan_meal,
        meal=forked_meal,
    )


@transaction.atomic
def remove_dailyplan_meal(
    *,
    dailyplan_meal: DailyPlanMeal,
) -> DailyPlanMealDeleteResult:
    dailyplan = dailyplan_meal.dailyplan
    meal = dailyplan_meal.meal

    dailyplan_meal_id = dailyplan_meal.id
    meal_id = meal.id

    dailyplan_meal.delete()
    meal.delete()
    _refresh_dailyplan_cache(dailyplan)

    return DailyPlanMealDeleteResult(
        dailyplan=dailyplan,
        dailyplan_meal_id=dailyplan_meal_id,
        meal_id=meal_id,
    )


# ==================================================

@transaction.atomic
def update_dailyplan_meal(
    *,
    dailyplan_meal: DailyPlanMeal,
    user,
    meal_id=None,
    hour=None,
    note=None,
) -> DailyPlanMealUpdateResult:
    clean_note = (note or "").strip() or None

    old_meal_id = dailyplan_meal.meal_id
    replaced_meal = False
    new_meal_id = old_meal_id

    dailyplan_meal.hour = hour or None
    dailyplan_meal.note = clean_note
    dailyplan_meal.save(update_fields=["hour", "note"])

    selected_meal_id = int(meal_id) if meal_id else None

    if selected_meal_id and selected_meal_id != old_meal_id:
        source_meal = Meal.objects.get(
            pk=selected_meal_id,
            created_by=user,
        )

        replace_result = replace_dailyplan_meal_snapshot(
            dailyplan_meal=dailyplan_meal,
            source_meal=source_meal,
            user=user,
        )

        replaced_meal = replace_result.replaced_meal
        new_meal_id = replace_result.new_meal_id

    dailyplan = dailyplan_meal.dailyplan
    dailyplan.update_draft_status()
    _refresh_dailyplan_cache(dailyplan)

    return DailyPlanMealUpdateResult(
        dailyplan_meal=dailyplan_meal,
        dailyplan=dailyplan,
        replaced_meal=replaced_meal,
        old_meal_id=old_meal_id,
        new_meal_id=new_meal_id,
    )


@transaction.atomic
def reorder_dailyplan_meals(
    *,
    dailyplan: DailyPlan,
    ordered_ids,
) -> DailyPlanMealReorderResult:
    updated_count = 0

    for index, dailyplan_meal_id in enumerate(ordered_ids, start=1):
        updated = DailyPlanMeal.objects.filter(
            id=dailyplan_meal_id,
            dailyplan=dailyplan,
        ).update(order=index)

        updated_count += updated

    _refresh_dailyplan_cache(dailyplan)

    return DailyPlanMealReorderResult(
        dailyplan=dailyplan,
        updated_count=updated_count,
    )


@transaction.atomic
def replace_dailyplan_meal_snapshot(
    *,
    dailyplan_meal: DailyPlanMeal,
    source_meal: Meal,
    user,
) -> DailyPlanMealSnapshotReplaceResult:
    from notas.application.services.commands.meal_commands import (
        fork_meal_for_dailyplan,
    )

    old_meal = dailyplan_meal.meal
    old_meal_id = old_meal.id

    if source_meal.id == old_meal_id:
        dailyplan = dailyplan_meal.dailyplan
        dailyplan.update_draft_status()
        _refresh_dailyplan_cache(dailyplan)

        return DailyPlanMealSnapshotReplaceResult(
            dailyplan_meal=dailyplan_meal,
            dailyplan=dailyplan,
            replaced_meal=False,
            old_meal_id=old_meal_id,
            new_meal_id=old_meal_id,
        )

    forked_meal = fork_meal_for_dailyplan(
        source_meal,
        user,
    )

    dailyplan_meal.meal = forked_meal
    dailyplan_meal.save(update_fields=["meal"])

    old_meal.delete()

    dailyplan = dailyplan_meal.dailyplan
    dailyplan.update_draft_status()
    _refresh_dailyplan_cache(dailyplan)

    return DailyPlanMealSnapshotReplaceResult(
        dailyplan_meal=dailyplan_meal,
        dailyplan=dailyplan,
        replaced_meal=True,
        old_meal_id=old_meal_id,
        new_meal_id=forked_meal.id,
    )

@transaction.atomic
def create_empty_meal_for_dailyplan_meal(
    *,
    dailyplan_meal: DailyPlanMeal,
    user,
    name: str = "New Meal",
) -> DailyPlanMealCreateEmptyMealResult:
    old_meal = dailyplan_meal.meal
    old_meal_id = old_meal.id if old_meal else None

    new_meal = Meal.objects.create(
        name=name,
        created_by=user,
        is_draft=True,
        is_public=False,
    )

    dailyplan_meal.meal = new_meal
    dailyplan_meal.save(update_fields=["meal"])

    dailyplan = dailyplan_meal.dailyplan
    dailyplan.update_draft_status()
    _refresh_dailyplan_cache(dailyplan)

    return DailyPlanMealCreateEmptyMealResult(
        dailyplan_meal=dailyplan_meal,
        dailyplan=dailyplan,
        meal=new_meal,
        old_meal_id=old_meal_id,
    )

@transaction.atomic
def create_pending_meal_for_dailyplan(
    *,
    dailyplan: DailyPlan,
    user,
    name: str,
) -> DailyPlanPendingMealCreateResult:
    clean_name = (name or "").strip()

    if not clean_name:
        raise ValueError("meal_name_required")

    meal = Meal.objects.create(
        name=clean_name,
        created_by=user,
        is_draft=True,
        pending_dailyplan=dailyplan,
    )

    return DailyPlanPendingMealCreateResult(
        dailyplan=dailyplan,
        meal=meal,
    )

