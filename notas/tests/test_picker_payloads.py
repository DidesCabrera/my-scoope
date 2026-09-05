import json

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from notas.domain.models import DailyPlan, Food, FoodLocalizedName, Meal, MealFood

User = get_user_model()


@override_settings(NUTRITION_ONBOARDING_GATE_ENABLED=False)
class PickerPayloadTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="felipe",
            email="felipe@test.com",
            password="12345678",
        )

        self.client = Client()
        self.client.login(
            username="felipe",
            password="12345678",
        )

    def test_meal_detail_includes_picker_payload_keys(self):
        meal = Meal.objects.create(
            name="Editable meal",
            created_by=self.user,
            is_draft=True,
        )

        Food.objects.create(
            name="Egg",
            protein=10,
            carbs=2,
            fat=5,
            created_by=self.user,
        )

        response = self.client.get(
            reverse("meal_detail", args=[meal.id])
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("foods_json", response.context)
        self.assertIn("food_picker_context", response.context)
        self.assertIn("show_return_to_dailyplan", response.context)

    def test_meal_detail_picker_payloads_are_valid_json(self):
        meal = Meal.objects.create(
            name="Editable meal",
            created_by=self.user,
            is_draft=True,
        )

        Food.objects.create(
            name="Egg",
            protein=10,
            carbs=2,
            fat=5,
            created_by=self.user,
        )

        response = self.client.get(
            reverse("meal_detail", args=[meal.id])
        )

        foods_json = response.context["foods_json"]
        picker_context_json = response.context["food_picker_context"]

        foods_payload = json.loads(foods_json)
        picker_context = json.loads(picker_context_json)

        self.assertIsInstance(foods_payload, list)
        self.assertIsInstance(picker_context, dict)

    def test_meal_detail_foods_json_contains_available_foods(self):
        meal = Meal.objects.create(
            name="Editable meal",
            created_by=self.user,
            is_draft=True,
        )

        food_1 = Food.objects.create(
            name="Egg",
            protein=10,
            carbs=2,
            fat=5,
            created_by=self.user,
        )

        food_2 = Food.objects.create(
            name="Rice",
            protein=2,
            carbs=30,
            fat=1,
            created_by=self.user,
        )

        response = self.client.get(
            reverse("meal_detail", args=[meal.id])
        )

        foods_payload = json.loads(response.context["foods_json"])

        self.assertEqual(len(foods_payload), 2)

        serialized = json.dumps(foods_payload)
        self.assertIn(str(food_1.id), serialized)
        self.assertIn(str(food_2.id), serialized)
        self.assertIn("Egg", serialized)
        self.assertIn("Rice", serialized)

    def test_meal_detail_show_return_to_dailyplan_is_false_without_pending_dailyplan(self):
        meal = Meal.objects.create(
            name="Editable meal",
            created_by=self.user,
            is_draft=False,
        )

        response = self.client.get(
            reverse("meal_detail", args=[meal.id])
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["show_return_to_dailyplan"])

    def test_meal_detail_show_return_to_dailyplan_is_true_with_pending_dailyplan_and_not_draft(self):
        dailyplan = DailyPlan.objects.create(
            name="Plan 1",
            created_by=self.user,
            is_draft=False,
        )

        meal = Meal.objects.create(
            name="Meal from plan",
            created_by=self.user,
            is_draft=False,
            pending_dailyplan=dailyplan,
        )

        response = self.client.get(
            reverse("meal_detail", args=[meal.id])
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["show_return_to_dailyplan"])

    def test_meal_detail_show_return_to_dailyplan_is_false_when_meal_is_still_draft(self):
        dailyplan = DailyPlan.objects.create(
            name="Plan 1",
            created_by=self.user,
            is_draft=False,
        )

        meal = Meal.objects.create(
            name="Draft meal from plan",
            created_by=self.user,
            is_draft=True,
            pending_dailyplan=dailyplan,
        )

        response = self.client.get(
            reverse("meal_detail", args=[meal.id])
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["show_return_to_dailyplan"])

    def test_meal_detail_with_edit_food_param_loads_picker_context_successfully(self):
        meal = Meal.objects.create(
            name="Editable meal",
            created_by=self.user,
            is_draft=False,
        )

        food = Food.objects.create(
            name="Egg",
            protein=10,
            carbs=2,
            fat=5,
            created_by=self.user,
        )

        meal_food = MealFood.objects.create(
            meal=meal,
            food=food,
            quantity=120,
        )

        response = self.client.get(
            reverse("meal_detail", args=[meal.id]) + f"?edit_food={meal_food.id}"
        )

        self.assertEqual(response.status_code, 200)

        picker_context = json.loads(response.context["food_picker_context"])

        self.assertEqual(picker_context["mode"], "edit")
        self.assertEqual(picker_context["editing"]["mealfood_id"], meal_food.id)
        self.assertEqual(picker_context["editing"]["food_id"], food.id)
        self.assertEqual(picker_context["editing"]["original_quantity"], 120.0)
        self.assertEqual(picker_context["meal"]["name"], "Editable meal")
        self.assertEqual(picker_context["meal"]["owner"], self.user.username)
        projected_food = picker_context["meal"]["foods"][0]
        self.assertEqual(projected_food["mealfood_id"], meal_food.id)
        self.assertEqual(projected_food["food_id"], food.id)
        self.assertEqual(projected_food["name"], "Egg")
        self.assertEqual(projected_food["quantity"], 120.0)
        self.assertEqual(projected_food["protein"], 12.0)
        self.assertEqual(projected_food["carbs"], 2.4)
        self.assertEqual(projected_food["fat"], 6.0)
        self.assertEqual(projected_food["total_kcal"], 111.6)
    def test_meal_detail_foods_json_includes_visible_global_foods(self):
        meal = Meal.objects.create(
            name="Editable meal",
            created_by=self.user,
            is_draft=True,
        )

        user_food = Food.objects.create(
            name="User Egg",
            protein=10,
            carbs=2,
            fat=5,
            created_by=self.user,
        )

        global_food = Food.objects.create(
            name="Global Oats",
            protein=16.9,
            carbs=66.3,
            fat=6.9,
            created_by=None,
            is_global=True,
            is_active=True,
            visibility=Food.VISIBILITY_CORE,
        )

        response = self.client.get(
            reverse("meal_detail", args=[meal.id])
        )

        foods_payload = json.loads(response.context["foods_json"])
        names = [item["name"] for item in foods_payload]

        self.assertIn(user_food.name, names)
        self.assertIn(global_food.name, names)

    def test_meal_detail_foods_json_includes_picker_metadata_for_global_foods(self):
        meal = Meal.objects.create(
            name="Editable meal",
            created_by=self.user,
            is_draft=True,
        )

        Food.objects.create(
            name="Global Oats",
            canonical_name="global oats",
            protein=16.9,
            carbs=66.3,
            fat=6.9,
            created_by=None,
            is_global=True,
            is_verified=True,
            is_active=True,
            visibility=Food.VISIBILITY_CORE,
            data_quality_score=90,
        )

        response = self.client.get(
            reverse("meal_detail", args=[meal.id])
        )

        foods_payload = json.loads(response.context["foods_json"])
        item = next(
            food
            for food in foods_payload
            if food["name"] == "Global Oats"
        )

        self.assertEqual(item["picker_source"], "global")
        self.assertEqual(item["picker_label"], "Global")
        self.assertFalse(item["is_user_food"])
        self.assertTrue(item["is_global_food"])
        self.assertTrue(item["is_verified"])
        self.assertEqual(item["visibility"], Food.VISIBILITY_CORE)


def test_meal_detail_foods_json_includes_display_name(self):
    meal = Meal.objects.create(
        name="Editable meal",
        created_by=self.user,
        is_draft=True,
    )

    global_food = Food.objects.create(
        name="Chicken breast, cooked",
        canonical_name="chicken breast cooked",
        protein=31,
        carbs=0,
        fat=3.6,
        created_by=None,
        is_global=True,
        is_verified=True,
        is_active=True,
        visibility=Food.VISIBILITY_CORE,
        data_quality_score=90,
    )

    FoodLocalizedName.objects.create(
        food=global_food,
        name="Pechuga de pollo cocida",
        normalized_name="pechuga de pollo cocida",
        language="es",
        country="CL",
        is_primary=True,
    )

    response = self.client.get(
        reverse("meal_detail", args=[meal.id])
    )

    foods_payload = json.loads(response.context["foods_json"])
    item = next(
        food
        for food in foods_payload
        if food["name"] == "Chicken breast, cooked"
    )

    self.assertEqual(item["display_name"], "Pechuga de pollo cocida")
