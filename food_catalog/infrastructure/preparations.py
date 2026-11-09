"""Curate and freeze preparation revisions before they enter a catalog release."""

from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from food_catalog.infrastructure.releases import payload_sha256
from food_catalog.models import CatalogFood, CatalogPreparationVersion


class PreparationPublicationError(ValueError):
    pass


@transaction.atomic
def publish_preparation_version(version: CatalogPreparationVersion, *, actor) -> CatalogPreparationVersion:
    if not getattr(actor, "is_staff", False):
        raise PreparationPublicationError("preparation_publication_staff_required")
    version = CatalogPreparationVersion.objects.select_for_update().select_related("preparation").get(pk=version.pk)
    if version.published_at:
        raise PreparationPublicationError("preparation_version_already_published")
    if not version.source_name.strip() or not version.yield_evidence.strip():
        raise PreparationPublicationError("preparation_evidence_required")
    if version.yield_g <= 0 or version.default_portion_g <= 0 or version.default_portion_g > version.yield_g:
        raise PreparationPublicationError("preparation_yield_or_portion_invalid")
    if not version.household_label.strip():
        raise PreparationPublicationError("preparation_household_label_required")

    ingredients = list(version.ingredients.select_related("food").order_by("order", "id"))
    if not ingredients:
        raise PreparationPublicationError("preparation_ingredients_required")
    totals = {key: Decimal("0") for key in ("protein_g", "carbs_g", "fat_g", "sodium_mg")}
    allergens: set[str] = set()
    snapshot = []
    for ingredient in ingredients:
        food = ingredient.food
        if food.status != CatalogFood.STATUS_PUBLISHED or food.portion_unit != CatalogFood.PORTION_UNIT_GRAMS:
            raise PreparationPublicationError("preparation_ingredient_food_unavailable")
        if ingredient.quantity_g <= 0 or ingredient.preparation_state == CatalogFood.PREPARATION_UNKNOWN:
            raise PreparationPublicationError("preparation_ingredient_quantity_or_state_invalid")
        if ingredient.preparation_state != food.preparation_state:
            raise PreparationPublicationError("preparation_ingredient_state_mismatch")
        if any(getattr(food, key) is None for key in ("protein_g_per_100g", "carbs_g_per_100g", "fat_g_per_100g", "sodium_mg_per_100g")):
            raise PreparationPublicationError("preparation_ingredient_nutrition_incomplete")
        if (
            not isinstance(food.allergens, list)
            or not food.allergens
            or any(not isinstance(value, str) or not value.strip() or value == "unknown" for value in food.allergens)
            or ("none" in food.allergens and len(food.allergens) != 1)
        ):
            raise PreparationPublicationError("preparation_ingredient_allergens_unconfirmed")
        factor = ingredient.quantity_g / Decimal("100")
        for key, food_field in (("protein_g", "protein_g_per_100g"), ("carbs_g", "carbs_g_per_100g"), ("fat_g", "fat_g_per_100g"), ("sodium_mg", "sodium_mg_per_100g")):
            totals[key] += getattr(food, food_field) * factor
        allergens.update(value for value in food.allergens if value != "none")
        snapshot.append({
            "catalog_food_ref": str(food.catalog_ref),
            "name": food.display_name,
            "quantity_g": str(ingredient.quantity_g),
            "preparation_state": ingredient.preparation_state,
            "is_condiment": ingredient.is_condiment,
            "nutrition_per_100g": {
                key: str(getattr(food, field)) for key, field in (
                    ("protein_g", "protein_g_per_100g"), ("carbs_g", "carbs_g_per_100g"),
                    ("fat_g", "fat_g_per_100g"), ("sodium_mg", "sodium_mg_per_100g"),
                )
            },
            "allergens": food.allergens,
        })
    nutrition = {key: str(value.quantize(Decimal("0.00001"))) for key, value in totals.items()}
    nutrition["allergens"] = sorted(allergens)
    content = {
        "catalog_ref": str(version.preparation.catalog_ref),
        "name": version.preparation.display_name,
        "version": version.version,
        "yield_g": str(version.yield_g),
        "default_portion_g": str(version.default_portion_g),
        "household_label": version.household_label,
        "source_name": version.source_name,
        "source_url": version.source_url,
        "yield_evidence": version.yield_evidence,
        "preparation_notes": version.preparation_notes,
        "nutrition": nutrition,
        "ingredients": snapshot,
    }
    version.nutrition = nutrition
    version.ingredients_snapshot = snapshot
    version.content_sha256 = payload_sha256(content)
    version.published_at = timezone.now()
    version.reviewed_by = actor
    version.save(update_fields=["nutrition", "ingredients_snapshot", "content_sha256", "published_at", "reviewed_by"])
    version.preparation.current_version = version
    version.preparation.save(update_fields=["current_version"])
    return version
