from django.test import Client, override_settings

from accounts.models import AccountDeletionRecord
from mobile_api.tests.base import AuthenticatedMobileAPITestCase
from notas.domain.models import (
    WeightLog,
)


@override_settings(NUTRITION_ONBOARDING_GATE_ENABLED=False)
class MobileAPIIdentityTests(AuthenticatedMobileAPITestCase):
    def test_protected_endpoint_uses_stable_error_envelope(self):
        response = Client().get("/api/v1/session")

        self.assertEqual(response.status_code, 401)
        self.assertFalse(response.json()["ok"])
        self.assertEqual(response.json()["error"]["code"], "mobile_auth_required")

    def test_session_profile_and_entitlements_use_existing_authorities(self):
        session = self.client.get("/api/v1/session")
        profile = self.client.get("/api/v1/me")
        entitlements = self.client.get("/api/v1/entitlements")

        self.assertEqual(session.status_code, 200)
        self.assertEqual(session.json()["data"]["device_session_id"], str(self.device_session.public_id))
        self.assertEqual(profile.status_code, 200)
        self.assertFalse(profile.json()["data"]["onboarding_completed"])
        self.assertTrue(profile.json()["data"]["review_disclosure_required"])
        self.assertEqual(entitlements.status_code, 200)
        self.assertEqual(entitlements.json()["data"]["plan_slug"], "basic")

    def test_onboarding_and_weight_endpoints_reuse_product_services(self):
        onboarding = self.client.post(
            "/api/v1/onboarding",
            data={
                "birth_date": "1990-05-10",
                "sex": "male",
                "height_cm": 188,
                "weight_kg": 84.5,
            },
            content_type="application/json",
        )
        weight = self.client.post(
            "/api/v1/weights",
            data={"weight_kg": 83.8, "measured_on": "2026-08-04"},
            content_type="application/json",
        )
        history = self.client.get("/api/v1/weights")

        self.assertEqual(onboarding.status_code, 200)
        self.assertTrue(onboarding.json()["data"]["onboarding_completed"])
        self.assertEqual(weight.status_code, 200)
        self.assertEqual(weight.json()["data"]["weight_kg"], 83.8)
        self.assertEqual(history.status_code, 200)
        self.assertEqual(history.json()["data"]["count"], 2)

    def test_account_deletion_is_available_through_the_mobile_contract(self):
        response = self.client.post(
            "/api/v1/account/delete",
            data={"confirmation": "ELIMINAR", "password": "mobile-pass-123"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["data"]["receipt_id"])
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_active)
        self.assertEqual(AccountDeletionRecord.objects.count(), 1)
        self.assertFalse(WeightLog.objects.filter(user=self.user).exists())

    def test_mobile_disclosure_acceptance_is_versioned_and_persisted(self):
        response = self.client.post(
            "/api/v1/account/disclosures",
            data={"accepted": True},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["data"]["review_disclosure_required"])
        self.user.profile.refresh_from_db()
        self.assertEqual(
            self.user.profile.mobile_disclosure_version,
            self.user.profile.MOBILE_DISCLOSURE_VERSION,
        )
        self.assertIsNotNone(self.user.profile.mobile_disclosure_accepted_at)
