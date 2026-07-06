from __future__ import annotations

from admin_analytics.filters import AdminAnalyticsFilters
from admin_analytics.selectors.accounts import get_account_metrics
from admin_analytics.viewmodels import (
    AdminAnalyticsAccountPlanRowVM,
    AdminAnalyticsAccountWalletRowVM,
    AdminAnalyticsAccountsVM,
    AdminAnalyticsKpiVM,
    AdminAnalyticsLedgerKindRowVM,
    AdminAnalyticsSectionVM,
)


def _format_int(value) -> str:
    return f"{int(value or 0):,}".replace(",", ".")


def _format_optional_int(value) -> str:
    return "—" if value is None else _format_int(value)


def _format_signed_int(value) -> str:
    number = int(value or 0)
    if number > 0:
        return f"+{_format_int(number)}"
    return _format_int(number)


def build_accounts_vm(analytics_filters: AdminAnalyticsFilters | None = None) -> AdminAnalyticsAccountsVM:
    analytics_filters = analytics_filters or AdminAnalyticsFilters()
    metrics = get_account_metrics(analytics_filters=analytics_filters)
    plans = metrics["plans"]
    subscriptions = metrics["subscriptions"]
    wallets = metrics["wallets"]
    ledger = metrics["ledger"]

    sections = [
        AdminAnalyticsSectionVM(
            title="Planes comerciales",
            description="Estado de AccountPlan y configuración de créditos incluida por plan.",
            kpis=[
                AdminAnalyticsKpiVM("Planes totales", _format_int(plans["total"]), "Todos los estados"),
                AdminAnalyticsKpiVM("Planes activos", _format_int(plans["active"]), "Disponibles comercialmente"),
                AdminAnalyticsKpiVM("Draft / archivados", f"{_format_int(plans['draft'])}/{_format_int(plans['archived'])}", "No productivos"),
            ],
        ),
        AdminAnalyticsSectionVM(
            title="Suscripciones",
            description="Lectura comercial de usuarios asociados a planes y estados de suscripción.",
            kpis=[
                AdminAnalyticsKpiVM("Suscripciones totales", _format_int(subscriptions["total"]), "Histórico actual"),
                AdminAnalyticsKpiVM("Activas", _format_int(subscriptions["active"]), "Trialing + active"),
                AdminAnalyticsKpiVM("Nuevas 7d / 30d", f"{_format_int(subscriptions['new_7d'])}/{_format_int(subscriptions['new_30d'])}", "Alta de AccountSubscription"),
                AdminAnalyticsKpiVM("Past due / canceladas", f"{_format_int(subscriptions['past_due'])}/{_format_int(subscriptions['canceled'])}", "Riesgo comercial"),
            ],
        ),
        AdminAnalyticsSectionVM(
            title="Wallets",
            description="Balances agregados de créditos visibles para usuarios.",
            kpis=[
                AdminAnalyticsKpiVM("Wallets", _format_int(wallets["total"]), "Cuentas con billetera"),
                AdminAnalyticsKpiVM("Disponibles", _format_int(wallets["available_total"]), "Balance - reservado"),
                AdminAnalyticsKpiVM("Balance total", _format_int(wallets["balance_total"]), "Créditos existentes"),
                AdminAnalyticsKpiVM("Reservados", _format_int(wallets["reserved_total"]), f"Wallets afectadas: {_format_int(wallets['with_reserved'])}"),
            ],
        ),
        AdminAnalyticsSectionVM(
            title="Ledger de créditos",
            description="Movimientos append-only de créditos comerciales durante el período inicial.",
            kpis=[
                AdminAnalyticsKpiVM("Entradas 7d", _format_int(ledger["entries_7d"]), f"Total: {_format_int(ledger['entries_total'])}"),
                AdminAnalyticsKpiVM("Otorgados 7d", _format_signed_int(ledger["credits_granted_7d"]), "Kind grant"),
                AdminAnalyticsKpiVM("Consumidos 7d", _format_int(ledger["credits_consumed_7d"]), "Kind consume"),
                AdminAnalyticsKpiVM("Reservados/liberados", f"{_format_int(ledger['credits_reserved_7d'])}/{_format_int(ledger['credits_released_7d'])}", "Reserve / release"),
            ],
        ),
    ]

    plan_rows = [
        AdminAnalyticsAccountPlanRowVM(
            slug=row["slug"],
            name=row["name"],
            status=row["status"],
            included_monthly_credits=_format_int(row["included_monthly_credits"]),
            daily_credit_limit=_format_optional_int(row["daily_credit_limit"]),
            monthly_credit_limit=_format_optional_int(row["monthly_credit_limit"]),
            active_subscriptions=_format_int(row["active_subscriptions"]),
        )
        for row in plans["rows"]
    ]

    wallet_rows = [
        AdminAnalyticsAccountWalletRowVM(
            email=row["email"],
            username=row["username"],
            balance=_format_int(row["balance"]),
            reserved_balance=_format_int(row["reserved_balance"]),
            available_credits=_format_int(row["available_credits"]),
            period=row["period"],
            plan_snapshot_code=row["plan_snapshot_code"],
        )
        for row in wallets["top_wallets"]
    ]

    ledger_kind_rows = [
        AdminAnalyticsLedgerKindRowVM(
            kind=row["kind"],
            entries=_format_int(row["entries"]),
            credits_delta=_format_signed_int(row["credits_delta"]),
            reserved_delta=_format_signed_int(row["reserved_delta"]),
        )
        for row in ledger["by_kind_7d"]
    ]

    active_by_plan = [
        AdminAnalyticsKpiVM(
            row["plan_name"],
            _format_int(row["count"]),
            row["plan_slug"],
        )
        for row in subscriptions["active_by_plan"]
    ]

    return AdminAnalyticsAccountsVM(
        title="Accounts Analytics",
        subtitle="Planes, suscripciones, wallets y ledger de créditos.",
        generated_at=metrics["generated_at"],
        period_label=metrics["period_label"],
        filters=analytics_filters.as_template_context(),
        sections=sections,
        plan_rows=plan_rows,
        active_subscriptions_by_plan=active_by_plan,
        wallet_rows=wallet_rows,
        ledger_kind_rows=ledger_kind_rows,
    )
