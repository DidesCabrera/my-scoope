from django.conf import settings
from django.utils import timezone
from django.db.models import Q
from accounts.models import AccountSubscription
from accounts.services.credits import resolve_account_plan_for_user

from billing.application.services.apple_app_store import get_or_create_apple_app_account_token
from billing.application.services.apple_environment import (
    UnsupportedAppleEnvironment,
    apple_catalog_environment,
)
from billing.application.services.credit_packs import may_buy_credit_packs
from billing.application.services.google_play import (
    get_or_create_google_play_account_token,
    google_play_environment,
)
from billing.models import BillingProduct, PaymentProvider, ProviderCreditPack, ProviderSubscription
from mobile_api.apple_billing import apple_purchase_environment_for_user


def _transaction_products(enabled_providers, *, apple_environment, google_environment):
    """Receipt routing includes retired mappings without offering them for sale."""
    environments = Q(pk__in=[])
    if PaymentProvider.APPLE_APP_STORE in enabled_providers and apple_environment is not None:
        environments |= Q(provider=PaymentProvider.APPLE_APP_STORE, environment=apple_environment)
    if PaymentProvider.GOOGLE_PLAY in enabled_providers and google_environment is not None:
        environments |= Q(provider=PaymentProvider.GOOGLE_PLAY, environment=google_environment)
    return [
        {"product_id": row.external_product_id, "provider": row.provider,
         "kind": "subscription", "plan_name": row.account_plan.name}
        for row in BillingProduct.objects.select_related("account_plan").filter(environments)
    ] + [
        {"product_id": row.external_product_id, "provider": row.provider, "kind": "credit_pack"}
        for row in ProviderCreditPack.objects.filter(environments)
    ]


def subscription_payload(user) -> dict:
    now = timezone.now()
    profile = getattr(user, "profile", None)
    eligible = str(getattr(profile, "role", "member") or "member").lower() == "member"
    can_buy_packs = may_buy_credit_packs(user)
    subscription = AccountSubscription.objects.select_related("plan").filter(user=user).first()
    effective_plan = resolve_account_plan_for_user(user)
    token = get_or_create_apple_app_account_token(user) if eligible or can_buy_packs else None
    products = []
    enabled_providers = []
    apple_purchase_environment = apple_purchase_environment_for_user(user)
    try:
        configured_apple_catalog_environment = (
            apple_catalog_environment(apple_purchase_environment)
            if apple_purchase_environment is not None
            else None
        )
    except UnsupportedAppleEnvironment:
        configured_apple_catalog_environment = None
    if configured_apple_catalog_environment is not None:
        enabled_providers.append(PaymentProvider.APPLE_APP_STORE)
    if settings.BILLING_GOOGLE_PLAY_PURCHASES_ENABLED:
        enabled_providers.append(PaymentProvider.GOOGLE_PLAY)
    try:
        configured_google_catalog_environment = google_play_environment(settings.BILLING_GOOGLE_PLAY_ENVIRONMENT)
    except ValueError:
        configured_google_catalog_environment = None
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
            product_query.filter(
                provider=PaymentProvider.GOOGLE_PLAY,
                environment=configured_google_catalog_environment,
            )
            if PaymentProvider.GOOGLE_PLAY in enabled_providers and configured_google_catalog_environment is not None
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
        ProviderSubscription.objects.select_related("product").filter(user=user)
        .exclude(status=ProviderSubscription.Status.PENDING)
        .order_by("provider", "-updated_at")
    )
    status = subscription.status if subscription is not None else "none"
    if subscription and status in {"active", "trialing"} and subscription.current_period_end and subscription.current_period_end <= now:
        status = "expired"
    active_providers = {item.provider for item in evidence if item.status == "authorized" and (
        item.current_period_end is None or item.current_period_end > now
    )}
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
            pack_query.filter(
                provider=PaymentProvider.GOOGLE_PLAY,
                environment=configured_google_catalog_environment,
            )
            if PaymentProvider.GOOGLE_PLAY in enabled_providers and configured_google_catalog_environment is not None
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
        "google_obfuscated_account_id": (
            get_or_create_google_play_account_token(user).token if eligible or can_buy_packs else ""
        ),
        "plan_name": effective_plan.name if effective_plan is not None else "Sin plan",
        "status": status,
        "products": products,
        "credit_packs": credit_packs,
        "transaction_products": _transaction_products(enabled_providers,
            apple_environment=configured_apple_catalog_environment,
            google_environment=configured_google_catalog_environment) if eligible or can_buy_packs else [],
        "can_buy_credit_packs": can_buy_packs,
        "evidence": [
            {
                "provider": item.provider,
                "status": "expired" if item.status == "authorized" and item.current_period_end and item.current_period_end <= now else item.status,
                "period_end": item.current_period_end,
                "product_id": item.product.external_product_id,
                "next_product_id": (item.metadata or {}).get("apple_next_product_id", ""),
                "cancel_at_period_end": item.cancel_at_period_end,
            }
            for item in evidence
        ],
        "duplicate_active_providers": len(active_providers) > 1,
    }
