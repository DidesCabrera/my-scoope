from __future__ import annotations

from django.contrib.auth import get_user_model
from django.test import TestCase

from accounts.models import AccountPlan, AccountSubscription
from accounts.seed_plans import seed_account_plans
from accounts.services.entitlements import resolve_account_entitlements
from notas.application.services.access.capabilities import get_capabilities
from notas.domain.models import Plan


class AccountEntitlementResolutionTests(TestCase):
    def setUp(self):
        seed_account_plans()
        self.user = get_user_model().objects.create_user(username="entitlements-user", password="x")

    def test_account_plan_entitlements_are_preferred_over_legacy_plan(self):
        legacy = Plan.objects.create(
            name="Legacy locked down",
            role="member",
            can_create_meal=False,
            can_create_dailyplan=False,
            can_create_program=False,
            can_publish=False,
            can_copy=False,
            can_fork=True,
        )
        self.user.profile.plan = legacy
        self.user.profile.save(update_fields=["plan"])
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

    def test_legacy_profile_plan_fills_missing_account_entitlement_keys(self):
        legacy = Plan.objects.create(
            name="Legacy publisher",
            role="nutritionist",
            can_create_meal=True,
            can_create_dailyplan=True,
            can_create_program=True,
            can_publish=True,
            can_copy=True,
            can_fork=True,
            max_active_subscriptions=12,
        )
        self.user.profile.plan = legacy
        self.user.profile.save(update_fields=["plan"])
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
        self.assertTrue(caps.can_copy())
        self.assertEqual(caps.max_active_subscriptions(), 12)

    def test_legacy_role_still_resolves_account_plan_without_subscription(self):
        entitlements = resolve_account_entitlements(self.user)
        caps = get_capabilities(self.user)

        self.assertEqual(entitlements.plan_slug, "basic")
        self.assertTrue(caps.can_create_dailyplan())
        self.assertTrue(caps.can_create_program())
        self.assertFalse(caps.can_publish())
