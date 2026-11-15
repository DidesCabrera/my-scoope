"""Fail-closed, side-effect-free preparation of Chilean Google Play order evidence.

No order is recorded or sent to OpenFactura here. Production issuance requires a
separate approved activation path and a verified Play order for every charge.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation


class GooglePlayTaxEvidenceError(ValueError):
    pass


def _clp_amount(value: object, *, field: str) -> int:
    if not isinstance(value, dict) or value.get("currencyCode") != "CLP":
        raise GooglePlayTaxEvidenceError(f"{field} must be CLP.")
    try:
        amount = Decimal(str(value.get("units", "0"))) + Decimal(str(value.get("nanos", 0))) / Decimal(10**9)
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise GooglePlayTaxEvidenceError(f"{field} is invalid.") from exc
    if not amount.is_finite() or amount != amount.to_integral_value() or amount < 0:
        raise GooglePlayTaxEvidenceError(f"{field} must be a nonnegative whole CLP amount.")
    return int(amount)


def prepare_google_play_tax_order(
    order: dict,
    *,
    expected_order_id: str,
    expected_product_id: str,
    expected_purchase_token: str,
    kind: str,
) -> dict:
    """Return only the minimum normalized fields needed for a future DTE decision.

    The caller must have verified ownership, environment and product entitlement
    with the relevant Google Play purchase endpoint first. Never persist `order`:
    it includes purchase tokens and potentially identifying buyer information.
    """
    if not isinstance(order, dict):
        raise GooglePlayTaxEvidenceError("Google Play order must be an object.")
    if kind not in {"subscription", "credit_pack"}:
        raise GooglePlayTaxEvidenceError("Unsupported Google Play purchase kind.")
    if not expected_order_id or order.get("orderId") != expected_order_id:
        raise GooglePlayTaxEvidenceError("Google Play order identity does not match.")
    if not expected_purchase_token or order.get("purchaseToken") != expected_purchase_token:
        raise GooglePlayTaxEvidenceError("Google Play purchase token does not match.")
    if order.get("state") != "PROCESSED":
        raise GooglePlayTaxEvidenceError("Google Play order is not a processed charge.")
    if (order.get("buyerAddress") or {}).get("buyerCountry") != "CL":
        raise GooglePlayTaxEvidenceError("Google Play buyer country is not confirmed as Chile.")
    lines = order.get("lineItems")
    if not isinstance(lines, list) or len(lines) != 1 or not isinstance(lines[0], dict):
        raise GooglePlayTaxEvidenceError("A single Google Play order line is required.")
    line = lines[0]
    if not expected_product_id or line.get("productId") != expected_product_id:
        raise GooglePlayTaxEvidenceError("Google Play order product does not match.")
    details = line.get("subscriptionDetails") if kind == "subscription" else line.get("oneTimePurchaseDetails")
    if not isinstance(details, dict):
        raise GooglePlayTaxEvidenceError("Google Play order kind does not match.")
    period_start = details.get("servicePeriodStartTime") if kind == "subscription" else None
    period_end = details.get("servicePeriodEndTime") if kind == "subscription" else None
    if kind == "subscription" and (not period_start or not period_end):
        raise GooglePlayTaxEvidenceError("Subscription accounting period is missing.")
    total = _clp_amount(order.get("total"), field="total")
    line_total = _clp_amount(line.get("total"), field="line total")
    if total <= 0 or line_total != total:
        raise GooglePlayTaxEvidenceError("Google Play order has no matching positive charge.")
    tax = _clp_amount(order.get("tax"), field="tax") if order.get("tax") is not None else None
    if tax is not None and tax > total:
        raise GooglePlayTaxEvidenceError("Google Play tax exceeds the charge.")
    if not order.get("createTime"):
        raise GooglePlayTaxEvidenceError("Google Play order creation time is missing.")
    return {
        "provider": "google_play",
        "order_id": expected_order_id,
        "product_id": expected_product_id,
        "kind": kind,
        "buyer_country": "CL",
        "currency": "CLP",
        "amount_minor": total,
        "google_tax_minor": tax,
        "charged_at": order["createTime"],
        "period_start": period_start,
        "period_end": period_end,
    }
