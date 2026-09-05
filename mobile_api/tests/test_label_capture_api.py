import base64
import json
from unittest.mock import patch

from django.test import override_settings

from accounts.models import CreditWallet
from accounts.services.credits import get_or_create_current_wallet
from ai_assistant.models import AIUsageEvent
from mobile_api.tests.base import AuthenticatedMobileAPITestCase
from notas.domain.models import Food, FoodLabelAIAnalysis, FoodLabelCaptureReceipt


def _provider_response(
    *,
    status="resolved",
    confidence=0.96,
    model="gpt-5.6-luna",
    basis="per_100g",
    serving_size=150,
):
    output = {
        "status": status,
        "product_name": "Yogur IA" if status == "resolved" else None,
        "basis": basis if status == "resolved" else "unknown",
        "serving_size_g": serving_size if status == "resolved" else None,
        "energy_value": 165 if status == "resolved" else None,
        "energy_unit": "kcal" if status == "resolved" else None,
        "protein_g": 10 if status == "resolved" else None,
        "carbs_g": 20 if status == "resolved" else None,
        "fat_g": 5 if status == "resolved" else None,
        "saturated_fat_g": 2 if status == "resolved" else None,
        "sugar_g": 8 if status == "resolved" else None,
        "fiber_g": 1 if status == "resolved" else None,
        "sodium_value": 50 if status == "resolved" else None,
        "sodium_unit": "mg" if status == "resolved" else None,
        "confidence": confidence,
    }
    return {
        "model": model,
        "output_text": json.dumps(output),
        "usage": {"input_tokens": 100, "output_tokens": 50, "total_tokens": 150},
    }


@override_settings(
    NUTRITION_ONBOARDING_GATE_ENABLED=False,
    RATE_LIMIT_NUTRITION_LABEL_SCAN_USER="1000/h",
)
class MobileAPILabelCaptureTests(AuthenticatedMobileAPITestCase):
    def _analysis_payload(self, key="label-analysis-0001"):
        return {
            "image_base64": base64.b64encode(b"\xff\xd8\xff" + b"image-bytes" * 1200).decode("ascii"),
            "image_content_type": "image/jpeg",
            "image_width": 1600,
            "image_height": 1200,
            "idempotency_key": key,
            "consent_to_ai_processing": True,
        }

    @override_settings(AI_ASSISTANT_CREDITS_ENABLED=True)
    @patch("notas.application.services.nutrition_label_ai._call_openai")
    def test_ai_analysis_charges_one_fixed_price_and_replays_without_new_provider_call(self, provider):
        provider.return_value = _provider_response()

        first = self.client.post(
            "/api/v1/foods/label-captures/analyze",
            data=self._analysis_payload(),
            content_type="application/json",
        )
        second = self.client.post(
            "/api/v1/foods/label-captures/analyze",
            data=self._analysis_payload(),
            content_type="application/json",
        )

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first.json()["data"]["credits_charged"], 2)
        self.assertEqual(first.json()["data"]["available_credits"], 148)
        self.assertEqual(provider.call_count, 1)
        self.assertEqual(FoodLabelAIAnalysis.objects.count(), 1)
        self.assertFalse(FoodLabelAIAnalysis.objects.get().escalated)
        self.assertEqual(AIUsageEvent.objects.filter(action_type="nutrition_label.scan").count(), 1)
        self.assertEqual(CreditWallet.objects.get(user=self.user).balance, 148)

    @override_settings(AI_ASSISTANT_CREDITS_ENABLED=True)
    @patch("notas.application.services.nutrition_label_ai._call_openai")
    def test_uncertain_primary_is_invisibly_escalated_without_changing_price(self, provider):
        provider.side_effect = [
            _provider_response(status="ambiguous"),
            _provider_response(model="gpt-5.6-sol"),
        ]

        response = self.client.post(
            "/api/v1/foods/label-captures/analyze",
            data=self._analysis_payload("label-analysis-0002"),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["credits_charged"], 2)
        analysis = FoodLabelAIAnalysis.objects.get()
        self.assertTrue(analysis.escalated)
        self.assertEqual(analysis.escalation_reason, "ambiguous")
        self.assertEqual(analysis.final_model, "gpt-5.6-sol")
        self.assertEqual(analysis.provider_call_count, 2)
        self.assertEqual(CreditWallet.objects.get(user=self.user).balance, 148)

    @override_settings(AI_ASSISTANT_CREDITS_ENABLED=True)
    @patch("notas.application.services.nutrition_label_ai._call_openai")
    def test_per_100ml_analysis_returns_extracted_values_for_safe_user_conversion(self, provider):
        provider.return_value = _provider_response(basis="per_100ml", serving_size=None)

        response = self.client.post(
            "/api/v1/foods/label-captures/analyze",
            data=self._analysis_payload("label-analysis-per-100ml"),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["basis"], "per_100ml")
        self.assertEqual(data["source_basis"], "per_100ml")
        self.assertEqual(data["normalization_status"], "volume_weight_required")
        self.assertEqual(data["ocr_engine_version"], "nutrition_label_ai.v2")
        self.assertEqual(data["values"], {})
        self.assertEqual(data["source_values"]["protein_g"], 10)
        self.assertEqual(data["credits_charged"], 2)
        self.assertFalse(FoodLabelAIAnalysis.objects.get().escalated)

    @override_settings(AI_ASSISTANT_CREDITS_ENABLED=True)
    @patch("notas.application.services.nutrition_label_ai._call_openai")
    def test_unknown_basis_is_escalated_then_returned_for_user_confirmation(self, provider):
        provider.side_effect = [
            _provider_response(basis="unknown", serving_size=None),
            _provider_response(basis="unknown", serving_size=None, model="gpt-5.6-sol"),
        ]

        response = self.client.post(
            "/api/v1/foods/label-captures/analyze",
            data=self._analysis_payload("label-analysis-unknown-basis"),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["basis"], "unknown")
        self.assertEqual(data["normalization_status"], "basis_confirmation_required")
        self.assertEqual(data["credits_charged"], 2)
        self.assertIn("model_escalation_unresolved", data["warnings"])
        analysis = FoodLabelAIAnalysis.objects.get()
        self.assertTrue(analysis.escalated)
        self.assertEqual(analysis.final_model, "gpt-5.6-sol")

    @override_settings(AI_ASSISTANT_CREDITS_ENABLED=True)
    @patch("notas.application.services.nutrition_label_ai._call_openai")
    def test_unresolved_scan_releases_reserved_credits(self, provider):
        provider.side_effect = [
            _provider_response(status="image_unreadable"),
            _provider_response(status="image_unreadable", model="gpt-5.6-sol"),
        ]

        response = self.client.post(
            "/api/v1/foods/label-captures/analyze",
            data=self._analysis_payload("label-analysis-0003"),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["error"]["code"], "nutrition_label_could_not_resolve")
        wallet = get_or_create_current_wallet(user=self.user)
        self.assertEqual(wallet.balance, 150)
        self.assertEqual(wallet.reserved_balance, 0)
        analysis = FoodLabelAIAnalysis.objects.get()
        self.assertEqual(analysis.status, FoodLabelAIAnalysis.STATUS_FAILED)
        self.assertTrue(analysis.escalated)

    @override_settings(AI_ASSISTANT_CREDITS_ENABLED=True)
    @patch("notas.application.services.nutrition_label_ai._call_openai")
    def test_low_quality_escalation_fails_closed_without_charge(self, provider):
        provider.side_effect = [
            _provider_response(status="ambiguous"),
            _provider_response(confidence=0.4, model="gpt-5.6-sol"),
        ]

        response = self.client.post(
            "/api/v1/foods/label-captures/analyze",
            data=self._analysis_payload("label-analysis-low-quality-escalation"),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 422)
        wallet = get_or_create_current_wallet(user=self.user)
        self.assertEqual(wallet.balance, 150)
        self.assertEqual(wallet.reserved_balance, 0)
        analysis = FoodLabelAIAnalysis.objects.get()
        self.assertEqual(analysis.error_type, "primary_low_confidence")

    @patch("notas.application.services.nutrition_label_ai._call_openai")
    def test_ai_analysis_requires_explicit_consent_before_provider_call(self, provider):
        payload = self._analysis_payload("label-analysis-no-consent")
        payload["consent_to_ai_processing"] = False

        response = self.client.post(
            "/api/v1/foods/label-captures/analyze",
            data=payload,
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["error"]["code"], "nutrition_label_ai_consent_required")
        provider.assert_not_called()
        self.assertFalse(FoodLabelAIAnalysis.objects.exists())

    @override_settings(AI_ASSISTANT_CREDITS_ENABLED=True)
    @patch("notas.application.services.nutrition_label_ai._call_openai")
    def test_insufficient_credits_prevents_provider_call(self, provider):
        wallet = get_or_create_current_wallet(user=self.user)
        wallet.balance = 1
        wallet.save(update_fields=["balance"])

        response = self.client.post(
            "/api/v1/foods/label-captures/analyze",
            data=self._analysis_payload("label-analysis-no-credits"),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 402)
        self.assertEqual(response.json()["error"]["code"], "nutrition_label_insufficient_credits")
        provider.assert_not_called()
        wallet.refresh_from_db()
        self.assertEqual(wallet.balance, 1)
        self.assertEqual(wallet.reserved_balance, 0)

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

    @override_settings(AI_ASSISTANT_CREDITS_ENABLED=True)
    @patch("notas.application.services.nutrition_label_ai._call_openai")
    def test_user_can_keep_and_delete_only_the_processed_analysis_image(self, provider):
        provider.return_value = _provider_response()
        analysis_payload = self._analysis_payload("label-analysis-image")
        analysis = self.client.post(
            "/api/v1/foods/label-captures/analyze",
            data=analysis_payload,
            content_type="application/json",
        ).json()["data"]
        confirmation = {
            "name": analysis["name"],
            "protein_g": 10,
            "carbs_g": 20,
            "fat_g": 5,
            "detected_basis": "per_100g",
            "ocr_engine": analysis["ocr_engine"],
            "ocr_engine_version": analysis["ocr_engine_version"],
            "field_confidence": analysis["field_confidence"],
            "warnings": analysis["warnings"],
            "idempotency_key": "label-confirm-image",
            "analysis_id": analysis["analysis_id"],
            "retain_label_image": True,
            "label_image_base64": analysis_payload["image_base64"],
            "label_image_content_type": "image/jpeg",
        }

        saved = self.client.post("/api/v1/foods/label-captures", data=confirmation, content_type="application/json")

        self.assertEqual(saved.status_code, 200)
        self.assertTrue(saved.json()["data"]["label_image_retained"])
        receipt_id = saved.json()["data"]["capture_receipt_id"]
        loaded = self.client.get(f"/api/v1/foods/label-captures/{receipt_id}/image")
        self.assertEqual(loaded.status_code, 200)
        self.assertEqual(loaded.json()["data"]["image_base64"], analysis_payload["image_base64"])
        deleted = self.client.delete(f"/api/v1/foods/label-captures/{receipt_id}/image")
        self.assertEqual(deleted.status_code, 200)
        self.assertTrue(deleted.json()["data"]["deleted"])

    @override_settings(AI_ASSISTANT_CREDITS_ENABLED=True)
    @patch("notas.application.services.nutrition_label_ai._call_openai")
    def test_saved_processed_image_is_owner_scoped(self, provider):
        provider.return_value = _provider_response()
        analysis_payload = self._analysis_payload("label-analysis-private-image")
        analysis = self.client.post(
            "/api/v1/foods/label-captures/analyze",
            data=analysis_payload,
            content_type="application/json",
        ).json()["data"]
        saved = self.client.post(
            "/api/v1/foods/label-captures",
            data={
                "name": analysis["name"],
                "protein_g": 10,
                "carbs_g": 20,
                "fat_g": 5,
                "detected_basis": "per_100g",
                "ocr_engine": analysis["ocr_engine"],
                "field_confidence": analysis["field_confidence"],
                "warnings": analysis["warnings"],
                "idempotency_key": "label-confirm-private-image",
                "analysis_id": analysis["analysis_id"],
                "retain_label_image": True,
                "label_image_base64": analysis_payload["image_base64"],
                "label_image_content_type": "image/jpeg",
            },
            content_type="application/json",
        )
        receipt = FoodLabelCaptureReceipt.objects.get(pk=saved.json()["data"]["capture_receipt_id"])
        receipt.food.created_by = None
        receipt.food.save(update_fields=["created_by"])

        response = self.client.get(f"/api/v1/foods/label-captures/{receipt.id}/image")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"]["code"], "nutrition_label_image_not_found")

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

    def test_per_100ml_capture_requires_and_records_conversion_weight(self):
        payload = {
            "name": "Leche por volumen",
            "protein_g": 3.204,
            "carbs_g": 4.854,
            "fat_g": 1.942,
            "detected_basis": "per_100ml",
            "ocr_engine": "openai_responses",
            "field_confidence": {"protein_g": 0.96},
            "warnings": ["basis_normalized_from_100ml"],
            "idempotency_key": "label-confirm-per-100ml",
        }

        missing = self.client.post(
            "/api/v1/foods/label-captures",
            data=payload,
            content_type="application/json",
        )
        self.assertEqual(missing.status_code, 422)
        self.assertEqual(missing.json()["error"]["code"], "food_label_volume_weight_required")

        payload["volume_weight_g_per_100ml"] = 103
        saved = self.client.post(
            "/api/v1/foods/label-captures",
            data=payload,
            content_type="application/json",
        )
        self.assertEqual(saved.status_code, 200)
        receipt = FoodLabelCaptureReceipt.objects.get(pk=saved.json()["data"]["capture_receipt_id"])
        self.assertEqual(receipt.detected_basis, "per_100ml")
        self.assertEqual(float(receipt.volume_weight_g_per_100ml), 103)
