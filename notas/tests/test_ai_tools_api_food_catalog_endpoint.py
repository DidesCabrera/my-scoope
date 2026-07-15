import json

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse

from notas.domain.models import Food


def json_post(client, url_name, payload):
    return client.post(
        reverse(url_name),
        data=json.dumps(payload),
        content_type="application/json",
    )


@override_settings(NUTRITION_ONBOARDING_GATE_ENABLED=False)
class AIToolsAPIFoodCatalogEndpointTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="felipe",
            password="pass123",
        )
        self.other_user = User.objects.create_user(
            username="other",
            password="pass123",
        )

        Food.objects.create(
            name="Plátano",
            protein=1.1,
            carbs=23,
            fat=0.3,
            created_by=None,
        )
        Food.objects.create(
            name="Pechuga pollo",
            protein=31,
            carbs=0,
            fat=3.6,
            created_by=self.user,
        )
        Food.objects.create(
            name="Private Other Food",
            protein=100,
            carbs=100,
            fat=100,
            created_by=self.other_user,
        )

    def test_list_food_catalog_endpoint_requires_login(self):
        response = json_post(
            self.client,
            "ai_tools_list_food_catalog",
            {},
        )

        self.assertEqual(response.status_code, 302)

    def test_list_food_catalog_endpoint_returns_catalog(self):
        self.client.force_login(self.user)

        response = json_post(
            self.client,
            "ai_tools_list_food_catalog",
            {},
        )

        self.assertEqual(response.status_code, 200)

        data = response.json()

        self.assertTrue(data["ok"])
        self.assertIsNone(data["error"])

        catalog = data["data"]["catalog"]

        names = {
            food["name"]
            for food in catalog["foods"]
        }

        self.assertIn("Plátano", names)
        self.assertIn("Pechuga pollo", names)
        self.assertNotIn("Private Other Food", names)

    def test_list_food_catalog_endpoint_accepts_search_and_limit(self):
        self.client.force_login(self.user)

        response = json_post(
            self.client,
            "ai_tools_list_food_catalog",
            {
                "search": "pechuga",
                "limit": 1,
            },
        )

        self.assertEqual(response.status_code, 200)

        data = response.json()

        self.assertTrue(data["ok"])
        self.assertEqual(data["data"]["catalog"]["count"], 1)
        self.assertEqual(data["data"]["catalog"]["limit"], 1)
        self.assertEqual(data["data"]["catalog"]["search"], "pechuga")
        self.assertEqual(
            data["data"]["catalog"]["foods"][0]["name"],
            "Pechuga pollo",
        )