from types import SimpleNamespace
from unittest.mock import Mock

from django.test import SimpleTestCase
from appstoreserverlibrary.signed_data_verifier import VerificationException, VerificationStatus

from billing.infrastructure.providers.apple_app_store import AppleAppStoreClient, AppleAppStoreConfigurationError, InvalidAppleSignedData


class AppleRenewalAdapterTests(SimpleTestCase):
    def test_retryable_certificate_failures_remain_unavailable_and_invalid_signatures_remain_invalid(self):
        gateway = AppleAppStoreClient.__new__(AppleAppStoreClient)
        gateway.verifier = Mock()
        for status, error_type in ((VerificationStatus.RETRYABLE_VERIFICATION_FAILURE, AppleAppStoreConfigurationError),
                                   (VerificationStatus.VERIFICATION_FAILURE, InvalidAppleSignedData)):
            for method in ("verify_and_decode_signed_transaction", "verify_and_decode_notification", "verify_and_decode_renewal_info"):
                getattr(gateway.verifier, method).side_effect = VerificationException(status)
            for action in (lambda: gateway.verify_transaction("transaction-jws"),
                           lambda: gateway.verify_notification("notification-jws"),
                           lambda: gateway._with_renewal(None, "renewal-jws")):
                with self.subTest(status=status, action=action), self.assertRaises(error_type):
                    action()

    def test_status_response_uses_verified_grace_and_renewal_preferences(self):
        decoded = SimpleNamespace(originalTransactionId="original", transactionId="latest", productId="pro",
            appAccountToken="token", purchaseDate=1000, expiresDate=2000, revocationDate=None,
            environment="Sandbox", inAppOwnershipType="PURCHASED", signedDate=3000, currency="CLP", price=100,
            isUpgraded=False, subscriptionGroupIdentifier="group")
        renewal = SimpleNamespace(originalTransactionId="original", autoRenewStatus=0,
            autoRenewProductId="basic.annual", gracePeriodExpiresDate=9000, signedDate=4000)
        gateway = AppleAppStoreClient.__new__(AppleAppStoreClient)
        gateway.verifier = Mock()
        gateway.verifier.verify_and_decode_signed_transaction.return_value = decoded
        gateway.verifier.verify_and_decode_renewal_info.return_value = renewal
        gateway.api_client = Mock()
        gateway.api_client.get_all_subscription_statuses.return_value = SimpleNamespace(data=[SimpleNamespace(
            lastTransactions=[SimpleNamespace(status=4, signedTransactionInfo="transaction-jws", signedRenewalInfo="renewal-jws")])])
        evidence = gateway.get_subscription_statuses("original")[0].transaction
        self.assertEqual(evidence.status, "grace_period")
        self.assertEqual(evidence.signed_date, 4000)
        self.assertEqual(evidence.metadata["apple_grace_period_expires_date"], 9000)
        self.assertEqual(evidence.metadata["apple_next_product_id"], "basic.annual")
        self.assertFalse(evidence.metadata["apple_auto_renew_enabled"])
        gateway.verifier.verify_and_decode_renewal_info.assert_called_once_with("renewal-jws")

    def test_renewal_from_another_original_transaction_is_rejected(self):
        from billing.application.contracts import AppleTransactionEvidence
        gateway = AppleAppStoreClient.__new__(AppleAppStoreClient)
        gateway.verifier = Mock()
        gateway.verifier.verify_and_decode_renewal_info.return_value = SimpleNamespace(originalTransactionId="another")
        evidence = AppleTransactionEvidence(original_transaction_id="original", transaction_id="latest", product_id="pro")
        with self.assertRaises(InvalidAppleSignedData):
            gateway._with_renewal(evidence, "renewal-jws")
