from django.contrib.auth.models import User
from django.test import override_settings

from mobile_api.tests.base import PaidMobileAPITestCase
from notas.domain.models import Food


@override_settings(NUTRITION_ONBOARDING_GATE_ENABLED=False)
class MobileAPIComparisonFoodCatalogTests(PaidMobileAPITestCase):
    def test_food_comparison_uses_visible_global_and_personal_catalog(self):
        personal = Food.objects.create(name="Avena personal", protein=10, carbs=20, fat=5, created_by=self.user)
        global_food = Food.objects.create(name="Avena global", protein=3, carbs=28, fat=1, is_global=True)
        hidden = Food.objects.create(
            name="Avena oculta", protein=3, carbs=28, fat=1,
            is_global=True, visibility=Food.VISIBILITY_HIDDEN,
        )
        inactive = Food.objects.create(
            name="Avena inactiva", protein=3, carbs=28, fat=1,
            is_global=True, is_active=False,
        )
        other_user = User.objects.create_user(username="comparison-catalog-outsider")
        private = Food.objects.create(
            name="Avena ajena", protein=3, carbs=28, fat=1, created_by=other_user,
        )

        options = self.client.get("/api/v1/comparisons/options/foods?search=Avena")
        self.assertEqual(options.status_code, 200)
        self.assertEqual(
            {item["id"] for item in options.json()["data"]["items"]},
            {personal.id, global_food.id},
        )

        compared = self.client.post(
            "/api/v1/comparisons/compare",
            data={"kind": "foods", "selections": [{"id": personal.id}, {"id": global_food.id}]},
            content_type="application/json",
        )
        self.assertEqual(compared.status_code, 200)
        self.assertEqual(
            [item["id"] for item in compared.json()["data"]["items"]],
            [personal.id, global_food.id],
        )

        saved = self.client.post(
            "/api/v1/comparisons/saved",
            data={"kind": "foods", "selections": [{"id": personal.id}, {"id": global_food.id}]},
            content_type="application/json",
        )
        self.assertEqual(saved.status_code, 200)
        self.assertEqual(
            [item["id"] for item in saved.json()["data"]["items"]],
            [personal.id, global_food.id],
        )

        for unavailable in (hidden, inactive, private):
            response = self.client.post(
                "/api/v1/comparisons/compare",
                data={"kind": "foods", "selections": [{"id": personal.id}, {"id": unavailable.id}]},
                content_type="application/json",
            )
            self.assertEqual(response.status_code, 404)
            self.assertEqual(response.json()["error"]["code"], "comparison_item_not_available")
