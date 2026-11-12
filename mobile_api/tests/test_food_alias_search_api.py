from django.test import override_settings

from mobile_api.tests.base import PaidMobileAPITestCase
from notas.domain.models import Food, FoodAlias


@override_settings(NUTRITION_ONBOARDING_GATE_ENABLED=False)
class MobileFoodAliasSearchTests(PaidMobileAPITestCase):
    def test_food_search_matches_normalized_chilean_aliases(self):
        quinoa = Food.objects.create(
            name="Quinoa cocida", protein=4, carbs=21, fat=2,
            created_by=None, is_global=True, visibility=Food.VISIBILITY_EXTENDED,
        )
        tuna = Food.objects.create(
            name="Atún en agua drenado", protein=25, carbs=0, fat=1,
            created_by=None, is_global=True, visibility=Food.VISIBILITY_EXTENDED,
        )
        FoodAlias.objects.create(
            food=quinoa, name="quinoa cocida", normalized_name="quinoa cocida",
            language="es", country="CL",
        )
        FoodAlias.objects.create(
            food=tuna, name="atun en agua drenado", normalized_name="atun en agua drenado",
            language="es", country="CL",
        )

        for search, expected_id in (
            ("Quínoa cocida", quinoa.id),
            ("Atún en agua, drenado", tuna.id),
        ):
            with self.subTest(search=search):
                response = self.client.get("/api/v1/foods", {"search": search})
                self.assertEqual(response.status_code, 200)
                self.assertIn(
                    expected_id,
                    [item["id"] for item in response.json()["data"]["items"]],
                )

        punctuation_only = self.client.get("/api/v1/foods", {"search": ","})
        self.assertEqual(punctuation_only.status_code, 200)
        self.assertEqual(punctuation_only.json()["data"]["total"], 0)
