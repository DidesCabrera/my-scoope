from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from django.utils import timezone

from accounts.models import AccountPlan, AccountSubscription, CreditWallet
from accounts.services.credits import (
    DEFAULT_ACCOUNT_PLAN_SLUG,
    current_account_credit_period,
    resolve_account_plan_for_user,
)


@dataclass(frozen=True)
class AccountCreditDisplay:
    """Read-only commercial account summary for user-facing/profile UI.

    The profile page must not create wallets just because the user opens their
    profile. When no wallet exists yet, the summary previews the monthly credits
    included by the effective plan and marks the source as plan defaults.
    """

    plan_name: str
    plan_slug: str
    subscription_status: str
    subscription_source: str
    period: str
    available_credits: int
    balance: int
    reserved_credits: int
    monthly_credit_limit: int
    daily_credit_limit: int
    included_monthly_credits: int
    wallet_exists: bool
    wallet_updated_at: str
    plan_source_label: str
    credit_source_label: str

    @property
    def available_label(self) -> str:
        return f"{self.available_credits} créditos"

    @property
    def reserved_label(self) -> str:
        return f"{self.reserved_credits} créditos"

    @property
    def monthly_limit_label(self) -> str:
        if self.monthly_credit_limit <= 0:
            return "Sin límite explícito"
        return f"{self.monthly_credit_limit} créditos/mes"

    @property
    def daily_limit_label(self) -> str:
        if self.daily_credit_limit <= 0:
            return "Sin límite diario"
        return f"{self.daily_credit_limit} créditos/día"


def build_account_credit_display(user: Any) -> AccountCreditDisplay:
    """Build the profile/admin friendly view of the user's commercial account."""

    plan = resolve_account_plan_for_user(user)
    subscription = _active_subscription_for_user(user)
    wallet = _wallet_for_user(user)
    period = current_account_credit_period()

    if plan is None:
        plan_name = "Sin plan comercial"
        plan_slug = DEFAULT_ACCOUNT_PLAN_SLUG
        included_monthly_credits = 0
        monthly_credit_limit = 0
        daily_credit_limit = 0
        plan_source_label = "No resuelto"
    else:
        plan_name = plan.name
        plan_slug = plan.slug
        included_monthly_credits = int(plan.included_monthly_credits or 0)
        monthly_credit_limit = _credit_limit_from_plan(plan, key="monthly_credit_limit")
        daily_credit_limit = _credit_limit_from_plan(plan, key="daily_credit_limit")
        plan_source_label = "Suscripción accounts" if subscription is not None else "Plan accounts por defecto"

    if wallet is None:
        balance = included_monthly_credits
        reserved_credits = 0
        available_credits = included_monthly_credits
        wallet_exists = False
        wallet_updated_at = "Sin wallet creada"
        credit_source_label = "Créditos incluidos del plan"
    else:
        balance = int(wallet.balance or 0)
        reserved_credits = int(wallet.reserved_balance or 0)
        available_credits = int(wallet.available_credits)
        wallet_exists = True
        wallet_updated_at = timezone.localtime(wallet.updated_at).strftime("%Y-%m-%d %H:%M")
        period = wallet.period or period
        credit_source_label = "Wallet comercial actual"

    return AccountCreditDisplay(
        plan_name=plan_name,
        plan_slug=plan_slug,
        subscription_status=subscription.get_status_display() if subscription is not None else "Sin suscripción account",
        subscription_source=subscription.get_source_display() if subscription is not None else "Fallback",
        period=period,
        available_credits=available_credits,
        balance=balance,
        reserved_credits=reserved_credits,
        monthly_credit_limit=monthly_credit_limit,
        daily_credit_limit=daily_credit_limit,
        included_monthly_credits=included_monthly_credits,
        wallet_exists=wallet_exists,
        wallet_updated_at=wallet_updated_at,
        plan_source_label=plan_source_label,
        credit_source_label=credit_source_label,
    )


def _active_subscription_for_user(user: Any) -> AccountSubscription | None:
    if user is None or not getattr(user, "pk", None):
        return None
    return (
        AccountSubscription.objects.select_related("plan")
        .filter(
            user=user,
            status__in=(AccountSubscription.Status.TRIALING, AccountSubscription.Status.ACTIVE),
            plan__status=AccountPlan.Status.ACTIVE,
        )
        .first()
    )


def _wallet_for_user(user: Any) -> CreditWallet | None:
    if user is None or not getattr(user, "pk", None):
        return None
    return CreditWallet.objects.filter(user=user).first()


def _credit_limit_from_plan(plan: AccountPlan, *, key: str) -> int:
    ai_entitlements = dict((plan.entitlements or {}).get("ai_assistant") or {})
    value = ai_entitlements.get(key, getattr(plan, key, 0) or 0)
    try:
        return max(int(value or 0), 0)
    except (TypeError, ValueError):
        return 0
