from __future__ import annotations

from dataclasses import asdict, dataclass

from django.db.models import Sum

from accounts.models import CreditLedger
from accounts.services.ai_credits import AI_CREDIT_REFERENCE_TYPE
from ai_assistant.models import AICreditLedger, AIUsageEvent, AIUserCreditQuota


@dataclass(frozen=True)
class AICreditReconciliationRow:
    user_id: int
    period: str
    legacy_quota_used: int
    legacy_ledger_used: int
    account_ledger_used: int
    usage_event_charged: int

    @property
    def reconciled(self) -> bool:
        return self.account_ledger_used == self.usage_event_charged

    @property
    def legacy_matches_account(self) -> bool:
        """Pre-cutover comparison; divergence is expected after legacy writes stop."""

        return (
            self.legacy_quota_used == self.account_ledger_used
            and self.legacy_ledger_used == self.account_ledger_used
        )

    def as_dict(self) -> dict[str, object]:
        return {
            **asdict(self),
            "reconciled": self.reconciled,
            "legacy_matches_account": self.legacy_matches_account,
        }


def build_ai_credit_reconciliation(*, period: str) -> list[AICreditReconciliationRow]:
    user_ids = set(
        AIUserCreditQuota.objects.filter(period=period).values_list("user_id", flat=True)
    )
    user_ids.update(
        AICreditLedger.objects.filter(period=period).values_list("user_id", flat=True)
    )
    user_ids.update(
        CreditLedger.objects.filter(
            period=period,
            reference_type=AI_CREDIT_REFERENCE_TYPE,
        ).values_list("user_id", flat=True)
    )
    user_ids.update(
        AIUsageEvent.objects.filter(period=period, user__isnull=False).values_list("user_id", flat=True)
    )

    rows = []
    for user_id in sorted(int(value) for value in user_ids if value is not None):
        quota = (
            AIUserCreditQuota.objects.filter(user_id=user_id, period=period)
            .order_by("-updated_at", "-pk")
            .first()
        )
        legacy_ledger = AICreditLedger.objects.filter(user_id=user_id, period=period).aggregate(
            total=Sum("credits")
        )["total"] or 0
        account_ledger = CreditLedger.objects.filter(
            user_id=user_id,
            period=period,
            kind=CreditLedger.Kind.CONSUME,
            reference_type=AI_CREDIT_REFERENCE_TYPE,
        ).aggregate(total=Sum("credits_delta"))["total"] or 0
        usage_events = AIUsageEvent.objects.filter(
            user_id=user_id,
            period=period,
        ).aggregate(total=Sum("charged_credits"))["total"] or 0
        rows.append(
            AICreditReconciliationRow(
                user_id=user_id,
                period=period,
                legacy_quota_used=int(getattr(quota, "credits_used", 0) or 0),
                legacy_ledger_used=int(legacy_ledger),
                account_ledger_used=abs(int(account_ledger)),
                usage_event_charged=int(usage_events),
            )
        )
    return rows


def ai_credit_reconciliation_summary(*, period: str) -> dict[str, object]:
    rows = build_ai_credit_reconciliation(period=period)
    return {
        "contract": "myscoope.ai_credit_reconciliation.v2",
        "period": period,
        "users": len(rows),
        "account_event_mismatches": sum(1 for row in rows if not row.reconciled),
        "legacy_account_mismatches": sum(1 for row in rows if not row.legacy_matches_account),
        "legacy_parity_is_informational": True,
        "rows": [row.as_dict() for row in rows],
    }
