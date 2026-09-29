from __future__ import annotations

from dataclasses import dataclass

from accounts.services.profile import AccountCreditDisplay, build_account_credit_display
from billing.application.services.credit_packs import may_buy_credit_packs
from billing.models import BillingPayment, BillingProduct, PaymentProvider, ProviderCreditPack, ProviderSubscription


@dataclass(frozen=True)
class BillingOverviewData:
    account: AccountCreditDisplay
    products: tuple[BillingProduct, ...]
    credit_packs: tuple[ProviderCreditPack, ...]
    subscriptions: tuple[ProviderSubscription, ...]
    payments: tuple[BillingPayment, ...]


def get_billing_overview_data(
    *,
    user,
    provider: str = PaymentProvider.MERCADO_PAGO,
    environment: str = BillingProduct.Environment.LIVE,
) -> BillingOverviewData:
    return BillingOverviewData(
        account=build_account_credit_display(user),
        products=tuple(
            BillingProduct.objects.select_related("account_plan")
            .filter(
                provider=provider,
                environment=environment,
                active=True,
                account_plan__status="active",
            )
            .order_by("account_plan__display_order", "amount_minor")
        ),
        credit_packs=tuple(
            ProviderCreditPack.objects.select_related("offer")
            .filter(provider=provider, environment=environment, active=True, offer__active=True, offer__public=True)
            .order_by("offer__display_order")
        ) if may_buy_credit_packs(user) else (),
        subscriptions=tuple(
            ProviderSubscription.objects.select_related("product", "product__account_plan")
            .filter(user=user)
            .order_by("-created_at")[:10]
        ),
        payments=tuple(
            BillingPayment.objects.select_related("subscription", "subscription__product", "tax_document")
            .filter(user=user)
            .order_by("-created_at")[:20]
        ),
    )
