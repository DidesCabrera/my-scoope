from django.contrib.auth.models import User
from django.test import TestCase

from notas.application.services.commands.food_commands import create_food_from_label_capture
from notas.domain.models import Food, FoodLabelCaptureReceipt


class FoodLabelCaptureTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="label-capture-user")

    def test_confirmation_persists_normalized_values_without_raw_ocr_or_image_by_default(self):
        result = create_food_from_label_capture(
            user=self.user,
            name="  Avena de etiqueta  ",
            protein_g=12.5,
            carbs_g=60.2,
            fat_g=7.1,
            fiber_g=8.4,
            sodium_mg=12,
            serving_size_g=40,
            declared_energy_kcal_per_100g=354,
            detected_basis="per_serving",
            ocr_engine="apple_vision",
            ocr_engine_version="1",
            field_confidence={"protein_g": 0.91},
            warnings=["basis_normalized_from_serving"],
            idempotency_key="label-service-0001",
        )

        self.assertEqual(result.food.name, "Avena de etiqueta")
        self.assertEqual(result.food.created_by, self.user)
        self.assertFalse(result.food.is_global)
        self.assertEqual(float(result.food.fiber_g_per_100g), 8.4)
        self.assertEqual(result.receipt.food, result.food)
        self.assertEqual(result.receipt.field_confidence, {"protein_g": 0.91})
        self.assertFalse(hasattr(result.receipt, "raw_text"))
        self.assertIsNone(result.receipt.retained_label_image)

    def test_invalid_or_unconfirmed_input_creates_nothing(self):
        with self.assertRaisesMessage(ValueError, "food_label_protein_invalid"):
            create_food_from_label_capture(
                user=self.user,
                name="Etiqueta imposible",
                protein_g=101,
                carbs_g=0,
                fat_g=0,
                detected_basis="per_100g",
                ocr_engine="apple_vision",
                idempotency_key="label-service-0002",
            )

        self.assertFalse(Food.objects.exists())
        self.assertFalse(FoodLabelCaptureReceipt.objects.exists())

    def test_zero_serving_size_is_rejected_without_persistence(self):
        with self.assertRaisesMessage(ValueError, "food_label_serving_size_invalid"):
            create_food_from_label_capture(
                user=self.user,
                name="Porción inválida",
                protein_g=10,
                carbs_g=20,
                fat_g=5,
                serving_size_g=0,
                detected_basis="per_serving",
                ocr_engine="apple_vision",
                idempotency_key="label-service-0004",
            )

        self.assertFalse(Food.objects.exists())
        self.assertFalse(FoodLabelCaptureReceipt.objects.exists())

    def test_per_serving_capture_requires_a_serving_weight(self):
        with self.assertRaisesMessage(ValueError, "food_label_serving_size_required"):
            create_food_from_label_capture(
                user=self.user,
                name="Porción sin peso",
                protein_g=10,
                carbs_g=20,
                fat_g=5,
                detected_basis="per_serving",
                ocr_engine="apple_vision",
                idempotency_key="label-service-0005",
            )

        self.assertFalse(Food.objects.exists())
        self.assertFalse(FoodLabelCaptureReceipt.objects.exists())

    def test_another_user_cannot_replay_a_capture_key(self):
        create_food_from_label_capture(
            user=self.user,
            name="Producto A",
            protein_g=10,
            carbs_g=20,
            fat_g=5,
            detected_basis="per_100g",
            ocr_engine="apple_vision",
            idempotency_key="label-service-0003",
        )
        other = User.objects.create_user(username="other-label-user")

        with self.assertRaisesMessage(ValueError, "food_label_idempotency_conflict"):
            create_food_from_label_capture(
                user=other,
                name="Producto A",
                protein_g=10,
                carbs_g=20,
                fat_g=5,
                detected_basis="per_100g",
                ocr_engine="apple_vision",
                idempotency_key="label-service-0003",
            )
