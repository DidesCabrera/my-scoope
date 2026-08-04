from django.contrib.auth import get_user_model
from django.test import TestCase

from notas.domain.models import (
    DailyPlan,
    DailyPlanMeal,
    Food,
    FoodLocalizedName,
    Meal,
    MealFood,
)
from notas.presentation.composition.viewmodel.components.builder_table_items import (
    build_dailyplanmeal_table_item,
    build_mealfood_table_item,
)

User = get_user_model()


class BuilderTableItemsTests(TestCase):
    def test_build_mealfood_table_item_uses_food_display_name(self):
        user = User.objects.create_user(
            username="felipe",
            email="felipe@test.com",
            password="12345678",
        )

        meal = Meal.objects.create(
            name="Meal test",
            created_by=user,
        )

        food = Food.objects.create(
            name="Oats, raw",
            canonical_name="oats raw",
            protein=16.9,
            carbs=66.3,
            fat=6.9,
            created_by=None,
            is_global=True,
            is_active=True,
            visibility=Food.VISIBILITY_CORE,
            data_quality_score=90,
        )

        FoodLocalizedName.objects.create(
            food=food,
            name="Avena",
            normalized_name="avena",
            language="es",
            country="CL",
            is_primary=True,
        )

        meal_food = MealFood.objects.create(
            meal=meal,
            food=food,
            quantity=100,
        )

        item = build_mealfood_table_item(meal_food)

        self.assertEqual(item["rel"]["name"], "Avena")
        self.assertEqual(item["rel"]["quantity_unit"], "g")


class DailyPlanMealTableItemSnapshotTests(TestCase):
    def test_build_dailyplanmeal_table_item_uses_dailyplan_snapshot_without_queries(self):
        user = User.objects.create_user(
            username="snapshot_user",
            email="snapshot@test.com",
            password="12345678",
        )

        food = Food.objects.create(
            name="Chicken",
            protein=20,
            carbs=10,
            fat=5,
            created_by=user,
        )

        meal = Meal.objects.create(
            name="Lunch",
            created_by=user,
        )

        MealFood.objects.create(
            meal=meal,
            food=food,
            quantity=100,
        )

        meal.refresh_from_db()

        dailyplan = DailyPlan.objects.create(
            name="Training day",
            created_by=user,
        )

        dpm = DailyPlanMeal.objects.create(
            dailyplan=dailyplan,
            meal=meal,
            order=1,
        )

        dpm = DailyPlanMeal.objects.select_related(
            "dailyplan",
            "meal",
        ).get(pk=dpm.pk)

        dailyplan_snapshot = {
            "kcal_protein": meal.kcal_protein_cached,
            "kcal_carbs": meal.kcal_carbs_cached,
            "kcal_fat": meal.kcal_fat_cached,
            "total_kcal": meal.total_kcal_cached,
        }

        with self.assertNumQueries(0):
            item = build_dailyplanmeal_table_item(
                dpm,
                dailyplan_snapshot=dailyplan_snapshot,
            )

        self.assertEqual(item["main_id"], dailyplan.id)
        self.assertEqual(item["child_id"], meal.id)
        self.assertEqual(item["rel"]["kcal_share"], 100)
        self.assertEqual(item["rel"]["alloc_protein"], 100)
        self.assertEqual(item["rel"]["alloc_carbs"], 100)
        self.assertEqual(item["rel"]["alloc_fat"], 100)