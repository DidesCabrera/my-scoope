from decimal import Decimal

from django.core.management import call_command
from django.test import TestCase
from django.contrib.auth import get_user_model

from food_catalog.models import (
    CatalogFood,
    CatalogFoodAlias,
    CatalogFoodPortion,
    CatalogFoodSource,
    CatalogImportBatch,
)
from notas.application.services.commands.food_catalog_backfill import (
    OPERATIONAL_BACKFILL_SOURCE_DATASET,
    OPERATIONAL_BACKFILL_SOURCE_NAME,
    DEFAULT_OPERATIONAL_BACKFILL_SOURCE_VERSION,
    DEFAULT_OPERATIONAL_BACKFILL_STATUS,
    backfill_catalog_from_operational_foods,
    dry_run_backfill_catalog_from_operational_foods,
    operational_backfill_identity,
)
from food_catalog.infrastructure.imports.governance import record_catalog_import_dry_run
from notas.domain.models import (
    Food,
    FoodAlias,
    FoodLocalizedName,
    FoodPortion,
    FoodSourceMetadata,
)


class FoodCatalogOperationalBackfillTests(TestCase):
    def test_dry_run_counts_trusted_operational_foods_without_writes(self):
        _create_trusted_food(name="Avena", canonical_name="avena")
        Food.objects.create(
            name="Food no verificado",
            canonical_name="food no verificado",
            protein=10,
            carbs=20,
            fat=3,
            created_by=None,
            is_global=True,
            is_verified=False,
            is_active=True,
        )

        result = dry_run_backfill_catalog_from_operational_foods()

        self.assertTrue(result.dry_run)
        self.assertIsNone(result.batch)
        self.assertEqual(result.total_rows, 1)
        self.assertEqual(result.created_rows, 1)
        self.assertEqual(result.skipped_rows, 0)
        self.assertEqual(result.reason_counts["would_create"], 1)
        self.assertEqual(CatalogFood.objects.count(), 0)
        self.assertEqual(CatalogImportBatch.objects.count(), 0)

    def test_backfill_creates_catalog_food_source_portions_and_aliases(self):
        food = _create_trusted_food(
            name="Pechuga de pollo cocida",
            canonical_name="pechuga de pollo cocida",
            protein=Decimal("31.0"),
            carbs=Decimal("0"),
            fat=Decimal("3.6"),
            food_group="meats",
            food_subgroup="chicken",
            data_quality_score=92,
            fiber_g_per_100g=Decimal("0"),
            sodium_mg_per_100g=Decimal("74"),
        )
        FoodPortion.objects.create(
            food=food,
            label="1 filete mediano",
            grams=Decimal("120"),
            source="manual",
            is_default=True,
        )
        FoodAlias.objects.create(
            food=food,
            name="Pollo cocido",
            normalized_name="pollo cocido",
            language="es",
            country="CL",
        )
        FoodLocalizedName.objects.create(
            food=food,
            name="Chicken breast cooked",
            normalized_name="chicken breast cooked",
            language="en",
            country="US",
            is_primary=True,
        )
        FoodSourceMetadata.objects.create(
            food=food,
            source=FoodSourceMetadata.SOURCE_USDA,
            source_food_id="12345",
            source_dataset="foundation_foods",
            source_version="2026-04",
            license_name="CC0",
            attribution="USDA FoodData Central",
        )

        result = self.governed_backfill(
            source_version="seed-2026-06",
            notes="Initial trusted foods backfill",
        )

        self.assertFalse(result.dry_run)
        self.assertIsNotNone(result.batch)
        self.assertEqual(result.total_rows, 1)
        self.assertEqual(result.created_rows, 1)
        self.assertEqual(result.skipped_rows, 0)
        self.assertEqual(CatalogFood.objects.count(), 1)
        self.assertEqual(CatalogFoodSource.objects.count(), 1)
        self.assertEqual(CatalogFoodPortion.objects.count(), 1)
        self.assertEqual(CatalogFoodAlias.objects.count(), 2)

        catalog_food = CatalogFood.objects.get()
        source = CatalogFoodSource.objects.get(catalog_food=catalog_food)
        batch = CatalogImportBatch.objects.get(is_dry_run=False)

        self.assertEqual(catalog_food.display_name, "Pechuga de pollo cocida")
        self.assertEqual(catalog_food.canonical_name, "pechuga de pollo cocida")
        self.assertEqual(catalog_food.status, CatalogFood.STATUS_PENDING_REVIEW)
        self.assertEqual(catalog_food.source_type, CatalogFood.SOURCE_ADMIN_IMPORT)
        self.assertEqual(catalog_food.protein_g_per_100g, Decimal("31.000"))
        self.assertEqual(catalog_food.carbs_g_per_100g, Decimal("0.000"))
        self.assertEqual(catalog_food.fat_g_per_100g, Decimal("3.600"))
        self.assertEqual(catalog_food.food_group, "meats")
        self.assertEqual(catalog_food.food_subgroup, "chicken")
        self.assertEqual(catalog_food.data_quality_score, 92)

        self.assertEqual(source.source_name, OPERATIONAL_BACKFILL_SOURCE_NAME)
        self.assertEqual(source.source_food_id, str(food.id))
        self.assertEqual(source.source_dataset, OPERATIONAL_BACKFILL_SOURCE_DATASET)
        self.assertEqual(source.source_version, "seed-2026-06")
        self.assertEqual(source.license_status, CatalogFoodSource.LICENSE_ALLOWED)
        self.assertEqual(source.evidence_payload["operational_food_id"], food.id)
        self.assertEqual(source.evidence_payload["original_source_metadata"]["source_food_id"], "12345")

        self.assertEqual(batch.source_name, OPERATIONAL_BACKFILL_SOURCE_NAME)
        self.assertEqual(batch.source_version, "seed-2026-06")
        self.assertEqual(batch.imported_rows, 1)
        self.assertEqual(batch.skipped_rows, 0)
        self.assertEqual(batch.failed_rows, 0)
        self.assertEqual(batch.status, CatalogImportBatch.STATUS_COMPLETED)

        portion = CatalogFoodPortion.objects.get(catalog_food=catalog_food)
        self.assertEqual(portion.label, "1 filete mediano")
        self.assertEqual(portion.grams, Decimal("120.000"))
        self.assertTrue(portion.is_default)

        alias_names = set(CatalogFoodAlias.objects.values_list("name", flat=True))
        self.assertEqual(alias_names, {"Pollo cocido", "Chicken breast cooked"})

        food.refresh_from_db()
        self.assertIsNone(food.catalog_food_id)
        self.assertIsNone(food.catalog_food_ref)
        self.assertEqual(food.catalog_sync_status, Food.CATALOG_SYNC_NONE)

    def test_backfill_skips_already_catalog_linked_operational_foods(self):
        catalog_food = CatalogFood.objects.create(
            display_name="Avena",
            canonical_name="avena",
            protein_g_per_100g=Decimal("16.900"),
            carbs_g_per_100g=Decimal("66.300"),
            fat_g_per_100g=Decimal("6.900"),
            status=CatalogFood.STATUS_PUBLISHED,
            source_type=CatalogFood.SOURCE_ADMIN_IMPORT,
        )
        _create_trusted_food(
            name="Avena",
            canonical_name="avena",
            catalog_food_id=catalog_food.id,
            catalog_food_ref=catalog_food.catalog_ref,
        )

        result = self.governed_backfill()

        self.assertEqual(result.created_rows, 0)
        self.assertEqual(result.skipped_rows, 1)
        self.assertEqual(result.reason_counts["already_linked_to_catalog"], 1)
        self.assertEqual(CatalogFood.objects.count(), 1)

    def test_backfill_skips_existing_catalog_canonical_name(self):
        CatalogFood.objects.create(
            display_name="Avena existente",
            canonical_name="avena",
            protein_g_per_100g=Decimal("16.900"),
            carbs_g_per_100g=Decimal("66.300"),
            fat_g_per_100g=Decimal("6.900"),
            status=CatalogFood.STATUS_REVIEWED,
            source_type=CatalogFood.SOURCE_ADMIN_IMPORT,
        )
        _create_trusted_food(name="Avena", canonical_name="avena")

        result = self.governed_backfill()

        self.assertEqual(result.created_rows, 0)
        self.assertEqual(result.skipped_rows, 1)
        self.assertEqual(result.reason_counts["already_cataloged_canonical_name"], 1)
        self.assertEqual(CatalogFood.objects.count(), 1)

    def test_management_command_supports_dry_run(self):
        _create_trusted_food(name="Lentejas cocidas", canonical_name="lentejas cocidas")

        call_command("backfill_catalog_from_operational_foods", dry_run=True, reason="Validate backfill.")

        self.assertEqual(CatalogFood.objects.count(), 0)
        self.assertEqual(CatalogImportBatch.objects.filter(is_dry_run=True).count(), 1)

    def test_management_command_creates_catalog_batch(self):
        _create_trusted_food(name="Arroz blanco cocido", canonical_name="arroz blanco cocido")

        call_command(
            "backfill_catalog_from_operational_foods",
            dry_run=True,
            source_version="seed-2026-06",
            reason="Validate command backfill.",
        )
        dry_run = CatalogImportBatch.objects.get(is_dry_run=True)
        call_command(
            "backfill_catalog_from_operational_foods",
            source_version="seed-2026-06",
            notes="Command test",
            reason="Apply command backfill.",
            dry_run_batch_id=dry_run.pk,
        )

        self.assertEqual(CatalogFood.objects.count(), 1)
        batch = CatalogImportBatch.objects.get(is_dry_run=False)
        self.assertEqual(batch.source_version, "seed-2026-06")
        self.assertEqual(batch.notes, "Command test")
        self.assertEqual(batch.imported_rows, 1)

    def test_private_user_food_is_never_eligible_or_promoted(self):
        owner = get_user_model().objects.create_user(username="private-food-owner")
        Food.objects.create(
            name="Receta privada",
            canonical_name="receta privada",
            protein=10,
            carbs=20,
            fat=5,
            created_by=owner,
            is_global=False,
            is_verified=True,
            is_active=True,
        )

        plan = dry_run_backfill_catalog_from_operational_foods()

        self.assertEqual(plan.total_rows, 0)
        self.assertEqual(plan.created_rows, 0)
        self.assertEqual(CatalogFood.objects.count(), 0)

    def governed_backfill(self, **kwargs):
        limit = kwargs.get("limit")
        source_name = kwargs.get("source_name", OPERATIONAL_BACKFILL_SOURCE_NAME)
        source_version = kwargs.get("source_version", DEFAULT_OPERATIONAL_BACKFILL_SOURCE_VERSION)
        status = kwargs.get("status", DEFAULT_OPERATIONAL_BACKFILL_STATUS)
        plan = dry_run_backfill_catalog_from_operational_foods(
            limit=limit,
            source_name=source_name,
            source_version=source_version,
            status=status,
        )
        dry_run = record_catalog_import_dry_run(
            identity=operational_backfill_identity(
                source_name=source_name,
                source_version=source_version,
                limit=limit,
                status=status,
            ),
            total_rows=plan.total_rows,
            would_import_rows=plan.created_rows,
            skipped_rows=plan.skipped_rows,
            failed_rows=plan.failed_rows,
            reason="Validate operational backfill.",
        )
        return backfill_catalog_from_operational_foods(
            **kwargs,
            dry_run_batch=dry_run,
            reason="Apply operational backfill.",
        )


def _create_trusted_food(
    *,
    name: str,
    canonical_name: str,
    protein=Decimal("16.9"),
    carbs=Decimal("66.3"),
    fat=Decimal("6.9"),
    food_group: str = "",
    food_subgroup: str = "",
    data_quality_score: int = 85,
    fiber_g_per_100g=None,
    sodium_mg_per_100g=None,
    catalog_food_id=None,
    catalog_food_ref=None,
) -> Food:
    return Food.objects.create(
        name=name,
        canonical_name=canonical_name,
        protein=float(protein),
        carbs=float(carbs),
        fat=float(fat),
        created_by=None,
        is_global=True,
        is_verified=True,
        is_active=True,
        food_group=food_group,
        food_subgroup=food_subgroup,
        data_quality_score=data_quality_score,
        visibility=Food.VISIBILITY_CORE,
        fiber_g_per_100g=fiber_g_per_100g,
        sodium_mg_per_100g=sodium_mg_per_100g,
        catalog_food_id=catalog_food_id,
        catalog_food_ref=catalog_food_ref,
    )
