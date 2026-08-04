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


@transaction.atomic
def project_provider_subscription(subscription: ProviderSubscription) -> AccountSubscription | None:
    """Project verified provider state into the account entitlement source of truth."""

    target_status = _STATUS_MAP.get(subscription.status)
    if target_status is None:
        return None

    existing = AccountSubscription.objects.select_for_update().filter(user=subscription.user).first()
    projection_key = str(subscription.pk)

    if existing is not None and subscription.status != ProviderSubscription.Status.AUTHORIZED:
        if str((existing.metadata or {}).get("billing_subscription_id", "")) != projection_key:
            return existing

    metadata = dict(existing.metadata or {}) if existing is not None else {}
    metadata.update(
        {
            "billing_provider": subscription.provider,
            "billing_subscription_id": projection_key,
            "external_subscription_id": subscription.external_subscription_id,
        }
    )
    defaults = {
        "plan": subscription.product.account_plan,
        "status": target_status,
        "source": AccountSubscription.Source.BILLING,
        "current_period_start": subscription.current_period_start,
        "current_period_end": subscription.current_period_end,
        "metadata": metadata,
    }
    if target_status in {AccountSubscription.Status.CANCELED, AccountSubscription.Status.EXPIRED}:
        defaults["ended_at"] = timezone.now()
    else:
        defaults["ended_at"] = None

    account_subscription, _ = AccountSubscription.objects.update_or_create(
        user=subscription.user,
        defaults=defaults,
    )
    return account_subscription
