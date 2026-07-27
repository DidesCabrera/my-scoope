from django.core.checks import run_checks
from django.test import SimpleTestCase, override_settings


class EmailDeliveryCheckTests(SimpleTestCase):
    @override_settings(
        TURNSTILE_ENABLED=True,
        TURNSTILE_SITE_KEY="",
        TURNSTILE_SECRET_KEY="",
    )
    def test_enabled_turnstile_requires_keys(self):
        ids = {
            finding.id
            for finding in run_checks(
                tags=["security"],
                include_deployment_checks=True,
            )
        }
        self.assertIn("email_delivery.E001", ids)
