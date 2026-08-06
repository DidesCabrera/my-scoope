"""Apple App Store Server API and signed-data adapter."""

from __future__ import annotations

from pathlib import Path

from appstoreserverlibrary.api_client import AppStoreServerAPIClient
from appstoreserverlibrary.models.Environment import Environment
from appstoreserverlibrary.models.Status import Status
from appstoreserverlibrary.signed_data_verifier import SignedDataVerifier, VerificationException

from billing.application.contracts import (
    AppleNotificationEvidence,
    AppleSubscriptionStatusEvidence,
    AppleTransactionEvidence,
)


class AppleAppStoreConfigurationError(RuntimeError):
    pass


class InvalidAppleSignedData(ValueError):
    pass


_STATUS_NAMES = {
    Status.ACTIVE.value: "active",
    Status.EXPIRED.value: "expired",
    Status.BILLING_RETRY.value: "billing_retry",
    Status.BILLING_GRACE_PERIOD.value: "grace_period",
    Status.REVOKED.value: "revoked",
}


class AppleAppStoreClient:
    def __init__(
        self,
        *,
        bundle_id: str,
        environment: str,
        root_certificate_paths: tuple[str, ...],
        online_checks: bool,
        app_apple_id: int | None = None,
        signing_key: str = "",
        key_id: str = "",
        issuer_id: str = "",
    ):
        if not bundle_id:
            raise AppleAppStoreConfigurationError("Apple bundle ID is required.")
        self.environment = _environment(environment)
        certificates = [Path(path).read_bytes() for path in root_certificate_paths]
        if not certificates:
            raise AppleAppStoreConfigurationError("At least one Apple root certificate is required.")
        self.verifier = SignedDataVerifier(
            certificates,
            online_checks,
            self.environment,
            bundle_id,
            app_apple_id,
        )
        self.api_client = None
        if signing_key and key_id and issuer_id:
            self.api_client = AppStoreServerAPIClient(
                signing_key.replace("\\n", "\n").encode(),
                key_id,
                issuer_id,
                bundle_id,
                self.environment,
            )

    def verify_transaction(self, signed_transaction: str) -> AppleTransactionEvidence:
        if not signed_transaction.strip():
            raise InvalidAppleSignedData("A signed StoreKit transaction is required.")
        try:
            decoded = self.verifier.verify_and_decode_signed_transaction(signed_transaction)
        except VerificationException as exc:
            raise InvalidAppleSignedData("The StoreKit transaction signature is invalid.") from exc
        return _transaction_evidence(decoded)

    def verify_notification(self, signed_payload: str) -> AppleNotificationEvidence:
        if not signed_payload.strip():
            raise InvalidAppleSignedData("A signed App Store notification is required.")
        try:
            decoded = self.verifier.verify_and_decode_notification(signed_payload)
            data = decoded.data
            transaction = (
                self.verify_transaction(data.signedTransactionInfo)
                if data is not None and data.signedTransactionInfo
                else None
            )
        except (VerificationException, InvalidAppleSignedData) as exc:
            raise InvalidAppleSignedData("The App Store notification signature is invalid.") from exc
        status_value = _enum_value(getattr(data, "status", None)) if data is not None else None
        if transaction is not None and status_value is not None:
            transaction = AppleTransactionEvidence(
                **{
                    **transaction.__dict__,
                    "status": _STATUS_NAMES.get(status_value, transaction.status),
                }
            )
        return AppleNotificationEvidence(
            notification_uuid=str(decoded.notificationUUID or ""),
            notification_type=str(_enum_value(decoded.notificationType) or ""),
            subtype=str(_enum_value(decoded.subtype) or ""),
            environment=str(_enum_value(getattr(data, "environment", None)) or ""),
            signed_date=decoded.signedDate,
            transaction=transaction,
        )

    def get_subscription_statuses(self, original_transaction_id: str) -> tuple[AppleSubscriptionStatusEvidence, ...]:
        if self.api_client is None:
            raise AppleAppStoreConfigurationError("App Store Server API credentials are not configured.")
        response = self.api_client.get_all_subscription_statuses(original_transaction_id)
        results: list[AppleSubscriptionStatusEvidence] = []
        for group in response.data or []:
            for latest in group.lastTransactions or []:
                if not latest.signedTransactionInfo:
                    continue
                transaction = self.verify_transaction(latest.signedTransactionInfo)
                raw_status = _enum_value(latest.status)
                status = _STATUS_NAMES.get(raw_status)
                if status is None:
                    continue
                transaction = AppleTransactionEvidence(**{**transaction.__dict__, "status": status})
                results.append(AppleSubscriptionStatusEvidence(status=status, transaction=transaction))
        return tuple(results)


def _transaction_evidence(decoded) -> AppleTransactionEvidence:
    return AppleTransactionEvidence(
        original_transaction_id=str(decoded.originalTransactionId or ""),
        transaction_id=str(decoded.transactionId or ""),
        product_id=str(decoded.productId or ""),
        app_account_token=str(decoded.appAccountToken or ""),
        purchase_date=decoded.purchaseDate,
        expires_date=decoded.expiresDate,
        revocation_date=decoded.revocationDate,
        environment=str(_enum_value(decoded.environment) or ""),
        ownership_type=str(_enum_value(decoded.inAppOwnershipType) or ""),
        signed_date=decoded.signedDate,
        metadata={
            "apple_currency": str(decoded.currency or ""),
            "apple_price_milliunits": decoded.price,
        },
    )


def _environment(value: str) -> Environment:
    normalized = value.strip().lower()
    if normalized == "sandbox":
        return Environment.SANDBOX
    if normalized == "production":
        return Environment.PRODUCTION
    raise AppleAppStoreConfigurationError("Apple environment must be sandbox or production.")


def _enum_value(value):
    return getattr(value, "value", value)
