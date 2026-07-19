"""Provider-neutral ports and normalized application snapshots."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Protocol


@dataclass(frozen=True)
class ProviderSubscriptionSnapshot:
    provider: str
    external_subscription_id: str
    status: str
    external_product_id: str = ""
    current_period_start: Any = None
    current_period_end: Any = None
    metadata: Mapping[str, Any] | None = None


@dataclass(frozen=True)
class ProviderPaymentSnapshot:
    provider: str
    external_payment_id: str
    external_subscription_id: str
    status: str
    amount_minor: int
    currency: str
    approved_at: Any = None
    metadata: Mapping[str, Any] | None = None


@dataclass(frozen=True)
class SubscriptionCheckoutResult:
    subscription: ProviderSubscriptionSnapshot
    checkout_url: str


@dataclass(frozen=True)
class TaxDocumentIssueResult:
    external_document_id: str
    folio: str = ""
    document_token: str = ""
    status: str = "issued"
    metadata: Mapping[str, Any] | None = None


@dataclass(frozen=True)
class TaxDocumentStatusResult:
    status: str
    metadata: Mapping[str, Any] | None = None


class PaymentGateway(Protocol):
    def create_subscription(
        self,
        *,
        external_product_id: str,
        payer_email: str,
        back_url: str,
        external_reference: str,
    ) -> SubscriptionCheckoutResult: ...

    def cancel_subscription(self, external_subscription_id: str) -> ProviderSubscriptionSnapshot: ...

    def get_subscription(self, external_subscription_id: str) -> ProviderSubscriptionSnapshot: ...

    def get_payment(self, external_payment_id: str) -> ProviderPaymentSnapshot: ...

    def get_authorized_payment(self, external_payment_id: str) -> ProviderPaymentSnapshot: ...


class TaxDocumentGateway(Protocol):
    def issue_document(self, *, idempotency_key: str, payload: Mapping[str, Any]) -> TaxDocumentIssueResult: ...

    def get_document_status(self, document_token: str) -> TaxDocumentStatusResult: ...
