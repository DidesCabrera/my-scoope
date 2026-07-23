from __future__ import annotations

from typing import Any, Mapping

from billing.application.contracts import (
    ProviderPaymentSnapshot,
    ProviderSubscriptionSnapshot,
    SubscriptionCheckoutResult,
    TaxDocumentIssueResult,
    TaxDocumentStatusResult,
)


class FakePaymentGateway:
    def __init__(
        self,
        *,
        subscriptions: Mapping[str, ProviderSubscriptionSnapshot] | None = None,
        payments: Mapping[str, ProviderPaymentSnapshot] | None = None,
        authorized_payments: Mapping[str, ProviderPaymentSnapshot] | None = None,
    ):
        self.subscriptions = dict(subscriptions or {})
        self.payments = dict(payments or {})
        self.authorized_payments = dict(authorized_payments or {})
        self.calls: list[tuple[str, str]] = []

    def create_subscription(
        self,
        *,
        external_product_id: str,
        payer_email: str,
        back_url: str,
        external_reference: str,
    ) -> SubscriptionCheckoutResult:
        external_id = f"fake-subscription-{len(self.subscriptions) + 1}"
        snapshot = ProviderSubscriptionSnapshot(
            provider="mercado_pago",
            external_subscription_id=external_id,
            external_product_id=external_product_id,
            status="pending",
            metadata={"external_reference": external_reference},
        )
        self.subscriptions[external_id] = snapshot
        self.calls.append(("create_subscription", external_product_id))
        return SubscriptionCheckoutResult(
            subscription=snapshot,
            checkout_url=f"https://checkout.example/{external_id}",
        )

    def cancel_subscription(self, external_subscription_id: str) -> ProviderSubscriptionSnapshot:
        self.calls.append(("cancel_subscription", external_subscription_id))
        current = self.subscriptions[external_subscription_id]
        canceled = ProviderSubscriptionSnapshot(
            provider=current.provider,
            external_subscription_id=current.external_subscription_id,
            external_product_id=current.external_product_id,
            status="canceled",
            metadata=current.metadata,
        )
        self.subscriptions[external_subscription_id] = canceled
        return canceled

    def get_subscription(self, external_subscription_id: str) -> ProviderSubscriptionSnapshot:
        self.calls.append(("get_subscription", external_subscription_id))
        return self.subscriptions[external_subscription_id]

    def get_payment(self, external_payment_id: str) -> ProviderPaymentSnapshot:
        self.calls.append(("get_payment", external_payment_id))
        return self.payments[external_payment_id]

    def get_authorized_payment(self, external_payment_id: str) -> ProviderPaymentSnapshot:
        self.calls.append(("get_authorized_payment", external_payment_id))
        return self.authorized_payments[external_payment_id]


class FakeTaxDocumentGateway:
    def __init__(self):
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self.results: dict[str, TaxDocumentIssueResult] = {}
        self.statuses: dict[str, TaxDocumentStatusResult] = {}

    def issue_document(self, *, idempotency_key: str, payload: Mapping[str, Any]) -> TaxDocumentIssueResult:
        self.calls.append((idempotency_key, dict(payload)))
        if idempotency_key not in self.results:
            self.results[idempotency_key] = TaxDocumentIssueResult(
                external_document_id=f"fake-{len(self.results) + 1}",
                folio=str(len(self.results) + 1),
                document_token=f"token-{len(self.results) + 1}",
            )
        return self.results[idempotency_key]

    def get_document_status(self, document_token: str) -> TaxDocumentStatusResult:
        self.calls.append((f"status:{document_token}", {}))
        return self.statuses.get(document_token, TaxDocumentStatusResult(status="accepted"))
