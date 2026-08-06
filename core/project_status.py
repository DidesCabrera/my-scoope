from __future__ import annotations

import platform
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Callable

import django
from django.conf import settings
from django.db import DatabaseError, connection
from django.db.migrations.executor import MigrationExecutor

from core.environment_diagnostics import build_environment_diagnostic


@dataclass(frozen=True)
class StatusProbe:
    code: str
    status: str
    data: dict[str, object]
    message: str = ""

    def as_dict(self) -> dict[str, object]:
        return {
            "code": self.code,
            "status": self.status,
            "data": self.data,
            "message": self.message,
        }


@dataclass(frozen=True)
class ProjectStatusReport:
    generated_at: str
    release: dict[str, object]
    runtime: dict[str, object]
    environment: dict[str, object]
    capabilities: dict[str, object]
    probes: tuple[StatusProbe, ...]

    @property
    def status(self) -> str:
        statuses = {probe.status for probe in self.probes}
        environment_status = self.environment.get("status")
        if "error" in statuses or environment_status == "error":
            return "error"
        if "warning" in statuses or environment_status == "warning":
            return "warning"
        return "ok"

    def as_dict(self) -> dict[str, object]:
        return {
            "contract": "myscoope.project_status.v1",
            "status": self.status,
            "generated_at": self.generated_at,
            "release": self.release,
            "runtime": self.runtime,
            "environment": self.environment,
            "capabilities": self.capabilities,
            "probes": [probe.as_dict() for probe in self.probes],
        }


def build_project_status(*, include_database: bool = True) -> ProjectStatusReport:
    environment_report = build_environment_diagnostic(include_database=include_database)
    probes: list[StatusProbe] = []
    probes.append(_safe_probe("architecture.transitions", _transition_probe))
    probes.append(_safe_probe("product.portfolio", _portfolio_probe))
    if include_database:
        probes.append(_safe_probe("database.migrations", _migration_probe))
        probes.append(_safe_probe("data.catalog", _catalog_probe))
        probes.append(_safe_probe("data.operational_foods", _operational_food_probe))

    environment_findings = [
        finding.as_dict()
        for finding in environment_report.findings
        if finding.status in {"warning", "error"}
    ]
    return ProjectStatusReport(
        generated_at=datetime.now(UTC).isoformat(),
        release={
            "commit": str(getattr(settings, "SENTRY_RELEASE", "") or "unknown"),
            "service": str(getattr(settings, "SENTRY_ENVIRONMENT", "") or "unknown"),
            "identity_configured": bool(getattr(settings, "SENTRY_RELEASE", "")),
        },
        runtime={
            "python": platform.python_version(),
            "django": django.get_version(),
        },
        environment={
            "name": environment_report.environment,
            "settings_module": environment_report.settings_module,
            "status": environment_report.status,
            "attention": environment_findings,
        },
        capabilities=_capability_snapshot(),
        probes=tuple(probes),
    )


def _safe_probe(code: str, callback: Callable[[], dict[str, object]]) -> StatusProbe:
    try:
        return StatusProbe(code=code, status="ok", data=callback())
    except DatabaseError:
        return StatusProbe(
            code=code,
            status="error",
            data={},
            message="The database probe could not read its schema or current state.",
        )
    except Exception:
        return StatusProbe(
            code=code,
            status="error",
            data={},
            message="The probe failed safely; inspect server logs for internal detail.",
        )


def _migration_probe() -> dict[str, object]:
    executor = MigrationExecutor(connection)
    targets = executor.loader.graph.leaf_nodes()
    pending = executor.migration_plan(targets)
    return {
        "database_vendor": connection.vendor,
        "pending_count": len(pending),
        "up_to_date": not pending,
    }


def _transition_probe() -> dict[str, object]:
    from collections import Counter

    from core.transition_registry import load_transition_registry, validate_transition_registry

    entries = load_transition_registry()
    counts = Counter(entry.status for entry in entries)
    errors = validate_transition_registry()
    if errors:
        raise ValueError("Transition registry is invalid.")
    return {
        "total": len(entries),
        "transitional": counts["transitional"],
        "intentionally_durable": counts["intentionally_durable"],
    }


def _portfolio_probe() -> dict[str, object]:
    from collections import Counter

    from core.product_portfolio import load_product_portfolio, validate_product_portfolio

    bets = load_product_portfolio()
    if validate_product_portfolio():
        raise ValueError("Product portfolio is invalid.")
    stages = Counter(bet.stage for bet in bets)
    return {
        "total": len(bets),
        "build": stages["build"],
        "validate": stages["validate"],
        "planned": stages["planned"],
    }


def _catalog_probe() -> dict[str, object]:
    from food_catalog.models import CatalogFood, CatalogImportBatch

    return {
        "foods_total": CatalogFood.objects.count(),
        "foods_verified": CatalogFood.objects.filter(status=CatalogFood.STATUS_VERIFIED).count(),
        "foods_published": CatalogFood.objects.filter(status=CatalogFood.STATUS_PUBLISHED).count(),
        "import_batches_total": CatalogImportBatch.objects.count(),
        "import_batches_failed": CatalogImportBatch.objects.filter(status=CatalogImportBatch.STATUS_FAILED).count(),
    }


def _operational_food_probe() -> dict[str, object]:
    from notas.domain.models import Food

    return {
        "foods_total": Food.objects.count(),
        "global_active_verified": Food.objects.filter(
            is_global=True,
            is_active=True,
            is_verified=True,
        ).count(),
    }


def _capability_snapshot() -> dict[str, object]:
    return {
        "ai_assistant": {
            "engine": str(getattr(settings, "AI_ASSISTANT_CHAT_ENGINE_MODE", "unknown")),
            "provider": str(getattr(settings, "AI_ASSISTANT_LLM_PROVIDER", "unknown")),
            "runtime_active": True,
            "credits_enabled": bool(getattr(settings, "AI_ASSISTANT_CREDITS_ENABLED", False)),
            "usage_observability": bool(getattr(settings, "AI_ASSISTANT_USAGE_OBSERVABILITY_ENABLED", False)),
        },
        "nutrition_solver": {
            "backend": str(getattr(settings, "NUTRITION_SOLVER_BACKEND", "unknown")),
            "shadow_enabled": bool(getattr(settings, "NUTRITION_SOLVER_SHADOW_ENABLED", False)),
            "shadow_backend": str(getattr(settings, "NUTRITION_SOLVER_SHADOW_BACKEND", "unknown")),
        },
        "food_catalog": {
            "fatsecret_enabled": bool(getattr(settings, "FOOD_CATALOG_FATSECRET_ENABLED", False)),
            "open_food_facts_enabled": bool(
                getattr(settings, "FOOD_CATALOG_OPEN_FOOD_FACTS_ENABLED", False)
            ),
        },
        "accounts": {
            "email_verification": str(getattr(settings, "ACCOUNT_EMAIL_VERIFICATION", "unknown")),
            "turnstile_enabled": bool(getattr(settings, "TURNSTILE_ENABLED", False)),
            "shared_rate_limit_cache": bool(getattr(settings, "CACHE_URL", "")),
            "share_email_enabled": bool(
                getattr(settings, "EMAIL_SHARE_DELIVERY_ENABLED", True)
            ),
            "onboarding_gate_enabled": bool(
                getattr(settings, "NUTRITION_ONBOARDING_GATE_ENABLED", False)
            ),
        },
        "billing": {
            "mercado_pago_checkout_enabled": bool(
                getattr(settings, "BILLING_MERCADOPAGO_CHECKOUT_ENABLED", False)
            ),
            "mercado_pago_webhook_enabled": bool(
                getattr(settings, "BILLING_MERCADOPAGO_WEBHOOK_ENABLED", False)
            ),
            "apple_purchases_enabled": bool(
                getattr(settings, "BILLING_APPLE_PURCHASES_ENABLED", False)
            ),
            "apple_notifications_enabled": bool(
                getattr(settings, "BILLING_APPLE_NOTIFICATIONS_ENABLED", False)
            ),
            "openfactura_enabled": bool(getattr(settings, "BILLING_OPENFACTURA_ENABLED", False)),
        },
    }
