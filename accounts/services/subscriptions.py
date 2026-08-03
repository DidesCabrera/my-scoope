from __future__ import annotations

from typing import Any

from django.db import transaction

from accounts.models import AccountPlan, AccountSubscription
from accounts.services.credits import ACCOUNT_PLAN_BY_PROFILE_ROLE, DEFAULT_ACCOUNT_PLAN_SLUG, resolve_account_plan_for_user


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

    plan = _initial_plan_for_user_role(user) or resolve_account_plan_for_user(user)
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


def _initial_plan_for_user_role(user: Any) -> AccountPlan | None:
    profile = getattr(user, "profile", None)
    role = str(getattr(profile, "role", "") or "").strip().lower()
    slug = ACCOUNT_PLAN_BY_PROFILE_ROLE.get(role, DEFAULT_ACCOUNT_PLAN_SLUG)
    return AccountPlan.objects.filter(slug=slug, status=AccountPlan.Status.ACTIVE).first()
