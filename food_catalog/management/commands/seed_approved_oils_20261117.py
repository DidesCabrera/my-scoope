"""Curate the two approved edible oils in the Food Catalog authority."""

import hashlib
import json
from decimal import Decimal
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from food_catalog.application.curation import transition_catalog_food_status
from food_catalog.models import CatalogFood, CatalogFoodAlias, CatalogFoodPortion, CatalogFoodSource

DATA_PATH = Path(__file__).resolve().parents[2] / "data/curation/approved_oils_2026_11_17.json"


class Command(BaseCommand):
    help = "Publish the two USDA-backed edible oils approved for the visual catalog. Authority only."

    def handle(self, *args, **options):
        payload = json.loads(DATA_PATH.read_text(encoding="utf-8"))
        results = []
        with transaction.atomic():
            for spec in payload["foods"]:
                name = spec["name"]
                fdc_id = spec["fdc_id"]
                existing = CatalogFood.objects.filter(canonical_name=spec["canonical_name"], country="CL").first()
                if existing:
                    if existing.display_name != name or existing.status != CatalogFood.STATUS_PUBLISHED or not existing.sources.filter(
                        source_name="USDA FoodData Central", source_food_id=fdc_id
                    ).exists():
                        raise CommandError(f"Existing catalog identity requires review: {name}")
                    results.append((name, existing.pk, "already published"))
                    continue
                if CatalogFood.objects.filter(display_name__iexact=name).exists():
                    raise CommandError(f"Name already belongs to another catalog food: {name}")
                if CatalogFoodSource.objects.filter(source_name="USDA FoodData Central", source_food_id=fdc_id).exists():
                    raise CommandError(f"USDA source is already assigned: {fdc_id}")
                food = CatalogFood.objects.create(
                    catalog_version="2026.11.6",
                    display_name=name,
                    canonical_name=spec["canonical_name"],
                    description=spec["description"],
                    country="CL",
                    food_group="fats",
                    food_subgroup="oil",
                    myscoope_group="fats_and_oils",
                    food_form=CatalogFood.FOOD_FORM_CONDIMENT,
                    preparation_state=CatalogFood.PREPARATION_READY_TO_EAT,
                    portion_unit=CatalogFood.PORTION_UNIT_GRAMS,
                    protein_g_per_100g=Decimal(spec["protein_g_per_100g"]),
                    carbs_g_per_100g=Decimal(spec["carbs_g_per_100g"]),
                    fat_g_per_100g=Decimal(spec["fat_g_per_100g"]),
                    calories_kcal_per_100g=Decimal(spec["calories_kcal_per_100g"]),
                    saturated_fat_g_per_100g=Decimal(spec["saturated_fat_g_per_100g"]),
                    sodium_mg_per_100g=Decimal(spec["sodium_mg_per_100g"]),
                    source_type=CatalogFood.SOURCE_USDA,
                    data_quality_score=90,
                    confidence_score=Decimal("90"),
                )
                CatalogFoodSource.objects.create(
                    catalog_food=food,
                    source_type=CatalogFood.SOURCE_USDA,
                    source_name="USDA FoodData Central",
                    source_food_id=fdc_id,
                    source_dataset="SR Legacy",
                    source_version="2018-04",
                    source_url=f"https://fdc.nal.usda.gov/fdc-app.html#/food-details/{fdc_id}/nutrients",
                    normalized_payload_hash=hashlib.sha256(json.dumps(spec, sort_keys=True).encode()).hexdigest(),
                    license_name="USDA public domain",
                    license_status=CatalogFoodSource.LICENSE_ALLOWED,
                    attribution="USDA FoodData Central SR Legacy",
                    evidence_payload={"retrieved_at": payload["retrieved_at"], "fdc_description": spec["fdc_description"]},
                )
                CatalogFoodPortion.objects.create(
                    catalog_food=food,
                    label="1 cucharada",
                    grams=Decimal(spec["tablespoon_g"]),
                    household_amount=Decimal("1"),
                    household_measure="tablespoon",
                    source="USDA SR Legacy",
                    is_default=True,
                )
                if name == "Aceite de maravilla":
                    CatalogFoodAlias.objects.create(catalog_food=food, name="Aceite de girasol", alias_type=CatalogFoodAlias.ALIAS_COMMON)
                for status in (
                    CatalogFood.STATUS_NORMALIZED,
                    CatalogFood.STATUS_PENDING_REVIEW,
                    CatalogFood.STATUS_REVIEWED,
                    CatalogFood.STATUS_PUBLISHED,
                ):
                    decision = transition_catalog_food_status(food, status)
                    if not decision.changed:
                        raise CommandError(f"Publication gate blocked {name}: {decision.errors}")
                results.append((name, food.pk, "published"))
        self.stdout.write(self.style.SUCCESS(f"Approved oils: {results}"))
