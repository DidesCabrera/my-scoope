import json

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from notas.domain.models import DailyPlan, DailyPlanMeal, Food, FoodLocalizedName, Meal, MealFood

User = get_user_model()


@override_settings(NUTRITION_ONBOARDING_GATE_ENABLED=False)
class DPMFoodPickerPayloadTests(TestCase):

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

        self.dailyplan = DailyPlan.objects.create(
            name="Plan 1",
            created_by=self.user,
            is_draft=False,
        )

        self.meal = Meal.objects.create(
            name="Meal snapshot",
            created_by=self.user,
            is_draft=False,
            is_public=False,
            is_forkable=True,
            is_copiable=False,
        )

        self.dpm = DailyPlanMeal.objects.create(
            dailyplan=self.dailyplan,
            meal=self.meal,
            order=1,
        )

    def test_dailyplan_meal_detail_includes_food_picker_payload_keys(self):
        Food.objects.create(
            name="Egg",
            protein=10,
            carbs=2,
            fat=5,
            created_by=self.user,
        )

        response = self.client.get(
            reverse("dailyplan_meal_detail", args=[self.dailyplan.id, self.dpm.id])
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("foods_json", response.context)
        self.assertIn("food_picker_json", response.context)
        self.assertContains(response, '<dialog\n  id="dpm-picker-section"')
        self.assertContains(response, 'data-picker-step-panel="selection"')
        self.assertContains(response, 'data-picker-step-panel="impact"')
        self.assertContains(response, 'data-scope="dpm-meal-result"')
        self.assertContains(response, 'data-scope="dpm-dailyplan-result"')
        self.assertNotContains(response, 'class="preview-picker"')

    def test_dailyplan_meal_detail_picker_context_contains_result_compositions(self):
        food = Food.objects.create(
            name="Egg",
            protein=10,
            carbs=2,
            fat=5,
            created_by=self.user,
        )
        meal_food = MealFood.objects.create(
            meal=self.meal,
            food=food,
            quantity=120,
        )

        response = self.client.get(
            reverse("dailyplan_meal_detail", args=[self.dailyplan.id, self.dpm.id])
        )
        picker_context = json.loads(response.context["food_picker_json"])

        self.assertEqual(picker_context["meal"]["name"], self.meal.name)
        self.assertEqual(picker_context["meal"]["foods"][0]["mealfood_id"], meal_food.id)
        self.assertEqual(picker_context["dailyplan"]["name"], self.dailyplan.name)
        self.assertEqual(
            picker_context["dailyplan"]["meals"][0]["dailyplanmeal_id"],
            self.dpm.id,
        )
        self.assertEqual(picker_context["dpm"]["id"], self.dpm.id)

    def test_dailyplan_meal_detail_payloads_are_valid_json(self):
        Food.objects.create(
            name="Egg",
            protein=10,
            carbs=2,
            fat=5,
            created_by=self.user,
        )

        response = self.client.get(
            reverse("dailyplan_meal_detail", args=[self.dailyplan.id, self.dpm.id])
        )

        foods_payload = json.loads(response.context["foods_json"])
        picker_context = json.loads(response.context["food_picker_json"])

        self.assertIsInstance(foods_payload, list)
        self.assertIsInstance(picker_context, dict)

    def test_dailyplan_meal_detail_foods_json_contains_available_foods(self):
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
            reverse("dailyplan_meal_detail", args=[self.dailyplan.id, self.dpm.id])
        )

        foods_payload = json.loads(response.context["foods_json"])
        serialized = json.dumps(foods_payload)

        self.assertIn(str(food_1.id), serialized)
        self.assertIn(str(food_2.id), serialized)
        self.assertIn("Egg", serialized)
        self.assertIn("Rice", serialized)

    def test_dailyplan_meal_detail_picker_context_is_add_mode_without_edit_food(self):
        Food.objects.create(
            name="Egg",
            protein=10,
            carbs=2,
            fat=5,
            created_by=self.user,
        )

        response = self.client.get(
            reverse("dailyplan_meal_detail", args=[self.dailyplan.id, self.dpm.id])
        )

        picker_context = json.loads(response.context["food_picker_json"])

        self.assertEqual(picker_context["mode"], "add")
        self.assertIsNone(picker_context["editing"])

    def test_dailyplan_meal_detail_picker_context_is_edit_mode_with_edit_food(self):
        food = Food.objects.create(
            name="Egg",
            protein=10,
            carbs=2,
            fat=5,
            created_by=self.user,
        )

        meal_food = MealFood.objects.create(
            meal=self.meal,
            food=food,
            quantity=120,
        )

        response = self.client.get(
            reverse("dailyplan_meal_detail", args=[self.dailyplan.id, self.dpm.id])
            + f"?edit_food={meal_food.id}"
        )

        self.assertEqual(response.status_code, 200)

        picker_context = json.loads(response.context["food_picker_json"])

        self.assertEqual(picker_context["mode"], "edit")
        self.assertEqual(picker_context["editing"]["mealfood_id"], meal_food.id)
        self.assertEqual(picker_context["editing"]["food_id"], food.id)
        self.assertEqual(picker_context["editing"]["original_quantity"], 120.0)

    def test_dailyplan_meal_detail_post_save_food_creates_mealfood(self):
        food = Food.objects.create(
            name="Egg",
            protein=10,
            carbs=2,
            fat=5,
            created_by=self.user,
        )

        response = self.client.post(
            reverse("dailyplan_meal_detail", args=[self.dailyplan.id, self.dpm.id]),
            data={
                "save_food": "1",
                "food_id": food.id,
                "quantity": 100,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.meal.meal_food_set.count(), 1)

        meal_food = self.meal.meal_food_set.first()
        self.assertEqual(meal_food.food, food)
        self.assertEqual(meal_food.quantity, 100)

    def test_dailyplan_meal_detail_post_save_food_updates_existing_mealfood(self):
        food = Food.objects.create(
            name="Egg",
            protein=10,
            carbs=2,
            fat=5,
            created_by=self.user,
        )

        meal_food = MealFood.objects.create(
            meal=self.meal,
            food=food,
            quantity=100,
        )

        response = self.client.post(
            reverse("dailyplan_meal_detail", args=[self.dailyplan.id, self.dpm.id]),
            data={
                "save_food": "1",
                "mealfood_id": meal_food.id,
                "food_id": food.id,
                "quantity": 150,
            },
        )

        self.assertEqual(response.status_code, 200)

        meal_food.refresh_from_db()
        self.assertEqual(meal_food.quantity, 150)

    def test_dailyplan_meal_detail_foods_json_includes_visible_global_foods(self):
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
            reverse("dailyplan_meal_detail", args=[self.dailyplan.id, self.dpm.id])
        )

        foods_payload = json.loads(response.context["foods_json"])
        names = [item["name"] for item in foods_payload]

        self.assertIn(user_food.name, names)
        self.assertIn(global_food.name, names)


    def test_dailyplan_meal_detail_foods_json_includes_picker_metadata_for_global_foods(self):
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
            reverse("dailyplan_meal_detail", args=[self.dailyplan.id, self.dpm.id])
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



def test_dailyplan_meal_detail_foods_json_includes_display_name(self):
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
        reverse("dailyplan_meal_detail", args=[self.dailyplan.id, self.dpm.id])
    )

    foods_payload = json.loads(response.context["foods_json"])
    item = next(
        food
        for food in foods_payload
        if food["name"] == "Chicken breast, cooked"
    )

    self.assertEqual(item["display_name"], "Pechuga de pollo cocida")
