import json
from decimal import Decimal

from django.test import override_settings

from food_catalog.infrastructure.preparations import PreparationPublicationError, publish_preparation_version
from food_catalog.infrastructure.releases import CatalogReleaseError, approve_catalog_release, build_catalog_release, import_catalog_release, release_envelope
from food_catalog.models import CatalogFood, CatalogPreparation, CatalogPreparationIngredient, CatalogPreparationVersion, CatalogRelease
from mobile_api.tests.base import AuthenticatedMobileAPITestCase
from notas.application.services.calendarization.snapshots import build_meal_snapshot
from notas.application.services.commands.preparation_commands import materialize_preparation_and_refresh
from notas.application.services.nutrition.meal_nutrition import rebuild_meal_cached_state
from notas.application.services.cache.dailyplan_summary import refresh_dailyplan_and_related_program_caches
from notas.application.services.commands.meal_commands import copy_meal
from notas.application.sharing.entities import build_meal_share_snapshot
from notas.application.sharing.inbox import _meal_from_snapshot
from notas.domain.models import DailyPlan, DailyPlanMeal, Food, Meal, MealFood, MealPreparation, Preparation, Program, ProgramDay
from notas.management.commands.import_food_catalog_release import _materialize_release


@override_settings(NUTRITION_ONBOARDING_GATE_ENABLED=False)
class PreparationAPITests(AuthenticatedMobileAPITestCase):
    def setUp(self):
        super().setUp()
        self.user.is_staff = True
        self.user.save(update_fields=["is_staff"])
        self.food = CatalogFood.objects.create(
            display_name="Ingrediente de prueba", status=CatalogFood.STATUS_PUBLISHED,
            preparation_state=CatalogFood.PREPARATION_COOKED,
            protein_g_per_100g=Decimal("10"), carbs_g_per_100g=Decimal("20"),
            fat_g_per_100g=Decimal("5"), sodium_mg_per_100g=Decimal("40"),
            allergens=["milk"],
        )
        self.operational_food = Food.objects.create(
            name="Ingrediente de prueba", protein=10, carbs=20, fat=5,
            sodium_mg_per_100g=Decimal("40"), is_global=True,
            catalog_food_ref=self.food.catalog_ref, catalog_food_id=self.food.id,
        )
        self.catalog_preparation = CatalogPreparation.objects.create(display_name="Preparación de prueba")
        self.v1 = self._draft_version(1, Decimal("80"))

    def _draft_version(self, number, yield_g):
        version = CatalogPreparationVersion.objects.create(
            preparation=self.catalog_preparation, version=number, yield_g=yield_g,
            default_portion_g=Decimal("40"), household_label="unidad",
            source_name="Fuente de prueba", yield_evidence="Medición de prueba",
        )
        CatalogPreparationIngredient.objects.create(
            version=version, food=self.food, quantity_g=Decimal("100"),
            preparation_state=CatalogFood.PREPARATION_COOKED,
        )
        return version

    def _publish_and_materialize(self, version):
        publish_preparation_version(version, actor=self.user)
        return materialize_preparation_and_refresh(self.catalog_preparation, release_version="test-release")

    def test_publication_requires_confirmed_sodium_and_allergens(self):
        self.food.sodium_mg_per_100g = None
        self.food.save(update_fields=["sodium_mg_per_100g"])
        with self.assertRaisesRegex(PreparationPublicationError, "nutrition_incomplete"):
            publish_preparation_version(self.v1, actor=self.user)
        self.food.sodium_mg_per_100g = Decimal("40")
        self.food.allergens = []
        self.food.save(update_fields=["sodium_mg_per_100g", "allergens"])
        with self.assertRaisesRegex(PreparationPublicationError, "allergens_unconfirmed"):
            publish_preparation_version(self.v1, actor=self.user)

    def test_release_contains_preparation_with_frozen_ingredients(self):
        self._publish_and_materialize(self.v1)
        release = approve_catalog_release(build_catalog_release(version="synthetic.1"))
        envelope = release_envelope(release)
        self.assertEqual(envelope["release"]["preparation_count"], 1)
        self.assertEqual(envelope["payload"]["preparations"][0]["ingredients"][0]["catalog_food_ref"], str(self.food.catalog_ref))
        self.assertEqual(envelope["payload"]["preparations"][0]["nutrition"]["sodium_mg"], "40.00000")
        CatalogRelease.objects.all().delete()
        self.catalog_preparation.current_version = None
        self.catalog_preparation.save(update_fields=["current_version"])
        CatalogPreparationIngredient.objects.all().delete()
        CatalogPreparationVersion.objects.all().delete()
        CatalogPreparation.objects.all().delete()
        import_catalog_release(envelope)
        restored = CatalogPreparation.objects.get()
        self.assertEqual(restored.current_version.version, 1)
        self.assertEqual(restored.current_version.ingredients.count(), 1)

    def test_changed_ingredient_requires_new_preparation_revision_before_release(self):
        self._publish_and_materialize(self.v1)
        self.food.sodium_mg_per_100g = Decimal("90")
        self.food.save(update_fields=["sodium_mg_per_100g"])
        with self.assertRaisesRegex(CatalogReleaseError, "changed_requires_revision"):
            build_catalog_release(version="synthetic.changed")

    def test_withdrawn_catalog_preparation_is_removed_from_mobile_catalog(self):
        self._publish_and_materialize(self.v1)
        self.catalog_preparation.is_active = False
        self.catalog_preparation.save(update_fields=["is_active"])
        _materialize_release(version="synthetic.withdrawn")
        self.assertFalse(Preparation.objects.get().is_active)
        self.assertEqual(self.client.get("/api/v1/preparations").json()["data"]["total"], 0)

    def test_meal_portion_copy_and_calendar_snapshot_are_independent_of_new_version(self):
        operational_version = self._publish_and_materialize(self.v1)
        meal = Meal.objects.create(name="Comida de prueba", created_by=self.user, is_draft=False)
        MealFood.objects.create(meal=meal, food=self.operational_food, quantity=50)
        relation = MealPreparation.objects.create(
            meal=meal, preparation=operational_version.preparation, version=operational_version,
            quantity_g=Decimal("40"), selected_units=Decimal("1"), selection_mode="units",
        )
        rebuild_meal_cached_state(meal)
        self.assertAlmostEqual(meal.protein, 10)
        dailyplan = DailyPlan.objects.create(name="Minuta de prueba", created_by=self.user, is_draft=False)
        DailyPlanMeal.objects.create(dailyplan=dailyplan, meal=meal)
        program = Program.objects.create(name="Programa de prueba", created_by=self.user, duration_weeks=1)
        ProgramDay.objects.create(program=program, dailyplan=dailyplan, week_number=1, day_number=1)
        refresh_dailyplan_and_related_program_caches(dailyplan)
        initial_plan_summary = DailyPlan.objects.get(pk=dailyplan.pk).summary_cache
        self.assertEqual(initial_plan_summary["foods_aggregation_table"][0]["rel"]["quantity"], 100)
        self.assertIn("Preparación de prueba", initial_plan_summary["menu"][0]["foods"][1])
        initial_program_summary = Program.objects.get(pk=program.pk).summary_cache
        self.assertAlmostEqual(Program.objects.get(pk=program.pk).protein, 10)
        self.assertEqual(initial_program_summary["program_foods_aggregation_table"][0]["rel"]["quantity"], 100)
        frozen = json.loads(json.dumps(build_meal_snapshot(meal=meal, key="meal:1", order=0, hour=None)))
        self.assertEqual(len(frozen["foods"]), 2)
        self.assertEqual(frozen["totals"]["protein_g"], 10)
        self.assertEqual(frozen["foods"][1]["ingredients"][0]["quantity_g"], 50)
        self.v2 = self._draft_version(2, Decimal("100"))
        self._publish_and_materialize(self.v2)
        relation.refresh_from_db()
        self.assertEqual(relation.version.version, 2)
        self.assertEqual(relation.quantity_g, Decimal("40"))
        self.assertAlmostEqual(Meal.objects.get(pk=meal.pk).protein, 9)
        self.assertAlmostEqual(DailyPlan.objects.get(pk=dailyplan.pk).protein, 9)
        self.assertAlmostEqual(Program.objects.get(pk=program.pk).protein, 9)
        self.assertEqual(DailyPlan.objects.get(pk=dailyplan.pk).summary_cache["foods_aggregation_table"][0]["rel"]["quantity"], 90)
        self.assertEqual(frozen["totals"]["protein_g"], 10)

    def test_mobile_selection_and_permissions(self):
        self._publish_and_materialize(self.v1)
        preparation = Preparation.objects.get()
        meal = Meal.objects.create(name="Comida de prueba", created_by=self.user)
        response = self.client.get(f"/api/v1/preparations/{preparation.id}?units=1.5")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["grams"], 60)
        ingredient = response.json()["data"]["ingredients"][0]
        self.assertEqual(ingredient["quantity_g"], 75)
        self.assertEqual(ingredient["protein_g"], 7.5)
        self.assertEqual(ingredient["carbs_g"], 15)
        self.assertEqual(ingredient["fat_g"], 3.75)
        self.assertEqual(ingredient["calories"], 123.75)
        response = self.client.post(
            f"/api/v1/library/meals/{meal.id}/preparations",
            data=json.dumps({"preparation_id": preparation.id, "units": 1.5}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(MealPreparation.objects.get().quantity_g, Decimal("60"))
        self.assertEqual(Meal.objects.get(pk=meal.pk).is_draft, False)
        detail = self.client.get(f"/api/v1/library/meals/{meal.id}").json()["data"]
        self.assertEqual(detail["indicators"][1], {"icon": "preparation", "label": "preparaciones", "value": 1})
        listing = self.client.get("/api/v1/library/meals").json()["data"]["items"]
        self.assertEqual(listing[0]["indicators"][1], {"icon": "preparation", "label": "preparaciones", "value": 1})
        panel = detail["panel"]["preparations"][0]
        self.assertEqual(panel["protein_g"], 7.5)
        self.assertEqual(panel["carbs_g"], 15)
        self.assertEqual(panel["fat_g"], 3.75)
        self.assertEqual(panel["ingredients"][0]["calories"], 123.75)
        self.operational_food.protein = 90
        self.operational_food.save(update_fields=["protein"])
        frozen = self.client.get(f"/api/v1/preparations/{preparation.id}?units=1.5").json()["data"]
        self.assertEqual(frozen["ingredients"][0]["protein_g"], 7.5)
        by_weight = self.client.get(f"/api/v1/preparations/{preparation.id}?grams=20").json()["data"]
        self.assertEqual(by_weight["ingredients"][0]["quantity_g"], 25)
        self.assertEqual(by_weight["ingredients"][0]["protein_g"], 2.5)
        invalid = self.client.post(
            f"/api/v1/library/meals/{meal.id}/preparations",
            data=json.dumps({"preparation_id": preparation.id, "units": 0.7}),
            content_type="application/json",
        )
        self.assertEqual(invalid.status_code, 422)
        other = type(self.user).objects.create_user(username="other-preparation-user")
        other_meal = Meal.objects.create(name="Privada", created_by=other)
        denied = self.client.post(
            f"/api/v1/library/meals/{other_meal.id}/preparations",
            data=json.dumps({"preparation_id": preparation.id, "units": 1}),
            content_type="application/json",
        )
        self.assertEqual(denied.status_code, 404)
        relation_id = MealPreparation.objects.get().id
        removed = self.client.delete(f"/api/v1/library/meals/{meal.id}/preparations/{relation_id}")
        self.assertEqual(removed.status_code, 200)
        self.assertFalse(MealPreparation.objects.filter(pk=relation_id).exists())

    def test_replace_preparation_keeps_relation_and_recalculates_meal(self):
        self._publish_and_materialize(self.v1)
        original = Preparation.objects.get()
        meal = Meal.objects.create(name="Comida de prueba", created_by=self.user)
        added = self.client.post(
            f"/api/v1/library/meals/{meal.id}/preparations",
            data=json.dumps({"preparation_id": original.id, "units": 1}),
            content_type="application/json",
        )
        self.assertEqual(added.status_code, 200)
        relation_id = added.json()["data"]["created_id"]
        original_protein = Meal.objects.get(pk=meal.pk).protein
        second_catalog = CatalogPreparation.objects.create(display_name="Otra preparación")
        second_version = CatalogPreparationVersion.objects.create(
            preparation=second_catalog, version=1, yield_g=Decimal("100"),
            default_portion_g=Decimal("100"), household_label="unidad",
            source_name="Fuente de prueba", yield_evidence="Medición de prueba",
        )
        CatalogPreparationIngredient.objects.create(
            version=second_version, food=self.food, quantity_g=Decimal("100"),
            preparation_state=CatalogFood.PREPARATION_COOKED,
        )
        publish_preparation_version(second_version, actor=self.user)
        materialize_preparation_and_refresh(second_catalog, release_version="test-release")
        replacement = Preparation.objects.get(name="Otra preparación")
        changed = self.client.patch(
            f"/api/v1/library/meals/{meal.id}/preparations/{relation_id}",
            data=json.dumps({"preparation_id": replacement.id, "units": 1}),
            content_type="application/json",
        )
        self.assertEqual(changed.status_code, 200)
        relation = MealPreparation.objects.get(pk=relation_id)
        self.assertEqual(relation.preparation_id, replacement.id)
        self.assertEqual(relation.quantity_g, Decimal("100"))
        self.assertEqual(MealPreparation.objects.filter(meal=meal).count(), 1)
        self.assertGreater(Meal.objects.get(pk=meal.pk).protein, original_protein)
        self.assertEqual(self.client.get(f"/api/v1/library/meals/{meal.id}").json()["data"]["panel"]["preparations"][0]["name"], "Otra preparación")
        rejected = self.client.patch(
            f"/api/v1/library/meals/{meal.id}/preparations/{relation_id}",
            data=json.dumps({"preparation_id": replacement.id + 1000000, "units": 2}),
            content_type="application/json",
        )
        self.assertEqual(rejected.status_code, 404)
        relation.refresh_from_db()
        self.assertEqual(relation.preparation_id, replacement.id)
        self.assertEqual(relation.quantity_g, Decimal("100"))

    def test_copy_and_share_preserve_preparation_identity(self):
        version = self._publish_and_materialize(self.v1)
        meal = Meal.objects.create(name="Comida de prueba", created_by=self.user, is_draft=False)
        MealPreparation.objects.create(
            meal=meal, preparation=version.preparation, version=version,
            quantity_g=Decimal("60"), selected_units=Decimal("1.5"), selection_mode="units",
        )
        copied = copy_meal(meal, self.user)
        copied_relation = copied.meal_preparation_set.get()
        self.assertEqual(copied_relation.preparation_id, version.preparation_id)
        self.assertEqual(copied_relation.selected_units, Decimal("1.5"))
        snapshot = build_meal_share_snapshot(meal)
        self.assertEqual(snapshot["summary"]["preparation_count"], 1)
        self.assertEqual(snapshot["nutrition"]["protein_grams"], 7.5)
        imported = _meal_from_snapshot(snapshot=snapshot, actor=self.user)
        self.assertEqual(imported.meal_preparation_set.get().version_id, version.id)
