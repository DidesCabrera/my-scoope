"""Create versioned, user-owned preparations from operational foods."""

import hashlib
import json
import math
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.db import transaction

from accounts.services.entitlements import resolve_account_entitlements
from notas.application.queries.food_picker_queries import get_food_picker_queryset
from notas.application.services.cache.dailyplan_summary import refresh_dailyplans_for_meal
from notas.application.services.nutrition.meal_nutrition import rebuild_meal_cached_state
from notas.domain.models import Food, Meal, MealPreparation, Preparation, PreparationIngredient, PreparationVersion


class PersonalPreparationError(ValueError):
    pass


def can_use_personal_preparations(user) -> bool:
    entitlements = resolve_account_entitlements(user)
    return bool(
        settings.PERSONAL_PREPARATIONS_FEATURE_ENABLED
        and entitlements
        and entitlements.enabled("can_use_personal_preparations")
    )


def require_personal_preparations_pro(user) -> None:
    if not can_use_personal_preparations(user):
        raise PermissionError("personal_preparations_pro_required")


def create_personal_preparation_draft(*, user, name):
    require_personal_preparations_pro(user)
    name = str(name or "").strip()
    if not name or len(name) > 255:
        raise PersonalPreparationError("preparation_identity_invalid")
    return Preparation.objects.create(name=name, is_global=False, created_by=user)


def _positive_decimal(value, *, maximum=Decimal("100000")) -> Decimal:
    try:
        amount = Decimal(str(value))
    except (TypeError, ValueError, InvalidOperation):
        raise PersonalPreparationError("preparation_quantity_invalid") from None
    if not amount.is_finite() or amount <= 0 or amount > maximum:
        raise PersonalPreparationError("preparation_quantity_invalid")
    return amount


def _clean_ingredients(ingredients):
    if not isinstance(ingredients, list) or not 1 <= len(ingredients) <= 100:
        raise PersonalPreparationError("preparation_ingredients_invalid")
    cleaned = []
    ids = set()
    for item in ingredients:
        if not isinstance(item, dict):
            raise PersonalPreparationError("preparation_ingredients_invalid")
        try:
            food_id = int(item.get("food_id"))
        except (TypeError, ValueError):
            raise PersonalPreparationError("preparation_ingredients_invalid") from None
        if food_id <= 0 or food_id in ids:
            raise PersonalPreparationError("preparation_ingredients_invalid")
        ids.add(food_id)
        cleaned.append((food_id, _positive_decimal(item.get("quantity_g"))))
    return cleaned, ids


def _ingredient_nutrition(cleaned, foods):
    totals = {key: Decimal("0") for key in ("protein_g", "carbs_g", "fat_g", "sodium_mg")}
    has_sodium = True
    snapshots = []
    for food_id, quantity in cleaned:
        food = foods[food_id]
        values = (food.protein, food.carbs, food.fat)
        if any(not math.isfinite(value) or value < 0 for value in values):
            raise PersonalPreparationError("preparation_ingredient_nutrition_invalid")
        factor = quantity / Decimal("100")
        for key, value in zip(("protein_g", "carbs_g", "fat_g"), values):
            totals[key] += Decimal(str(value)) * factor
        if food.sodium_mg_per_100g is None:
            has_sodium = False
        else:
            if not food.sodium_mg_per_100g.is_finite() or food.sodium_mg_per_100g < 0:
                raise PersonalPreparationError("preparation_ingredient_nutrition_invalid")
            totals["sodium_mg"] += food.sodium_mg_per_100g * factor
        snapshots.append(
            {
                "name": food.name,
                "quantity_g": str(quantity),
                "preparation_state": food.preparation_state,
                "is_condiment": False,
                "nutrition_per_100g": {
                    "protein_g": str(food.protein),
                    "carbs_g": str(food.carbs),
                    "fat_g": str(food.fat),
                    "sodium_mg": str(food.sodium_mg_per_100g) if food.sodium_mg_per_100g is not None else None,
                },
            }
        )
    if any(value > Decimal("9999999") for value in totals.values()):
        raise PersonalPreparationError("preparation_ingredient_nutrition_invalid")
    return totals, has_sodium, snapshots


@transaction.atomic
def save_personal_preparation(
    *, user, name, ingredients, yield_g=None, default_portion_g=100, household_label="porción", preparation_id=None
):
    require_personal_preparations_pro(user)
    name = str(name or "").strip()
    household_label = str(household_label or "").strip()
    if not name or len(name) > 255 or not household_label or len(household_label) > 80:
        raise PersonalPreparationError("preparation_identity_invalid")
    cleaned, ids = _clean_ingredients(ingredients)
    yield_amount = _positive_decimal(yield_g if yield_g is not None else sum((quantity for _, quantity in cleaned), Decimal("0")))
    portion_amount = _positive_decimal(default_portion_g)

    foods = {
        food.pk: food
        for food in get_food_picker_queryset(user).filter(
            pk__in=ids, is_active=True, portion_unit=Food.PORTION_UNIT_GRAMS
        )
    }
    if set(foods) != ids:
        raise PersonalPreparationError("preparation_ingredient_unavailable")

    totals, has_sodium, snapshots = _ingredient_nutrition(cleaned, foods)

    if preparation_id is None:
        preparation = Preparation.objects.create(name=name, is_global=False, created_by=user)
        version_number = 1
    else:
        preparation = (
            Preparation.objects.select_for_update()
            .filter(pk=preparation_id, is_global=False, created_by=user, is_active=True)
            .first()
        )
        if preparation is None:
            raise PersonalPreparationError("preparation_not_found")
        version_number = (preparation.current_version.version if preparation.current_version else 0) + 1

    content = {
        "name": name,
        "yield_g": str(yield_amount),
        "default_portion_g": str(portion_amount),
        "household_label": household_label,
        "ingredients": snapshots,
    }
    version = PreparationVersion.objects.create(
        preparation=preparation,
        version=version_number,
        release_version="personal",
        yield_g=yield_amount,
        default_portion_g=portion_amount,
        household_label=household_label,
        protein_g=totals["protein_g"],
        carbs_g=totals["carbs_g"],
        fat_g=totals["fat_g"],
        sodium_mg=totals["sodium_mg"] if has_sodium else None,
        allergens=[],
        allergen_status="unknown",
        evidence={"source_name": "Registro personal", "yield_is_manual": yield_g is not None},
        ingredients_snapshot=snapshots,
        content_sha256=hashlib.sha256(json.dumps(content, sort_keys=True, ensure_ascii=False).encode()).hexdigest(),
    )
    PreparationIngredient.objects.bulk_create(
        [
            PreparationIngredient(
                version=version,
                food=foods[food_id],
                quantity_g=quantity,
                preparation_state=foods[food_id].preparation_state,
                order=index,
            )
            for index, (food_id, quantity) in enumerate(cleaned)
        ]
    )
    preparation.name = name
    preparation.current_version = version
    preparation.save(update_fields=["name", "current_version"])

    if version_number > 1:
        meal_ids = set()
        for relation in MealPreparation.objects.filter(preparation=preparation).iterator():
            relation.version = version
            if relation.selection_mode == "units":
                relation.quantity_g = relation.selected_units * portion_amount
            relation.save(update_fields=["version", "quantity_g"])
            meal_ids.add(relation.meal_id)
        for meal in Meal.objects.filter(pk__in=meal_ids).iterator():
            rebuild_meal_cached_state(meal)
            refresh_dailyplans_for_meal(meal)
    return preparation


def preview_personal_preparation_food(*, user, preparation_id, food_id, quantity_g, replace_food_id=None):
    """Validate a picker selection against the same recipe rules used on save."""
    require_personal_preparations_pro(user)
    preparation = Preparation.objects.select_related("current_version").filter(
        pk=preparation_id, is_global=False, created_by=user, is_active=True
    ).first()
    if preparation is None:
        raise PersonalPreparationError("preparation_not_found")
    current = list(preparation.current_version.ingredients.order_by("order", "id")) if preparation.current_version_id else []
    if replace_food_id is not None and not any(row.food_id == replace_food_id for row in current):
        raise PersonalPreparationError("preparation_ingredient_unavailable")
    if any(row.food_id == food_id and row.food_id != replace_food_id for row in current):
        raise PersonalPreparationError("preparation_ingredient_already_added")
    ingredients = [
        {"food_id": food_id, "quantity_g": quantity_g} if row.food_id == replace_food_id
        else {"food_id": row.food_id, "quantity_g": row.quantity_g}
        for row in current
    ]
    if replace_food_id is None:
        ingredients.append({"food_id": food_id, "quantity_g": quantity_g})
    cleaned, ids = _clean_ingredients(ingredients)
    foods = {
        food.pk: food for food in get_food_picker_queryset(user).filter(
            pk__in=ids, is_active=True, portion_unit=Food.PORTION_UNIT_GRAMS
        )
    }
    if set(foods) != ids:
        raise PersonalPreparationError("preparation_ingredient_unavailable")
    _ingredient_nutrition(cleaned, foods)
    return preparation, foods[food_id], cleaned


@transaction.atomic
def add_personal_preparation_food(*, user, preparation_id, food_id, quantity_g, replace_food_id=None):
    require_personal_preparations_pro(user)
    # current_version is nullable for drafts; joining it here makes FOR UPDATE fail on PostgreSQL.
    preparation = Preparation.objects.select_for_update().filter(
        pk=preparation_id, is_global=False, created_by=user, is_active=True
    ).first()
    if preparation is None:
        raise PersonalPreparationError("preparation_not_found")
    _, _, cleaned = preview_personal_preparation_food(
        user=user, preparation_id=preparation_id, food_id=food_id, quantity_g=quantity_g, replace_food_id=replace_food_id
    )
    version = preparation.current_version
    return save_personal_preparation(
        user=user,
        preparation_id=preparation_id,
        name=preparation.name,
        ingredients=[{"food_id": item_id, "quantity_g": amount} for item_id, amount in cleaned],
        yield_g=version.yield_g if version and version.evidence.get("yield_is_manual") else None,
        default_portion_g=version.default_portion_g if version else 100,
        household_label=version.household_label if version else "porción",
    )


@transaction.atomic
def rename_personal_preparation_draft(*, user, preparation_id, name):
    require_personal_preparations_pro(user)
    name = str(name or "").strip()
    if not name or len(name) > 255:
        raise PersonalPreparationError("preparation_identity_invalid")
    preparation = Preparation.objects.select_for_update().filter(
        pk=preparation_id, is_global=False, created_by=user, is_active=True, current_version__isnull=True
    ).first()
    if preparation is None:
        raise PersonalPreparationError("preparation_not_found")
    preparation.name = name
    preparation.save(update_fields=["name"])
    return preparation


@transaction.atomic
def clear_personal_preparation_ingredients(*, user, preparation_id):
    require_personal_preparations_pro(user)
    preparation = Preparation.objects.select_for_update().filter(
        pk=preparation_id, is_global=False, created_by=user, is_active=True
    ).first()
    if preparation is None:
        raise PersonalPreparationError("preparation_not_found")
    preparation.current_version = None
    preparation.save(update_fields=["current_version"])
    return preparation


@transaction.atomic
def remove_personal_preparation(*, user, preparation_id):
    require_personal_preparations_pro(user)
    preparation = (
        Preparation.objects.select_for_update()
        .filter(pk=preparation_id, is_global=False, created_by=user, is_active=True)
        .first()
    )
    if preparation is None:
        raise PersonalPreparationError("preparation_not_found")
    preparation.is_active = False
    preparation.save(update_fields=["is_active"])
