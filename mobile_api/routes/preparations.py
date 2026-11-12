"""Serve curated and personal preparations as distinct meal components."""

from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.db.models import Q
from ninja import Field, Router, Schema

from mobile_api.api_support import calendarization_error, require_scope, success
from mobile_api.auth import mobile_bearer
from mobile_api.composition_projections import project_preparation_food_result
from mobile_api.errors import MobileAPIError
from mobile_api.preparation_projections import ingredient_payload
from notas.application.services.cache.dailyplan_summary import refresh_dailyplans_for_meal
from notas.application.services.commands.calendarization_commands import save_calendarized_preparation
from notas.application.services.commands.personal_preparation_commands import (
    PersonalPreparationError,
    add_personal_preparation_food,
    can_use_personal_preparations,
    clear_personal_preparation_ingredients,
    create_personal_preparation_draft,
    remove_personal_preparation,
    rename_personal_preparation_draft,
    require_personal_preparations_pro,
    save_personal_preparation,
    preview_personal_preparation_food,
)
from notas.application.services.nutrition.meal_nutrition import rebuild_meal_cached_state
from notas.application.services.nutrition.weight import get_current_weight
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


class PersonalPreparationIngredientInput(Schema):
    food_id: int = Field(gt=0)
    quantity_g: float = Field(gt=0, le=100000)


class PersonalPreparationInput(Schema):
    name: str
    yield_g: float | None = Field(default=None, gt=0, le=100000)
    default_portion_g: float = Field(default=100, gt=0, le=100000)
    ingredients: list[PersonalPreparationIngredientInput]


class PersonalPreparationDraftInput(Schema):
    name: str


class PersonalPreparationFoodPickerInput(Schema):
    food_id: int = Field(gt=0)
    quantity_g: float = Field(gt=0, le=100000)
    replace_food_id: int | None = Field(default=None, gt=0)


def _personal_access(user):
    try:
        require_personal_preparations_pro(user)
    except PermissionError as exc:
        raise MobileAPIError("personal_preparations_pro_required", "Las preparaciones personales requieren Pro y estar habilitadas.", 403) from exc


def _personal_error(exc):
    code = str(exc)
    if code == "preparation_not_found":
        raise MobileAPIError(code, "La preparación no está disponible.", 404) from exc
    if code == "preparation_ingredient_already_added":
        raise MobileAPIError(code, "Este alimento ya está en la preparación. Puedes ajustar su cantidad desde el detalle.", 422) from exc
    raise MobileAPIError(code, "Revisa los datos de la preparación y sus ingredientes.", 422) from exc


def _available_preparation(user, preparation_id, *, allow_inactive_personal=False, allow_personal_draft=False):
    queryset = Preparation.objects.select_related("current_version").filter(pk=preparation_id).filter(Q(is_global=True) | Q(created_by=user))
    if allow_inactive_personal:
        queryset = queryset.filter(Q(is_active=True) | Q(is_global=False, created_by=user))
    else:
        queryset = queryset.filter(is_active=True)
    preparation = queryset.first()
    owned_draft = (
        preparation is not None
        and allow_personal_draft
        and not preparation.is_global
        and preparation.created_by_id == user.id
    )
    if (
        preparation is None
        or (preparation.current_version is None and not owned_draft)
        or (not preparation.is_global and not can_use_personal_preparations(user))
    ):
        raise MobileAPIError("preparation_not_found", "La preparación no está disponible.", 404)
    return preparation


def _personal_draft(preparation):
    return {"id": preparation.id, "name": preparation.name, "is_personal": True, "is_active": preparation.is_active, "is_draft": True}


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


def _detail(preparation, *, units=None, grams=None, full_recipe=False, current_weight=None):
    version = preparation.current_version
    if full_recipe:
        mode, selected_units, quantity = "grams", None, version.yield_g
        factor = Decimal("1")
    else:
        mode, selected_units, quantity = _portion(version, units=1 if units is None and grams is None else units, grams=grams)
        factor = quantity / version.yield_g
    ingredients = list(version.ingredients.select_related("food").order_by("order", "id"))
    inferred_yield = sum((row.quantity_g for row in ingredients), Decimal("0"))
    return {
        "id": preparation.id,
        "name": preparation.name,
        "is_personal": not preparation.is_global,
        "is_active": preparation.is_active,
        "is_draft": False,
        "version": version.version,
        "household_label": version.household_label,
        "default_portion_g": float(version.default_portion_g),
        "yield_g": float(version.yield_g),
        "yield_is_manual": bool(version.evidence.get("yield_is_manual", version.yield_g != inferred_yield)),
        "selection_mode": mode,
        "selected_units": float(selected_units) if selected_units is not None else None,
        "grams": float(quantity),
        "nutrition": {
            "protein_g": round(float(version.protein_g * factor), 3),
            "protein_per_kilogram": round(float(version.protein_g * factor) / current_weight, 1) if current_weight and version.protein_g else None,
            "carbs_g": round(float(version.carbs_g * factor), 3),
            "fat_g": round(float(version.fat_g * factor), 3),
            "sodium_mg": round(float(version.sodium_mg * factor), 3) if version.sodium_mg is not None else None,
            "calories": round(float((version.protein_g * 4 + version.carbs_g * 4 + version.fat_g * 9) * factor), 3),
        },
        "allergens": version.allergens,
        "allergen_status": version.allergen_status,
        "evidence": version.evidence,
        "ingredients": [ingredient_payload(row, version.ingredients_snapshot[index], factor) for index, row in enumerate(ingredients)],
        "recipe_ingredients": [{"food_id": row.food_id, "name": version.ingredients_snapshot[index]["name"], "quantity_g": float(row.quantity_g)} for index, row in enumerate(ingredients)],
    }


def _calendarized_snapshot(preparation, *, units=None, grams=None):
    detail = _detail(preparation, units=units, grams=grams)
    return {
        "component_type": "preparation",
        "source_preparation_id": preparation.id,
        "source_preparation_version": detail["version"],
        "name": detail["name"],
        "quantity_g": detail["grams"],
        "quantity_unit": "g",
        "portion_display_quantity": detail["selected_units"] if detail["selection_mode"] == "units" else detail["grams"],
        "portion_display_measure": detail["household_label"] if detail["selection_mode"] == "units" else "g",
        "ingredients": [
            {
                "source_food_id": item.get("food_id"),
                "name": item["name"],
                "quantity_g": item["quantity_g"],
                "preparation_state": item.get("preparation_state", ""),
                "is_condiment": item.get("is_condiment", False),
            }
            for item in detail["ingredients"]
        ],
        "source_evidence": detail["evidence"],
        "allergens": detail["allergens"],
        "sodium_mg": detail["nutrition"]["sodium_mg"],
        "protein_g": detail["nutrition"]["protein_g"],
        "carbs_g": detail["nutrition"]["carbs_g"],
        "fat_g": detail["nutrition"]["fat_g"],
        "total_kcal": detail["nutrition"]["calories"],
    }


@router.get("/preparations", operation_id="mobile_api_api_preparations", auth=mobile_bearer, response={200: dict})
def preparations(request, search: str | None = None, offset: int = 0, limit: int = 30):
    visible = Q(is_global=True)
    if can_use_personal_preparations(request.auth.user):
        visible |= Q(is_global=False, created_by=request.auth.user)
    queryset = Preparation.objects.select_related("current_version").filter(is_active=True, current_version__isnull=False).filter(visible)
    if search:
        queryset = queryset.filter(name__icontains=search.strip())
    total = queryset.count()
    current_weight = get_current_weight(request.auth.user)
    items = [_detail(item, current_weight=current_weight) for item in queryset.order_by("name", "id")[max(offset, 0):max(offset, 0) + min(max(limit, 1), 100)]]
    return success({"items": items, "total": total, "offset": max(offset, 0), "limit": min(max(limit, 1), 100)})


@router.get("/preparations/{preparation_id}", operation_id="mobile_api_api_preparation_detail", auth=mobile_bearer, response={200: dict})
def preparation_detail(request, preparation_id: int, units: float | None = None, grams: float | None = None, full_recipe: bool = False):
    preparation = _available_preparation(request.auth.user, preparation_id, allow_inactive_personal=True, allow_personal_draft=True)
    if preparation.current_version is None:
        return success(_personal_draft(preparation))
    return success(_detail(preparation, units=units, grams=grams, full_recipe=full_recipe, current_weight=get_current_weight(request.auth.user)))


@router.get("/library/preparations", operation_id="mobile_api_personal_preparations", auth=mobile_bearer, response={200: dict})
def personal_preparations(request, search: str | None = None, offset: int = 0, limit: int = 30):
    _personal_access(request.auth.user)
    queryset = Preparation.objects.select_related("current_version").filter(is_active=True, is_global=False, created_by=request.auth.user)
    if search:
        queryset = queryset.filter(name__icontains=search.strip())
    safe_offset = max(offset, 0)
    safe_limit = min(max(limit, 1), 100)
    current_weight = get_current_weight(request.auth.user)
    return success({"items": [_detail(item, current_weight=current_weight) if item.current_version_id else _personal_draft(item) for item in queryset.order_by("name", "id")[safe_offset:safe_offset + safe_limit]], "total": queryset.count(), "offset": safe_offset, "limit": safe_limit})


@router.post("/library/preparations/drafts", operation_id="mobile_api_create_personal_preparation_draft", auth=mobile_bearer, response={200: dict})
def create_personal_preparation_draft_route(request, payload: PersonalPreparationDraftInput):
    require_scope(request.auth, MOBILE_SCOPE_WRITE)
    _personal_access(request.auth.user)
    try:
        preparation = create_personal_preparation_draft(user=request.auth.user, name=payload.name)
    except PersonalPreparationError as exc:
        _personal_error(exc)
    return success(_personal_draft(preparation))


@router.patch("/library/preparations/{preparation_id}/draft", operation_id="mobile_api_rename_personal_preparation_draft", auth=mobile_bearer, response={200: dict})
def rename_personal_preparation_draft_route(request, preparation_id: int, payload: PersonalPreparationDraftInput):
    require_scope(request.auth, MOBILE_SCOPE_WRITE)
    _personal_access(request.auth.user)
    try:
        preparation = rename_personal_preparation_draft(
            user=request.auth.user, preparation_id=preparation_id, name=payload.name
        )
    except PersonalPreparationError as exc:
        _personal_error(exc)
    return success(_personal_draft(preparation))


@router.delete("/library/preparations/{preparation_id}/foods", operation_id="mobile_api_clear_personal_preparation_ingredients", auth=mobile_bearer, response={200: dict})
def clear_personal_preparation_ingredients_route(request, preparation_id: int):
    require_scope(request.auth, MOBILE_SCOPE_WRITE)
    _personal_access(request.auth.user)
    try:
        preparation = clear_personal_preparation_ingredients(user=request.auth.user, preparation_id=preparation_id)
    except PersonalPreparationError as exc:
        _personal_error(exc)
    return success(_personal_draft(preparation))


@router.post("/library/preparations/{preparation_id}/food-picker/preview", operation_id="mobile_api_preparation_food_picker_preview", auth=mobile_bearer, response={200: dict})
def preparation_food_picker_preview(request, preparation_id: int, payload: PersonalPreparationFoodPickerInput):
    _personal_access(request.auth.user)
    try:
        preparation, food, cleaned, foods = preview_personal_preparation_food(
            user=request.auth.user, preparation_id=preparation_id, **payload.model_dump()
        )
    except PersonalPreparationError as exc:
        _personal_error(exc)
    return success({
        "selection": {"id": food.id, "entity": "food", "name": food.name, "nutrition": None, "quantity": payload.quantity_g, "hour": None},
        "impacts": [],
        "result": project_preparation_food_result(
            preparation=preparation,
            selected_food_id=food.id,
            cleaned=cleaned,
            foods=foods,
            current_weight=get_current_weight(request.auth.user),
            replacing=payload.replace_food_id is not None,
        ),
        "replacements": [], "confirmation_required": False,
    })


@router.post("/library/preparations/{preparation_id}/food-picker/commit", operation_id="mobile_api_preparation_food_picker_commit", auth=mobile_bearer, response={200: dict})
def preparation_food_picker_commit(request, preparation_id: int, payload: PersonalPreparationFoodPickerInput):
    require_scope(request.auth, MOBILE_SCOPE_WRITE)
    _personal_access(request.auth.user)
    try:
        preparation = add_personal_preparation_food(
            user=request.auth.user, preparation_id=preparation_id, **payload.model_dump()
        )
    except PersonalPreparationError as exc:
        _personal_error(exc)
    return success({"message": "Alimento agregado a la preparación.", "target_id": preparation_id, "created_id": preparation.id})


@router.post("/library/preparations", operation_id="mobile_api_create_personal_preparation", auth=mobile_bearer, response={200: dict})
def create_personal_preparation(request, payload: PersonalPreparationInput):
    require_scope(request.auth, MOBILE_SCOPE_WRITE)
    _personal_access(request.auth.user)
    try:
        preparation = save_personal_preparation(user=request.auth.user, **payload.model_dump())
    except PersonalPreparationError as exc:
        _personal_error(exc)
    return success(_detail(preparation, current_weight=get_current_weight(request.auth.user)))


@router.put("/library/preparations/{preparation_id}", operation_id="mobile_api_update_personal_preparation", auth=mobile_bearer, response={200: dict})
def update_personal_preparation(request, preparation_id: int, payload: PersonalPreparationInput):
    require_scope(request.auth, MOBILE_SCOPE_WRITE)
    _personal_access(request.auth.user)
    try:
        preparation = save_personal_preparation(user=request.auth.user, preparation_id=preparation_id, **payload.model_dump())
    except PersonalPreparationError as exc:
        _personal_error(exc)
    return success(_detail(preparation, current_weight=get_current_weight(request.auth.user)))


@router.delete("/library/preparations/{preparation_id}", operation_id="mobile_api_remove_personal_preparation", auth=mobile_bearer, response={200: dict})
def delete_personal_preparation(request, preparation_id: int):
    require_scope(request.auth, MOBILE_SCOPE_WRITE)
    _personal_access(request.auth.user)
    try:
        remove_personal_preparation(user=request.auth.user, preparation_id=preparation_id)
    except PersonalPreparationError as exc:
        _personal_error(exc)
    return success({"affected_id": preparation_id})


@router.post("/program/days/{day_id}/meals/{meal_snapshot_key}/preparations", operation_id="mobile_api_routes_preparations_add_calendarized_preparation", auth=mobile_bearer, response={200: dict})
def add_calendarized_preparation(request, day_id: int, meal_snapshot_key: str, payload: PreparationSelection):
    require_scope(request.auth, MOBILE_SCOPE_WRITE)
    preparation = _available_preparation(request.auth.user, payload.preparation_id)
    try:
        save_calendarized_preparation(
            user=request.auth.user,
            day_id=day_id,
            meal_snapshot_key=meal_snapshot_key,
            preparation_snapshot=_calendarized_snapshot(preparation, units=payload.units, grams=payload.grams),
        )
    except ValueError as exc:
        raise calendarization_error(exc) from exc
    return success({"target_id": day_id, "created_id": preparation.id})


@router.patch("/program/days/{day_id}/meals/{meal_snapshot_key}/preparations/{component_snapshot_key}", operation_id="mobile_api_routes_preparations_update_calendarized_preparation", auth=mobile_bearer, response={200: dict})
def update_calendarized_preparation(request, day_id: int, meal_snapshot_key: str, component_snapshot_key: str, payload: PreparationPortionUpdate):
    require_scope(request.auth, MOBILE_SCOPE_WRITE)
    if payload.preparation_id is None:
        raise MobileAPIError("preparation_not_found", "La preparación no está disponible.", 404)
    preparation = _available_preparation(request.auth.user, payload.preparation_id)
    try:
        save_calendarized_preparation(
            user=request.auth.user,
            day_id=day_id,
            meal_snapshot_key=meal_snapshot_key,
            component_snapshot_key=component_snapshot_key,
            preparation_snapshot=_calendarized_snapshot(preparation, units=payload.units, grams=payload.grams),
        )
    except ValueError as exc:
        raise calendarization_error(exc) from exc
    return success({"target_id": day_id, "created_id": preparation.id})


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
    preparation = _available_preparation(request.auth.user, payload.preparation_id or relation.preparation_id)
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
