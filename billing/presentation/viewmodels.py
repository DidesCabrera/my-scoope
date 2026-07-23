from __future__ import annotations

from dataclasses import dataclass

from django.utils import timezone

from billing.application.queries import get_billing_overview_data
from billing.models import ProviderSubscription


@dataclass(frozen=True)
class BillingProductVM:
    id: int
    name: str
    description: str
    price: str
    interval: str


@dataclass(frozen=True)
class BillingSubscriptionVM:
    id: int
    plan: str
    provider: str
    status: str
    can_cancel: bool
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
    products: tuple[BillingProductVM, ...]
    subscriptions: tuple[BillingSubscriptionVM, ...]
    payments: tuple[BillingPaymentVM, ...]


def build_billing_overview_vm(*, user, checkout_enabled: bool) -> BillingOverviewVM:
    data = get_billing_overview_data(user=user)
    products = tuple(
        BillingProductVM(
            id=product.pk,
            name=product.account_plan.name,
            description=product.account_plan.description,
            price=_money(product.amount_minor, product.currency),
            interval="mensual" if product.interval == product.Interval.MONTH else "anual",
        )
        for product in data.products
    )
    subscriptions = tuple(
        BillingSubscriptionVM(
            id=subscription.pk,
            plan=subscription.product.account_plan.name,
            provider=subscription.get_provider_display(),
            status=subscription.get_status_display(),
            can_cancel=subscription.status not in {
                ProviderSubscription.Status.CANCELED,
                ProviderSubscription.Status.EXPIRED,
            },
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
        products=products,
        subscriptions=subscriptions,
        payments=tuple(payments),
    )


def _money(amount_minor: int, currency: str) -> str:
    if currency == "CLP":
        return f"${int(amount_minor):,} CLP".replace(",", ".")
    return f"{int(amount_minor) / 100:.2f} {currency}"
