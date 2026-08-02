from __future__ import annotations

from dataclasses import dataclass, field


from admin_operations.viewmodel_modules.common import AdminOperationsMetricVM

@dataclass(frozen=True)
class AdminOperationsCreditWalletVM:
    user_id: int
    user_label: str
    email: str
    balance: str
    reserved_balance: str
    available_credits: str
    period: str
    plan_snapshot_code: str
    subscription_label: str = "Sin suscripción activa"
    detail_url: str = "#"
    admin_url: str = "#"
    has_reserved_credits: bool = False


@dataclass(frozen=True)
class AdminOperationsCreditLedgerVM:
    pk: int
    created_label: str
    kind: str
    credits_delta: str
    reserved_delta: str
    balance_after: str
    reserved_balance_after: str
    reference_label: str
    reason: str


@dataclass(frozen=True)
class AdminOperationsCreditReservationVM:
    pk: int
    user_id: int
    user_label: str
    email: str
    credits: str
    reference_type: str
    reference_id: str
    reference_label: str
    created_label: str
    reason: str
    detail_url: str = "#"


@dataclass(frozen=True)
class AdminOperationsAccountsVM:
    title: str = "Operaciones de cuentas y créditos"
    subtitle: str = (
        "Revisión staff-only de wallets, reservas abiertas y contexto comercial antes "
        "de ajustes manuales."
    )
    period_label: str = "OPS04 · Accounts and credits operations"
    current_period: str = "OPS04 · Accounts & Credits"
    query: str = ""
    metrics: list[AdminOperationsMetricVM] = field(default_factory=list)
    wallets: list[AdminOperationsCreditWalletVM] = field(default_factory=list)
    reservations: list[AdminOperationsCreditReservationVM] = field(default_factory=list)


@dataclass(frozen=True)
class AdminOperationsAccountDetailVM:
    title: str
    subtitle: str
    period_label: str = "OPS04 · Account wallet review"
    current_period: str = "OPS04 · Accounts & Credits"
    wallet: AdminOperationsCreditWalletVM | None = None
    ledger_entries: list[AdminOperationsCreditLedgerVM] = field(default_factory=list)
    reservations: list[AdminOperationsCreditReservationVM] = field(default_factory=list)


__all__ = ['AdminOperationsCreditWalletVM', 'AdminOperationsCreditLedgerVM', 'AdminOperationsCreditReservationVM', 'AdminOperationsAccountsVM', 'AdminOperationsAccountDetailVM']
