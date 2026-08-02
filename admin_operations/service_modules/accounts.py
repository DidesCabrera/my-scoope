from __future__ import annotations


from django.contrib.auth import get_user_model
from django.db import transaction
from django.urls import reverse

from admin_operations.selectors import (
    get_account_detail_payload,
    get_accounts_operations_payload,
)
from admin_operations.viewmodels import (
    AdminOperationsAccountDetailVM,
    AdminOperationsAccountsVM,
    AdminOperationsCreditLedgerVM,
    AdminOperationsCreditReservationVM,
    AdminOperationsCreditWalletVM,
    AdminOperationsMetricVM,
)
from accounts.models import AccountSubscription, CreditLedger, CreditWallet
from accounts.services.credits import current_account_credit_period, release_account_credit_reservation


from admin_operations.service_modules.common import (
    AdminOperationResult,
    _format_int,
    _get_operation_target,
    _user_label,
    record_admin_operation_audit_event,
)

def _subscription_label(subscription: AccountSubscription | None) -> str:
    if subscription is None:
        return "Sin suscripción activa"
    plan_label = getattr(subscription.plan, "slug", "") or getattr(subscription.plan, "name", "") or "plan"
    return f"{plan_label} · {subscription.status}"


def _wallet_to_vm(wallet: CreditWallet, *, subscription: AccountSubscription | None = None) -> AdminOperationsCreditWalletVM:
    user = wallet.user
    return AdminOperationsCreditWalletVM(
        user_id=user.pk,
        user_label=_user_label(user),
        email=getattr(user, "email", "") or getattr(user, "username", ""),
        balance=_format_int(wallet.balance),
        reserved_balance=_format_int(wallet.reserved_balance),
        available_credits=_format_int(wallet.available_credits),
        period=wallet.period or "—",
        plan_snapshot_code=wallet.plan_snapshot_code or "—",
        subscription_label=_subscription_label(subscription),
        detail_url=reverse("admin_operations_account_detail", args=[user.pk]),
        admin_url=reverse("admin:accounts_creditwallet_change", args=[wallet.pk]),
        has_reserved_credits=wallet.has_reserved_credits,
    )


def _reservation_to_vm(reservation: CreditLedger) -> AdminOperationsCreditReservationVM:
    user = reservation.user
    reference_label = " · ".join(part for part in [reservation.reference_type, reservation.reference_id] if part) or "Sin referencia"
    return AdminOperationsCreditReservationVM(
        pk=reservation.pk,
        user_id=user.pk,
        user_label=_user_label(user),
        email=getattr(user, "email", "") or getattr(user, "username", ""),
        credits=_format_int(reservation.reserved_delta),
        reference_type=reservation.reference_type,
        reference_id=reservation.reference_id,
        reference_label=reference_label,
        created_label=f"{reservation.created_at:%Y-%m-%d %H:%M}",
        reason=reservation.reason,
        detail_url=reverse("admin_operations_account_detail", args=[user.pk]),
    )


def _ledger_to_vm(entry: CreditLedger) -> AdminOperationsCreditLedgerVM:
    reference_label = " · ".join(part for part in [entry.reference_type, entry.reference_id] if part) or "—"
    return AdminOperationsCreditLedgerVM(
        pk=entry.pk,
        created_label=f"{entry.created_at:%Y-%m-%d %H:%M}",
        kind=entry.kind,
        credits_delta=f"{int(entry.credits_delta or 0):+d}",
        reserved_delta=f"{int(entry.reserved_delta or 0):+d}",
        balance_after=_format_int(entry.balance_after),
        reserved_balance_after=_format_int(entry.reserved_balance_after),
        reference_label=reference_label,
        reason=entry.reason or "—",
    )


def build_accounts_operations_vm(*, query: str = "") -> AdminOperationsAccountsVM:
    payload = get_accounts_operations_payload(query=query)
    wallet_counts = payload["wallet_counts"]
    reservation_counts = payload["reservation_counts"]
    subscriptions_by_user = payload["subscriptions_by_user"]
    total_work = int(wallet_counts.get("with_reserved") or 0) + int(reservation_counts.get("total") or 0)

    return AdminOperationsAccountsVM(
        query=payload["query"],
        metrics=[
            AdminOperationsMetricVM(
                label="Trabajo Accounts",
                value=_format_int(total_work),
                helper="Wallets con reservas + reservas abiertas accionables.",
                icon="credit-card",
            ),
            AdminOperationsMetricVM(
                label="Wallets",
                value=_format_int(wallet_counts.get("total")),
                helper=f"{_format_int(wallet_counts.get('with_reserved'))} con créditos reservados.",
                icon="wallet-cards",
            ),
            AdminOperationsMetricVM(
                label="Reservas abiertas",
                value=_format_int(reservation_counts.get("total")),
                helper=f"{_format_int(reservation_counts.get('reserved_total'))} créditos retenidos por reservas no cerradas.",
                icon="lock-keyhole",
            ),
            AdminOperationsMetricVM(
                label="Mutaciones OPS04",
                value="ledger",
                helper="Ajustes y releases siempre agregan CreditLedger con razón obligatoria.",
                icon="shield-check",
            ),
        ],
        wallets=[
            _wallet_to_vm(wallet, subscription=subscriptions_by_user.get(wallet.user_id))
            for wallet in payload["wallets"]
        ],
        reservations=[_reservation_to_vm(reservation) for reservation in payload["reservations"]],
    )


def build_account_detail_vm(user_id: int) -> AdminOperationsAccountDetailVM:
    payload = get_account_detail_payload(user_id=user_id)
    user = payload["user"]
    wallet = payload["wallet"]
    if wallet is None:
        wallet = CreditWallet.objects.create(
            user=user,
            balance=0,
            reserved_balance=0,
            period=current_account_credit_period(),
        )
    return AdminOperationsAccountDetailVM(
        title=f"Cuenta · {_user_label(user)}",
        subtitle="Revisión staff-only de wallet, ledger append-only, reservas abiertas y ajustes manuales con razón obligatoria.",
        wallet=_wallet_to_vm(wallet, subscription=payload["subscription"]),
        ledger_entries=[_ledger_to_vm(entry) for entry in payload["ledger_entries"]],
        reservations=[_reservation_to_vm(reservation) for reservation in payload["reservations"]],
    )


def perform_credit_adjustment(*, user_id: int, actor, credits_delta: str, reason: str) -> AdminOperationResult:
    reason = (reason or "").strip()
    if not reason:
        return AdminOperationResult(ok=False, message="La razón es obligatoria para ajustar créditos.")
    try:
        delta = int(str(credits_delta or "").strip())
    except (TypeError, ValueError):
        return AdminOperationResult(ok=False, message="El ajuste debe ser un número entero de créditos.")
    if delta == 0:
        return AdminOperationResult(ok=False, message="El ajuste debe ser distinto de cero.")

    User = get_user_model()
    target_user = _get_operation_target(User, pk=user_id)
    actor_label = getattr(actor, "email", "") or getattr(actor, "username", "staff") or "staff"

    with transaction.atomic():
        wallet, _created = CreditWallet.objects.select_for_update().get_or_create(
            user=target_user,
            defaults={"balance": 0, "reserved_balance": 0, "period": current_account_credit_period()},
        )
        old_balance = int(wallet.balance or 0)
        old_reserved_balance = int(wallet.reserved_balance or 0)
        new_balance = old_balance + delta
        if new_balance < 0:
            return AdminOperationResult(ok=False, message="El ajuste no puede dejar balance negativo.")
        if new_balance < int(wallet.reserved_balance or 0):
            return AdminOperationResult(ok=False, message="El ajuste no puede dejar balance menor que los créditos reservados.")
        wallet.balance = new_balance
        wallet.save(update_fields=["balance", "updated_at"])
        ledger = CreditLedger.objects.create(
            wallet=wallet,
            user=target_user,
            kind=CreditLedger.Kind.ADJUSTMENT,
            credits_delta=delta,
            reserved_delta=0,
            balance_after=wallet.balance,
            reserved_balance_after=wallet.reserved_balance,
            period=wallet.period,
            plan_snapshot_code=wallet.plan_snapshot_code,
            reference_type="admin_operations.credit_adjustment",
            reference_id=str(actor.pk) if getattr(actor, "pk", None) else "staff",
            reason=reason,
            metadata={"actor": actor_label, "source": "OPS04"},
        )
        record_admin_operation_audit_event(
            actor=actor,
            action="accounts.credit.adjustment",
            target=wallet,
            reason=reason,
            status_before=f"balance={old_balance};reserved={old_reserved_balance}",
            status_after=f"balance={wallet.balance};reserved={wallet.reserved_balance}",
            metadata={"source_patch": "OPS04", "ledger_id": ledger.pk, "credits_delta": delta, "target_user_id": target_user.pk},
        )
    return AdminOperationResult(ok=True, message=f"Ajuste registrado en ledger #{ledger.pk} ({delta:+d} créditos).")


def perform_credit_reservation_release(*, reservation_id: int, actor, reason: str) -> AdminOperationResult:
    reason = (reason or "").strip()
    if not reason:
        return AdminOperationResult(ok=False, message="La razón es obligatoria para liberar una reserva.")
    reservation = _get_operation_target(
        CreditLedger.objects.select_related("wallet", "user"),
        pk=reservation_id,
        kind=CreditLedger.Kind.RESERVE,
    )
    if reservation.reserved_delta <= 0:
        return AdminOperationResult(ok=False, message="La reserva no tiene créditos retenidos.")
    closed = CreditLedger.objects.filter(
        kind__in=(CreditLedger.Kind.CONSUME, CreditLedger.Kind.RELEASE),
        reference_type=reservation.reference_type,
        reference_id=reservation.reference_id,
    ).exists()
    if closed:
        return AdminOperationResult(ok=False, message="La reserva ya fue cerrada anteriormente.")

    actor_label = getattr(actor, "email", "") or getattr(actor, "username", "staff") or "staff"
    result = release_account_credit_reservation(
        user=reservation.user,
        reference_type=reservation.reference_type,
        reference_id=reservation.reference_id,
        reason=reason,
        metadata={"actor": actor_label, "source": "OPS04", "released_by_staff": True},
    )
    if not result.get("released"):
        return AdminOperationResult(ok=False, message=f"No se pudo liberar la reserva: {result.get('reason', 'unknown')}.")
    reservation.wallet.refresh_from_db(fields=["balance", "reserved_balance", "updated_at"])
    record_admin_operation_audit_event(
        actor=actor,
        action="accounts.credit.reservation_release",
        target=reservation,
        reason=reason,
        status_before=f"reserved_delta={reservation.reserved_delta}",
        status_after=f"released={result.get('released')};wallet_reserved={reservation.wallet.reserved_balance}",
        metadata={
            "source_patch": "OPS04",
            "released_credits": result.get("credits"),
            "reference_type": reservation.reference_type,
            "reference_id": reservation.reference_id,
            "wallet_id": reservation.wallet_id,
        },
    )
    return AdminOperationResult(ok=True, message=f"Reserva liberada: {_format_int(result.get('credits'))} créditos.")




__all__ = ['build_accounts_operations_vm', 'build_account_detail_vm', 'perform_credit_adjustment', 'perform_credit_reservation_release']
