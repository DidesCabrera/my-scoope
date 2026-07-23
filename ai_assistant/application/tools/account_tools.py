from django.conf import settings

from billing.application.queries import get_billing_overview_data
from billing.models import ProviderSubscription
from notas.application.ai_tools.results import tool_success


def read_account_billing_context_tool(user):
    overview = get_billing_overview_data(user=user)
    latest_subscription = overview.subscriptions[0] if overview.subscriptions else None
    return tool_success(
        {
            "account_billing": {
                "plan_name": overview.account.plan_name,
                "plan_slug": overview.account.plan_slug,
                "available_credits": overview.account.available_credits,
                "reserved_credits": overview.account.reserved_credits,
                "subscription_status": (
                    latest_subscription.get_status_display()
                    if latest_subscription is not None
                    else overview.account.subscription_status
                ),
                "checkout_enabled": bool(
                    getattr(settings, "BILLING_MERCADOPAGO_CHECKOUT_ENABLED", False)
                ),
                "products": [
                    {
                        "id": product.id,
                        "name": product.account_plan.name,
                        "description": product.account_plan.description,
                        "amount_minor": product.amount_minor,
                        "currency": product.currency,
                        "interval": product.interval,
                    }
                    for product in overview.products
                ],
                "subscriptions": [
                    {
                        "id": subscription.id,
                        "plan": subscription.product.account_plan.name,
                        "provider": subscription.get_provider_display(),
                        "status": subscription.get_status_display(),
                        "can_cancel": subscription.status not in {
                            ProviderSubscription.Status.CANCELED,
                            ProviderSubscription.Status.EXPIRED,
                        },
                        "created_at": subscription.created_at.isoformat(),
                    }
                    for subscription in overview.subscriptions
                ],
                "payments": [
                    {
                        "external_id": payment.external_payment_id,
                        "date": payment.created_at.isoformat(),
                        "amount_minor": payment.amount_minor,
                        "currency": payment.currency,
                        "status": payment.get_status_display(),
                        "tax_status": (
                            payment.tax_document.get_status_display()
                            if getattr(payment, "tax_document", None) is not None
                            else "Sin documento"
                        ),
                        "folio": (
                            payment.tax_document.folio
                            if getattr(payment, "tax_document", None) is not None
                            else ""
                        ),
                    }
                    for payment in overview.payments
                ],
            },
            "navigation_policy": {
                "checkout_requires_trusted_ui": True,
                "subscription_cancellation_requires_trusted_ui": True,
                "assistant_may_not_call_payment_provider": True,
            },
        }
    )
