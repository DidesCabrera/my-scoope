from unittest.mock import patch

from django.test import override_settings

from mobile_api.tests.base import PaidMobileAPITestCase
from notas.application.commercial.limits import CommercialLimitReached
from notas.domain.models import Program


@override_settings(NUTRITION_ONBOARDING_GATE_ENABLED=False)
class MobileLibraryActionLimitTests(PaidMobileAPITestCase):
    def test_duplicate_limits_are_controlled_conflicts(self):
        program = Program.objects.create(name="Programa límite", created_by=self.user, duration_weeks=1)

        for code in ("max_programs_reached", "max_dailyplans_reached"):
            with self.subTest(code=code), patch(
                "mobile_api.library_actions.fork_program",
                side_effect=CommercialLimitReached(code),
            ):
                response = self.client.post(
                    f"/api/v1/library/programs/{program.id}/actions",
                    data={"action": "duplicate"},
                    content_type="application/json",
                )

            self.assertEqual(response.status_code, 409)
            self.assertEqual(response.json()["error"]["code"], code)
