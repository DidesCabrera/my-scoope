from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings

from accounts.models import AccountPlan, AccountSubscription
from accounts.seed_plans import seed_account_plans
from billing.catalog import seed_billing_offers
from billing.models import BillingProduct, PaymentProvider, ProviderSubscription


class LaunchPlanReconciliationTests(TestCase):
    def setUp(self):
        seed_account_plans()
        seed_billing_offers()
        users = get_user_model().objects
        self.owner = users.create_user(username="bacardides")
        self.other = users.create_user(username="nutritionist")
        AccountSubscription.objects.filter(user=self.other).update(plan=AccountPlan.objects.get(slug="basic"))

    @override_settings(DEBUG=True)
    def test_dry_run_does_not_change_entitlements(self):
        output = StringIO()
        call_command("reconcile_launch_account_plans", "--scope=local", stdout=output)
        self.assertIn("changes=2 mode=dry-run", output.getvalue())
        self.assertEqual(AccountSubscription.objects.get(user=self.owner).plan.slug, "free")
        self.assertEqual(AccountSubscription.objects.get(user=self.other).plan.slug, "basic")

    @override_settings(DEBUG=True)
    def test_apply_is_audited_and_idempotent(self):
        call_command("reconcile_launch_account_plans", "--scope=local", "--apply", stdout=StringIO())
        owner = AccountSubscription.objects.get(user=self.owner)
        other = AccountSubscription.objects.get(user=self.other)
        self.assertEqual((owner.plan.slug, other.plan.slug), ("pro", "pro"))
        self.assertNotIn("commercial_cadence", owner.metadata)
        self.assertEqual(len(owner.metadata["launch_plan_transitions"]), 1)
        call_command("reconcile_launch_account_plans", "--scope=local", "--apply", stdout=StringIO())
        owner.refresh_from_db()
        self.assertEqual(len(owner.metadata["launch_plan_transitions"]), 1)

    @override_settings(DEBUG=False, SENTRY_ENVIRONMENT="my-scoope")
    def test_production_keeps_only_owner_pro_annual(self):
        call_command("reconcile_launch_account_plans", "--scope=production", "--apply", stdout=StringIO())
        owner = AccountSubscription.objects.get(user=self.owner)
        other = AccountSubscription.objects.get(user=self.other)
        self.assertEqual((owner.plan.slug, other.plan.slug), ("pro", "free"))
        self.assertEqual(owner.metadata["commercial_cadence"], "annual")

    @override_settings(DEBUG=False, SENTRY_ENVIRONMENT="my-scoope")
    def test_active_provider_agreement_blocks_entitlement_change(self):
        from billing.models import BillingOffer

        offer = BillingOffer.objects.filter(account_plan__slug="basic").first()
        product = BillingProduct.objects.create(
            provider=PaymentProvider.PADDLE, environment="sandbox",
            external_product_id="pro_test", external_price_id="pri_test", offer=offer,
            account_plan=offer.account_plan, amount_minor=offer.amount_minor,
            currency=offer.currency, interval=offer.interval,
        )
        ProviderSubscription.objects.create(
            user=self.other, product=product, provider=PaymentProvider.PADDLE,
            external_subscription_id="sub_test", status=ProviderSubscription.Status.AUTHORIZED,
        )
        with self.assertRaises(CommandError):
            call_command("reconcile_launch_account_plans", "--scope=production", "--apply", stdout=StringIO())
        self.assertEqual(AccountSubscription.objects.get(user=self.other).plan.slug, "basic")
