from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from accounts.models import AccountPlan, AccountSubscription
from accounts.services.entitlements import has_mcp_access


class MCPPlanEntitlementTests(TestCase):
    def test_only_current_active_pro_plan_grants_mcp_access(self):
        user = User.objects.create_user(username="mcp-entitlement-test")
        plans = {
            slug: AccountPlan.objects.create(
                slug=slug,
                name=slug.title(),
                status=AccountPlan.Status.ACTIVE,
                entitlements={"integrations": {"mcp": {"enabled": slug == "pro"}}},
            )
            for slug in ("free", "basic", "pro")
        }
        subscription = AccountSubscription.objects.create(
            user=user,
            plan=plans["free"],
            status=AccountSubscription.Status.ACTIVE,
        )

        self.assertFalse(has_mcp_access(user))

        subscription.plan = plans["basic"]
        subscription.save(update_fields=["plan"])
        self.assertFalse(has_mcp_access(user))

        subscription.plan = plans["pro"]
        subscription.save(update_fields=["plan"])
        self.assertTrue(has_mcp_access(user))

        subscription.current_period_end = timezone.now() - timedelta(seconds=1)
        subscription.save(update_fields=["current_period_end"])
        self.assertFalse(has_mcp_access(user))
