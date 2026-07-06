from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase

from food_catalog.models import (
    CatalogFood,
    CatalogFoodAlias,
    CatalogFoodPortion,
    CatalogFoodSource,
)
from notas.application.queries.food_catalog_queries import list_food_catalog_for_planning
from notas.application.services.food_catalog_snapshots import (
    CatalogFoodNotPublishedError,
    FOOD_CATALOG_PORTION_SOURCE,
    build_operational_food_snapshot_payload,
    create_operational_food_snapshot_from_catalog,
    mark_operational_food_catalog_snapshot_stale,
    refresh_operational_food_snapshot_from_catalog,
)
from notas.domain.models import Food


class FoodCatalogSnapshotProtocolTests(TestCase):
    def test_build_payload_requires_published_catalog_food(self):
        catalog_food = CatalogFood.objects.create(
            display_name="Candidato no publicado",
            canonical_name="candidato no publicado",
            protein_g_per_100g=Decimal("10.000"),
            carbs_g_per_100g=Decimal("20.000"),
            fat_g_per_100g=Decimal("3.000"),
            status=CatalogFood.STATUS_REVIEWED,
            source_type=CatalogFood.SOURCE_ADMIN_IMPORT,
        )

        with self.assertRaises(CatalogFoodNotPublishedError):
            build_operational_food_snapshot_payload(catalog_food)

    def test_create_operational_food_snapshot_copies_values_into_notas_food(self):
        catalog_food = self._create_published_catalog_food()

        result = create_operational_food_snapshot_from_catalog(catalog_food)
        food = result.food

        self.assertIsInstance(food, Food)
        self.assertEqual(food.name, "Pechuga de pollo cocida")
        self.assertEqual(food.protein, 31.0)
        self.assertEqual(food.carbs, 0.0)
        self.assertEqual(food.fat, 3.6)
        self.assertEqual(food.food_group, "meats")
        self.assertEqual(food.food_subgroup, "poultry")
        self.assertEqual(food.preparation_state, Food.PREPARATION_COOKED)
        self.assertTrue(food.solver_enabled)
        self.assertTrue(food.is_global)
        self.assertTrue(food.is_verified)
        self.assertTrue(food.is_active)
        self.assertEqual(food.visibility, Food.VISIBILITY_EXTENDED)
        self.assertEqual(food.catalog_food_id, catalog_food.id)
        self.assertEqual(food.catalog_food_ref, catalog_food.catalog_ref)
        self.assertEqual(food.catalog_snapshot_version, "v1")
        self.assertEqual(food.catalog_sync_status, Food.CATALOG_SYNC_SNAPSHOT)
        self.assertIsNotNone(food.catalog_snapshot_created_at)
        self.assertEqual(food.catalog_snapshot_payload["source"], "food_catalog")
        self.assertEqual(food.catalog_snapshot_payload["catalog_food_id"], catalog_food.id)
        self.assertEqual(food.catalog_snapshot_payload["contract"]["food_defaults"]["preparation_state"], "cooked")
        self.assertTrue(food.catalog_snapshot_payload["contract"]["food_defaults"]["solver_enabled"])
        self.assertNotIn("food_id", food.catalog_snapshot_payload)
        self.assertAlmostEqual(food.total_kcal, 156.4)
        self.assertEqual(result.created_portions, 1)
        self.assertEqual(result.created_aliases, 1)
        self.assertEqual(result.skipped_aliases, 0)
        self.assertEqual(food.portions.get().source, FOOD_CATALOG_PORTION_SOURCE)
        self.assertEqual(food.portions.get().grams, Decimal("120.000"))
        self.assertEqual(food.default_portion_g, Decimal("120.000"))
        self.assertEqual(food.min_portion_g, Decimal("60.000"))
        self.assertEqual(food.max_portion_g, Decimal("300.000"))
        self.assertEqual(food.portion_step_g, Decimal("10.000"))
        self.assertEqual(food.aliases.get().normalized_name, "pollo cocido")

    def test_catalog_trace_fields_are_not_foreign_keys(self):
        catalog_food_id_field = Food._meta.get_field("catalog_food_id")
        catalog_food_ref_field = Food._meta.get_field("catalog_food_ref")

        self.assertIsNone(catalog_food_id_field.remote_field)
        self.assertIsNone(catalog_food_ref_field.remote_field)

    def test_refresh_operational_food_snapshot_updates_existing_food(self):
        catalog_food = self._create_published_catalog_food()
        result = create_operational_food_snapshot_from_catalog(catalog_food)
        food = result.food
        original_food_id = food.id

        catalog_food.display_name = "Pechuga de pollo cocida actualizada"
        catalog_food.protein_g_per_100g = Decimal("32.000")
        catalog_food.fat_g_per_100g = Decimal("4.000")
        catalog_food.catalog_version = "v2"
        catalog_food.save(update_fields=["display_name", "protein_g_per_100g", "fat_g_per_100g", "catalog_version"])

        refreshed = refresh_operational_food_snapshot_from_catalog(food).food

        self.assertEqual(refreshed.id, original_food_id)
        self.assertEqual(refreshed.name, "Pechuga de pollo cocida actualizada")
        self.assertEqual(refreshed.protein, 32.0)
        self.assertEqual(refreshed.fat, 4.0)
        self.assertEqual(refreshed.catalog_snapshot_version, "v2")
        self.assertEqual(refreshed.catalog_sync_status, Food.CATALOG_SYNC_SNAPSHOT)
        self.assertEqual(refreshed.catalog_snapshot_payload["catalog_version"], "v2")

    def test_mark_snapshot_stale_does_not_change_operational_nutrition(self):
        catalog_food = self._create_published_catalog_food()
        food = create_operational_food_snapshot_from_catalog(catalog_food).food

        result = mark_operational_food_catalog_snapshot_stale(food)
        food.refresh_from_db()

        self.assertEqual(result.food.id, food.id)
        self.assertEqual(food.catalog_sync_status, Food.CATALOG_SYNC_STALE)
        self.assertEqual(food.protein, 31.0)
        self.assertEqual(food.carbs, 0.0)
        self.assertEqual(food.fat, 3.6)

    def test_mcp_planning_catalog_still_lists_only_notas_food_ids(self):
        user = User.objects.create_user(username="planner", password="x")
        catalog_food = self._create_published_catalog_food()
        operational_food = create_operational_food_snapshot_from_catalog(catalog_food).food

        catalog = list_food_catalog_for_planning(user=user).as_dict()
        first_item = catalog["foods"][0]

        self.assertEqual(first_item["food_id"], operational_food.id)
        self.assertNotIn("catalog_food_id", first_item)
        self.assertNotIn("catalog_food_ref", first_item)

    def _create_published_catalog_food(self) -> CatalogFood:
        catalog_food = CatalogFood.objects.create(
            display_name="Pechuga de pollo cocida",
            canonical_name="pechuga pollo cocida",
            catalog_version="v1",
            food_group="meats",
            food_subgroup="poultry",
            preparation_state=CatalogFood.PREPARATION_COOKED,
            solver_enabled=True,
            protein_g_per_100g=Decimal("31.000"),
            carbs_g_per_100g=Decimal("0.000"),
            fat_g_per_100g=Decimal("3.600"),
            calories_kcal_per_100g=Decimal("165.000"),
            fiber_g_per_100g=Decimal("0.000"),
            status=CatalogFood.STATUS_PUBLISHED,
            source_type=CatalogFood.SOURCE_NATURAL_VERIFIED,
            data_quality_score=95,
        )
        CatalogFoodPortion.objects.create(
            catalog_food=catalog_food,
            label="1 porción",
            grams=Decimal("120.000"),
            source="reviewed",
            is_default=True,
        )
        CatalogFoodAlias.objects.create(
            catalog_food=catalog_food,
            name="pollo cocido",
            normalized_name="pollo cocido",
            language="es",
            is_primary=True,
        )
        CatalogFoodSource.objects.create(
            catalog_food=catalog_food,
            source_type=CatalogFood.SOURCE_NATURAL_VERIFIED,
            source_name="Tabla oficial",
            source_food_id="pollo-cocido-001",
            source_version="2026",
            license_status=CatalogFoodSource.LICENSE_ALLOWED,
            normalized_payload_hash="hash-1",
        )
        return catalog_food
