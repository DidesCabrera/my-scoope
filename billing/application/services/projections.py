"""Projection of verified commercial state into accounts."""

from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from accounts.models import AccountSubscription
from billing.models import ProviderSubscription

_STATUS_MAP = {
    ProviderSubscription.Status.AUTHORIZED: AccountSubscription.Status.ACTIVE,
    ProviderSubscription.Status.PAUSED: AccountSubscription.Status.PAST_DUE,
    ProviderSubscription.Status.PAST_DUE: AccountSubscription.Status.PAST_DUE,
    ProviderSubscription.Status.CANCELED: AccountSubscription.Status.CANCELED,
    ProviderSubscription.Status.EXPIRED: AccountSubscription.Status.EXPIRED,
}

_INACTIVE_STATUS_PRIORITY = {
    ProviderSubscription.Status.PAST_DUE: 30,
    ProviderSubscription.Status.PAUSED: 20,
    ProviderSubscription.Status.CANCELED: 10,
    ProviderSubscription.Status.EXPIRED: 0,
}

_PROVIDER_PRIORITY = {
    "apple_app_store": 20,
    "mercado_pago": 10,
}


@transaction.atomic
def project_provider_subscription(subscription: ProviderSubscription) -> AccountSubscription | None:
    """Recompute the account projection from every verified provider evidence row."""

    return project_user_billing_entitlement(subscription.user)


@transaction.atomic
def project_user_billing_entitlement(user) -> AccountSubscription | None:
    evidence = list(
        ProviderSubscription.objects.select_for_update()
        .select_related("product", "product__account_plan")
        .filter(user=user)
        .exclude(status=ProviderSubscription.Status.PENDING)
    )
    if not evidence:
        return None

    active = [item for item in evidence if item.status == ProviderSubscription.Status.AUTHORIZED]
    selected = max(active or evidence, key=_projection_sort_key)
    target_status = _STATUS_MAP[selected.status]
    existing = AccountSubscription.objects.select_for_update().filter(user=user).first()
    active_providers = sorted({item.provider for item in active})
    metadata = dict(existing.metadata or {}) if existing is not None else {}
    metadata.update(
        {
            "billing_projection_version": "cml06.v1",
            "billing_provider": selected.provider,
            "billing_subscription_id": str(selected.pk),
            "billing_subscription_ids": [str(item.pk) for item in sorted(evidence, key=lambda item: item.pk)],
            "billing_active_providers": active_providers,
            "billing_duplicate_active_providers": len(active_providers) > 1,
            "external_subscription_id": selected.external_subscription_id,
        }
    )
    defaults = {
        "plan": selected.product.account_plan,
        "status": target_status,
        "source": AccountSubscription.Source.BILLING,
        "current_period_start": selected.current_period_start,
        "current_period_end": selected.current_period_end,
        "metadata": metadata,
    }
    if target_status in {AccountSubscription.Status.CANCELED, AccountSubscription.Status.EXPIRED}:
        defaults["ended_at"] = timezone.now()
    else:
        defaults["ended_at"] = None

    account_subscription, _ = AccountSubscription.objects.update_or_create(
        user=user,
        defaults=defaults,
    )
    return account_subscription


def _projection_sort_key(subscription: ProviderSubscription) -> tuple:
    period_end = subscription.current_period_end
    period_end_value = period_end.timestamp() if period_end is not None else 0
    return (
        1 if subscription.status == ProviderSubscription.Status.AUTHORIZED else 0,
        int(subscription.product.account_plan.display_order or 0),
        period_end_value,
        _INACTIVE_STATUS_PRIORITY.get(subscription.status, -1),
        _PROVIDER_PRIORITY.get(subscription.provider, 0),
        subscription.pk,
    )
