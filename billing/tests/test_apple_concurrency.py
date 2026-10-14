from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import timedelta
from threading import Barrier
from unittest import skipUnless

from django.contrib.auth import get_user_model
from django.db import close_old_connections, connection, connections
from django.test import TransactionTestCase
from django.utils import timezone

from accounts.models import AccountPlan, AccountSubscription, CreditWallet
from accounts.seed_plans import seed_account_plans
from billing.application.contracts import AppleNotificationEvidence, AppleTransactionEvidence
from billing.application.services.apple_app_store import UnknownAppleAccountToken, get_or_create_apple_app_account_token, process_apple_notification, sync_apple_transaction
from billing.application.services.credit_packs import configure_credit_pack_product, refund_apple_credit_pack, settle_apple_credit_pack
from billing.application.services.events import receive_verified_billing_event
from billing.models import BillingProduct, CreditPackPurchase, ProviderSubscription
from billing.catalog import seed_credit_pack_offers


@skipUnless(connection.vendor == "postgresql", "Row-lock concurrency requires PostgreSQL.")
class AppleConcurrencyTests(TransactionTestCase):
    def setUp(self):
        seed_account_plans()
        seed_credit_pack_offers()
        self.user = get_user_model().objects.create_user(username="apple-concurrent")
        token = get_or_create_apple_app_account_token(self.user)
        self.basic = BillingProduct.objects.create(provider="apple_app_store", environment="sandbox",
            external_product_id="basic", account_plan=AccountPlan.objects.get(slug="basic"), amount_minor=0)
        self.pro = BillingProduct.objects.create(provider="apple_app_store", environment="sandbox",
            external_product_id="pro", account_plan=AccountPlan.objects.get(slug="pro"), amount_minor=0)
        now = timezone.now()
        self.evidence = AppleTransactionEvidence(original_transaction_id="chain", transaction_id="200",
            product_id="basic", app_account_token=str(token.token), environment="Sandbox", ownership_type="PURCHASED",
            purchase_date=now, expires_date=now + timedelta(days=30), signed_date=now)

    def parallel(self, first, second):
        barrier = Barrier(2)
        def run(action):
            close_old_connections()
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SET lock_timeout = '3s'")
                    cursor.execute("SET statement_timeout = '10s'")
                barrier.wait(timeout=5)
                return action()
            finally:
                connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(run, action) for action in (first, second)]
            return [future.result(timeout=15) for future in futures]

    def test_delayed_basic_and_immediate_pro_are_serialized_without_rollback(self):
        newer = replace(self.evidence, transaction_id="201", product_id="pro",
            purchase_date=self.evidence.purchase_date + timedelta(seconds=1))
        self.parallel(lambda: sync_apple_transaction(self.evidence, source="mobile_storekit"),
                      lambda: sync_apple_transaction(newer, source="app_store_notification_v2"))
        self.assertEqual(ProviderSubscription.objects.count(), 1)
        self.assertEqual(AccountSubscription.objects.get(user=self.user).plan.slug, "pro")

    def test_racing_account_tokens_never_transfer_an_original_transaction(self):
        other = get_user_model().objects.create_user(username="apple-other-concurrent")
        other_token = get_or_create_apple_app_account_token(other)
        def sync(evidence):
            try:
                return sync_apple_transaction(evidence, source="mobile_storekit").user_id
            except UnknownAppleAccountToken:
                return None
        results = self.parallel(lambda: sync(self.evidence), lambda: sync(replace(self.evidence, app_account_token=str(other_token.token))))
        self.assertEqual(sum(result is not None for result in results), 1)
        self.assertEqual(ProviderSubscription.objects.get().user_id, next(result for result in results if result is not None))

    def test_direct_consumable_and_webhook_grant_exactly_once(self):
        product = configure_credit_pack_product(provider="apple_app_store", environment="sandbox",
            offer_code="credits-500", external_product_id="credits")
        evidence = replace(self.evidence, product_id=product.external_product_id, expires_date=None)
        event = receive_verified_billing_event(provider="apple_app_store", external_event_id="pack-event",
            event_type="ONE_TIME_CHARGE", signature_verified=True).event
        notification = AppleNotificationEvidence(notification_uuid="pack-event", notification_type="ONE_TIME_CHARGE",
            environment="Sandbox", transaction=evidence)
        self.parallel(lambda: settle_apple_credit_pack(user=self.user, evidence=evidence),
                      lambda: process_apple_notification(event=event, notification=notification))
        self.assertEqual(CreditPackPurchase.objects.count(), 1)
        self.assertEqual(CreditWallet.objects.get(user=self.user).purchased_balance, 500)
        event.refresh_from_db()
        self.assertEqual((event.status, event.attempts), ("processed", 1))

    def test_concurrent_duplicate_notifications_have_one_claim_and_settlement(self):
        event = receive_verified_billing_event(provider="apple_app_store", external_event_id="renewal-event",
            event_type="DID_RENEW", signature_verified=True).event
        notification = AppleNotificationEvidence(notification_uuid="renewal-event", notification_type="DID_RENEW",
            environment="Sandbox", transaction=self.evidence)
        action = lambda: process_apple_notification(event=event, notification=notification)
        self.parallel(action, action)
        event.refresh_from_db()
        self.assertEqual((event.status, event.attempts), ("processed", 1))
        self.assertEqual(ProviderSubscription.objects.count(), 1)

    def test_deletion_and_refund_do_not_deadlock_or_recreate_personal_credit_data(self):
        from accounts.services.deletion import delete_user_account
        product = configure_credit_pack_product(provider="apple_app_store", environment="sandbox",
            offer_code="credits-500", external_product_id="credits-delete-race")
        evidence = replace(self.evidence, product_id=product.external_product_id, expires_date=None)
        settle_apple_credit_pack(user=self.user, evidence=evidence)
        self.parallel(lambda: delete_user_account(user=self.user, source="test_refund_race"),
                      lambda: refund_apple_credit_pack(user=self.user, evidence=evidence))
        self.assertEqual(CreditPackPurchase.objects.get(user=self.user).status, "refunded")
        self.assertFalse(CreditWallet.objects.filter(user=self.user).exists())
