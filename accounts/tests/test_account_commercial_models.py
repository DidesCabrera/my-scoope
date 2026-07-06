from django.contrib.auth import get_user_model
from django.test import TestCase

from accounts.models import AccountPlan, AccountSubscription


class AccountCommercialModelsTests(TestCase):
    def test_account_plan_active_property_and_credit_fields(self):
        plan = AccountPlan.objects.create(
            slug="starter",
            name="Starter",
            status=AccountPlan.Status.ACTIVE,
            included_monthly_credits=1000,
            daily_credit_limit=100,
            monthly_credit_limit=1000,
            entitlements={"ai_assistant": True},
        )

        self.assertTrue(plan.is_active)
        self.assertEqual(plan.included_monthly_credits, 1000)
        self.assertEqual(plan.entitlements["ai_assistant"], True)

    def test_account_subscription_is_single_current_subscription_per_user(self):
        user = get_user_model().objects.create_user(username="felipe", email="felipe@example.com")
        plan = AccountPlan.objects.create(slug="starter", name="Starter", status=AccountPlan.Status.ACTIVE)

        subscription = AccountSubscription.objects.create(
            user=user,
            plan=plan,
            status=AccountSubscription.Status.ACTIVE,
            source=AccountSubscription.Source.MIGRATION,
        )

        self.assertTrue(subscription.is_active)
        self.assertEqual(user.account_subscription.plan, plan)
