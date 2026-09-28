from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from django.db import transaction
from django.utils import timezone

from accounts.models import AccountPlan, AccountSubscription, CreditLedger, CreditWallet

DEFAULT_ACCOUNT_PLAN_SLUG = "free"
ACCOUNT_PLAN_BY_PROFILE_ROLE = {
    "default": "free",
    "member": "free",
    "nutritionist": "free",
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
    with transaction.atomic():
        wallet, created = CreditWallet.objects.get_or_create(user=user, defaults=defaults)
        wallet = CreditWallet.objects.select_for_update().get(pk=wallet.pk)
        if created:
            if wallet.balance:
                _record_wallet_movement(wallet, CreditLedger.Kind.GRANT, wallet.balance, "plan_monthly_grant")
            return wallet
        _refresh_wallet_for_plan(wallet, plan=plan, period=period)
        return wallet


def _record_wallet_movement(wallet: CreditWallet, kind: str, delta: int, reason: str) -> None:
    CreditLedger.objects.create(
        wallet=wallet,
        user=wallet.user,
        kind=kind,
        credits_delta=delta,
        reserved_delta=0,
        balance_after=wallet.balance,
        reserved_balance_after=wallet.reserved_balance,
        period=wallet.period,
        plan_snapshot_code=wallet.plan_snapshot_code,
        reference_type="account_plan_period",
        reference_id=f"{wallet.period}:{wallet.plan_snapshot_code}",
        reason=reason,
        metadata={"credit_source": "monthly"},
    )


def _refresh_wallet_for_plan(wallet: CreditWallet, *, plan: AccountPlan | None, period: str) -> None:
    if plan is None or (wallet.period == period and wallet.plan_snapshot_code == plan.slug):
        return
    # An in-flight reservation must close against its original buckets first.
    if wallet.reserved_balance:
        return
    monthly_remaining = max(wallet.balance - wallet.purchased_balance, 0)
    if monthly_remaining:
        wallet.balance -= monthly_remaining
        wallet.save(update_fields=["balance", "updated_at"])
        _record_wallet_movement(wallet, CreditLedger.Kind.EXPIRE, -monthly_remaining, "plan_monthly_expire")
    wallet.period = period
    wallet.plan_snapshot_code = plan.slug
    grant = int(plan.included_monthly_credits or 0)
    wallet.balance += grant
    wallet.save(update_fields=["period", "plan_snapshot_code", "balance", "updated_at"])
    if grant:
        _record_wallet_movement(wallet, CreditLedger.Kind.GRANT, grant, "plan_monthly_grant")


def grant_purchased_credits(*, user: Any, credits: int, provider: str, purchase_id: str) -> bool:
    """Idempotent settlement after verified provider payment evidence."""

    credits = _non_negative_int(credits)
    if credits <= 0 or not provider or not purchase_id:
        raise ValueError("A verified purchase identity and positive credit amount are required.")
    with transaction.atomic():
        wallet = get_or_create_current_wallet(user=user)
        wallet = CreditWallet.objects.select_for_update().get(pk=wallet.pk)
        reference_id = f"{provider}:{purchase_id}"
        if CreditLedger.objects.filter(
            wallet=wallet, kind=CreditLedger.Kind.GRANT,
            reference_type="credit_pack_purchase", reference_id=reference_id,
        ).exists():
            return False
        wallet.balance += credits
        wallet.purchased_balance += credits
        wallet.save(update_fields=["balance", "purchased_balance", "updated_at"])
        CreditLedger.objects.create(
            wallet=wallet, user=user, kind=CreditLedger.Kind.GRANT,
            credits_delta=credits, reserved_delta=0,
            balance_after=wallet.balance, reserved_balance_after=wallet.reserved_balance,
            period=wallet.period, plan_snapshot_code=wallet.plan_snapshot_code,
            reference_type="credit_pack_purchase", reference_id=reference_id,
            reason="verified_credit_pack_purchase",
            metadata={"credit_source": "purchased", "provider": provider},
        )
    return True


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
        ai_config = (plan.entitlements or {}).get("ai_assistant") or {}
        if plan.slug == DEFAULT_ACCOUNT_PLAN_SLUG or not isinstance(ai_config, Mapping) or not ai_config.get("enabled", False):
            raise InsufficientAccountCredits("The current plan cannot run credit-consuming tasks.")
        wallet = get_or_create_current_wallet(user=user, plan=plan)
        wallet = CreditWallet.objects.select_for_update().get(pk=wallet.pk)
        if wallet.period != current_account_credit_period() or wallet.plan_snapshot_code != plan.slug:
            raise AccountCreditsFrozen("An earlier credit reservation must finish before the plan changes.")

        if wallet.is_frozen:
            raise AccountCreditsFrozen(wallet.frozen_reason or "Account credits are frozen.")

        if wallet.available_credits < credits:
            raise InsufficientAccountCredits("Insufficient account credits available for this reservation.")

        monthly_reserved = min(credits, wallet.available_monthly_credits)
        purchased_reserved = credits - monthly_reserved
        wallet.reserved_balance = int(wallet.reserved_balance or 0) + credits
        wallet.purchased_reserved_balance += purchased_reserved
        wallet.save(update_fields=["reserved_balance", "purchased_reserved_balance", "updated_at"])
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
            metadata={**dict(metadata or {}), "monthly_reserved": monthly_reserved, "purchased_reserved": purchased_reserved},
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
        reserved_purchased = int((reservation.metadata or {}).get("purchased_reserved") or 0)
        reserved_monthly = reserved_to_close - reserved_purchased
        monthly_to_consume = min(credits, reserved_monthly)
        remainder = credits - monthly_to_consume
        purchased_to_consume = min(remainder, reserved_purchased)
        remainder -= purchased_to_consume
        if remainder:
            extra_monthly = min(remainder, wallet.available_monthly_credits)
            monthly_to_consume += extra_monthly
            purchased_to_consume += remainder - extra_monthly
        wallet.balance = max(0, int(wallet.balance or 0) - credits)
        wallet.purchased_balance -= purchased_to_consume
        wallet.reserved_balance = max(0, int(wallet.reserved_balance or 0) - reserved_to_close)
        wallet.purchased_reserved_balance -= reserved_purchased
        wallet.save(update_fields=["balance", "purchased_balance", "reserved_balance", "purchased_reserved_balance", "updated_at"])
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
            metadata={**dict(metadata or {}), "monthly_consumed": monthly_to_consume, "purchased_consumed": purchased_to_consume},
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
        reserved_purchased = int((reservation.metadata or {}).get("purchased_reserved") or 0)
        wallet.reserved_balance = max(0, int(wallet.reserved_balance or 0) - reserved_to_close)
        wallet.purchased_reserved_balance = max(0, wallet.purchased_reserved_balance - reserved_purchased)
        wallet.save(update_fields=["reserved_balance", "purchased_reserved_balance", "updated_at"])
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
