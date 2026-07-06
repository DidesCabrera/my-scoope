from __future__ import annotations

from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from accounts.models import AccountPlan
from accounts.seed_plans import ACCOUNT_PLAN_SEEDS, seed_account_plans


class AccountPlanSeedTests(TestCase):
    def test_seed_creates_initial_commercial_plans(self):
        summary = seed_account_plans()

        self.assertEqual(summary["created"], len(ACCOUNT_PLAN_SEEDS))
        self.assertEqual(AccountPlan.objects.count(), len(ACCOUNT_PLAN_SEEDS))
        self.assertEqual(set(AccountPlan.objects.values_list("slug", flat=True)), {"free", "basic", "pro"})
        self.assertTrue(AccountPlan.objects.get(slug="basic").is_active)
        self.assertEqual(AccountPlan.objects.get(slug="basic").included_monthly_credits, 150)
        self.assertEqual(
            AccountPlan.objects.get(slug="pro").entitlements["ai_assistant"]["daily_credit_limit"],
            150,
        )

    def test_seed_is_idempotent_and_does_not_duplicate_plans(self):
        seed_account_plans()
        second_summary = seed_account_plans()

        self.assertEqual(second_summary, {"created": 0, "updated": 0, "unchanged": len(ACCOUNT_PLAN_SEEDS)})
        self.assertEqual(AccountPlan.objects.count(), len(ACCOUNT_PLAN_SEEDS))

    def test_seed_updates_existing_plan_by_stable_slug(self):
        seed_account_plans()
        plan = AccountPlan.objects.get(slug="basic")
        plan.name = "Old basic name"
        plan.included_monthly_credits = 1
        plan.save(update_fields=["name", "included_monthly_credits", "updated_at"])

        summary = seed_account_plans()
        plan.refresh_from_db()

        self.assertEqual(summary["updated"], 1)
        self.assertEqual(plan.name, "Basic")
        self.assertEqual(plan.included_monthly_credits, 150)

    def test_management_command_supports_dry_run_without_creating_rows(self):
        output = StringIO()

        call_command("seed_account_plans", "--dry-run", stdout=output)

        self.assertIn("would seed", output.getvalue())
        self.assertEqual(AccountPlan.objects.count(), 0)

    def test_management_command_seeds_plans(self):
        output = StringIO()

        call_command("seed_account_plans", stdout=output)

        self.assertIn("Account plans seeded", output.getvalue())
        self.assertTrue(AccountPlan.objects.filter(slug="free").exists())
        self.assertTrue(AccountPlan.objects.filter(slug="basic").exists())
        self.assertTrue(AccountPlan.objects.filter(slug="pro").exists())
