from __future__ import annotations

from dataclasses import dataclass

from accounts.services.profile import AccountCreditDisplay, build_account_credit_display
from billing.models import BillingPayment, BillingProduct, PaymentProvider, ProviderSubscription


@dataclass(frozen=True)
class BillingOverviewData:
    account: AccountCreditDisplay
    products: tuple[BillingProduct, ...]
    subscriptions: tuple[ProviderSubscription, ...]
    payments: tuple[BillingPayment, ...]


def get_billing_overview_data(*, user) -> BillingOverviewData:
    return BillingOverviewData(
        account=build_account_credit_display(user),
        products=tuple(
            BillingProduct.objects.select_related("account_plan")
            .filter(provider=PaymentProvider.MERCADO_PAGO, active=True, account_plan__status="active")
            .order_by("account_plan__display_order", "amount_minor")
        ),
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
