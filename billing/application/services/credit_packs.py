"""Canonical pack catalog and verified one-time purchase settlement."""

from __future__ import annotations

import hashlib

from django.db import transaction

from accounts.models import CreditLedger, CreditWallet
from accounts.services.credits import (
    credit_pack_ledger_reference_id,
    grant_purchased_credits,
    resolve_account_plan_for_user,
)
from billing.models import (
    AppleAppAccountToken,
    CreditPackOffer,
    CreditPackPurchase,
    PaymentProvider,
    ProviderCreditPack,
)


class CreditPackUnavailable(ValueError):
    pass


def _stored_purchase_id(*, provider: str, purchase_id: str) -> str:
    """Use a stable digest if a provider's opaque ID exceeds the database field."""

    max_length = CreditPackPurchase._meta.get_field("external_purchase_id").max_length
    if len(purchase_id) <= max_length:
        return purchase_id
    digest = hashlib.sha256(f"{provider}:{purchase_id}".encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def may_buy_credit_packs(user) -> bool:
    plan = resolve_account_plan_for_user(user)
    return plan is not None and plan.slug in {"basic", "pro"}


def public_credit_pack_offers(user) -> tuple[CreditPackOffer, ...]:
    if not may_buy_credit_packs(user):
        return ()
    return tuple(CreditPackOffer.objects.filter(active=True, public=True).order_by("display_order"))


@transaction.atomic
def configure_credit_pack_product(
    *, provider: str, environment: str, offer_code: str,
    external_product_id: str, external_price_id: str = "",
) -> ProviderCreditPack:
    if provider not in PaymentProvider.values or environment not in {"sandbox", "live"}:
        raise CreditPackUnavailable("credit_pack_provider_invalid")
    if not external_product_id.strip() or len(external_product_id) > 160 or len(external_price_id) > 160:
        raise CreditPackUnavailable("credit_pack_external_id_invalid")
    if provider == PaymentProvider.PADDLE and (
        not external_product_id.startswith("pro_") or not external_price_id.startswith("pri_")
    ):
        raise CreditPackUnavailable("credit_pack_paddle_id_invalid")
    offer = CreditPackOffer.objects.filter(code=offer_code, active=True).first()
    if offer is None:
        raise CreditPackUnavailable("credit_pack_offer_unavailable")
    current = ProviderCreditPack.objects.select_for_update().filter(
        provider=provider, environment=environment, offer=offer, active=True
    ).first()
    if current and (current.external_product_id, current.external_price_id) == (
        external_product_id, external_price_id
    ):
        if (current.credits_snapshot, current.amount_minor, current.currency) != (
            offer.credits, offer.amount_minor, offer.currency
        ):
            raise CreditPackUnavailable("credit_pack_mapping_drift")
        return current
    historical = ProviderCreditPack.objects.filter(
        provider=provider, environment=environment,
        external_product_id=external_product_id, external_price_id=external_price_id,
    ).first()
    if historical is not None and (
        historical.offer_id != offer.pk
        or historical.credits_snapshot != offer.credits
        or historical.amount_minor != offer.amount_minor
        or historical.currency != offer.currency
    ):
        raise CreditPackUnavailable("credit_pack_external_id_reused")
    if current:
        current.active = False
        current.save(update_fields=["active", "updated_at"])
    if historical:
        historical.active = True
        historical.save(update_fields=["active", "updated_at"])
        return historical
    return ProviderCreditPack.objects.create(
        offer=offer, provider=provider, environment=environment,
        external_product_id=external_product_id, external_price_id=external_price_id,
        credits_snapshot=offer.credits, amount_minor=offer.amount_minor,
        currency=offer.currency, active=True,
    )


@transaction.atomic
def settle_credit_pack_purchase(
    *, user, product: ProviderCreditPack, external_purchase_id: str,
    evidence: dict | None = None,
) -> CreditPackPurchase:
    """Call only after server-side provider verification and account binding."""

    purchase_id = str(external_purchase_id or "").strip()
    if not purchase_id:
        raise CreditPackUnavailable("credit_pack_purchase_id_missing")
    purchase_id = _stored_purchase_id(provider=product.provider, purchase_id=purchase_id)
    existing = CreditPackPurchase.objects.select_for_update().filter(
        provider=product.provider, external_purchase_id=purchase_id
    ).first()
    if existing is not None:
        if existing.user_id != user.pk or existing.product_id != product.pk:
            raise CreditPackUnavailable("credit_pack_purchase_owner_mismatch")
        return existing
    if product.credits_snapshot <= 0:
        raise CreditPackUnavailable("credit_pack_product_invalid")
    purchase = CreditPackPurchase.objects.create(
        user=user, product=product, provider=product.provider,
        external_purchase_id=purchase_id, credits_granted=product.credits_snapshot,
        evidence=dict(evidence or {}),
    )
    grant_purchased_credits(
        user=user, credits=product.credits_snapshot,
        provider=product.provider, purchase_id=purchase_id,
    )
    return purchase


def settle_apple_credit_pack(*, user, evidence) -> CreditPackPurchase:
    token, _ = AppleAppAccountToken.objects.get_or_create(user=user)
    if str(evidence.app_account_token or "").lower() != str(token.token).lower():
        raise CreditPackUnavailable("credit_pack_apple_account_mismatch")
    if evidence.revocation_date or evidence.expires_date:
        raise CreditPackUnavailable("credit_pack_apple_transaction_not_consumable")
    if str(evidence.ownership_type or "").upper() not in {"PURCHASED", ""}:
        raise CreditPackUnavailable("credit_pack_apple_ownership_invalid")
    environment = "sandbox" if str(evidence.environment).lower() == "sandbox" else "live"
    product = ProviderCreditPack.objects.filter(
        provider=PaymentProvider.APPLE_APP_STORE,
        environment=environment,
        external_product_id=evidence.product_id,
    ).first()
    if product is None:
        raise CreditPackUnavailable("credit_pack_apple_product_unmapped")
    return settle_credit_pack_purchase(
        user=user, product=product, external_purchase_id=evidence.transaction_id,
        evidence={"source": "apple_verified_jws", "product_id": evidence.product_id, "environment": environment},
    )


def settle_google_play_credit_pack(*, user, evidence) -> CreditPackPurchase:
    from billing.application.services.google_play import google_play_account_id

    if evidence.obfuscated_account_id != google_play_account_id(user):
        raise CreditPackUnavailable("credit_pack_google_account_mismatch")
    if evidence.status != "PURCHASED":
        raise CreditPackUnavailable("credit_pack_google_purchase_not_completed")
    product = ProviderCreditPack.objects.filter(
        provider=PaymentProvider.GOOGLE_PLAY,
        environment=evidence.environment,
        external_product_id=evidence.product_id,
        active=True,
    ).first()
    if product is None:
        raise CreditPackUnavailable("credit_pack_google_product_unmapped")
    return settle_credit_pack_purchase(
        user=user, product=product, external_purchase_id=evidence.purchase_token,
        evidence={"source": "google_play_server_api", "product_id": evidence.product_id, "order_id": evidence.order_id},
    )


@transaction.atomic
def refund_credit_pack_purchase(*, provider: str, external_purchase_id: str) -> CreditPackPurchase:
    purchase_id = _stored_purchase_id(provider=provider, purchase_id=external_purchase_id)
    purchase = CreditPackPurchase.objects.select_for_update().get(
        provider=provider, external_purchase_id=purchase_id
    )
    if purchase.status == CreditPackPurchase.Status.REFUNDED:
        return purchase
    wallet = CreditWallet.objects.select_for_update().get(user=purchase.user)
    recoverable = min(wallet.available_purchased_credits, purchase.credits_granted)
    deficit = purchase.credits_granted - recoverable
    wallet.purchased_balance -= recoverable
    wallet.balance -= recoverable
    if deficit:
        wallet.is_frozen = True
        wallet.frozen_reason = "Refunded credits were already consumed; review required"
        from django.utils import timezone
        wallet.frozen_at = timezone.now()
    wallet.save(update_fields=[
        "purchased_balance", "balance", "is_frozen", "frozen_reason", "frozen_at", "updated_at"
    ])
    CreditLedger.objects.create(
        wallet=wallet, user=purchase.user, kind=CreditLedger.Kind.ADJUSTMENT,
        credits_delta=-recoverable, reserved_delta=0,
        balance_after=wallet.balance, reserved_balance_after=wallet.reserved_balance,
        period=wallet.period, plan_snapshot_code=wallet.plan_snapshot_code,
        reference_type="credit_pack_refund",
        reference_id=credit_pack_ledger_reference_id(provider=provider, purchase_id=purchase_id),
        reason="verified_credit_pack_refund",
        metadata={"credit_source": "purchased", "unrecovered_credits": deficit},
    )
    purchase.status = CreditPackPurchase.Status.REFUNDED
    purchase.save(update_fields=["status", "updated_at"])
    return purchase


def reconcile_google_play_voided_products(*, gateway, start_time_ms: int, apply: bool = False) -> dict[str, int]:
    """Revoke only our matched, fully voided consumables from Google's API.

    A recurring scan is needed even if RTDN delivery fails. Tokens and order
    identifiers are never logged by this boundary.
    """
    summary = {"seen": 0, "matched": 0, "refunded": 0, "already_refunded": 0, "unknown": 0}
    for voided in gateway.list_voided_products(start_time_ms=start_time_ms):
        summary["seen"] += 1
        if voided.get("voidedQuantity") is not None:
            # The checkout only supports a single item; partial refunds need a
            # separate quantity-aware entitlement model before they can be used.
            continue
        token = str(voided.get("purchaseToken") or "")
        if not token:
            summary["unknown"] += 1
            continue
        purchase = CreditPackPurchase.objects.filter(
            provider=PaymentProvider.GOOGLE_PLAY,
            external_purchase_id=_stored_purchase_id(provider=PaymentProvider.GOOGLE_PLAY, purchase_id=token),
        ).first()
        if purchase is None:
            summary["unknown"] += 1
            continue
        known_order = str((purchase.evidence or {}).get("order_id") or "")
        voided_order = str(voided.get("orderId") or "")
        if known_order and voided_order and known_order != voided_order:
            raise CreditPackUnavailable("credit_pack_google_voided_order_mismatch")
        summary["matched"] += 1
        if purchase.status == CreditPackPurchase.Status.REFUNDED:
            summary["already_refunded"] += 1
        elif apply:
            refund_credit_pack_purchase(
                provider=PaymentProvider.GOOGLE_PLAY, external_purchase_id=token
            )
            summary["refunded"] += 1
    return summary
