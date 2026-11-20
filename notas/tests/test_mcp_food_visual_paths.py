from django.contrib.auth.models import User
from django.test import TestCase

from food_catalog.models import CatalogFood, FoodVisualAsset
from notas.application.ai_tools.proposal_tools import _with_published_simulation_food_images
from notas.application.queries.dailyplan_queries import build_dailyplan_dto
from notas.application.queries.food_queries import build_food_dto
from notas.application.queries.food_visual_queries import published_food_visual_paths
from notas.application.queries.meal_queries import build_meal_dto
from notas.domain.models import DailyPlan, DailyPlanMeal, Food, LegacyFoodVisualAsset, Meal, MealFood


class MCPFoodVisualPathTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("visual-reader")
        self.catalog = CatalogFood.objects.create(
            display_name="Avena tradicional", status=CatalogFood.STATUS_PUBLISHED,
            protein_g_per_100g=13, carbs_g_per_100g=67, fat_g_per_100g=7,
        )
        self.food = Food.objects.create(
            name="Avena tradicional", protein=13, carbs=67, fat=7,
            is_global=True, catalog_food_id=self.catalog.id,
            catalog_food_ref=self.catalog.catalog_ref,
        )
        self.asset = FoodVisualAsset.objects.create(
            food=self.catalog, image_data=b"image", mobile_image_data=b"image",
            content_sha256="a" * 64, is_published=True,
        )

    def test_published_image_reaches_food_and_meal_read_dtos(self):
        path = f"/api/v1/foods/visual-assets/{self.catalog.catalog_ref}/{'a' * 64}.png"
        self.assertEqual(build_food_dto(self.food).as_dict()["image_path"], path)
        meal = Meal.objects.create(name="Avena con fruta", created_by=self.user, is_draft=False)
        MealFood.objects.create(meal=meal, food=self.food, quantity=100, order=1)
        self.assertEqual(build_meal_dto(meal, self.user).as_dict()["foods"][0]["image_path"], path)
        dailyplan = DailyPlan.objects.create(name="Día con avena", created_by=self.user, is_draft=False)
        DailyPlanMeal.objects.create(dailyplan=dailyplan, meal=meal, order=1)
        plan_data = build_dailyplan_dto(dailyplan, self.user).as_dict()
        self.assertEqual(plan_data["meals"][0]["foods"][0]["image_path"], path)
        self.assertEqual(plan_data["foods_aggregation"][0]["image_path"], path)

    def test_unpublished_or_private_food_has_no_public_image_path(self):
        self.asset.is_published = False
        self.asset.save(update_fields=["is_published"])
        self.assertNotIn("image_path", build_food_dto(self.food).as_dict())
        self.asset.is_published = True
        self.asset.save(update_fields=["is_published"])
        private_food = Food.objects.create(name="Avena personal", protein=13, carbs=67, fat=7, created_by=self.user)
        self.assertEqual(published_food_visual_paths([private_food]), {})
        self.asset.mobile_image_data = b""
        self.asset.save(update_fields=["mobile_image_data"])
        self.assertNotIn("image_path", build_food_dto(self.food).as_dict())

    def test_generated_proposal_response_adds_only_published_food_image(self):
        proposal = {"validation_summary": {"simulation": {"dailyplan": {"meals": [
            {"meal": {"foods": [{"food_id": self.food.id, "food_name": "Avena tradicional"}]}}
        ]}}}}
        response = _with_published_simulation_food_images(proposal)
        image = response["validation_summary"]["simulation"]["dailyplan"]["meals"][0]["meal"]["foods"][0]
        self.assertIn("image_path", image)
        self.assertNotIn("image_path", proposal["validation_summary"]["simulation"]["dailyplan"]["meals"][0]["meal"]["foods"][0])
        self.asset.is_published = False
        self.asset.save(update_fields=["is_published"])
        proposal["validation_summary"]["simulation"]["dailyplan"]["meals"][0]["meal"]["foods"][0]["image_path"] = "https://untrusted.example/food.png"
        unpublished = _with_published_simulation_food_images(proposal)
        self.assertNotIn("image_path", unpublished["validation_summary"]["simulation"]["dailyplan"]["meals"][0]["meal"]["foods"][0])

    def test_published_operational_override_takes_precedence(self):
        override = LegacyFoodVisualAsset.objects.create(
            food=self.food, image_data=b"override", mobile_image_data=b"override",
            content_sha256="b" * 64, is_published=True,
        )
        path = f"/api/v1/foods/visual-assets/{override.public_ref}/{'b' * 64}.png"
        self.assertEqual(build_food_dto(self.food).as_dict()["image_path"], path)
        self.catalog.status = CatalogFood.STATUS_REVIEWED
        self.catalog.save(update_fields=["status"])
        self.assertNotIn("image_path", build_food_dto(self.food).as_dict())
