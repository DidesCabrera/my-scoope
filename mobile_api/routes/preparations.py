"""Read published preparations and serve them as distinct meal components."""

from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.db.models import Q
from ninja import Field, Router, Schema

from mobile_api.api_support import require_scope, success
from mobile_api.auth import mobile_bearer
from mobile_api.errors import MobileAPIError
from mobile_api.preparation_projections import ingredient_payload
from notas.application.services.cache.dailyplan_summary import refresh_dailyplans_for_meal
from notas.application.services.nutrition.meal_nutrition import rebuild_meal_cached_state
from notas.application.services.oauth_device_sessions import MOBILE_SCOPE_WRITE
from notas.domain.models import Meal, MealPreparation, Preparation

router = Router()


class PreparationSelection(Schema):
    preparation_id: int = Field(gt=0)
    units: float | None = Field(default=None, ge=0.5, le=10)
    grams: float | None = Field(default=None, gt=0, le=100000)


class PreparationPortionUpdate(Schema):
    preparation_id: int | None = Field(default=None, gt=0)
    units: float | None = Field(default=None, ge=0.5, le=10)
    grams: float | None = Field(default=None, gt=0, le=100000)


def _available_preparation(user, preparation_id):
    preparation = Preparation.objects.select_related("current_version").filter(
        pk=preparation_id, is_active=True
    ).filter(Q(is_global=True) | Q(created_by=user)).first()
    if preparation is None or preparation.current_version is None:
        raise MobileAPIError("preparation_not_found", "La preparación no está disponible.", 404)
    return preparation


def _portion(version, *, units, grams):
    if (units is None) == (grams is None):
        raise MobileAPIError("preparation_portion_invalid", "Elige unidades o gramos.", 422)
    try:
        if units is not None:
            count = Decimal(str(units))
            if count < Decimal("0.5") or count > 10 or count * 2 != (count * 2).to_integral_value():
                raise ValueError
            quantity = count * version.default_portion_g
            return "units", count, quantity
        quantity = Decimal(str(grams))
        if quantity <= 0 or quantity > version.default_portion_g * 10:
            raise ValueError
        return "grams", None, quantity
    except (ValueError, InvalidOperation) as exc:
        raise MobileAPIError("preparation_portion_invalid", "La porción no es válida.", 422) from exc


def _detail(preparation, *, units=None, grams=None):
    version = preparation.current_version
    mode, selected_units, quantity = _portion(version, units=1 if units is None and grams is None else units, grams=grams)
    factor = quantity / version.yield_g
    ingredients = list(version.ingredients.select_related("food").order_by("order", "id"))
    return {
        "id": preparation.id,
        "name": preparation.name,
        "version": version.version,
        "household_label": version.household_label,
        "default_portion_g": float(version.default_portion_g),
        "yield_g": float(version.yield_g),
        "selection_mode": mode,
        "selected_units": float(selected_units) if selected_units is not None else None,
        "grams": float(quantity),
        "nutrition": {
            "protein_g": round(float(version.protein_g * factor), 3),
            "carbs_g": round(float(version.carbs_g * factor), 3),
            "fat_g": round(float(version.fat_g * factor), 3),
            "sodium_mg": round(float(version.sodium_mg * factor), 3) if version.sodium_mg is not None else None,
            "calories": round(float((version.protein_g * 4 + version.carbs_g * 4 + version.fat_g * 9) * factor), 3),
        },
        "allergens": version.allergens,
        "allergen_status": version.allergen_status,
        "evidence": version.evidence,
        "ingredients": [ingredient_payload(row, version.ingredients_snapshot[index], factor) for index, row in enumerate(ingredients)],
    }


@router.get("/preparations", operation_id="mobile_api_api_preparations", auth=mobile_bearer, response={200: dict})
def preparations(request, search: str | None = None, offset: int = 0, limit: int = 30):
    queryset = Preparation.objects.select_related("current_version").filter(is_active=True, is_global=True, current_version__isnull=False)
    if search:
        queryset = queryset.filter(name__icontains=search.strip())
    total = queryset.count()
    items = [_detail(item) for item in queryset.order_by("name", "id")[max(offset, 0):max(offset, 0) + min(max(limit, 1), 100)]]
    return success({"items": items, "total": total, "offset": max(offset, 0), "limit": min(max(limit, 1), 100)})


@router.get("/preparations/{preparation_id}", operation_id="mobile_api_api_preparation_detail", auth=mobile_bearer, response={200: dict})
def preparation_detail(request, preparation_id: int, units: float | None = None, grams: float | None = None):
    return success(_detail(_available_preparation(request.auth.user, preparation_id), units=units, grams=grams))


def _owned_meal(user, meal_id):
    meal = Meal.objects.filter(pk=meal_id, created_by=user).first()
    if meal is None:
        raise MobileAPIError("meal_not_found", "La comida no está disponible.", 404)
    return meal


def _save_selection(meal, preparation, *, units, grams, relation=None):
    version = preparation.current_version
    mode, count, quantity = _portion(version, units=units, grams=grams)
    if relation is None:
        relation = MealPreparation(meal=meal, preparation=preparation, order=meal.meal_food_set.count() + meal.meal_preparation_set.count() + 1)
    relation.preparation = preparation
    relation.version = version
    relation.selection_mode = mode
    relation.selected_units = count
    relation.quantity_g = quantity
    relation.save()
    meal.update_draft_status()
    rebuild_meal_cached_state(meal)
    refresh_dailyplans_for_meal(meal)
    return relation


@router.post("/library/meals/{meal_id}/preparations", operation_id="mobile_api_api_add_preparation", auth=mobile_bearer, response={200: dict})
@transaction.atomic
def add_preparation(request, meal_id: int, payload: PreparationSelection):
    require_scope(request.auth, MOBILE_SCOPE_WRITE)
    meal = _owned_meal(request.auth.user, meal_id)
    preparation = _available_preparation(request.auth.user, payload.preparation_id)
    relation = _save_selection(meal, preparation, units=payload.units, grams=payload.grams)
    return success({"target_id": meal.id, "created_id": relation.id, "preparation": _detail(preparation, units=payload.units, grams=payload.grams)})


@router.patch("/library/meals/{meal_id}/preparations/{relation_id}", operation_id="mobile_api_api_update_preparation", auth=mobile_bearer, response={200: dict})
@transaction.atomic
def update_preparation(request, meal_id: int, relation_id: int, payload: PreparationPortionUpdate):
    require_scope(request.auth, MOBILE_SCOPE_WRITE)
    meal = _owned_meal(request.auth.user, meal_id)
    relation = MealPreparation.objects.select_related("preparation__current_version").filter(pk=relation_id, meal=meal).first()
    if relation is None:
        raise MobileAPIError("preparation_relation_not_found", "La porción no está disponible.", 404)
    preparation = _available_preparation(request.auth.user, payload.preparation_id) if payload.preparation_id is not None else relation.preparation
    _save_selection(meal, preparation, units=payload.units, grams=payload.grams, relation=relation)
    return success({"target_id": meal.id, "affected_id": relation.id})


@router.delete("/library/meals/{meal_id}/preparations/{relation_id}", operation_id="mobile_api_api_delete_preparation", auth=mobile_bearer, response={200: dict})
@transaction.atomic
def delete_preparation(request, meal_id: int, relation_id: int):
    require_scope(request.auth, MOBILE_SCOPE_WRITE)
    meal = _owned_meal(request.auth.user, meal_id)
    deleted, _ = MealPreparation.objects.filter(pk=relation_id, meal=meal).delete()
    if not deleted:
        raise MobileAPIError("preparation_relation_not_found", "La porción no está disponible.", 404)
    rebuild_meal_cached_state(meal)
    refresh_dailyplans_for_meal(meal)
    return success({"target_id": meal.id, "affected_id": relation_id})
