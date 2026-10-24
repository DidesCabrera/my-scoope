from django.contrib.auth.models import User
from django.test import override_settings

from mobile_api.tests.base import PaidMobileAPITestCase
from notas.domain.models import Food, Meal, MealCatalogEntry, MealFood


@override_settings(NUTRITION_ONBOARDING_GATE_ENABLED=False)
class ExploreMealsAPITests(PaidMobileAPITestCase):
    def setUp(self):
        super().setUp()
        self.curator = User.objects.create_user(username="catalog-curator", first_name="Equipo", last_name="My Scoope")
        self.food = Food.objects.create(
            name="Quinoa del catálogo",
            protein=4,
            carbs=21,
            fat=2,
            created_by=self.curator,
            is_global=True,
        )
        self.meal = Meal.objects.create(
            name="Bowl vegetal curado",
            created_by=self.curator,
            is_draft=False,
            is_public=False,
        )
        MealFood.objects.create(meal=self.meal, food=self.food, quantity=180)
        self.entry = MealCatalogEntry.objects.create(
            meal=self.meal,
            summary="Una comida vegetal para el almuerzo.",
            occasion=MealCatalogEntry.Occasion.LUNCH,
            dietary_style=MealCatalogEntry.DietaryStyle.VEGAN,
            is_published=True,
            sort_order=1,
        )

    def test_explore_lists_only_published_catalog_entries_with_editorial_classification(self):
        public_user = User.objects.create_user(username="legacy-public-user")
        Meal.objects.create(name="Pública de un usuario", created_by=public_user, is_public=True, is_draft=False)
        hidden_meal = Meal.objects.create(name="Curada oculta", created_by=self.curator, is_draft=False)
        MealCatalogEntry.objects.create(
            meal=hidden_meal,
            occasion=MealCatalogEntry.Occasion.DINNER,
            dietary_style=MealCatalogEntry.DietaryStyle.OMNIVORE,
            is_published=False,
            sort_order=2,
        )

        response = self.client.get("/api/v1/explore/meals", {"occasion": "lunch", "dietary_style": "vegan"})

        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["total"], 1)
        self.assertEqual(data["items"][0]["name"], "Bowl vegetal curado")
        self.assertEqual(data["items"][0]["occasion_label"], "Almuerzo")
        self.assertEqual(data["items"][0]["dietary_style_label"], "Vegana")
        self.assertFalse(data["items"][0]["is_saved"])

    def test_save_creates_one_private_independent_library_meal(self):
        first = self.client.post(f"/api/v1/explore/meals/{self.entry.id}/save")
        second = self.client.post(f"/api/v1/explore/meals/{self.entry.id}/save")

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertFalse(first.json()["data"]["already_saved"])
        self.assertTrue(second.json()["data"]["already_saved"])
        saved = Meal.objects.get(pk=first.json()["data"]["saved_meal_id"])
        self.assertEqual(saved.created_by, self.user)
        self.assertEqual(saved.name, self.meal.name)
        self.assertFalse(saved.is_public)
        self.assertEqual(saved.forked_from, self.meal)
        self.assertEqual(float(saved.meal_food_set.get().quantity), 180)
        self.assertEqual(Meal.objects.filter(created_by=self.user, forked_from=self.meal).count(), 1)

        listed = self.client.get("/api/v1/explore/meals").json()["data"]["items"][0]
        self.assertTrue(listed["is_saved"])

    def test_unpublished_catalog_entry_cannot_be_opened_or_saved(self):
        self.entry.is_published = False
        self.entry.save(update_fields=["is_published"])

        self.assertEqual(self.client.get(f"/api/v1/explore/meals/{self.entry.id}").status_code, 404)
        self.assertEqual(self.client.post(f"/api/v1/explore/meals/{self.entry.id}/save").status_code, 404)

