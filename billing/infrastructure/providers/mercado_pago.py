from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any, Mapping

import requests
from django.utils.dateparse import parse_datetime

from billing.application.contracts import (
    ProviderPaymentSnapshot,
    ProviderSubscriptionSnapshot,
    SubscriptionCheckoutResult,
)
from billing.models import BillingPayment, PaymentProvider, ProviderSubscription


class MercadoPagoProviderError(RuntimeError):
    def __init__(self, message: str, *, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class MercadoPagoClient:
    def __init__(self, *, access_token: str, base_url: str, timeout_seconds: int = 10, session=None):
        if not access_token.strip():
            raise ValueError("Mercado Pago access token is required.")
        self.access_token = access_token.strip()
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.session = session or requests.Session()

    def create_subscription(
        self,
        *,
        external_product_id: str,
        payer_email: str,
        back_url: str,
        external_reference: str,
    ) -> SubscriptionCheckoutResult:
        payload = self._request(
            "POST",
            "/preapproval",
            json={
                "preapproval_plan_id": external_product_id,
                "payer_email": payer_email,
                "back_url": back_url,
                "external_reference": external_reference,
            },
        )
        checkout_url = str(payload.get("init_point") or "").strip()
        if not checkout_url.startswith("https://"):
            raise MercadoPagoProviderError("Mercado Pago subscription has no secure checkout URL.")
        return SubscriptionCheckoutResult(subscription=_subscription_snapshot(payload), checkout_url=checkout_url)

    def cancel_subscription(self, external_subscription_id: str) -> ProviderSubscriptionSnapshot:
        payload = self._request("PUT", f"/preapproval/{external_subscription_id}", json={"status": "canceled"})
        return _subscription_snapshot(payload)

    def get_subscription(self, external_subscription_id: str) -> ProviderSubscriptionSnapshot:
        payload = self._request("GET", f"/preapproval/{external_subscription_id}")
        return _subscription_snapshot(payload)

    def get_payment(self, external_payment_id: str) -> ProviderPaymentSnapshot:
        payload = self._request("GET", f"/v1/payments/{external_payment_id}")
        return _payment_snapshot(payload)

    def get_authorized_payment(self, external_payment_id: str) -> ProviderPaymentSnapshot:
        payload = self._request("GET", f"/authorized_payments/{external_payment_id}")
        return _payment_snapshot(payload)

    def _request(self, method: str, path: str, **kwargs) -> dict[str, Any]:
        try:
            response = self.session.request(
                method,
                f"{self.base_url}{path}",
                headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
                timeout=self.timeout_seconds,
                **kwargs,
            )
        except requests.RequestException as exc:
            raise MercadoPagoProviderError("Mercado Pago request failed.") from exc
        if response.status_code < 200 or response.status_code >= 300:
            raise MercadoPagoProviderError(
                "Mercado Pago returned a non-success response.",
                status_code=response.status_code,
            )
        try:
            payload = response.json()
        except ValueError as exc:
            raise MercadoPagoProviderError("Mercado Pago returned invalid JSON.") from exc
        if not isinstance(payload, dict):
            raise MercadoPagoProviderError("Mercado Pago returned an invalid object.")
        return payload


_SUBSCRIPTION_STATUS_MAP = {
    "pending": ProviderSubscription.Status.PENDING,
    "authorized": ProviderSubscription.Status.AUTHORIZED,
    "paused": ProviderSubscription.Status.PAUSED,
    "cancelled": ProviderSubscription.Status.CANCELED,
    "canceled": ProviderSubscription.Status.CANCELED,
}

_PAYMENT_STATUS_MAP = {
    "pending": BillingPayment.Status.PENDING,
    "in_process": BillingPayment.Status.PENDING,
    "approved": BillingPayment.Status.APPROVED,
    "rejected": BillingPayment.Status.REJECTED,
    "cancelled": BillingPayment.Status.CANCELED,
    "canceled": BillingPayment.Status.CANCELED,
    "refunded": BillingPayment.Status.REFUNDED,
    "charged_back": BillingPayment.Status.CHARGED_BACK,
}


def _subscription_snapshot(payload: Mapping[str, Any]) -> ProviderSubscriptionSnapshot:
    external_id = str(payload.get("id") or "").strip()
    if not external_id:
        raise MercadoPagoProviderError("Mercado Pago subscription has no id.")
    raw_status = str(payload.get("status") or "pending").lower()
    status = _SUBSCRIPTION_STATUS_MAP.get(raw_status, ProviderSubscription.Status.PENDING)
    recurring = payload.get("auto_recurring") if isinstance(payload.get("auto_recurring"), dict) else {}
    return ProviderSubscriptionSnapshot(
        provider=PaymentProvider.MERCADO_PAGO,
        external_subscription_id=external_id,
        external_product_id=str(payload.get("preapproval_plan_id") or ""),
        status=status,
        metadata={
            "raw_status": raw_status,
            "next_payment_date": str(payload.get("next_payment_date") or ""),
            "agreement_start_date": str(recurring.get("start_date") or ""),
            "agreement_end_date": str(recurring.get("end_date") or ""),
        },
    )


def _payment_snapshot(payload: Mapping[str, Any]) -> ProviderPaymentSnapshot:
    external_id = str(payload.get("id") or "").strip()
    if not external_id:
        raise MercadoPagoProviderError("Mercado Pago payment has no id.")
    raw_status = str(payload.get("status") or "pending").lower()
    currency = str(payload.get("currency_id") or "CLP").upper()
    amount = payload.get("transaction_amount", payload.get("amount", 0))
    return ProviderPaymentSnapshot(
        provider=PaymentProvider.MERCADO_PAGO,
        external_payment_id=external_id,
        external_subscription_id=str(payload.get("preapproval_id") or ""),
        status=_PAYMENT_STATUS_MAP.get(raw_status, BillingPayment.Status.PENDING),
        amount_minor=_amount_to_minor(amount, currency),
        currency=currency,
        approved_at=_parse_optional_datetime(payload.get("date_approved")),
        metadata={
            "raw_status": raw_status,
            "status_detail": str(payload.get("status_detail") or ""),
            "payment_type_id": str(payload.get("payment_type_id") or ""),
        },
    )


def _amount_to_minor(value: Any, currency: str) -> int:
    exponent = 0 if currency == "CLP" else 2
    try:
        amount = Decimal(str(value or 0))
    except (InvalidOperation, ValueError) as exc:
        raise MercadoPagoProviderError("Mercado Pago payment has an invalid amount.") from exc
    if amount < 0:
        raise MercadoPagoProviderError("Mercado Pago payment amount cannot be negative.")
    factor = Decimal(10) ** exponent
    return int((amount * factor).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _parse_optional_datetime(value: Any):
    if not value:
        return None
    parsed = parse_datetime(str(value))
    if parsed is None:
        raise MercadoPagoProviderError("Mercado Pago returned an invalid datetime.")
    return parsed
