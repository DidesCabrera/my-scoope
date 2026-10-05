from django.conf import settings

from billing.application.services.apple_app_store import (
    UnsupportedAppleEnvironment,
    apple_catalog_environment,
    get_or_create_apple_app_account_token,
)
from billing.application.services.credit_packs import may_buy_credit_packs
from billing.application.services.google_play import google_play_account_id
from billing.models import BillingProduct, PaymentProvider, ProviderCreditPack, ProviderSubscription


def subscription_payload(user) -> dict:
    profile = getattr(user, "profile", None)
    eligible = str(getattr(profile, "role", "member") or "member").lower() == "member"
    can_buy_packs = may_buy_credit_packs(user)
    subscription = getattr(user, "account_subscription", None)
    token = get_or_create_apple_app_account_token(user) if eligible or can_buy_packs else None
    products = []
    enabled_providers = []
    try:
        configured_apple_catalog_environment = apple_catalog_environment(settings.BILLING_APPLE_ENVIRONMENT)
    except UnsupportedAppleEnvironment:
        configured_apple_catalog_environment = None
    if settings.BILLING_APPLE_PURCHASES_ENABLED and configured_apple_catalog_environment is not None:
        enabled_providers.append(PaymentProvider.APPLE_APP_STORE)
    if settings.BILLING_GOOGLE_PLAY_PURCHASES_ENABLED:
        enabled_providers.append(PaymentProvider.GOOGLE_PLAY)
    if eligible and enabled_providers:
        product_query = BillingProduct.objects.select_related("account_plan").filter(
            active=True,
            account_plan__status="active",
        )
        apple_products = (
            product_query.filter(
                provider=PaymentProvider.APPLE_APP_STORE,
                environment=configured_apple_catalog_environment,
            )
            if PaymentProvider.APPLE_APP_STORE in enabled_providers
            else product_query.none()
        )
        google_products = (
            product_query.filter(provider=PaymentProvider.GOOGLE_PLAY)
            if PaymentProvider.GOOGLE_PLAY in enabled_providers
            else product_query.none()
        )
        products = [
            {
                "product_id": product.external_product_id,
                "provider": product.provider,
                "base_plan_id": product.external_price_id,
                "plan_name": product.account_plan.name,
                "interval": product.interval,
            }
            for product in (*apple_products, *google_products)
        ]
    evidence = list(
        ProviderSubscription.objects.filter(user=user)
        .exclude(status=ProviderSubscription.Status.PENDING)
        .order_by("provider", "-updated_at")
        .values("provider", "status", "current_period_end")
    )
    metadata = dict(getattr(subscription, "metadata", {}) or {})
    credit_packs = []
    if (eligible or can_buy_packs) and enabled_providers:
        pack_query = ProviderCreditPack.objects.select_related("offer").filter(
            active=True,
            offer__active=True,
            offer__public=True,
        )
        apple_packs = (
            pack_query.filter(
                provider=PaymentProvider.APPLE_APP_STORE,
                environment=configured_apple_catalog_environment,
            )
            if PaymentProvider.APPLE_APP_STORE in enabled_providers
            else pack_query.none()
        )
        google_packs = (
            pack_query.filter(provider=PaymentProvider.GOOGLE_PLAY)
            if PaymentProvider.GOOGLE_PLAY in enabled_providers
            else pack_query.none()
        )
        credit_packs = [
            {
                "product_id": product.external_product_id,
                "provider": product.provider,
                "credits": product.credits_snapshot,
                "amount_minor": product.amount_minor,
                "currency": product.currency,
            }
            for product in sorted(
                (*apple_packs, *google_packs),
                key=lambda item: item.offer.display_order,
            )
        ]
    return {
        "eligible": eligible,
        "purchases_enabled": bool(eligible and products),
        "app_account_token": str(token.token) if token is not None else "",
        "google_obfuscated_account_id": google_play_account_id(user) if eligible or can_buy_packs else "",
        "plan_name": subscription.plan.name if subscription is not None else "Sin plan",
        "status": subscription.status if subscription is not None else "none",
        "products": products,
        "credit_packs": credit_packs,
        "can_buy_credit_packs": can_buy_packs,
        "evidence": [
            {
                "provider": item["provider"],
                "status": item["status"],
                "period_end": item["current_period_end"],
            }
            for item in evidence
        ],
        "duplicate_active_providers": bool(metadata.get("billing_duplicate_active_providers")),
    }
