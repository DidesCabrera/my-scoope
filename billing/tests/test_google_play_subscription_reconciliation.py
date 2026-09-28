from datetime import timedelta
from io import StringIO
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from django.utils import timezone

from accounts.models import AccountPlan, AccountSubscription
from billing.application.contracts import GooglePlaySubscriptionEvidence
from billing.application.services.google_play import google_play_account_id
from billing.infrastructure.providers.google_play import InvalidGooglePlayPurchase
from billing.models import BillingProduct, PaymentProvider, ProviderSubscription


class GooglePlaySubscriptionReconciliationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="google-reconcile", password="test-pass")
        AccountPlan.objects.get_or_create(
            slug="free", defaults={"name": "Free", "status": AccountPlan.Status.ACTIVE}
        )
        plan = AccountPlan.objects.create(slug="basic", name="Basic", status=AccountPlan.Status.ACTIVE)
        product = BillingProduct.objects.create(
            provider=PaymentProvider.GOOGLE_PLAY,
            external_product_id="myscoope_basic",
            external_price_id="monthly",
            account_plan=plan,
            amount_minor=3990,
        )
        self.subscription = ProviderSubscription.objects.create(
            user=self.user,
            product=product,
            provider=PaymentProvider.GOOGLE_PLAY,
            external_subscription_id="play-token-1",
            status=ProviderSubscription.Status.AUTHORIZED,
            current_period_end=timezone.now() + timedelta(days=20),
        )

    def evidence(self, status):
        return GooglePlaySubscriptionEvidence(
            purchase_token=self.subscription.external_subscription_id,
            product_id="myscoope_basic",
            base_plan_id="monthly",
            status=status,
            expiry_time=(timezone.now() - timedelta(days=1)).isoformat(),
            obfuscated_account_id=google_play_account_id(self.user),
        )

    @override_settings(BILLING_GOOGLE_PLAY_SUBSCRIPTION_RECONCILIATION_ENABLED=False)
    @patch("billing.management.commands.reconcile_google_play_subscriptions.build_google_play_gateway")
    def test_scheduled_command_is_inert_until_enabled(self, build):
        output = StringIO()
        call_command("reconcile_google_play_subscriptions", "--apply", "--if-enabled", stdout=output)
        self.assertIn("disabled; skipped", output.getvalue())
        build.assert_not_called()

    @patch("billing.management.commands.reconcile_google_play_subscriptions.build_google_play_gateway")
    def test_dry_run_reads_google_without_changing_entitlement(self, build):
        build.return_value.verify_subscription.return_value = self.evidence("SUBSCRIPTION_STATE_EXPIRED")
        output = StringIO()
        call_command("reconcile_google_play_subscriptions", stdout=output)
        self.subscription.refresh_from_db()
        self.assertEqual(self.subscription.status, ProviderSubscription.Status.AUTHORIZED)
        self.assertIn("dry-run", output.getvalue())

    @patch("billing.management.commands.reconcile_google_play_subscriptions.build_google_play_gateway")
    def test_apply_revokes_expired_subscription_after_google_confirms(self, build):
        build.return_value.verify_subscription.return_value = self.evidence("SUBSCRIPTION_STATE_EXPIRED")
        output = StringIO()
        call_command("reconcile_google_play_subscriptions", "--apply", stdout=output)
        self.subscription.refresh_from_db()
        self.assertEqual(self.subscription.status, ProviderSubscription.Status.EXPIRED)
        self.assertEqual(AccountSubscription.objects.get(user=self.user).status, AccountSubscription.Status.EXPIRED)
        self.assertIn("changed=1", output.getvalue())

    @patch("billing.management.commands.reconcile_google_play_subscriptions.build_google_play_gateway")
    def test_google_error_keeps_existing_access_and_alerts_job(self, build):
        build.return_value.verify_subscription.side_effect = InvalidGooglePlayPurchase("Unknown purchase")
        with self.assertRaises(CommandError):
            call_command("reconcile_google_play_subscriptions", "--apply", stdout=StringIO(), stderr=StringIO())
        self.subscription.refresh_from_db()
        self.assertEqual(self.subscription.status, ProviderSubscription.Status.AUTHORIZED)
