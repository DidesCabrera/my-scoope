from django.test import override_settings

from mobile_api.tests.base import AuthenticatedMobileAPITestCase
from notas.domain.models import Food, FoodLabelCaptureReceipt


@override_settings(NUTRITION_ONBOARDING_GATE_ENABLED=False)
class MobileAPILabelCaptureTests(AuthenticatedMobileAPITestCase):
    def test_confirmed_label_capture_creates_only_a_private_food_and_is_idempotent(self):
        payload = {
            "name": "Yogur alto en proteína",
            "protein_g": 10.2,
            "carbs_g": 4.1,
            "fat_g": 0.4,
            "saturated_fat_g": 0.2,
            "sugar_g": 3.7,
            "fiber_g": 0,
            "sodium_mg": 48,
            "serving_size_g": 150,
            "declared_energy_kcal_per_100g": 61,
            "detected_basis": "per_serving",
            "ocr_engine": "apple_vision",
            "ocr_engine_version": "1",
            "field_confidence": {"protein_g": 0.94, "carbs_g": 0.89},
            "warnings": ["energy_macro_mismatch"],
            "idempotency_key": "label-capture-0001",
        }

        first = self.client.post("/api/v1/foods/label-captures", data=payload, content_type="application/json")
        second = self.client.post("/api/v1/foods/label-captures", data=payload, content_type="application/json")

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first.json()["data"]["id"], second.json()["data"]["id"])
        food = Food.objects.get(pk=first.json()["data"]["id"])
        self.assertEqual(food.created_by, self.user)
        self.assertFalse(food.is_global)
        self.assertFalse(food.is_verified)
        self.assertFalse(food.solver_enabled)
        self.assertEqual(FoodLabelCaptureReceipt.objects.count(), 1)
        receipt = food.label_capture_receipt
        self.assertEqual(receipt.ocr_engine, "apple_vision")
        self.assertNotIn("raw_text", receipt.field_confidence)

    def test_label_capture_rejects_an_idempotency_key_reused_for_different_values(self):
        payload = {
            "name": "Producto privado",
            "protein_g": 10,
            "carbs_g": 20,
            "fat_g": 5,
            "detected_basis": "per_100g",
            "ocr_engine": "apple_vision",
            "field_confidence": {},
            "warnings": [],
            "idempotency_key": "label-capture-0002",
        }
        self.client.post("/api/v1/foods/label-captures", data=payload, content_type="application/json")
        payload["protein_g"] = 11

        conflict = self.client.post("/api/v1/foods/label-captures", data=payload, content_type="application/json")

        self.assertEqual(conflict.status_code, 409)
        self.assertEqual(conflict.json()["error"]["code"], "food_label_idempotency_conflict")

    def test_per_serving_capture_without_weight_is_rejected(self):
        response = self.client.post(
            "/api/v1/foods/label-captures",
            data={
                "name": "Porción sin peso",
                "protein_g": 10,
                "carbs_g": 20,
                "fat_g": 5,
                "detected_basis": "per_serving",
                "ocr_engine": "apple_vision",
                "field_confidence": {},
                "warnings": ["serving_size_required"],
                "idempotency_key": "label-capture-0003",
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["error"]["code"], "food_label_serving_size_required")
        self.assertFalse(Food.objects.exists())
        self.assertFalse(FoodLabelCaptureReceipt.objects.exists())
