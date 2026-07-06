from __future__ import annotations

from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase

from accounts.models import AccountPlan, AccountSubscription
from accounts.seed_plans import seed_account_plans
from accounts.services.subscriptions import ensure_account_subscription_for_user
from notas.domain.models import Plan


class AccountSubscriptionSyncTests(TestCase):
    def setUp(self):
        seed_account_plans()

    def test_ensure_subscription_maps_legacy_nutritionist_to_pro(self):
        legacy = Plan.objects.create(name="Legacy Pro", role="nutritionist")
        user = get_user_model().objects.create_user(username="sync-pro", password="x")
        user.profile.role = "nutritionist"
        user.profile.plan = legacy
        user.profile.save(update_fields=["role", "plan"])

        subscription, created, updated = ensure_account_subscription_for_user(user, update_existing=True)

        self.assertFalse(created)
        self.assertTrue(updated)
        self.assertEqual(subscription.plan.slug, "pro")
        self.assertEqual(subscription.source, AccountSubscription.Source.MIGRATION)

    def test_user_creation_creates_subscription_when_seeded_plans_exist(self):
        user = get_user_model().objects.create_user(username="new-user-sub", password="x")

        subscription = AccountSubscription.objects.get(user=user)
        self.assertEqual(subscription.plan.slug, "basic")
        self.assertEqual(subscription.source, AccountSubscription.Source.SEED)

    def test_sync_command_backfills_missing_subscriptions(self):
        user = get_user_model().objects.create_user(username="sync-command", password="x")
        AccountSubscription.objects.filter(user=user).delete()
        output = StringIO()

        call_command("sync_account_subscriptions", stdout=output)

        self.assertIn("Account subscriptions synced", output.getvalue())
        self.assertTrue(AccountSubscription.objects.filter(user=user, plan__slug="basic").exists())

    def test_sync_command_can_update_existing_subscription_when_requested(self):
        user = get_user_model().objects.create_user(username="sync-update", password="x")
        free = AccountPlan.objects.get(slug="free")
        AccountSubscription.objects.update_or_create(
            user=user,
            defaults={"plan": free, "status": AccountSubscription.Status.ACTIVE, "source": AccountSubscription.Source.MANUAL},
        )
        output = StringIO()

        call_command("sync_account_subscriptions", "--update-existing", stdout=output)

        self.assertIn("updated=1", output.getvalue())
        self.assertEqual(AccountSubscription.objects.get(user=user).plan.slug, "basic")

    def test_sync_command_dry_run_does_not_create_rows(self):
        user = get_user_model().objects.create_user(username="dry-run-user", password="x")
        AccountSubscription.objects.filter(user=user).delete()
        output = StringIO()

        call_command("sync_account_subscriptions", "--dry-run", stdout=output)

        self.assertIn("would sync", output.getvalue())
        self.assertFalse(AccountSubscription.objects.filter(user=user).exists())
