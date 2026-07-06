from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.db.models import Count, Sum
from django.utils import timezone

from admin_analytics.filters import AdminAnalyticsFilters

from accounts.models import AccountPlan, AccountSubscription, CreditLedger, CreditWallet


ACTIVE_SUBSCRIPTION_STATUSES = [
    AccountSubscription.Status.TRIALING,
    AccountSubscription.Status.ACTIVE,
]


def _sum(queryset, field: str):
    return queryset.aggregate(total=Sum(field))["total"] or 0


def _wallet_available_total() -> int:
    total = 0
    for wallet in CreditWallet.objects.only("balance", "reserved_balance"):
        total += wallet.available_credits
    return total


def get_account_metrics(*, now=None, analytics_filters: AdminAnalyticsFilters | None = None, top_wallet_limit: int = 8) -> dict:
    """Return read-only ADM03 commercial account metrics.

    The selector keeps `admin_analytics` as a reporting consumer of the
    `accounts` domain. It aggregates plans, subscriptions, wallets and ledger
    entries without mutating commercial state.
    """

    now = now or timezone.now()
    analytics_filters = analytics_filters or AdminAnalyticsFilters()
    since_7d = analytics_filters.since(now=now)
    since_30d = now - timedelta(days=30)

    plans = AccountPlan.objects.all()
    subscriptions = analytics_filters.apply_user_segment(AccountSubscription.objects.select_related("plan", "user"), "user")
    wallets = analytics_filters.apply_user_segment(CreditWallet.objects.select_related("user"), "user")
    ledger = analytics_filters.apply_user_segment(CreditLedger.objects.select_related("wallet", "user"), "user")

    wallet_totals = wallets.aggregate(
        balance=Sum("balance"),
        reserved_balance=Sum("reserved_balance"),
    )
    balance_total = wallet_totals["balance"] or 0
    reserved_total = wallet_totals["reserved_balance"] or 0
    available_total = _wallet_available_total()

    active_subscriptions = subscriptions.filter(status__in=ACTIVE_SUBSCRIPTION_STATUSES)
    active_by_plan = [
        {
            "plan_slug": row["plan__slug"] or "—",
            "plan_name": row["plan__name"] or "Sin plan",
            "count": row["count"],
        }
        for row in active_subscriptions.values("plan__slug", "plan__name").annotate(count=Count("id")).order_by("-count", "plan__display_order", "plan__name")
    ]

    plan_rows = [
        {
            "slug": plan.slug,
            "name": plan.name,
            "status": plan.status,
            "included_monthly_credits": plan.included_monthly_credits,
            "daily_credit_limit": plan.daily_credit_limit,
            "monthly_credit_limit": plan.monthly_credit_limit,
            "active_subscriptions": active_subscriptions.filter(plan=plan).count(),
        }
        for plan in plans.order_by("display_order", "name")
    ]

    ledger_7d = ledger.filter(created_at__gte=since_7d)
    ledger_30d = ledger.filter(created_at__gte=since_30d)
    ledger_by_kind_7d = [
        {
            "kind": row["kind"],
            "entries": row["entries"],
            "credits_delta": row["credits_delta"] or 0,
            "reserved_delta": row["reserved_delta"] or 0,
        }
        for row in ledger_7d.values("kind")
        .annotate(
            entries=Count("id"),
            credits_delta=Sum("credits_delta"),
            reserved_delta=Sum("reserved_delta"),
        )
        .order_by("kind")
    ]

    credits_granted_7d = _sum(ledger_7d.filter(kind=CreditLedger.Kind.GRANT), "credits_delta")
    credits_consumed_7d = abs(_sum(ledger_7d.filter(kind=CreditLedger.Kind.CONSUME), "credits_delta"))
    credits_refunded_7d = _sum(ledger_7d.filter(kind=CreditLedger.Kind.REFUND), "credits_delta")
    credits_expired_7d = abs(_sum(ledger_7d.filter(kind=CreditLedger.Kind.EXPIRE), "credits_delta"))
    credits_reserved_7d = abs(_sum(ledger_7d.filter(kind=CreditLedger.Kind.RESERVE), "reserved_delta"))
    credits_released_7d = abs(_sum(ledger_7d.filter(kind=CreditLedger.Kind.RELEASE), "reserved_delta"))

    top_wallets = [
        {
            "email": wallet.user.email or wallet.user.get_username(),
            "username": wallet.user.get_username(),
            "balance": wallet.balance,
            "reserved_balance": wallet.reserved_balance,
            "available_credits": wallet.available_credits,
            "period": wallet.period or "—",
            "plan_snapshot_code": wallet.plan_snapshot_code or "—",
        }
        for wallet in wallets.order_by("-balance", "-reserved_balance", "user__email")[:top_wallet_limit]
    ]

    return {
        "generated_at": now,
        "period_label": analytics_filters.period_label,
        "plans": {
            "total": plans.count(),
            "active": plans.filter(status=AccountPlan.Status.ACTIVE).count(),
            "draft": plans.filter(status=AccountPlan.Status.DRAFT).count(),
            "archived": plans.filter(status=AccountPlan.Status.ARCHIVED).count(),
            "rows": plan_rows,
        },
        "subscriptions": {
            "total": subscriptions.count(),
            "active": active_subscriptions.count(),
            "trialing": subscriptions.filter(status=AccountSubscription.Status.TRIALING).count(),
            "past_due": subscriptions.filter(status=AccountSubscription.Status.PAST_DUE).count(),
            "canceled": subscriptions.filter(status=AccountSubscription.Status.CANCELED).count(),
            "expired": subscriptions.filter(status=AccountSubscription.Status.EXPIRED).count(),
            "new_7d": subscriptions.filter(created_at__gte=since_7d).count(),
            "new_30d": subscriptions.filter(created_at__gte=since_30d).count(),
            "active_by_plan": active_by_plan,
        },
        "wallets": {
            "total": wallets.count(),
            "with_reserved": wallets.filter(reserved_balance__gt=0).count(),
            "balance_total": balance_total,
            "reserved_total": reserved_total,
            "available_total": available_total,
            "top_wallets": top_wallets,
        },
        "ledger": {
            "entries_total": ledger.count(),
            "entries_7d": ledger_7d.count(),
            "entries_30d": ledger_30d.count(),
            "credits_granted_7d": credits_granted_7d,
            "credits_consumed_7d": credits_consumed_7d,
            "credits_refunded_7d": credits_refunded_7d,
            "credits_expired_7d": credits_expired_7d,
            "credits_reserved_7d": credits_reserved_7d,
            "credits_released_7d": credits_released_7d,
            "by_kind_7d": ledger_by_kind_7d,
        },
    }
