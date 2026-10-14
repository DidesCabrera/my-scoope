from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from accounts.models import AccountPlan, AccountSubscription, CreditWallet
from accounts.seed_plans import seed_account_plans
from accounts.services.credits import (
    AccountCreditsFrozen,
    InsufficientAccountCredits,
    consume_account_credit_reservation,
    get_or_create_current_wallet,
    release_account_credit_reservation,
    reserve_account_credits,
)
from accounts.services.profile import build_account_credit_display
from mobile_api.entitlements_selector import entitlements_payload


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

    def test_free_cannot_spend_without_purchased_credits_or_bypass_a_frozen_wallet(self):
        AccountSubscription.objects.filter(user=self.user).update(plan=AccountPlan.objects.get(slug="free"))
        with self.assertRaises(InsufficientAccountCredits):
            reserve_account_credits(user=self.user, credits=1, reference_type="test-task", reference_id="no-purchase")
        wallet = get_or_create_current_wallet(user=self.user)
        wallet.balance = wallet.purchased_balance = 500
        wallet.is_frozen = True
        wallet.save(update_fields=["balance", "purchased_balance", "is_frozen"])
        with self.assertRaises(AccountCreditsFrozen):
            reserve_account_credits(user=self.user, credits=1, reference_type="test-task", reference_id="frozen")

    def test_a_frozen_wallet_never_reports_credits_as_spendable(self):
        wallet = get_or_create_current_wallet(user=self.user)
        wallet.is_frozen = True
        wallet.save(update_fields=["is_frozen"])
        display = build_account_credit_display(self.user)
        self.assertEqual((display.credit_status, display.available_credits), ("frozen", 0))

    def test_expiration_removes_included_credits_and_keeps_purchased_credits_spendable(self):
        AccountSubscription.objects.filter(user=self.user).update(plan=AccountPlan.objects.get(slug="pro"))
        wallet = get_or_create_current_wallet(user=self.user)
        wallet.balance += 1000
        wallet.purchased_balance = 1000
        wallet.save(update_fields=["balance", "purchased_balance"])
        AccountSubscription.objects.filter(user=self.user).update(current_period_end=timezone.now() - timedelta(seconds=1))

        display = build_account_credit_display(self.user)
        self.assertEqual((display.plan_slug, display.available_credits, display.purchased_credits), ("free", 1000, 1000))
        self.assertEqual(entitlements_payload(self.user)["available_credits"], 1000)
        # The next real spend expires only the included bucket and consumes the purchased one.
        reserve_account_credits(user=self.user, credits=10, reference_type="test-task", reference_id="after-expiry")
        wallet.refresh_from_db()
        self.assertEqual((wallet.plan_snapshot_code, wallet.balance, wallet.purchased_balance, wallet.available_credits),
                         ("free", 1000, 1000, 990))
        self.assertEqual(build_account_credit_display(self.user).available_credits, 990)
        consume_account_credit_reservation(user=self.user, credits=10, reference_type="test-task", reference_id="after-expiry")
        wallet.refresh_from_db()
        self.assertEqual((wallet.balance, wallet.purchased_balance, wallet.reserved_balance), (990, 990, 0))
