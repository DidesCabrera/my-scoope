from io import StringIO
from unittest.mock import Mock, patch

from django.core.management import call_command
from django.test import SimpleTestCase, override_settings

from billing.infrastructure.providers.google_play import GooglePlayClient, GooglePlayConfigurationError


class GooglePlayVoidedClientTests(SimpleTestCase):
    @patch.object(GooglePlayClient, "_access_token", return_value="access")
    @patch("billing.infrastructure.providers.google_play.requests.get")
    def test_lists_all_pages_of_in_app_voided_purchases(self, get, _token):
        get.side_effect = [
            Mock(status_code=200, json=lambda: {
                "voidedPurchases": [{"purchaseToken": "one"}],
                "tokenPagination": {"nextPageToken": "page-2"},
            }),
            Mock(status_code=200, json=lambda: {"voidedPurchases": [{"purchaseToken": "two"}]}),
        ]
        gateway = GooglePlayClient(package_name="com.myscoope.app", service_account={"key": "test"})
        result = gateway.list_voided_products(start_time_ms=123)
        self.assertEqual([item["purchaseToken"] for item in result], ["one", "two"])
        self.assertEqual(get.call_args_list[0].kwargs["params"]["type"], 0)
        self.assertEqual(get.call_args_list[1].kwargs["params"], {"pageSelection.token": "page-2"})

    @patch.object(GooglePlayClient, "_access_token", return_value="access")
    @patch("billing.infrastructure.providers.google_play.requests.get")
    def test_api_error_fails_closed(self, get, _token):
        get.return_value = Mock(status_code=403)
        gateway = GooglePlayClient(package_name="com.myscoope.app", service_account={"key": "test"})
        with self.assertRaises(GooglePlayConfigurationError):
            gateway.list_voided_products(start_time_ms=123)

    @patch("billing.management.commands.reconcile_google_play_credit_pack_refunds.build_google_play_gateway")
    def test_management_command_defaults_to_dry_run(self, build):
        build.return_value.list_voided_products.return_value = []
        output = StringIO()
        call_command("reconcile_google_play_credit_pack_refunds", stdout=output)
        self.assertIn("dry-run", output.getvalue())
        self.assertEqual(build.return_value.list_voided_products.call_count, 1)

    @override_settings(BILLING_GOOGLE_PLAY_REFUND_RECONCILIATION_ENABLED=False)
    @patch("billing.management.commands.reconcile_google_play_credit_pack_refunds.build_google_play_gateway")
    def test_scheduled_command_is_inert_until_explicitly_enabled(self, build):
        output = StringIO()
        call_command("reconcile_google_play_credit_pack_refunds", "--apply", "--if-enabled", stdout=output)
        self.assertIn("disabled; skipped", output.getvalue())
        build.assert_not_called()
