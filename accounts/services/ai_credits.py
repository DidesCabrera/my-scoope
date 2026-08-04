from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from accounts.models import CreditLedger, CreditWallet
from accounts.services.credits import (
    current_account_credit_period,
    get_or_create_current_wallet,
    resolve_account_credit_plan_snapshot,
)

AI_CREDIT_REFERENCE_TYPE = "ai_assistant_turn"
AI_CREDIT_ADMIN_REFERENCE_TYPE = "admin_operations_ai_credit_freeze"


@dataclass(frozen=True)
class AccountAICreditQuotaSnapshot:
    """Read model derived exclusively from account-owned commercial state."""

    wallet: CreditWallet
    period: str
    plan_code: str
    credits_used: int
    daily_credits_used: int
    monthly_credit_limit: int
    daily_credit_limit: int
    hard_blocked: bool

    @property
    def pk(self) -> int:
        return self.wallet.pk

    @property
    def user(self):
        return self.wallet.user

    @property
    def user_id(self) -> int:
        return self.wallet.user_id

    @property
    def usage_ratio(self) -> Decimal:
        if self.monthly_credit_limit <= 0:
            return Decimal("0")
        return Decimal(self.credits_used) / Decimal(self.monthly_credit_limit)

    @property
    def is_under_pressure(self) -> bool:
        return self.hard_blocked or (
            self.monthly_credit_limit > 0
            and self.credits_used >= self.monthly_credit_limit
        )

    @property
    def frozen_reason(self) -> str:
        return self.wallet.frozen_reason

    @property
    def frozen_at(self):
        return self.wallet.frozen_at


def account_ai_credit_quota_for_user(
    user: Any,
    *,
    period: str | None = None,
    today: date | None = None,
) -> AccountAICreditQuotaSnapshot:
    wallet = get_or_create_current_wallet(user=user)
    return account_ai_credit_quota_from_wallet(wallet, period=period, today=today)


def account_ai_credit_quota_from_wallet(
    wallet: CreditWallet,
    *,
    period: str | None = None,
    today: date | None = None,
) -> AccountAICreditQuotaSnapshot:
    selected_period = period or current_account_credit_period()
    selected_day = today or timezone.localdate()
    plan = resolve_account_credit_plan_snapshot(wallet.user)
    monthly_limit = int(getattr(plan, "monthly_credit_limit", 0) or 0)
    daily_limit = int(getattr(plan, "daily_credit_limit", 0) or 0)
    plan_code = str(getattr(plan, "slug", "") or wallet.plan_snapshot_code or "")
    consumed = CreditLedger.objects.filter(
        wallet=wallet,
        kind=CreditLedger.Kind.CONSUME,
        period=selected_period,
        reference_type=AI_CREDIT_REFERENCE_TYPE,
    )
    monthly_value = consumed.aggregate(total=Sum("credits_delta"))["total"] or 0
    daily_value = consumed.filter(created_at__date=selected_day).aggregate(total=Sum("credits_delta"))["total"] or 0
    return AccountAICreditQuotaSnapshot(
        wallet=wallet,
        period=selected_period,
        plan_code=plan_code,
        credits_used=abs(int(monthly_value)),
        daily_credits_used=abs(int(daily_value)),
        monthly_credit_limit=monthly_limit,
        daily_credit_limit=daily_limit,
        hard_blocked=bool(wallet.is_frozen),
    )


def list_account_ai_credit_quotas(
    *,
    period: str | None = None,
    query: str = "",
    user_segment: str = "all",
    pressured_only: bool = False,
) -> list[AccountAICreditQuotaSnapshot]:
    wallets = CreditWallet.objects.select_related(
        "user",
        "user__account_subscription",
        "user__account_subscription__plan",
    ).order_by("user__email", "user__username", "pk")
    if user_segment == "staff":
        wallets = wallets.filter(user__is_staff=True)
    elif user_segment == "members":
        wallets = wallets.filter(user__is_staff=False)

    normalized_query = " ".join(str(query or "").split()).casefold()
    snapshots = []
    for wallet in wallets:
        snapshot = account_ai_credit_quota_from_wallet(wallet, period=period)
        if pressured_only and not snapshot.is_under_pressure:
            continue
        if normalized_query:
            haystack = " ".join(
                (
                    wallet.user.get_username(),
                    wallet.user.email or "",
                    wallet.user.first_name or "",
                    wallet.user.last_name or "",
                    snapshot.plan_code,
                    snapshot.period,
                )
            ).casefold()
            if normalized_query not in haystack:
                continue
        snapshots.append(snapshot)
    snapshots.sort(
        key=lambda item: (item.hard_blocked, item.usage_ratio, item.credits_used),
        reverse=True,
    )
    return snapshots


@transaction.atomic
def set_account_ai_credit_freeze(
    *,
    wallet_id: int,
    frozen: bool,
    reason: str,
    actor: Any | None = None,
) -> tuple[CreditWallet, CreditLedger | None, bool]:
    normalized_reason = " ".join(str(reason or "").split())[:160]
    if not normalized_reason:
        raise ValueError("A reason is required to change an account credit freeze.")

    wallet = CreditWallet.objects.select_for_update().select_related("user").get(pk=wallet_id)
    if wallet.is_frozen == frozen:
        return wallet, None, False

    wallet.is_frozen = frozen
    wallet.frozen_reason = normalized_reason if frozen else ""
    wallet.frozen_at = timezone.now() if frozen else None
    wallet.save(update_fields=["is_frozen", "frozen_reason", "frozen_at", "updated_at"])
    actor_label = str(getattr(actor, "email", "") or getattr(actor, "username", "") or "system")
    ledger = CreditLedger.objects.create(
        wallet=wallet,
        user=wallet.user,
        kind=CreditLedger.Kind.ADJUSTMENT,
        credits_delta=0,
        reserved_delta=0,
        balance_after=wallet.balance,
        reserved_balance_after=wallet.reserved_balance,
        period=wallet.period,
        plan_snapshot_code=wallet.plan_snapshot_code,
        reference_type=AI_CREDIT_ADMIN_REFERENCE_TYPE,
        reference_id=uuid.uuid4().hex,
        reason=normalized_reason,
        metadata={
            "frozen": frozen,
            "actor": actor_label,
            "actor_id": getattr(actor, "pk", None),
            "source": "accounts.services.ai_credits",
        },
    )
    return wallet, ledger, True
