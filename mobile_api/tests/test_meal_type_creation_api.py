from django.test import override_settings

from mobile_api.tests.base import PaidMobileAPITestCase
from notas.domain.models import Meal


@override_settings(NUTRITION_ONBOARDING_GATE_ENABLED=False)
class MealTypeCreationAPITests(PaidMobileAPITestCase):
    def test_selected_type_persists_and_survives_duplication(self):
        created = self.client.post(
            "/api/v1/library/meals",
            data={"name": "Batido de fruta", "meal_type": "shake"},
            content_type="application/json",
        )
        self.assertEqual(created.status_code, 200)
        item = created.json()["data"]
        self.assertEqual(item["meal_type"], "shake")
        self.assertEqual(Meal.objects.get(pk=item["id"]).meal_type, "shake")

        listed = self.client.get("/api/v1/library/meals", {"include_drafts": True}).json()["data"]
        self.assertEqual(listed["items"][0]["meal_type"], "shake")
        detail = self.client.get(f"/api/v1/library/meals/{item['id']}").json()["data"]
        self.assertEqual(detail["meal_type"], "shake")

        duplicated = self.client.post(
            f"/api/v1/library/meals/{item['id']}/actions",
            data={"action": "duplicate"}, content_type="application/json",
        )
        self.assertEqual(duplicated.status_code, 200)
        duplicate_id = duplicated.json()["data"]["item_id"]
        self.assertEqual(Meal.objects.get(pk=duplicate_id).meal_type, "shake")

    def test_invalid_type_is_rejected_and_legacy_creation_remains_available(self):
        invalid = self.client.post(
            "/api/v1/library/meals", data={"name": "No válida", "meal_type": "brunch"}, content_type="application/json",
        )
        self.assertEqual(invalid.status_code, 422)
        self.assertEqual(invalid.json()["error"]["code"], "request_validation_failed")

        legacy = self.client.post(
            "/api/v1/library/meals", data={"name": "Comida anterior"}, content_type="application/json",
        )
        self.assertEqual(legacy.status_code, 200)
        self.assertIsNone(legacy.json()["data"]["meal_type"])
