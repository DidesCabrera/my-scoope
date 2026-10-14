from django.contrib.auth import get_user_model
from django.test import TestCase

from accounts.models import AccountPlan, AccountSubscription, CreditWallet
from accounts.seed_plans import seed_account_plans
from accounts.services.credits import (
    get_or_create_current_wallet,
    release_account_credit_reservation,
    reserve_account_credits,
)
from accounts.services.profile import build_account_credit_display


class CreditTransitionDisplayTests(TestCase):
    def setUp(self):
        seed_account_plans()
        self.user = get_user_model().objects.create_user(username="credit-transition")
        AccountSubscription.objects.filter(user=self.user).update(plan=AccountPlan.objects.get(slug="basic"))

    def test_upgrade_waits_for_the_real_reservation_then_matches_spendable_credits(self):
        reserve_account_credits(user=self.user, credits=10, reference_type="test-task", reference_id="before-upgrade")
        AccountSubscription.objects.filter(user=self.user).update(plan=AccountPlan.objects.get(slug="pro"))
        display = build_account_credit_display(self.user)
        self.assertEqual((display.plan_name, display.credit_status, display.available_credits, display.reserved_credits),
                         ("Pro", "pending_reservation", 0, 10))
        release_account_credit_reservation(user=self.user, reference_type="test-task", reference_id="before-upgrade")
        display = build_account_credit_display(self.user)
        self.assertEqual((display.credit_status, display.available_credits), ("ready", 1000))
        reserve_account_credits(user=self.user, credits=10, reference_type="test-task", reference_id="after-upgrade")
        self.assertEqual(build_account_credit_display(self.user).available_credits, 990)
        self.assertEqual(CreditWallet.objects.get(user=self.user).plan_snapshot_code, "pro")

    def test_a_frozen_wallet_never_reports_credits_as_spendable(self):
        wallet = get_or_create_current_wallet(user=self.user)
        wallet.is_frozen = True
        wallet.save(update_fields=["is_frozen"])
        display = build_account_credit_display(self.user)
        self.assertEqual((display.credit_status, display.available_credits), ("frozen", 0))
