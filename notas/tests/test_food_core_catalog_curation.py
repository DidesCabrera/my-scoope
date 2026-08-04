from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase

from notas.application.services.food_imports.core_catalog import (
    INITIAL_CORE_FOOD_CANONICAL_NAMES,
    is_initial_core_food,
)
from notas.application.services.food_imports.core_catalog_curation import (
    promote_initial_core_foods,
)
from notas.domain.models import Food

User = get_user_model()


class FoodCoreCatalogCurationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="felipe",
            email="felipe@test.com",
            password="12345678",
        )

        self.oats = Food.objects.create(
            name="Oats, raw",
            canonical_name="oats raw",
            protein=16.9,
            carbs=66.3,
            fat=6.9,
            created_by=None,
            is_global=True,
            is_verified=False,
            is_active=False,
            visibility=Food.VISIBILITY_HIDDEN,
            data_quality_score=75,
        )

        self.chicken = Food.objects.create(
            name="Chicken breast, cooked",
            canonical_name="chicken breast cooked",
            protein=31,
            carbs=0,
            fat=3.6,
            created_by=None,
            is_global=True,
            is_verified=False,
            is_active=True,
            visibility=Food.VISIBILITY_EXTENDED,
            data_quality_score=75,
        )

        self.unknown_global = Food.objects.create(
            name="Unknown global food",
            canonical_name="unknown global food",
            protein=1,
            carbs=1,
            fat=1,
            created_by=None,
            is_global=True,
            is_verified=False,
            is_active=True,
            visibility=Food.VISIBILITY_EXTENDED,
            data_quality_score=60,
        )

        self.user_food_with_same_name = Food.objects.create(
            name="Oats, raw user copy",
            canonical_name="oats raw",
            protein=16.9,
            carbs=66.3,
            fat=6.9,
            created_by=self.user,
            is_global=False,
            is_verified=False,
            is_active=True,
            visibility=Food.VISIBILITY_EXTENDED,
            data_quality_score=75,
        )

    def test_initial_core_catalog_contains_expected_foods(self):
        self.assertIn(
            "oats raw",
            INITIAL_CORE_FOOD_CANONICAL_NAMES,
        )
        self.assertIn(
            "chicken breast cooked",
            INITIAL_CORE_FOOD_CANONICAL_NAMES,
        )

    def test_is_initial_core_food_returns_true_for_known_food(self):
        self.assertTrue(
            is_initial_core_food("oats raw")
        )

    def test_is_initial_core_food_returns_false_for_unknown_food(self):
        self.assertFalse(
            is_initial_core_food("unknown global food")
        )

    def test_promote_initial_core_foods_promotes_known_global_foods(self):
        result = promote_initial_core_foods()

        self.assertEqual(result.matched_foods, 2)
        self.assertEqual(result.promoted_foods, 2)

        self.oats.refresh_from_db()
        self.chicken.refresh_from_db()
        self.unknown_global.refresh_from_db()

        self.assertEqual(self.oats.visibility, Food.VISIBILITY_CORE)
        self.assertTrue(self.oats.is_verified)
        self.assertTrue(self.oats.is_active)

        self.assertEqual(self.chicken.visibility, Food.VISIBILITY_CORE)
        self.assertTrue(self.chicken.is_verified)
        self.assertTrue(self.chicken.is_active)

        self.assertEqual(
            self.unknown_global.visibility,
            Food.VISIBILITY_EXTENDED,
        )
        self.assertFalse(self.unknown_global.is_verified)

    def test_promote_initial_core_foods_does_not_modify_user_foods(self):
        promote_initial_core_foods()

        self.user_food_with_same_name.refresh_from_db()

        self.assertFalse(self.user_food_with_same_name.is_global)
        self.assertFalse(self.user_food_with_same_name.is_verified)
        self.assertEqual(
            self.user_food_with_same_name.visibility,
            Food.VISIBILITY_EXTENDED,
        )

    def test_promote_initial_core_foods_command_runs(self):
        call_command("promote_initial_core_foods")

        self.oats.refresh_from_db()

        self.assertEqual(self.oats.visibility, Food.VISIBILITY_CORE)
        self.assertTrue(self.oats.is_verified)
        self.assertTrue(self.oats.is_active)