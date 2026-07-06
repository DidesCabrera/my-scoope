from __future__ import annotations

import re
from typing import Any, Mapping

from django.conf import settings
from django.db import transaction

from accounts.models import AccountPlan, AccountSubscription
from accounts.services.credits import DEFAULT_ACCOUNT_PLAN_SLUG, LEGACY_ACCOUNT_PLAN_ALIASES, resolve_account_plan_for_user


def ensure_account_subscription_for_user(
    user: Any,
    *,
    source: str = AccountSubscription.Source.MIGRATION,
    update_existing: bool = False,
) -> tuple[AccountSubscription | None, bool, bool]:
    """Ensure a user has an active AccountSubscription when a plan can resolve.

    Returns `(subscription, created, updated)`. Missing seeded account plans are
    treated as a safe no-op so signals can call this during early setup.
    """

    if user is None or not getattr(user, "pk", None):
        return None, False, False

    plan = _preferred_plan_from_legacy_profile(user) or resolve_account_plan_for_user(user)
    if plan is None:
        plan = AccountPlan.objects.filter(slug=DEFAULT_ACCOUNT_PLAN_SLUG, status=AccountPlan.Status.ACTIVE).first()
    if plan is None:
        return None, False, False

    with transaction.atomic():
        subscription = AccountSubscription.objects.select_for_update().filter(user=user).first()
        if subscription is None:
            subscription = AccountSubscription.objects.create(
                user=user,
                plan=plan,
                status=AccountSubscription.Status.ACTIVE,
                source=source,
                metadata={"created_by": "accounts.services.subscriptions.ensure_account_subscription_for_user"},
            )
            return subscription, True, False

        if not update_existing:
            return subscription, False, False

        changed = False
        if subscription.plan_id != plan.pk:
            subscription.plan = plan
            changed = True
        if subscription.status not in (AccountSubscription.Status.TRIALING, AccountSubscription.Status.ACTIVE):
            subscription.status = AccountSubscription.Status.ACTIVE
            changed = True
        if changed:
            subscription.source = source
            metadata = dict(subscription.metadata or {})
            metadata["updated_by"] = "accounts.services.subscriptions.ensure_account_subscription_for_user"
            subscription.metadata = metadata
            subscription.save(update_fields=["plan", "status", "source", "metadata", "updated_at"])
            return subscription, False, True

    return subscription, False, False


def _preferred_plan_from_legacy_profile(user: Any) -> AccountPlan | None:
    profile = getattr(user, "profile", None)
    plan = getattr(profile, "plan", None)
    aliases = {**LEGACY_ACCOUNT_PLAN_ALIASES, **_settings_aliases()}
    candidates = (getattr(plan, "name", ""), getattr(plan, "role", ""), getattr(profile, "role", ""), DEFAULT_ACCOUNT_PLAN_SLUG)
    for value in candidates:
        normalized = _normalize_plan_slug(value)
        if not normalized:
            continue
        slug = aliases.get(normalized, normalized)
        account_plan = AccountPlan.objects.filter(slug=slug, status=AccountPlan.Status.ACTIVE).first()
        if account_plan is not None:
            return account_plan
    return None


def _settings_aliases() -> dict[str, str]:
    aliases = getattr(settings, "AI_ASSISTANT_CREDIT_PLAN_ALIASES", {}) or {}
    if not isinstance(aliases, Mapping):
        return {}
    return {_normalize_plan_slug(key): _normalize_plan_slug(value) for key, value in aliases.items() if key and value}


def _normalize_plan_slug(value: Any) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"[^a-z0-9]+", "_", text).strip("_")
    return text[:60]
