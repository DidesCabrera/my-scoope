import json
from io import StringIO

from allauth.socialaccount.models import SocialApp
from django.contrib.sites.models import Site
from django.core.management import call_command
from django.test import TestCase, override_settings

from core.environment_diagnostics import build_environment_diagnostic


class EnvironmentDiagnosticTests(TestCase):
    def test_google_oauth_shape_is_checked_without_exposing_credentials(self):
        site, _ = Site.objects.update_or_create(
            pk=1,
            defaults={"domain": "localhost:8000", "name": "Local My Scoope"},
        )
        social_app = SocialApp.objects.create(
            provider="google",
            name="Local Google",
            client_id="diagnostic-client-id",
            secret="diagnostic-client-secret",
        )
        social_app.sites.add(site)

        payload = build_environment_diagnostic().as_dict()
        serialized = json.dumps(payload)

        oauth_finding = next(item for item in payload["findings"] if item["code"] == "oauth.google")
        self.assertEqual(oauth_finding["status"], "ok")
        self.assertNotIn("diagnostic-client-id", serialized)
        self.assertNotIn("diagnostic-client-secret", serialized)

    @override_settings(AI_ASSISTANT_LLM_PROVIDER="openai", AI_ASSISTANT_OPENAI_API_KEY="")
    def test_missing_selected_provider_credential_is_actionable(self):
        report = build_environment_diagnostic(include_database=False)

        finding = next(item for item in report.findings if item.code == "ai.provider")
        self.assertEqual(finding.status, "error")
        self.assertIn("API key", finding.summary)

    def test_json_command_is_machine_readable_and_sanitized(self):
        output = StringIO()

        call_command("diagnose_environment", "--json", "--skip-database", stdout=output)
        payload = json.loads(output.getvalue())

        self.assertEqual(payload["contract"], "myscoope.environment_diagnostic.v1")
        self.assertIn(payload["status"], {"ok", "warning", "error"})
        self.assertTrue(payload["configuration_summary"])
        self.assertNotIn("value", payload["configuration_summary"][0])
