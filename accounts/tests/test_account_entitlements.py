from __future__ import annotations

from django.contrib.auth import get_user_model
from django.test import TestCase

from accounts.models import AccountPlan, AccountSubscription
from accounts.seed_plans import seed_account_plans
from accounts.services.entitlements import resolve_account_entitlements
from notas.application.services.access.capabilities import get_capabilities


class AccountEntitlementResolutionTests(TestCase):
    def setUp(self):
        seed_account_plans()
        self.user = get_user_model().objects.create_user(username="entitlements-user", password="x")

    def test_account_plan_entitlements_are_resolved_from_subscription(self):
        pro = AccountPlan.objects.get(slug="pro")
        AccountSubscription.objects.update_or_create(
            user=self.user,
            defaults={"plan": pro, "status": AccountSubscription.Status.ACTIVE, "source": AccountSubscription.Source.MANUAL},
        )

        entitlements = resolve_account_entitlements(self.user)
        caps = get_capabilities(self.user)

        self.assertEqual(entitlements.plan_slug, "pro")
        self.assertEqual(entitlements.source, "accounts_account_plan")
        self.assertTrue(caps.can_publish())
        self.assertTrue(caps.can_copy())
        self.assertTrue(caps.can_create_program())

    def test_missing_account_entitlement_keys_use_conservative_defaults(self):
        plan = AccountPlan.objects.create(
            slug="partial",
            name="Partial",
            status=AccountPlan.Status.ACTIVE,
            included_monthly_credits=10,
            entitlements={"nutrition_workspace": {"can_publish": False}},
        )
        AccountSubscription.objects.update_or_create(
            user=self.user,
            defaults={"plan": plan, "status": AccountSubscription.Status.ACTIVE, "source": AccountSubscription.Source.MANUAL},
        )

        caps = get_capabilities(self.user)

        self.assertFalse(caps.can_publish())
        self.assertFalse(caps.can_copy())
        self.assertIsNone(caps.max_active_subscriptions())

    def test_seeded_subscription_resolves_basic_member_plan(self):
        entitlements = resolve_account_entitlements(self.user)
        caps = get_capabilities(self.user)

        self.assertEqual(entitlements.plan_slug, "basic")
        self.assertTrue(caps.can_create_dailyplan())
        self.assertTrue(caps.can_create_program())
        self.assertFalse(caps.can_publish())
