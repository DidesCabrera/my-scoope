from django.test import override_settings

from mobile_api.tests.base import AuthenticatedMobileAPITestCase
from notas.domain.models import DailyPlan, DailyPlanMeal, Food, Meal, MealFood, Program, ProgramDay


@override_settings(NUTRITION_ONBOARDING_GATE_ENABLED=False)
class MobileCompositionProjectionAPITests(AuthenticatedMobileAPITestCase):
    def test_program_dailyplan_can_be_saved_as_an_independent_library_plan(self):
        food = Food.objects.create(name="Arroz", protein=3, carbs=28, fat=1, created_by=self.user)
        meal = Meal.objects.create(name="Almuerzo ajustado", created_by=self.user, is_draft=False)
        MealFood.objects.create(meal=meal, food=food, quantity=180)
        embedded_plan = DailyPlan.objects.create(
            name="Día ajustado",
            created_by=self.user,
            is_draft=False,
            source=DailyPlan.SOURCE_PROGRAM,
        )
        DailyPlanMeal.objects.create(dailyplan=embedded_plan, meal=meal, hour="13:00")
        program = Program.objects.create(name="Programa editable", created_by=self.user, duration_weeks=1)
        program_day = ProgramDay.objects.create(
            program=program,
            dailyplan=embedded_plan,
            week_number=1,
            day_number=2,
        )

        response = self.client.post(
            f"/api/v1/library/programs/{program.id}/weeks/1/days/2/save-to-library"
        )

        self.assertEqual(response.status_code, 200)
        saved = DailyPlan.objects.get(pk=response.json()["data"]["affected_id"])
        self.assertNotEqual(saved.id, embedded_plan.id)
        self.assertEqual(saved.source, DailyPlan.SOURCE_MANUAL)
        self.assertEqual(saved.name, "Día ajustado")
        self.assertEqual(float(saved.dailyplan_meals.get().meal.meal_food_set.get().quantity), 180)
        program_day.refresh_from_db()
        self.assertEqual(program_day.dailyplan_id, embedded_plan.id)

    def test_program_dailyplan_save_rejects_another_users_program(self):
        other = type(self.user).objects.create_user(username="other-program-user")
        embedded_plan = DailyPlan.objects.create(
            name="Plan privado",
            created_by=other,
            is_draft=False,
            source=DailyPlan.SOURCE_PROGRAM,
        )
        program = Program.objects.create(name="Programa privado", created_by=other, duration_weeks=1)
        ProgramDay.objects.create(program=program, dailyplan=embedded_plan, week_number=1, day_number=1)

        response = self.client.post(
            f"/api/v1/library/programs/{program.id}/weeks/1/days/1/save-to-library"
        )

        self.assertEqual(response.status_code, 404)

    def test_dailyplan_meal_can_be_saved_as_an_independent_library_meal(self):
        food = Food.objects.create(name="Avena", protein=10, carbs=60, fat=5, created_by=self.user)
        embedded_meal = Meal.objects.create(
            name="Desayuno ajustado",
            created_by=self.user,
            is_draft=False,
            scope=Meal.Scope.EMBEDDED,
        )
        MealFood.objects.create(meal=embedded_meal, food=food, quantity=75)
        dailyplan = DailyPlan.objects.create(name="Plan editable", created_by=self.user, is_draft=False)
        relation = DailyPlanMeal.objects.create(dailyplan=dailyplan, meal=embedded_meal, hour="08:30")

        response = self.client.post(
            f"/api/v1/library/daily-plans/{dailyplan.id}/meals/{relation.id}/save-to-library"
        )

        self.assertEqual(response.status_code, 200)
        saved_id = response.json()["data"]["affected_id"]
        saved = Meal.objects.get(pk=saved_id)
        self.assertNotEqual(saved.id, embedded_meal.id)
        self.assertEqual(saved.scope, Meal.Scope.LIBRARY)
        self.assertEqual(saved.name, "Desayuno ajustado (Copia)")
        self.assertEqual(float(saved.meal_food_set.get().quantity), 75)
        relation.refresh_from_db()
        self.assertEqual(relation.meal_id, embedded_meal.id)

    def test_dailyplan_meal_save_rejects_another_users_plan(self):
        other = type(self.user).objects.create_user(username="other-mobile-user")
        meal = Meal.objects.create(name="Privada", created_by=other, is_draft=False)
        dailyplan = DailyPlan.objects.create(name="Plan privado", created_by=other, is_draft=False)
        relation = DailyPlanMeal.objects.create(dailyplan=dailyplan, meal=meal)

        response = self.client.post(
            f"/api/v1/library/daily-plans/{dailyplan.id}/meals/{relation.id}/save-to-library"
        )

        self.assertEqual(response.status_code, 404)

    def test_food_picker_replaces_the_owned_relation_and_projects_the_result(self):
        original = Food.objects.create(
            name="Avena original", protein=10, carbs=60, fat=5, created_by=self.user
        )
        replacement = Food.objects.create(
            name="Yogur de reemplazo", protein=12, carbs=8, fat=3, created_by=self.user
        )
        meal = Meal.objects.create(name="Comida editable", created_by=self.user, is_draft=False)
        relation = MealFood.objects.create(meal=meal, food=original, quantity=50)
        payload = {"food_id": replacement.id, "meal_food_id": relation.id, "quantity": 80}

        preview = self.client.post(
            f"/api/v1/library/meals/{meal.id}/food-picker/preview",
            data=payload,
            content_type="application/json",
        )

        self.assertEqual(preview.status_code, 200)
        projected = preview.json()["data"]["result"]["panel"]["foods"]
        self.assertEqual(len(projected), 1)
        self.assertEqual(projected[0]["relation_id"], relation.id)
        self.assertEqual(projected[0]["projected_label"], "Reemplazo")
        self.assertEqual(projected[0]["name"], "Yogur de reemplazo")

        dailyplan = DailyPlan.objects.create(name="Plan del DPM", created_by=self.user, is_draft=False)
        dailyplan_meal = DailyPlanMeal.objects.create(dailyplan=dailyplan, meal=meal)
        contextual_preview = self.client.post(
            f"/api/v1/library/meals/{meal.id}/food-picker/preview",
            data={**payload, "dailyplan_id": dailyplan.id, "dailyplan_meal_id": dailyplan_meal.id},
            content_type="application/json",
        )
        self.assertEqual(contextual_preview.status_code, 200)
        contextual_result = contextual_preview.json()["data"]["result"]
        self.assertEqual(contextual_result["entity"], "dailyPlan")
        self.assertEqual(contextual_result["id"], dailyplan.id)
        self.assertEqual(contextual_result["panel"]["kind"], "meals")
        projected_meal = contextual_result["panel"]["meals"][0]
        self.assertEqual(projected_meal["relation_id"], dailyplan_meal.id)
        self.assertEqual(projected_meal["projected_label"], "Actualizada")
        self.assertEqual(projected_meal["foods"][0]["name"], "Yogur de reemplazo")

        commit = self.client.post(
            f"/api/v1/library/meals/{meal.id}/food-picker/commit",
            data=payload,
            content_type="application/json",
        )

        self.assertEqual(commit.status_code, 200)
        relation.refresh_from_db()
        self.assertEqual(relation.id, commit.json()["data"]["created_id"])
        self.assertEqual(relation.food_id, replacement.id)
        self.assertEqual(float(relation.quantity), 80)
        self.assertEqual(MealFood.objects.filter(meal=meal).count(), 1)
