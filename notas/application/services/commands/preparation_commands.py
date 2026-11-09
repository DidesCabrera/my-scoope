"""Refresh live library caches after a preparation release is materialized."""

from django.db import transaction

from notas.application.services.cache.dailyplan_summary import refresh_dailyplans_for_meal
from notas.application.services.food_catalog_snapshots import materialize_preparation
from notas.application.services.nutrition.meal_nutrition import rebuild_meal_cached_state
from notas.domain.models import Meal, MealPreparation, Preparation


@transaction.atomic
def materialize_preparation_and_refresh(catalog_preparation, *, release_version: str):
    previous = Preparation.objects.filter(catalog_ref=catalog_preparation.catalog_ref).values_list(
        "current_version_id", flat=True
    ).first()
    version = materialize_preparation(catalog_preparation, release_version=release_version)
    if previous and previous != version.pk:
        meal_ids = MealPreparation.objects.filter(preparation=version.preparation).values_list("meal_id", flat=True).distinct()
        for meal in Meal.objects.filter(pk__in=meal_ids).iterator():
            rebuild_meal_cached_state(meal)
            refresh_dailyplans_for_meal(meal)
    return version
