from django.db.models import Count, Prefetch, Q

from mobile_api import library_projections
from mobile_api.selectors import _empty_library_panel, _food_panel_item, _library_nutrition_payload
from notas.application.services.nutrition.weight import get_current_weight
from notas.domain.models import Meal, MealCatalogEntry


def _explore_meal_item_payload(entry, *, current_weight, saved_source_ids) -> dict:
    meal = entry.meal
    return {
        "id": meal.id,
        "catalog_id": entry.id,
        "entity": "meal",
        "name": meal.name,
        "subtitle": entry.summary,
        "summary": entry.summary,
        "occasion": entry.occasion,
        "occasion_label": entry.get_occasion_display(),
        "dietary_style": entry.dietary_style,
        "dietary_style_label": entry.get_dietary_style_display(),
        "is_saved": meal.id in saved_source_ids,
        "nutrition": _library_nutrition_payload(meal, current_weight),
        "indicators": [
            {"label": "ocasión", "value": entry.get_occasion_display()},
            {"label": "estilo", "value": entry.get_dietary_style_display()},
            {"icon": "food", "label": "alimentos", "value": entry.library_food_count},
        ],
        "panel": {
            **_empty_library_panel("foods"),
            "foods": [_food_panel_item(meal_food, current_weight) for meal_food in meal.meal_food_set.all()],
        },
        "creator": "My Scoope",
        "created_at": entry.created_at,
        "is_draft": False,
        "can_calendarize": False,
        "actions": [],
    }


def _published_meal_catalog_queryset():
    return (
        MealCatalogEntry.objects.filter(
            is_published=True,
            meal__is_draft=False,
            meal__scope=Meal.Scope.LIBRARY,
        )
        .select_related("meal", "meal__created_by")
        .annotate(library_food_count=Count("meal__meal_food_set", distinct=True))
        .prefetch_related(
            Prefetch("meal__meal_food_set", queryset=library_projections.meal_foods_for_library_projection())
        )
        .order_by("sort_order", "meal__name", "id")
    )


def explore_meals_payload(
    user,
    *,
    search=None,
    occasion=None,
    dietary_style=None,
    offset=0,
    limit=30,
) -> dict:
    queryset = _published_meal_catalog_queryset()
    normalized_search = (search or "").strip()[:100] or None
    if normalized_search:
        queryset = queryset.filter(Q(meal__name__icontains=normalized_search) | Q(summary__icontains=normalized_search))
    if occasion in MealCatalogEntry.Occasion.values:
        queryset = queryset.filter(occasion=occasion)
    if dietary_style in MealCatalogEntry.DietaryStyle.values:
        queryset = queryset.filter(dietary_style=dietary_style)

    safe_offset = max(int(offset or 0), 0)
    safe_limit = min(max(int(limit or 30), 1), 100)
    total = queryset.count()
    entries = list(queryset[safe_offset : safe_offset + safe_limit])
    source_ids = [entry.meal_id for entry in entries]
    saved_source_ids = set(
        Meal.objects.filter(
            created_by=user,
            scope=Meal.Scope.LIBRARY,
            forked_from_id__in=source_ids,
        ).values_list("forked_from_id", flat=True)
    )
    current_weight = get_current_weight(user)
    return {
        "items": [
            _explore_meal_item_payload(entry, current_weight=current_weight, saved_source_ids=saved_source_ids)
            for entry in entries
        ],
        "total": total,
        "offset": safe_offset,
        "limit": safe_limit,
        "search": normalized_search,
    }


def explore_meal_detail_payload(user, catalog_id: int) -> dict | None:
    entry = _published_meal_catalog_queryset().filter(pk=catalog_id).first()
    if entry is None:
        return None
    saved_source_ids = set(
        Meal.objects.filter(
            created_by=user,
            scope=Meal.Scope.LIBRARY,
            forked_from_id=entry.meal_id,
        ).values_list("forked_from_id", flat=True)
    )
    return _explore_meal_item_payload(
        entry,
        current_weight=get_current_weight(user),
        saved_source_ids=saved_source_ids,
    )
