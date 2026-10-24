from django.contrib.auth.models import User
from django.test import override_settings

from mobile_api.tests.base import PaidMobileAPITestCase
from notas.domain.models import DailyPlan, DailyPlanCatalogEntry, DailyPlanMeal, Food, Meal, MealFood


@override_settings(NUTRITION_ONBOARDING_GATE_ENABLED=False)
class ExploreDailyPlansAPITests(PaidMobileAPITestCase):
    def setUp(self):
        super().setUp()
        self.curator = User.objects.create_user(username="plan-curator", first_name="Equipo", last_name="My Scoope")
        food = Food.objects.create(name="Quinoa del plan", protein=4, carbs=21, fat=2, created_by=self.curator, is_global=True)
        meal = Meal.objects.create(name="Bowl del plan", created_by=self.curator, is_draft=False, scope=Meal.Scope.EMBEDDED)
        MealFood.objects.create(meal=meal, food=food, quantity=180)
        self.plan = DailyPlan.objects.create(name="Día vegetal", created_by=self.curator, is_draft=False)
        DailyPlanMeal.objects.create(dailyplan=self.plan, meal=meal, order=1)
        self.entry = DailyPlanCatalogEntry.objects.create(
            dailyplan=self.plan, summary="Un día vegetal sencillo.", dietary_style="vegan", is_published=True, sort_order=1,
        )

    def test_list_search_and_filters_include_only_published_plans(self):
        hidden = DailyPlan.objects.create(name="Oculta", created_by=self.curator, is_draft=False)
        DailyPlanCatalogEntry.objects.create(dailyplan=hidden, dietary_style="omnivore", is_published=False)
        response = self.client.get("/api/v1/explore/daily-plans", {"dietary_style": "vegan", "search": "vegetal"})
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["total"], 1)
        self.assertEqual(data["items"][0]["meal_count"], 1)
        self.assertEqual(data["items"][0]["panel"]["meals"][0]["name"], "Bowl del plan")
        self.assertEqual(self.client.get("/api/v1/explore/daily-plans", {"meal_count": 3}).json()["data"]["total"], 0)

    def test_save_creates_one_private_independent_plan(self):
        first = self.client.post(f"/api/v1/explore/daily-plans/{self.entry.id}/save")
        second = self.client.post(f"/api/v1/explore/daily-plans/{self.entry.id}/save")
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertFalse(first.json()["data"]["already_saved"])
        self.assertTrue(second.json()["data"]["already_saved"])
        saved = DailyPlan.objects.get(pk=first.json()["data"]["saved_dailyplan_id"])
        self.assertEqual(saved.created_by, self.user)
        self.assertEqual(saved.forked_from, self.plan)
        self.assertFalse(saved.is_public)
        self.assertEqual(saved.dailyplan_meals.count(), 1)
        self.assertNotEqual(saved.dailyplan_meals.get().meal_id, self.plan.dailyplan_meals.get().meal_id)
        self.assertEqual(DailyPlan.objects.filter(created_by=self.user, forked_from=self.plan).count(), 1)
        self.assertTrue(self.client.get("/api/v1/explore/daily-plans").json()["data"]["items"][0]["is_saved"])
        library = self.client.get("/api/v1/library/daily-plans").json()["data"]["items"]
        self.assertIn(saved.id, [item["id"] for item in library])

    def test_unpublished_plan_cannot_be_opened_or_saved(self):
        self.entry.is_published = False
        self.entry.save(update_fields=["is_published"])
        self.assertEqual(self.client.get(f"/api/v1/explore/daily-plans/{self.entry.id}").status_code, 404)
        self.assertEqual(self.client.post(f"/api/v1/explore/daily-plans/{self.entry.id}/save").status_code, 404)
