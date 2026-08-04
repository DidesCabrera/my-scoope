from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase

from notas.application.queries.performance.dailyplan_queries import (
    dailyplans_with_kcal,
    get_dailyplan_meals_with_foods,
)
from notas.application.services.nutrition.weight import get_current_weight
from notas.domain.models import (
    DailyPlan,
    DailyPlanMeal,
    Food,
    FoodLocalizedName,
    Meal,
    MealFood,
    WeightLog,
)
from notas.presentation.composition.viewmodel.components.builder_table_items import (
    build_mealfood_table_item,
)

User = get_user_model()


class WeightDefaultsTests(TestCase):
    def test_get_current_weight_uses_default_when_user_has_no_weight_log(self):
        user = User.objects.create_user(
            username="no_weight",
            email="no_weight@test.com",
            password="12345678",
        )

        self.assertEqual(get_current_weight(user), 75)

        with self.assertNumQueries(0):
            self.assertEqual(get_current_weight(user), 75)

    def test_get_current_weight_prefers_latest_weight_log(self):
        user = User.objects.create_user(
            username="with_weight",
            email="with_weight@test.com",
            password="12345678",
        )
        WeightLog.objects.create(
            user=user,
            date=date(2026, 1, 1),
            weight_kg=88,
        )

        self.assertEqual(get_current_weight(user), 88)


class DailyPlanQueryPatternTests(TestCase):
    def test_dailyplan_query_prefetches_food_display_names_for_card_rendering(self):
        user = User.objects.create_user(
            username="dailyplan_prefetch",
            email="dailyplan_prefetch@test.com",
            password="12345678",
        )
        dailyplan = DailyPlan.objects.create(
            name="Training day",
            created_by=user,
            is_draft=False,
        )

        meal = Meal.objects.create(
            name="Lunch",
            created_by=user,
            is_draft=False,
        )

        for index in range(3):
            food = Food.objects.create(
                name=f"Food {index}",
                protein=10,
                carbs=20,
                fat=5,
                created_by=user,
            )
            FoodLocalizedName.objects.create(
                food=food,
                name=f"Alimento {index}",
                normalized_name=f"alimento {index}",
                language="es",
                country="CL",
                is_primary=True,
            )
            MealFood.objects.create(
                meal=meal,
                food=food,
                quantity=100,
                order=index,
            )

        DailyPlanMeal.objects.create(
            dailyplan=dailyplan,
            meal=meal,
            order=1,
        )

        dailyplan = dailyplans_with_kcal().get(pk=dailyplan.pk)
        dailyplan_meals = get_dailyplan_meals_with_foods(dailyplan)
        meal_foods = list(dailyplan_meals[0].meal.meal_food_set.all())

        with self.assertNumQueries(0):
            table_items = [
                build_mealfood_table_item(meal_food)
                for meal_food in meal_foods
            ]

        self.assertEqual(
            [item["rel"]["name"] for item in table_items],
            ["Alimento 0", "Alimento 1", "Alimento 2"],
        )
