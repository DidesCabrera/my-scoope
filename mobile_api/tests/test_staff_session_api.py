from django.test import override_settings

from mobile_api.tests.base import AuthenticatedMobileAPITestCase


@override_settings(NUTRITION_ONBOARDING_GATE_ENABLED=False)
class MobileAPIStaffSessionTests(AuthenticatedMobileAPITestCase):
    def test_session_exposes_staff_status_for_admin_only_mobile_tools(self):
        self.user.is_staff = True
        self.user.save(update_fields=["is_staff"])

        response = self.client.get("/api/v1/session")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["data"]["is_staff"])
