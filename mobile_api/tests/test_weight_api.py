from django.test import override_settings

from mobile_api.tests.base import AuthenticatedMobileAPITestCase
from notas.domain.models import WeightLog


@override_settings(NUTRITION_ONBOARDING_GATE_ENABLED=False)
class MobileAPIWeightTests(AuthenticatedMobileAPITestCase):
    def test_comment_round_trip_and_delete(self):
        created = self.client.post(
            "/api/v1/weights",
            data={
                "weight_kg": 83.8,
                "measured_on": "2026-08-04",
                "measured_time": "07:45",
                "comment": "Después de entrenar.",
            },
            content_type="application/json",
        )
        weight_id = created.json()["data"]["id"]
        history = self.client.get("/api/v1/weights")
        saved = next(item for item in history.json()["data"]["items"] if item["id"] == weight_id)

        self.assertEqual(created.status_code, 200)
        self.assertEqual(created.json()["data"]["comment"], "Después de entrenar.")
        self.assertEqual(saved["comment"], "Después de entrenar.")

        updated = self.client.patch(
            f"/api/v1/weights/{weight_id}",
            data={"weight_kg": 82.9, "measured_on": "2026-08-05", "comment": "En ayunas."},
            content_type="application/json",
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()["data"]["comment"], "En ayunas.")

        deleted = self.client.delete(f"/api/v1/weights/{weight_id}")
        self.assertEqual(deleted.status_code, 200)
        self.assertEqual(deleted.json()["data"]["deleted_id"], weight_id)
        self.assertFalse(WeightLog.objects.filter(id=weight_id, user=self.user).exists())
