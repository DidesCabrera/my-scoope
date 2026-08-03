from __future__ import annotations


from django.contrib.auth import get_user_model
from django.db.models import Count, Q, Sum

from accounts.models import AccountSubscription, CreditLedger, CreditWallet

def get_accounts_operations_payload(*, query: str = "", limit: int = 25) -> dict:
    """Return actionable Accounts & Credits queues for OPS04.

    The selector is read-only. Wallet mutations are handled by explicit services
    that append CreditLedger movements instead of editing historical entries.
    """

    normalized_query = (query or "").strip()
    wallet_qs = (
        CreditWallet.objects.select_related("user")
        .order_by("-reserved_balance", "user__email", "user__username")
    )
    if normalized_query:
        wallet_qs = wallet_qs.filter(
            Q(user__email__icontains=normalized_query)
            | Q(user__username__icontains=normalized_query)
            | Q(user__first_name__icontains=normalized_query)
            | Q(user__last_name__icontains=normalized_query)
        )

    reservations_qs = _open_credit_reservations_queryset()
    if normalized_query:
        reservations_qs = reservations_qs.filter(
            Q(user__email__icontains=normalized_query)
            | Q(user__username__icontains=normalized_query)
            | Q(reference_type__icontains=normalized_query)
            | Q(reference_id__icontains=normalized_query)
        )

    wallet_counts = wallet_qs.aggregate(
        total=Count("id"),
        with_reserved=Count("id", filter=Q(reserved_balance__gt=0)),
        reserved_total=Sum("reserved_balance"),
    )
    wallet_counts["reserved_total"] = wallet_counts["reserved_total"] or 0
    open_reservations = reservations_qs.aggregate(
        total=Count("id"),
        reserved_total=Sum("reserved_delta"),
    )
    open_reservations["reserved_total"] = open_reservations["reserved_total"] or 0

    subscriptions = _subscriptions_by_user(wallet_qs[:limit])

    return {
        "query": normalized_query,
        "wallet_counts": wallet_counts,
        "reservation_counts": open_reservations,
        "wallets": list(wallet_qs[:limit]),
        "reservations": list(reservations_qs[:limit]),
        "subscriptions_by_user": subscriptions,
    }


def get_account_detail_payload(*, user_id: int, ledger_limit: int = 30) -> dict:
    User = get_user_model()
    user = User.objects.get(pk=user_id)
    wallet = CreditWallet.objects.select_related("user").filter(user=user).first()
    subscription = (
        AccountSubscription.objects.select_related("plan")
        .filter(user=user)
        .order_by("-created_at")
        .first()
    )
    ledger_entries = []
    reservations = []
    if wallet is not None:
        ledger_entries = list(
            CreditLedger.objects.filter(wallet=wallet)
            .select_related("user")
            .order_by("-created_at", "-id")[:ledger_limit]
        )
        reservations = list(_open_credit_reservations_queryset().filter(wallet=wallet)[:ledger_limit])
    return {
        "user": user,
        "wallet": wallet,
        "subscription": subscription,
        "ledger_entries": ledger_entries,
        "reservations": reservations,
    }


def _open_credit_reservations_queryset():
    closed_references = CreditLedger.objects.filter(
        kind__in=(CreditLedger.Kind.CONSUME, CreditLedger.Kind.RELEASE),
        reference_type__gt="",
        reference_id__gt="",
    ).values_list("reference_type", "reference_id")
    closed_pairs = {(reference_type, reference_id) for reference_type, reference_id in closed_references}

    qs = (
        CreditLedger.objects.select_related("wallet", "user")
        .filter(kind=CreditLedger.Kind.RESERVE, reserved_delta__gt=0)
        .order_by("created_at", "id")
    )
    if not closed_pairs:
        return qs

    closed_q = Q()
    for reference_type, reference_id in closed_pairs:
        closed_q |= Q(reference_type=reference_type, reference_id=reference_id)
    return qs.exclude(closed_q)


def _subscriptions_by_user(wallets) -> dict[int, AccountSubscription]:
    user_ids = [wallet.user_id for wallet in wallets]
    if not user_ids:
        return {}
    subscriptions = (
        AccountSubscription.objects.select_related("plan")
        .filter(user_id__in=user_ids)
        .order_by("user_id", "-created_at")
    )
    result: dict[int, AccountSubscription] = {}
    for subscription in subscriptions:
        result.setdefault(subscription.user_id, subscription)
    return result




__all__ = ['get_accounts_operations_payload', 'get_account_detail_payload']
