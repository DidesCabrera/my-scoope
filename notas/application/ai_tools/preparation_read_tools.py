"""Visible operational preparations, distinct from foods and catalog authority."""

from django.db.models import Q

from notas.application.ai_tools.runtime import run_ai_tool
from notas.application.services.commands.personal_preparation_commands import can_use_personal_preparations
from notas.domain.models import Meal, Preparation


def query_preparations_tool(user, *, object_id=None, search="", limit=20, offset=0):
    return run_ai_tool(
        _query_preparations, user, object_id=object_id, search=search,
        limit=limit, offset=offset, user=user,
    )


def query_meal_preparations_tool(user, *, meal_id):
    return run_ai_tool(_meal_preparations, user, meal_id=meal_id, user=user)


def _meal_preparations(user, *, meal_id):
    meal = Meal.objects.filter(pk=meal_id, created_by=user).first()
    if meal is None:
        raise ValueError("meal_not_found")
    return {
        "resource": "meal_preparations", "meal_id": meal.id,
        "items": [
            {
                "relation_id": row.id, "preparation_id": row.preparation_id,
                "name": row.preparation.name, "version": row.version.version,
                "grams": str(row.quantity_g), "units": str(row.selected_units) if row.selected_units else None,
                "selection_mode": row.selection_mode,
            }
            for row in meal.meal_preparation_set.select_related("preparation", "version").all()
        ],
    }


def _query_preparations(user, *, object_id, search, limit, offset):
    personal_access = can_use_personal_preparations(user)
    visible = Q(is_global=True, is_active=True, current_version__isnull=False)
    if personal_access:
        visible |= Q(is_global=False, created_by=user, is_active=True)
    queryset = Preparation.objects.select_related("current_version").filter(visible)
    if object_id is not None:
        row = queryset.filter(pk=object_id).first()
        if row is None:
            raise ValueError("preparation_not_found")
        return {"resource": "preparations", "item": _item(row, detail=True)}
    if search:
        queryset = queryset.filter(name__icontains=search)
    limit = max(1, min(int(limit), 50))
    offset = max(0, int(offset))
    queryset = queryset.order_by("name", "id")
    total = queryset.count()
    items = [_item(row) for row in queryset[offset:offset + limit]]
    returned = len(items)
    return {
        "resource": "preparations", "scope": "library", "items": items,
        "total_count": total, "count_for_user_questions": total,
        "returned_count": returned, "offset": offset,
        "has_more": offset + returned < total,
        "next_offset": offset + returned if offset + returned < total else None,
    }


def _item(row, *, detail=False):
    version = row.current_version
    item = {
        "id": row.id, "name": row.name, "is_personal": not row.is_global,
        "is_draft": version is None, "version": version.version if version else None,
    }
    if detail and version:
        item.update({
            "yield_g": str(version.yield_g),
            "default_portion_g": str(version.default_portion_g),
            "household_label": version.household_label,
            "recipe_nutrition": {
                "protein_g": str(version.protein_g), "carbs_g": str(version.carbs_g),
                "fat_g": str(version.fat_g),
                "sodium_mg": str(version.sodium_mg) if version.sodium_mg is not None else None,
            },
            "allergens": version.allergens,
            "allergen_status": version.allergen_status,
            "evidence": version.evidence,
            "ingredients": version.ingredients_snapshot,
            "default_portion_nutrition": {
                "protein_g": str(version.protein_g * version.default_portion_g / version.yield_g),
                "carbs_g": str(version.carbs_g * version.default_portion_g / version.yield_g),
                "fat_g": str(version.fat_g * version.default_portion_g / version.yield_g),
                "sodium_mg": str(version.sodium_mg * version.default_portion_g / version.yield_g) if version.sodium_mg is not None else None,
            },
            "nutrition_basis": "recipe_nutrition is full recipe; default_portion_nutrition is one default serving",
        })
    return item
