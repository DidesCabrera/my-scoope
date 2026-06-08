from django.db.models import Prefetch, Sum, F, ExpressionWrapper, FloatField

from notas.domain.models import (
    DailyPlan,
    DailyPlanMeal,
    FoodLocalizedName,
    MealFood,
)
from notas.domain.constants.nutrition import (
    PROTEIN_KCAL_PER_GRAM,
    CARBS_KCAL_PER_GRAM,
    FAT_KCAL_PER_GRAM,
)


def primary_display_names_queryset():
    return (
        FoodLocalizedName.objects
        .filter(
            language="es",
            country__in=["CL", ""],
            is_primary=True,
        )
        .order_by("country", "name")
    )


def meal_foods_with_display_names():
    return (
        MealFood.objects
        .select_related("food")
        .prefetch_related(
            Prefetch(
                "food__localized_names",
                queryset=primary_display_names_queryset(),
                to_attr="_prefetched_primary_display_names",
            )
        )
        .order_by("order", "id")
    )


def dailyplan_meals_with_display_names():
    return (
        DailyPlanMeal.objects
        .select_related(
            "dailyplan",
            "meal",
            "meal__created_by",
            "meal__original_author",
            "meal__forked_from",
        )
        .prefetch_related(
            Prefetch(
                "meal__meal_food_set",
                queryset=meal_foods_with_display_names(),
            )
        )
        .order_by("order", "id")
    )


def get_dailyplan_meals_with_foods(dailyplan):
    prefetched = getattr(dailyplan, "_prefetched_objects_cache", {}).get(
        "dailyplan_meals"
    )

    if prefetched is not None:
        return list(prefetched)

    return list(
        dailyplan.dailyplan_meals
        .select_related(
            "dailyplan",
            "meal",
            "meal__created_by",
            "meal__original_author",
            "meal__forked_from",
        )
        .prefetch_related(
            Prefetch(
                "meal__meal_food_set",
                queryset=meal_foods_with_display_names(),
            )
        )
        .order_by("order", "id")
    )


def dailyplans_with_kcal():
    return (
        DailyPlan.objects
        .select_related("created_by", "original_author", "forked_from")
        .prefetch_related(
            "shares",
            Prefetch(
                "dailyplan_meals",
                queryset=dailyplan_meals_with_display_names(),
            ),
        )
        .annotate(
            total_kcal_sql=Sum(
                ExpressionWrapper(
                    (F("dailyplan_meals__meal__meal_food_set__quantity") / 100.0) * (
                        F("dailyplan_meals__meal__meal_food_set__food__protein") * PROTEIN_KCAL_PER_GRAM +
                        F("dailyplan_meals__meal__meal_food_set__food__carbs")   * CARBS_KCAL_PER_GRAM +
                        F("dailyplan_meals__meal__meal_food_set__food__fat")     * FAT_KCAL_PER_GRAM
                    ),
                    output_field=FloatField(),
                )
            )
        )
    )

def get_dailyplan_for_edit(user, pk):
    return (
        DailyPlan.objects
        .filter(pk=pk, created_by=user)
        .select_related("created_by", "original_author")
        .prefetch_related(
            Prefetch(
                "dailyplan_meals",
                queryset=dailyplan_meals_with_display_names(),
            ),
        )
        .get()
    )

