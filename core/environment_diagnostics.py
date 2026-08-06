from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import UTC, datetime

from django.conf import settings
from django.db import DatabaseError

from core.environment_contract import ENVIRONMENT_VARIABLE_SPECS


@dataclass(frozen=True)
class DiagnosticFinding:
    code: str
    status: str
    category: str
    summary: str
    action: str = ""

    def as_dict(self) -> dict[str, str]:
        return {
            "code": self.code,
            "status": self.status,
            "category": self.category,
            "summary": self.summary,
            "action": self.action,
        }


@dataclass(frozen=True)
class EnvironmentDiagnosticReport:
    environment: str
    settings_module: str
    generated_at: str
    findings: tuple[DiagnosticFinding, ...]
    configuration_summary: tuple[dict[str, object], ...]

    @property
    def status(self) -> str:
        statuses = {finding.status for finding in self.findings}
        if "error" in statuses:
            return "error"
        if "warning" in statuses:
            return "warning"
        return "ok"

    def as_dict(self) -> dict[str, object]:
        return {
            "contract": "myscoope.environment_diagnostic.v1",
            "status": self.status,
            "environment": self.environment,
            "settings_module": self.settings_module,
            "generated_at": self.generated_at,
            "findings": [finding.as_dict() for finding in self.findings],
            "configuration_summary": list(self.configuration_summary),
        }


def resolve_environment_name(settings_module: str) -> str:
    if settings_module.endswith(".prod"):
        return "production"
    if settings_module.endswith(".dev"):
        return "development"
    if ".export_" in settings_module:
        return "export"
    return "custom"


def build_environment_diagnostic(*, include_database: bool = True) -> EnvironmentDiagnosticReport:
    settings_module = os.environ.get("DJANGO_SETTINGS_MODULE", "")
    environment = resolve_environment_name(settings_module)
    findings: list[DiagnosticFinding] = []

    findings.extend(_settings_findings(environment, settings_module))
    findings.extend(_integration_findings(environment))
    if include_database:
        findings.extend(_database_findings(environment))

    return EnvironmentDiagnosticReport(
        environment=environment,
        settings_module=settings_module,
        generated_at=datetime.now(UTC).isoformat(),
        findings=tuple(findings),
        configuration_summary=_configuration_summary(),
    )


def _settings_findings(environment: str, settings_module: str) -> list[DiagnosticFinding]:
    findings = []
    if environment == "custom":
        findings.append(DiagnosticFinding(
            code="settings.module.custom",
            status="warning",
            category="django",
            summary="The settings module is not one of the explicit development, production, or export profiles.",
            action="Confirm that the custom profile deliberately inherits a supported settings contract.",
        ))
    else:
        findings.append(DiagnosticFinding(
            code="settings.module.explicit",
            status="ok",
            category="django",
            summary=f"The {environment} settings profile is explicit.",
        ))

    engine = settings.DATABASES["default"].get("ENGINE", "")
    sqlite_in_production = environment == "production" and engine.endswith("sqlite3")
    findings.append(DiagnosticFinding(
        code="database.engine",
        status="error" if sqlite_in_production else "ok",
        category="django",
        summary="Production is using SQLite." if sqlite_in_production else "The database backend is configured.",
        action="Configure DATABASE_URL for PostgreSQL." if sqlite_in_production else "",
    ))

    if environment == "production":
        for spec in ENVIRONMENT_VARIABLE_SPECS:
            if spec.required_in_production and not os.environ.get(spec.name, "").strip():
                findings.append(DiagnosticFinding(
                    code=f"environment.required.{spec.name.lower()}",
                    status="error",
                    category=spec.category,
                    summary=f"Required production setting {spec.name} is not configured.",
                    action=f"Configure {spec.name} in the deployment environment.",
                ))
    return findings


def _integration_findings(environment: str) -> list[DiagnosticFinding]:
    findings = []
    email_backend = str(getattr(settings, "EMAIL_BACKEND", ""))
    email_ready = "smtp" in email_backend.lower() and bool(getattr(settings, "EMAIL_HOST", ""))
    findings.append(DiagnosticFinding(
        code="email.delivery",
        status="ok" if email_ready else ("warning" if environment == "production" else "ok"),
        category="email",
        summary="SMTP email delivery is configured." if email_ready else "Email uses a local/non-SMTP backend.",
        action="Configure SMTP before requiring email delivery." if environment == "production" and not email_ready else "",
    ))

    turnstile_ready = (
        bool(getattr(settings, "TURNSTILE_ENABLED", False))
        and bool(getattr(settings, "TURNSTILE_SITE_KEY", ""))
        and bool(getattr(settings, "TURNSTILE_SECRET_KEY", ""))
    )
    findings.append(DiagnosticFinding(
        code="email.abuse.turnstile",
        status="ok" if turnstile_ready else ("warning" if environment == "production" else "ok"),
        category="email",
        summary="Turnstile signup protection is configured." if turnstile_ready else "Turnstile signup protection is disabled or incomplete.",
        action="Configure both Turnstile keys and enable it." if environment == "production" and not turnstile_ready else "",
    ))

    shared_cache_ready = bool(getattr(settings, "CACHE_URL", ""))
    findings.append(DiagnosticFinding(
        code="email.abuse.shared_cache",
        status="ok" if shared_cache_ready else ("warning" if environment == "production" else "ok"),
        category="email",
        summary="Rate limits use a configured shared cache." if shared_cache_ready else "Rate limits use process-local cache.",
        action="Configure CACHE_URL with Render Key Value." if environment == "production" and not shared_cache_ready else "",
    ))

    share_email_enabled = bool(
        getattr(settings, "EMAIL_SHARE_DELIVERY_ENABLED", True)
    )
    findings.append(DiagnosticFinding(
        code="email.share_delivery",
        status="ok",
        category="email",
        summary="Share email delivery is enabled." if share_email_enabled else "Share email delivery is intentionally disabled.",
        action="",
    ))

    sentry_ready = bool(getattr(settings, "SENTRY_DSN", ""))
    findings.append(DiagnosticFinding(
        code="observability.sentry",
        status="ok" if sentry_ready else ("warning" if environment == "production" else "ok"),
        category="observability",
        summary="Error observability is configured." if sentry_ready else "Sentry is disabled.",
        action="Configure SENTRY_DSN before production operation." if environment == "production" and not sentry_ready else "",
    ))

    apns_enabled = bool(getattr(settings, "MYSCOOPE_APNS_ENABLED", False))
    apns_ready = all(
        bool(getattr(settings, name, ""))
        for name in (
            "MYSCOOPE_APNS_KEY_ID",
            "MYSCOOPE_APNS_TEAM_ID",
            "MYSCOOPE_APNS_PRIVATE_KEY",
            "MYSCOOPE_APNS_BUNDLE_ID",
        )
    )
    findings.append(DiagnosticFinding(
        code="notifications.apns",
        status="error" if apns_enabled and not apns_ready else "ok",
        category="notifications",
        summary=(
            "APNs delivery is configured."
            if apns_enabled and apns_ready
            else "APNs delivery is disabled."
            if not apns_enabled
            else "APNs is enabled without complete provider credentials."
        ),
        action="Disable APNs or configure its key, team, private key and bundle ID." if apns_enabled and not apns_ready else "",
    ))

    provider = str(getattr(settings, "AI_ASSISTANT_LLM_PROVIDER", "fake"))
    provider_ready = provider != "openai" or bool(getattr(settings, "AI_ASSISTANT_OPENAI_API_KEY", ""))
    findings.append(DiagnosticFinding(
        code="ai.provider",
        status="ok" if provider_ready else "error",
        category="ai_assistant",
        summary="The AI provider configuration is internally complete." if provider_ready else "OpenAI is selected without an API key.",
        action="Configure AI_ASSISTANT_OPENAI_API_KEY or select the fake provider." if not provider_ready else "",
    ))

    fatsecret_enabled = bool(getattr(settings, "FOOD_CATALOG_FATSECRET_ENABLED", False))
    fatsecret_ready = bool(getattr(settings, "FOOD_CATALOG_FATSECRET_CLIENT_ID", "")) and bool(
        getattr(settings, "FOOD_CATALOG_FATSECRET_CLIENT_SECRET", "")
    )
    findings.append(DiagnosticFinding(
        code="food_catalog.fatsecret",
        status="error" if fatsecret_enabled and not fatsecret_ready else "ok",
        category="food_catalog",
        summary=(
            "FatSecret is enabled with credentials."
            if fatsecret_enabled and fatsecret_ready
            else "FatSecret is disabled."
            if not fatsecret_enabled
            else "FatSecret is enabled without complete credentials."
        ),
        action="Disable FatSecret or configure both credential fields." if fatsecret_enabled and not fatsecret_ready else "",
    ))
    mercado_pago_enabled = bool(getattr(settings, "BILLING_MERCADOPAGO_WEBHOOK_ENABLED", False))
    mercado_pago_checkout_enabled = bool(getattr(settings, "BILLING_MERCADOPAGO_CHECKOUT_ENABLED", False))
    mercado_pago_ready = bool(getattr(settings, "BILLING_MERCADOPAGO_ACCESS_TOKEN", "")) and bool(
        getattr(settings, "BILLING_MERCADOPAGO_WEBHOOK_SECRET", "")
    )
    findings.append(DiagnosticFinding(
        code="billing.mercado_pago",
        status="error" if mercado_pago_enabled and not mercado_pago_ready else "ok",
        category="billing",
        summary=(
            "Mercado Pago webhooks are enabled with credentials."
            if mercado_pago_enabled and mercado_pago_ready
            else "Mercado Pago webhooks are disabled."
            if not mercado_pago_enabled
            else "Mercado Pago webhooks are enabled without complete credentials."
        ),
        action=(
            "Disable the webhook or configure its access token and signing secret."
            if mercado_pago_enabled and not mercado_pago_ready
            else ""
        ),
    ))
    public_base_url = str(getattr(settings, "BILLING_PUBLIC_BASE_URL", ""))
    findings.append(DiagnosticFinding(
        code="billing.mercado_pago_checkout",
        status="error" if mercado_pago_checkout_enabled and (not mercado_pago_ready or not public_base_url.startswith("https://")) else "ok",
        category="billing",
        summary="Mercado Pago checkout is ready." if mercado_pago_checkout_enabled and mercado_pago_ready and public_base_url.startswith("https://") else "Mercado Pago checkout is disabled." if not mercado_pago_checkout_enabled else "Mercado Pago checkout is missing credentials or a public HTTPS URL.",
        action="Configure the access token and BILLING_PUBLIC_BASE_URL, or disable checkout." if mercado_pago_checkout_enabled and (not mercado_pago_ready or not public_base_url.startswith("https://")) else "",
    ))
    apple_enabled = bool(getattr(settings, "BILLING_APPLE_PURCHASES_ENABLED", False)) or bool(
        getattr(settings, "BILLING_APPLE_NOTIFICATIONS_ENABLED", False)
    )
    apple_environment = str(getattr(settings, "BILLING_APPLE_ENVIRONMENT", ""))
    apple_verifier_ready = bool(getattr(settings, "BILLING_APPLE_BUNDLE_ID", "")) and apple_environment in {
        "sandbox", "production"
    }
    if apple_environment == "production":
        apple_verifier_ready = apple_verifier_ready and bool(getattr(settings, "BILLING_APPLE_APP_ID", None))
    findings.append(DiagnosticFinding(
        code="billing.apple_app_store",
        status="error" if apple_enabled and not apple_verifier_ready else "ok",
        category="billing",
        summary=(
            "Apple purchase verification is enabled and configured."
            if apple_enabled and apple_verifier_ready
            else "Apple purchase verification is disabled."
            if not apple_enabled
            else "Apple purchase verification is missing bundle, environment or production app ID configuration."
        ),
        action="Complete Apple verifier configuration or disable both Apple billing flags." if apple_enabled and not apple_verifier_ready else "",
    ))
    openfactura_enabled = bool(getattr(settings, "BILLING_OPENFACTURA_ENABLED", False))
    openfactura_ready = bool(getattr(settings, "BILLING_OPENFACTURA_API_KEY", "")) and bool(
        getattr(settings, "BILLING_OPENFACTURA_ISSUER_JSON", {})
    )
    findings.append(DiagnosticFinding(
        code="billing.openfactura",
        status="error" if openfactura_enabled and not openfactura_ready else "ok",
        category="billing",
        summary=(
            "OpenFactura is enabled with an API key."
            if openfactura_enabled and openfactura_ready
            else "OpenFactura is disabled."
            if not openfactura_enabled
            else "OpenFactura is enabled without an API key."
        ),
        action="Disable OpenFactura or configure its API key and approved issuer JSON." if openfactura_enabled and not openfactura_ready else "",
    ))
    return findings


def _database_findings(environment: str) -> list[DiagnosticFinding]:
    try:
        from allauth.socialaccount.models import SocialApp
        from django.contrib.sites.models import Site

        site_id = getattr(settings, "SITE_ID", 1)
        site_exists = Site.objects.filter(pk=site_id).exists()
        google_apps = SocialApp.objects.filter(provider="google")
        google_configured = google_apps.exclude(client_id="").exclude(secret="").exists()
        google_linked = google_apps.filter(sites__id=site_id).exists() if site_exists else False
    except DatabaseError:
        return [DiagnosticFinding(
            code="database.schema",
            status="error",
            category="django",
            summary="Database-backed diagnostics could not read the current schema.",
            action="Run migrations and retry the diagnostic.",
        )]

    findings = [DiagnosticFinding(
        code="sites.current",
        status="ok" if site_exists else "error",
        category="accounts",
        summary="The configured Django Site exists." if site_exists else "The configured SITE_ID does not exist.",
        action="Create or select the correct Django Site." if not site_exists else "",
    )]
    findings.append(DiagnosticFinding(
        code="oauth.google",
        status="ok" if google_configured and google_linked else ("warning" if environment == "development" else "error"),
        category="accounts",
        summary=(
            "Google OAuth credentials exist and are linked to the configured Site."
            if google_configured and google_linked
            else "Google OAuth is missing credentials or the configured Site association."
        ),
        action="Configure the Google SocialApp and associate it with SITE_ID." if not google_configured or not google_linked else "",
    ))
    findings.append(DiagnosticFinding(
        code="oauth.clock",
        status="warning",
        category="accounts",
        summary="OAuth token time validity cannot be verified without an external trusted clock.",
        action="Keep automatic system time enabled when diagnosing Invalid id_token responses.",
    ))
    return findings


def _configuration_summary() -> tuple[dict[str, object], ...]:
    summary = []
    for spec in ENVIRONMENT_VARIABLE_SPECS:
        summary.append({
            "name": spec.name,
            "category": spec.category,
            "value_type": spec.value_type,
            "secret": spec.secret,
            "required_in_production": spec.required_in_production,
            "configured": bool(os.environ.get(spec.name, "").strip()),
        })
    return tuple(summary)
