from unittest.mock import patch

from django.test import override_settings

from accounts.services.deletion import AppleCredentialRevocationError
from mobile_api.tests.base import AuthenticatedMobileAPITestCase


@override_settings(NUTRITION_ONBOARDING_GATE_ENABLED=False)
class MobileAPIAppleRevocationTests(AuthenticatedMobileAPITestCase):
    @patch("mobile_api.routes.identity.delete_user_account")
    def test_account_deletion_reports_temporary_apple_revocation_failure(self, delete_account):
        delete_account.side_effect = AppleCredentialRevocationError("Apple unavailable")

        response = self.client.post(
            "/api/v1/account/delete",
            data={"confirmation": "ELIMINAR", "password": "mobile-pass-123"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["error"]["code"], "apple_credential_revocation_unavailable")
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_active)
