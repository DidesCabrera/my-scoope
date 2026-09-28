from __future__ import annotations

from django.contrib.auth import get_user_model
from django.core import signing
from django.test import TestCase

from accounts.models import AccountPlan, AccountSubscription, CreditLedger, CreditWallet
from accounts.seed_plans import seed_account_plans
from accounts.services.credits import (
    InsufficientAccountCredits,
    consume_account_credit_reservation,
    get_or_create_current_wallet,
    reserve_account_credits,
)
from billing.application.contracts import GooglePlayProductEvidence, ProviderPaymentSnapshot
from billing.application.services.credit_packs import (
    configure_credit_pack_product,
    may_buy_credit_packs,
    reconcile_google_play_voided_products,
    refund_credit_pack_purchase,
    settle_credit_pack_purchase,
    settle_google_play_credit_pack,
)
from billing.application.services.google_play import google_play_account_id
from billing.application.services.mercado_pago_credit_packs import (
    REFERENCE_SALT,
    sync_mercado_pago_credit_pack_payment,
)
from billing.application.services.paddle_checkout import build_paddle_credit_pack_checkout_payload
from billing.application.services.paddle_events import (
    PaddleEventError,
    sync_paddle_adjustment,
    sync_paddle_credit_pack_transaction,
)
from billing.models import BillingPayment, CreditPackOffer, CreditPackPurchase, PaymentProvider


class CreditPackSettlementTests(TestCase):
    def setUp(self):
        seed_account_plans()
        self.user = get_user_model().objects.create_user(username="pack-buyer", email="pack@example.com")
        self.offer = CreditPackOffer.objects.get(code="credits-500")
        self.product = configure_credit_pack_product(
            provider=PaymentProvider.PADDLE, environment="sandbox", offer_code=self.offer.code,
            external_product_id="pro_pack_500", external_price_id="pri_pack_500",
        )

    def _set_plan(self, slug):
        AccountSubscription.objects.update_or_create(
            user=self.user,
            defaults={"plan": AccountPlan.objects.get(slug=slug), "status": AccountSubscription.Status.ACTIVE},
        )

    def test_free_cannot_buy_and_paid_can_buy(self):
        self.assertFalse(may_buy_credit_packs(self.user))
        self._set_plan("basic")
        self.assertTrue(may_buy_credit_packs(self.user))

    def test_purchase_is_idempotent_and_spends_monthly_before_bought(self):
        self._set_plan("basic")
        first = settle_credit_pack_purchase(
            user=self.user, product=self.product, external_purchase_id="txn-1",
        )
        second = settle_credit_pack_purchase(
            user=self.user, product=self.product, external_purchase_id="txn-1",
        )
        self.assertEqual(first.pk, second.pk)
        wallet = get_or_create_current_wallet(user=self.user)
        self.assertEqual((wallet.balance, wallet.purchased_balance), (650, 500))
        reserve_account_credits(user=self.user, credits=200, reference_type="test", reference_id="task-1")
        consume_account_credit_reservation(
            user=self.user, credits=200, reference_type="test", reference_id="task-1",
        )
        wallet.refresh_from_db()
        self.assertEqual((wallet.balance, wallet.purchased_balance), (450, 450))

    def test_downgrade_keeps_bought_credits_but_blocks_consumption(self):
        self._set_plan("basic")
        settle_credit_pack_purchase(user=self.user, product=self.product, external_purchase_id="txn-2")
        self._set_plan("free")
        wallet = get_or_create_current_wallet(user=self.user)
        self.assertEqual((wallet.balance, wallet.purchased_balance), (500, 500))
        with self.assertRaises(InsufficientAccountCredits):
            reserve_account_credits(user=self.user, credits=1, reference_type="test", reference_id="task-2")
        self._set_plan("pro")
        wallet = get_or_create_current_wallet(user=self.user)
        self.assertEqual((wallet.balance, wallet.purchased_balance), (1500, 500))

    def test_refund_debits_only_bought_credits_once(self):
        self._set_plan("basic")
        settle_credit_pack_purchase(user=self.user, product=self.product, external_purchase_id="txn-3")
        refund_credit_pack_purchase(provider=PaymentProvider.PADDLE, external_purchase_id="txn-3")
        refund_credit_pack_purchase(provider=PaymentProvider.PADDLE, external_purchase_id="txn-3")
        wallet = CreditWallet.objects.get(user=self.user)
        self.assertEqual((wallet.balance, wallet.purchased_balance), (150, 0))
        self.assertEqual(CreditPackPurchase.objects.get(external_purchase_id="txn-3").status, "refunded")


class MercadoPagoCreditPackTests(TestCase):
    def setUp(self):
        seed_account_plans()
        self.user = get_user_model().objects.create_user(username="mp-buyer", email="mp@example.com")
        self.product = configure_credit_pack_product(
            provider=PaymentProvider.MERCADO_PAGO, environment="sandbox", offer_code="credits-500",
            external_product_id="myscoope.credits.500",
        )
        AccountSubscription.objects.update_or_create(
            user=self.user,
            defaults={"plan": AccountPlan.objects.get(slug="basic"), "status": AccountSubscription.Status.ACTIVE},
        )

    def _snapshot(self, *, amount=2990, status=BillingPayment.Status.APPROVED):
        reference = signing.dumps(
            {"user_id": self.user.pk, "product_id": self.product.pk}, salt=REFERENCE_SALT, compress=True,
        )
        return ProviderPaymentSnapshot(
            provider=PaymentProvider.MERCADO_PAGO, external_payment_id="mp-payment-1",
            external_subscription_id="", status=status, amount_minor=amount,
            currency="CLP", metadata={"external_reference": reference},
        )

    def test_verified_payment_grants_once_and_wrong_amount_does_not(self):
        from billing.application.services.credit_packs import CreditPackUnavailable
        with self.assertRaises(CreditPackUnavailable):
            sync_mercado_pago_credit_pack_payment(self._snapshot(amount=1))
        self.assertFalse(CreditPackPurchase.objects.exists())
        sync_mercado_pago_credit_pack_payment(self._snapshot())
        sync_mercado_pago_credit_pack_payment(self._snapshot())
        self.assertEqual(CreditPackPurchase.objects.count(), 1)
        self.assertEqual(CreditWallet.objects.get(user=self.user).purchased_balance, 500)

    def test_refund_reverses_verified_purchase(self):
        sync_mercado_pago_credit_pack_payment(self._snapshot())
        sync_mercado_pago_credit_pack_payment(self._snapshot(status=BillingPayment.Status.REFUNDED))
        self.assertEqual(CreditWallet.objects.get(user=self.user).purchased_balance, 0)


class PaddleCreditPackTests(TestCase):
    def setUp(self):
        seed_account_plans()
        self.user = get_user_model().objects.create_user(username="paddle-pack", email="paddle@example.com")
        AccountSubscription.objects.update_or_create(
            user=self.user, defaults={"plan": AccountPlan.objects.get(slug="basic")},
        )
        self.product = configure_credit_pack_product(
            provider=PaymentProvider.PADDLE, environment="sandbox", offer_code="credits-500",
            external_product_id="pro_credit_500", external_price_id="pri_credit_500",
        )
        self.checkout = build_paddle_credit_pack_checkout_payload(
            user=self.user, product=self.product, environment="sandbox",
        )

    def _transaction(self, amount="2990"):
        return {
            "id": "txn-credit-500", "status": "completed", "subscription_id": None,
            "items": [{"price": {"id": self.product.external_price_id}}],
            "custom_data": {"myscoope_checkout_reference": self.checkout.checkout_reference},
            "details": {"totals": {"total": amount}}, "currency_code": "CLP",
        }

    def test_completed_transaction_credits_once_and_amount_mismatch_fails(self):
        with self.assertRaises(PaddleEventError):
            sync_paddle_credit_pack_transaction(
                self._transaction(amount="1"), event_type="transaction.completed", environment="sandbox",
            )
        for _ in range(2):
            sync_paddle_credit_pack_transaction(
                self._transaction(), event_type="transaction.completed", environment="sandbox",
            )
        self.assertEqual(CreditPackPurchase.objects.count(), 1)
        self.assertEqual(CreditWallet.objects.get(user=self.user).purchased_balance, 500)
        sync_paddle_adjustment({
            "id": "adj-credit-500", "transaction_id": "txn-credit-500",
            "action": "refund", "type": "full", "status": "approved",
        }, environment="sandbox")
        self.assertEqual(CreditWallet.objects.get(user=self.user).purchased_balance, 0)


class GooglePlayCreditPackTests(TestCase):
    def test_opaque_purchase_token_fits_ledger_and_refund_is_idempotent(self):
        seed_account_plans()
        user = get_user_model().objects.create_user(username="google-long-token")
        AccountSubscription.objects.update_or_create(
            user=user, defaults={"plan": AccountPlan.objects.get(slug="basic")}
        )
        configure_credit_pack_product(
            provider=PaymentProvider.GOOGLE_PLAY, environment="sandbox", offer_code="credits-500",
            external_product_id="myscoope.credits.500",
        )
        token = "g" * 123  # Length observed from an actual Google Play test purchase.
        evidence = GooglePlayProductEvidence(
            purchase_token=token, product_id="myscoope.credits.500", status="PURCHASED",
            obfuscated_account_id=google_play_account_id(user), environment="sandbox", order_id="GPA.123",
        )
        settle_google_play_credit_pack(user=user, evidence=evidence)
        settle_google_play_credit_pack(user=user, evidence=evidence)
        self.assertEqual(CreditPackPurchase.objects.count(), 1)
        self.assertEqual(CreditWallet.objects.get(user=user).purchased_balance, 500)
        grant = CreditLedger.objects.get(user=user, reference_type="credit_pack_purchase")
        self.assertLessEqual(len(grant.reference_id), CreditLedger._meta.get_field("reference_id").max_length)

        refund_credit_pack_purchase(provider=PaymentProvider.GOOGLE_PLAY, external_purchase_id=token)
        refund_credit_pack_purchase(provider=PaymentProvider.GOOGLE_PLAY, external_purchase_id=token)
        self.assertEqual(CreditWallet.objects.get(user=user).purchased_balance, 0)
        refund = CreditLedger.objects.get(user=user, reference_type="credit_pack_refund")
        self.assertEqual(refund.reference_id, grant.reference_id)

    def test_very_long_google_token_is_digest_stored_and_refundable(self):
        from unittest.mock import Mock

        seed_account_plans()
        user = get_user_model().objects.create_user(username="google-very-long-token")
        AccountSubscription.objects.update_or_create(
            user=user, defaults={"plan": AccountPlan.objects.get(slug="basic")}
        )
        product = configure_credit_pack_product(
            provider=PaymentProvider.GOOGLE_PLAY, environment="sandbox", offer_code="credits-500",
            external_product_id="myscoope.credits.500",
        )
        token = "g" * 512
        settle_credit_pack_purchase(
            user=user, product=product, external_purchase_id=token, evidence={"order_id": "GPA.512"},
        )
        settle_credit_pack_purchase(user=user, product=product, external_purchase_id=token)
        purchase = CreditPackPurchase.objects.get(user=user)
        self.assertLessEqual(len(purchase.external_purchase_id), 160)
        self.assertNotIn(token, purchase.external_purchase_id)
        self.assertEqual(CreditWallet.objects.get(user=user).purchased_balance, 500)
        gateway = Mock()
        gateway.list_voided_products.return_value = [{"purchaseToken": token, "orderId": "GPA.512"}]
        result = reconcile_google_play_voided_products(gateway=gateway, start_time_ms=1, apply=True)
        self.assertEqual(result["refunded"], 1)
        self.assertEqual(CreditWallet.objects.get(user=user).purchased_balance, 0)

    def test_voided_product_reconciliation_is_idempotent_and_order_bound(self):
        from unittest.mock import Mock

        from billing.application.services.credit_packs import CreditPackUnavailable

        seed_account_plans()
        user = get_user_model().objects.create_user(username="google-refund")
        AccountSubscription.objects.update_or_create(
            user=user, defaults={"plan": AccountPlan.objects.get(slug="basic")}
        )
        product = configure_credit_pack_product(
            provider=PaymentProvider.GOOGLE_PLAY, environment="sandbox", offer_code="credits-500",
            external_product_id="myscoope.credits.500",
        )
        settle_credit_pack_purchase(
            user=user, product=product, external_purchase_id="google-token-1",
            evidence={"order_id": "GPA.123"},
        )
        gateway = Mock()
        gateway.list_voided_products.return_value = [
            {"purchaseToken": "google-token-1", "orderId": "GPA.123"},
            {"purchaseToken": "unrelated-token", "orderId": "GPA.999"},
        ]
        dry_run = reconcile_google_play_voided_products(gateway=gateway, start_time_ms=1)
        self.assertEqual(dry_run["refunded"], 0)
        self.assertEqual(CreditWallet.objects.get(user=user).purchased_balance, 500)
        applied = reconcile_google_play_voided_products(gateway=gateway, start_time_ms=1, apply=True)
        repeated = reconcile_google_play_voided_products(gateway=gateway, start_time_ms=1, apply=True)
        self.assertEqual((applied["refunded"], repeated["already_refunded"]), (1, 1))
        self.assertEqual(CreditWallet.objects.get(user=user).purchased_balance, 0)
        self.assertEqual(CreditLedger.objects.filter(user=user, reference_type="credit_pack_refund").count(), 1)
        gateway.list_voided_products.return_value = [
            {"purchaseToken": "google-token-1", "orderId": "GPA.different"}
        ]
        with self.assertRaises(CreditPackUnavailable):
            reconcile_google_play_voided_products(gateway=gateway, start_time_ms=1, apply=True)

    def test_verified_product_is_bound_to_account_and_idempotent(self):
        from billing.application.services.credit_packs import CreditPackUnavailable

        seed_account_plans()
        user = get_user_model().objects.create_user(username="google-pack")
        configure_credit_pack_product(
            provider=PaymentProvider.GOOGLE_PLAY, environment="sandbox",
            offer_code="credits-1000", external_product_id="myscoope_credits_1000",
        )
        evidence = GooglePlayProductEvidence(
            purchase_token="purchase-token-1", product_id="myscoope_credits_1000",
            status="PURCHASED", obfuscated_account_id="wrong", environment="sandbox",
        )
        with self.assertRaises(CreditPackUnavailable):
            settle_google_play_credit_pack(user=user, evidence=evidence)
        evidence = GooglePlayProductEvidence(
            purchase_token=evidence.purchase_token, product_id=evidence.product_id,
            status="PURCHASED", obfuscated_account_id=google_play_account_id(user), environment="sandbox",
        )
        settle_google_play_credit_pack(user=user, evidence=evidence)
        settle_google_play_credit_pack(user=user, evidence=evidence)
        self.assertEqual(CreditPackPurchase.objects.count(), 1)
        self.assertEqual(CreditWallet.objects.get(user=user).purchased_balance, 1000)
