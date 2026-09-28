from __future__ import annotations

from dataclasses import dataclass

from django.conf import settings
from django.utils import timezone

from billing.application.queries import get_billing_overview_data
from billing.application.services.credit_packs import public_credit_pack_offers
from billing.application.services.paddle_checkout import (
    PaddleCheckoutUnavailable,
    build_paddle_checkout_payload,
    build_paddle_credit_pack_checkout_payload,
)
from billing.models import PaymentProvider, ProviderCreditPack, ProviderSubscription


@dataclass(frozen=True)
class BillingProductVM:
    id: int
    name: str
    description: str
    price: str
    interval: str
    can_checkout: bool
    paddle_price_id: str
    paddle_checkout_reference: str
    customer_email: str


@dataclass(frozen=True)
class CreditPackVM:
    credits: int
    price: str
    can_checkout: bool
    paddle_price_id: str
    paddle_checkout_reference: str
    customer_email: str
    mercado_pago_product_id: int | None
    mercado_pago_can_checkout: bool


@dataclass(frozen=True)
class BillingSubscriptionVM:
    id: int
    plan: str
    provider: str
    status: str
    can_cancel: bool
    can_manage: bool
    created_at: str


@dataclass(frozen=True)
class BillingPaymentVM:
    external_id: str
    date: str
    amount: str
    status: str
    tax_status: str
    folio: str


@dataclass(frozen=True)
class BillingOverviewVM:
    title: str
    subtitle: str
    plan_name: str
    available_credits: str
    subscription_status: str
    checkout_enabled: bool
    checkout_provider: str
    paddle_environment: str
    paddle_client_token: str
    paddle_success_url: str
    products: tuple[BillingProductVM, ...]
    credit_packs: tuple[CreditPackVM, ...]
    subscriptions: tuple[BillingSubscriptionVM, ...]
    payments: tuple[BillingPaymentVM, ...]


def build_billing_overview_vm(
    *,
    user,
    checkout_enabled: bool,
    provider: str,
    environment: str,
    paddle_client_token: str = "",
    paddle_success_url: str = "",
    paddle_portal_enabled: bool = False,
) -> BillingOverviewVM:
    data = get_billing_overview_data(user=user, provider=provider, environment=environment)
    products = []
    for product in data.products:
        paddle_payload = None
        if checkout_enabled and provider == PaymentProvider.PADDLE:
            try:
                paddle_payload = build_paddle_checkout_payload(
                    user=user,
                    product=product,
                    environment=environment,
                )
            except PaddleCheckoutUnavailable:
                paddle_payload = None
        products.append(BillingProductVM(
            id=product.pk,
            name=product.account_plan.name,
            description=product.account_plan.description,
            price=_money(product.amount_minor, product.currency),
            interval="mensual" if product.interval == product.Interval.MONTH else "anual",
            can_checkout=paddle_payload is not None,
            paddle_price_id=paddle_payload.price_id if paddle_payload else "",
            paddle_checkout_reference=paddle_payload.checkout_reference if paddle_payload else "",
            customer_email=paddle_payload.customer_email if paddle_payload else "",
        ))
    credit_packs = []
    paddle_packs = {pack.offer_id: pack for pack in data.credit_packs}
    mercado_pago_packs = {
        pack.offer_id: pack
        for pack in ProviderCreditPack.objects.select_related("offer").filter(
            provider=PaymentProvider.MERCADO_PAGO,
            environment=settings.BILLING_MERCADOPAGO_ENVIRONMENT,
            active=True, offer__active=True, offer__public=True,
        )
    }
    for offer in public_credit_pack_offers(user):
        pack = paddle_packs.get(offer.pk)
        mercado_pago_pack = mercado_pago_packs.get(offer.pk)
        paddle_payload = None
        if pack is not None and checkout_enabled and provider == PaymentProvider.PADDLE:
            try:
                paddle_payload = build_paddle_credit_pack_checkout_payload(
                    user=user, product=pack, environment=environment,
                )
            except PaddleCheckoutUnavailable:
                pass
        credit_packs.append(CreditPackVM(
            credits=offer.credits,
            price=_money(offer.amount_minor, offer.currency),
            can_checkout=paddle_payload is not None,
            paddle_price_id=paddle_payload.price_id if paddle_payload else "",
            paddle_checkout_reference=paddle_payload.checkout_reference if paddle_payload else "",
            customer_email=paddle_payload.customer_email if paddle_payload else "",
            mercado_pago_product_id=mercado_pago_pack.pk if mercado_pago_pack else None,
            mercado_pago_can_checkout=bool(
                mercado_pago_pack and settings.BILLING_MERCADOPAGO_CHECKOUT_ENABLED
                and settings.BILLING_PUBLIC_BASE_URL.startswith("https://") and user.email
            ),
        ))
    subscriptions = tuple(
        BillingSubscriptionVM(
            id=subscription.pk,
            plan=subscription.product.account_plan.name,
            provider=subscription.get_provider_display(),
            status=subscription.get_status_display(),
            can_cancel=subscription.provider == PaymentProvider.MERCADO_PAGO and subscription.status not in {
                ProviderSubscription.Status.CANCELED,
                ProviderSubscription.Status.EXPIRED,
            },
            can_manage=(
                subscription.provider == PaymentProvider.PADDLE
                and paddle_portal_enabled
                and subscription.product.environment == environment
                and bool((subscription.metadata or {}).get("paddle_customer_id"))
                and subscription.status not in {
                    ProviderSubscription.Status.CANCELED,
                    ProviderSubscription.Status.EXPIRED,
                }
            ),
            created_at=timezone.localtime(subscription.created_at).strftime("%Y-%m-%d"),
        )
        for subscription in data.subscriptions
    )
    payments = []
    for payment in data.payments:
        tax_document = getattr(payment, "tax_document", None)
        payments.append(BillingPaymentVM(
            external_id=payment.external_payment_id,
            date=timezone.localtime(payment.created_at).strftime("%Y-%m-%d %H:%M"),
            amount=_money(payment.amount_minor, payment.currency),
            status=payment.get_status_display(),
            tax_status=tax_document.get_status_display() if tax_document is not None else "Sin documento",
            folio=tax_document.folio if tax_document is not None else "",
        ))
    latest_subscription = data.subscriptions[0] if data.subscriptions else None
    return BillingOverviewVM(
        title="Billing",
        subtitle="Gestiona tu plan comercial, suscripción, pagos y documentos tributarios.",
        plan_name=data.account.plan_name,
        available_credits=data.account.available_label,
        subscription_status=(
            latest_subscription.get_status_display()
            if latest_subscription is not None
            else data.account.subscription_status
        ),
        checkout_enabled=checkout_enabled,
        checkout_provider=provider,
        paddle_environment=environment if provider == PaymentProvider.PADDLE else "",
        paddle_client_token=paddle_client_token if provider == PaymentProvider.PADDLE else "",
        paddle_success_url=paddle_success_url if provider == PaymentProvider.PADDLE else "",
        products=tuple(products),
        credit_packs=tuple(credit_packs),
        subscriptions=subscriptions,
        payments=tuple(payments),
    )


def _money(amount_minor: int, currency: str) -> str:
    if currency == "CLP":
        return f"${int(amount_minor):,} CLP".replace(",", ".")
    return f"{int(amount_minor) / 100:.2f} {currency}"
