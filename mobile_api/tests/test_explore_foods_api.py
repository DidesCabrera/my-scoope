from django.contrib.auth.models import User
from django.test import Client, override_settings

from mobile_api.tests.base import AuthenticatedMobileAPITestCase
from notas.domain.models import Food


@override_settings(NUTRITION_ONBOARDING_GATE_ENABLED=False)
class ExploreFoodsAPITests(AuthenticatedMobileAPITestCase):
    def test_exploration_only_lists_visible_active_global_foods(self):
        curator = User.objects.create_user(username="global-food-curator")
        core = Food.objects.create(name="Avena global", protein=4, carbs=20, fat=2, is_global=True)
        extended = Food.objects.create(name="Quinoa global", protein=5, carbs=22, fat=2, is_global=True, visibility=Food.VISIBILITY_EXTENDED)
        Food.objects.create(name="Avena personal", protein=4, carbs=20, fat=2, created_by=self.user)
        Food.objects.create(name="Avena privada", protein=4, carbs=20, fat=2, created_by=curator)
        Food.objects.create(name="Avena oculta", protein=4, carbs=20, fat=2, is_global=True, visibility=Food.VISIBILITY_HIDDEN)
        Food.objects.create(name="Avena rechazada", protein=4, carbs=20, fat=2, is_global=True, visibility=Food.VISIBILITY_REJECTED)
        Food.objects.create(name="Avena inactiva", protein=4, carbs=20, fat=2, is_global=True, is_active=False)

        response = self.client.get("/api/v1/explore/foods")
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["total"], 2)
        self.assertEqual([item["id"] for item in data["items"]], [core.id, extended.id])
        self.assertTrue(all(item["actions"] == [] for item in data["items"]))
        self.assertEqual(self.client.get("/api/v1/explore/foods", {"search": "avena"}).json()["data"]["total"], 1)
        self.assertEqual(self.client.get("/api/v1/explore/foods", {"limit": 1, "offset": 1}).json()["data"]["items"][0]["id"], extended.id)
        self.assertEqual(self.client.get(f"/api/v1/library/foods/{core.id}").status_code, 200)

    def test_exploration_requires_authentication(self):
        self.assertEqual(Client().get("/api/v1/explore/foods").status_code, 401)
