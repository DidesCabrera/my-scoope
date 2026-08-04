from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from django.db import transaction
from django.utils import timezone

from accounts.models import AccountPlan, AccountSubscription, CreditLedger, CreditWallet

DEFAULT_ACCOUNT_PLAN_SLUG = "free"
ACCOUNT_PLAN_BY_PROFILE_ROLE = {
    "default": "free",
    "member": "basic",
    "nutritionist": "pro",
}


class InsufficientAccountCredits(Exception):
    """Raised when a wallet cannot reserve or consume the requested credits."""


class AccountCreditsFrozen(InsufficientAccountCredits):
    """Raised when account credit consumption is operationally frozen."""


@dataclass(frozen=True)
class AccountCreditPlanSnapshot:
    slug: str
    name: str
    included_monthly_credits: int
    monthly_credit_limit: int
    daily_credit_limit: int
    block_on_exhaustion: bool

    def as_ai_credit_plan_kwargs(self) -> dict[str, Any]:
        return {
            "code": self.slug,
            "monthly_credit_limit": self.monthly_credit_limit,
            "daily_credit_limit": self.daily_credit_limit,
            "block_on_exhaustion": self.block_on_exhaustion,
        }


def current_account_credit_period() -> str:
    return timezone.localdate().strftime("%Y-%m")


def resolve_account_plan_for_user(user: Any | None) -> AccountPlan | None:
    if user is None or not getattr(user, "pk", None):
        return _active_plan_by_slug(DEFAULT_ACCOUNT_PLAN_SLUG)

    subscription = (
        AccountSubscription.objects.select_related("plan")
        .filter(
            user=user,
            status__in=(AccountSubscription.Status.TRIALING, AccountSubscription.Status.ACTIVE),
            plan__status=AccountPlan.Status.ACTIVE,
        )
        .first()
    )
    if subscription is not None:
        return subscription.plan

    return _active_plan_by_slug(DEFAULT_ACCOUNT_PLAN_SLUG)


def resolve_account_credit_plan_snapshot(user: Any | None) -> AccountCreditPlanSnapshot | None:
    plan = resolve_account_plan_for_user(user)
    if plan is None:
        return None
    ai_entitlements = dict((plan.entitlements or {}).get("ai_assistant") or {})
    return AccountCreditPlanSnapshot(
        slug=plan.slug,
        name=plan.name,
        included_monthly_credits=int(plan.included_monthly_credits or 0),
        monthly_credit_limit=_non_negative_int(
            ai_entitlements.get("monthly_credit_limit", plan.monthly_credit_limit or plan.included_monthly_credits or 0)
        ),
        daily_credit_limit=_non_negative_int(ai_entitlements.get("daily_credit_limit", plan.daily_credit_limit or 0)),
        block_on_exhaustion=_truthy(ai_entitlements.get("block_on_exhaustion", True)),
    )


def get_or_create_current_wallet(*, user: Any, plan: AccountPlan | None = None) -> CreditWallet:
    if user is None or not getattr(user, "pk", None):
        raise ValueError("A persisted user is required for account credit wallets.")
    plan = plan or resolve_account_plan_for_user(user)
    period = current_account_credit_period()
    defaults = {
        "period": period,
        "balance": int(getattr(plan, "included_monthly_credits", 0) or 0),
        "reserved_balance": 0,
        "plan_snapshot_code": str(getattr(plan, "slug", "") or ""),
    }
    wallet, created = CreditWallet.objects.get_or_create(user=user, defaults=defaults)
    update_fields: list[str] = []
    if created:
        return wallet
    if wallet.period != period:
        wallet.period = period
        wallet.balance = defaults["balance"]
        wallet.reserved_balance = 0
        wallet.plan_snapshot_code = defaults["plan_snapshot_code"]
        update_fields.extend(["period", "balance", "reserved_balance", "plan_snapshot_code"])
    elif plan is not None and wallet.plan_snapshot_code != plan.slug:
        wallet.plan_snapshot_code = plan.slug
        update_fields.append("plan_snapshot_code")
    if update_fields:
        update_fields.append("updated_at")
        wallet.save(update_fields=update_fields)
    return wallet


def reserve_account_credits(
    *,
    user: Any,
    credits: int,
    reference_type: str,
    reference_id: str,
    reason: str = "",
    metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    credits = _non_negative_int(credits)
    if credits <= 0:
        return {"reserved": False, "reason": "zero_credit_reservation"}
    if not reference_type or not reference_id:
        return {"reserved": False, "reason": "missing_reference"}

    with transaction.atomic():
        existing = _reservation_entry(reference_type=reference_type, reference_id=reference_id)
        if existing is not None:
            return _reservation_summary(existing.wallet, existing, already_reserved=True)

        plan = resolve_account_plan_for_user(user)
        if plan is None:
            return {"reserved": False, "reason": "account_plan_not_found"}
        wallet = CreditWallet.objects.select_for_update().filter(user=user).first()
        if wallet is None:
            wallet = get_or_create_current_wallet(user=user, plan=plan)
            wallet = CreditWallet.objects.select_for_update().get(pk=wallet.pk)
        elif wallet.period != current_account_credit_period():
            wallet.period = current_account_credit_period()
            wallet.balance = int(plan.included_monthly_credits or 0)
            wallet.reserved_balance = 0
            wallet.plan_snapshot_code = plan.slug

        if wallet.is_frozen:
            raise AccountCreditsFrozen(wallet.frozen_reason or "Account credits are frozen.")

        if wallet.available_credits < credits:
            raise InsufficientAccountCredits("Insufficient account credits available for this reservation.")

        wallet.reserved_balance = int(wallet.reserved_balance or 0) + credits
        wallet.save(update_fields=["period", "balance", "reserved_balance", "plan_snapshot_code", "updated_at"])
        ledger = CreditLedger.objects.create(
            wallet=wallet,
            user=user,
            kind=CreditLedger.Kind.RESERVE,
            credits_delta=0,
            reserved_delta=credits,
            balance_after=wallet.balance,
            reserved_balance_after=wallet.reserved_balance,
            period=wallet.period,
            plan_snapshot_code=wallet.plan_snapshot_code,
            reference_type=reference_type,
            reference_id=reference_id,
            reason=reason or "ai_turn_credit_reservation",
            metadata=dict(metadata or {}),
        )
    return _reservation_summary(wallet, ledger, already_reserved=False)


def consume_account_credit_reservation(
    *,
    user: Any,
    credits: int,
    reference_type: str,
    reference_id: str,
    reason: str = "",
    metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    credits = _non_negative_int(credits)
    if credits <= 0:
        return release_account_credit_reservation(
            user=user,
            reference_type=reference_type,
            reference_id=reference_id,
            reason=reason or "zero_credit_consumption_release",
            metadata=metadata,
        )

    with transaction.atomic():
        reservation = _reservation_entry(reference_type=reference_type, reference_id=reference_id)
        if reservation is None:
            return {"consumed": False, "reason": "reservation_not_found"}
        if _movement_exists(
            kinds=(CreditLedger.Kind.CONSUME, CreditLedger.Kind.RELEASE),
            reference_type=reference_type,
            reference_id=reference_id,
        ):
            return {"consumed": False, "reason": "reservation_already_closed"}

        wallet = CreditWallet.objects.select_for_update().get(pk=reservation.wallet_id)
        reserved_to_close = max(0, int(reservation.reserved_delta or 0))
        extra_credits = max(0, credits - reserved_to_close)
        if wallet.available_credits < extra_credits:
            raise InsufficientAccountCredits("Insufficient account credits available to consume this turn.")
        wallet.balance = max(0, int(wallet.balance or 0) - credits)
        wallet.reserved_balance = max(0, int(wallet.reserved_balance or 0) - reserved_to_close)
        wallet.save(update_fields=["balance", "reserved_balance", "updated_at"])
        ledger = CreditLedger.objects.create(
            wallet=wallet,
            user=user,
            kind=CreditLedger.Kind.CONSUME,
            credits_delta=-credits,
            reserved_delta=-reserved_to_close,
            balance_after=wallet.balance,
            reserved_balance_after=wallet.reserved_balance,
            period=wallet.period,
            plan_snapshot_code=wallet.plan_snapshot_code,
            reference_type=reference_type,
            reference_id=reference_id,
            reason=reason or "ai_turn_credit_consumption",
            metadata=dict(metadata or {}),
        )
    return {"consumed": True, "ledger_id": ledger.pk, "credits": credits, "balance_after": wallet.balance, "reserved_balance_after": wallet.reserved_balance}


def release_account_credit_reservation(
    *,
    user: Any,
    reference_type: str,
    reference_id: str,
    reason: str = "",
    metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    with transaction.atomic():
        reservation = _reservation_entry(reference_type=reference_type, reference_id=reference_id)
        if reservation is None:
            return {"released": False, "reason": "reservation_not_found"}
        if _movement_exists(
            kinds=(CreditLedger.Kind.CONSUME, CreditLedger.Kind.RELEASE),
            reference_type=reference_type,
            reference_id=reference_id,
        ):
            return {"released": False, "reason": "reservation_already_closed"}
        wallet = CreditWallet.objects.select_for_update().get(pk=reservation.wallet_id)
        reserved_to_close = max(0, int(reservation.reserved_delta or 0))
        wallet.reserved_balance = max(0, int(wallet.reserved_balance or 0) - reserved_to_close)
        wallet.save(update_fields=["reserved_balance", "updated_at"])
        ledger = CreditLedger.objects.create(
            wallet=wallet,
            user=user,
            kind=CreditLedger.Kind.RELEASE,
            credits_delta=0,
            reserved_delta=-reserved_to_close,
            balance_after=wallet.balance,
            reserved_balance_after=wallet.reserved_balance,
            period=wallet.period,
            plan_snapshot_code=wallet.plan_snapshot_code,
            reference_type=reference_type,
            reference_id=reference_id,
            reason=reason or "ai_turn_credit_release",
            metadata=dict(metadata or {}),
        )
    return {"released": True, "ledger_id": ledger.pk, "credits": reserved_to_close, "balance_after": wallet.balance, "reserved_balance_after": wallet.reserved_balance}


def _reservation_entry(*, reference_type: str, reference_id: str) -> CreditLedger | None:
    return (
        CreditLedger.objects.select_related("wallet")
        .filter(
            kind=CreditLedger.Kind.RESERVE,
            reference_type=reference_type,
            reference_id=reference_id,
        )
        .order_by("created_at", "id")
        .first()
    )


def _movement_exists(*, kinds: tuple[str, ...], reference_type: str, reference_id: str) -> bool:
    return CreditLedger.objects.filter(kind__in=kinds, reference_type=reference_type, reference_id=reference_id).exists()


def _reservation_summary(wallet: CreditWallet, ledger: CreditLedger, *, already_reserved: bool) -> dict[str, Any]:
    return {
        "reserved": True,
        "already_reserved": already_reserved,
        "ledger_id": ledger.pk,
        "credits": int(ledger.reserved_delta or 0),
        "balance_after": wallet.balance,
        "reserved_balance_after": wallet.reserved_balance,
        "available_credits_after": wallet.available_credits,
        "plan_code": wallet.plan_snapshot_code,
    }


def _active_plan_by_slug(slug: str) -> AccountPlan | None:
    return AccountPlan.objects.filter(slug=slug, status=AccountPlan.Status.ACTIVE).first()


def _non_negative_int(value: Any) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}
