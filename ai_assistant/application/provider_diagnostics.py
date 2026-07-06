from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from django.conf import settings

from ai_assistant.infrastructure.providers import (
    LLMClient,
    LLMMessage,
    LLMProviderConfigurationError,
    LLMProviderError,
    LLMProviderRequest,
    LLMProviderRequestError,
    get_llm_client,
)

SUPPORTED_PROVIDERS = {"fake", "openai"}
DIAGNOSTIC_LIVE_USER_MESSAGE = "AI Assistant provider diagnostic ping. Reply with OK only."


@dataclass(frozen=True)
class LLMProviderDiagnosticResult:
    """Safe operational summary for the configured LLM provider.

    This result is designed for logs, management commands and future health
    checks. It must not contain API keys, headers, prompts, raw responses or
    user-specific data.
    """

    provider: str
    configured: bool
    client_buildable: bool
    live_check: str = "skipped"
    status: str = "ok"
    missing_settings: tuple[str, ...] = field(default_factory=tuple)
    model: str = ""
    base_url_configured: bool | None = None
    timeout_seconds: int | float | None = None
    error_message: str = ""
    live_response_provider: str = ""
    live_response_model: str = ""
    live_response_id: str = ""

    @property
    def ok(self) -> bool:
        return self.status == "ok"

    def as_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "provider": self.provider,
            "configured": self.configured,
            "client_buildable": self.client_buildable,
            "live_check": self.live_check,
            "status": self.status,
            "missing_settings": list(self.missing_settings),
        }
        if self.model:
            payload["model"] = self.model
        if self.base_url_configured is not None:
            payload["base_url_configured"] = self.base_url_configured
        if self.timeout_seconds is not None:
            payload["timeout_seconds"] = self.timeout_seconds
        if self.error_message:
            payload["error_message"] = self.error_message
        if self.live_response_provider:
            payload["live_response_provider"] = self.live_response_provider
        if self.live_response_model:
            payload["live_response_model"] = self.live_response_model
        if self.live_response_id:
            payload["live_response_id"] = self.live_response_id
        return payload


def diagnose_llm_provider(
    *,
    provider_name: str | None = None,
    live: bool = False,
    client_factory: Callable[[str | None], LLMClient] = get_llm_client,
) -> LLMProviderDiagnosticResult:
    """Diagnose the external LLM provider without changing product behavior.

    By default this performs configuration and factory checks only. A live
    provider call happens only when `live=True`, using a tiny generic message
    that contains no user data and asks for no tools.
    """

    provider = _resolve_provider_name(provider_name)
    missing_settings = _missing_settings_for_provider(provider)
    provider_metadata = _provider_metadata(provider)

    if provider not in SUPPORTED_PROVIDERS:
        return LLMProviderDiagnosticResult(
            provider=provider or "<empty>",
            configured=False,
            client_buildable=False,
            live_check="skipped",
            status="configuration_error",
            missing_settings=missing_settings,
            error_message=f"Unsupported AI_ASSISTANT_LLM_PROVIDER: {provider or '<empty>'}.",
            **provider_metadata,
        )

    if missing_settings:
        return LLMProviderDiagnosticResult(
            provider=provider,
            configured=False,
            client_buildable=False,
            live_check="skipped",
            status="configuration_error",
            missing_settings=missing_settings,
            error_message="Missing required LLM provider settings.",
            **provider_metadata,
        )

    try:
        client = client_factory(provider)
    except LLMProviderConfigurationError as exc:
        return LLMProviderDiagnosticResult(
            provider=provider,
            configured=False,
            client_buildable=False,
            live_check="skipped",
            status="configuration_error",
            missing_settings=missing_settings,
            error_message=_safe_error_message(exc),
            **provider_metadata,
        )
    except LLMProviderError as exc:
        return LLMProviderDiagnosticResult(
            provider=provider,
            configured=True,
            client_buildable=False,
            live_check="skipped",
            status="provider_error",
            missing_settings=missing_settings,
            error_message=_safe_error_message(exc),
            **provider_metadata,
        )

    if not live:
        return LLMProviderDiagnosticResult(
            provider=provider,
            configured=True,
            client_buildable=True,
            live_check="skipped",
            status="ok",
            missing_settings=missing_settings,
            **provider_metadata,
        )

    try:
        response = client.generate(
            LLMProviderRequest(
                messages=(
                    LLMMessage(
                        role="developer",
                        content="You are running a configuration diagnostic. Do not request tools.",
                    ),
                    LLMMessage(role="user", content=DIAGNOSTIC_LIVE_USER_MESSAGE),
                ),
                max_output_tokens=16,
                metadata={"diagnostic": True},
            )
        )
    except LLMProviderConfigurationError as exc:
        return LLMProviderDiagnosticResult(
            provider=provider,
            configured=False,
            client_buildable=True,
            live_check="failed",
            status="configuration_error",
            missing_settings=missing_settings,
            error_message=_safe_error_message(exc),
            **provider_metadata,
        )
    except LLMProviderRequestError as exc:
        return LLMProviderDiagnosticResult(
            provider=provider,
            configured=True,
            client_buildable=True,
            live_check="failed",
            status="provider_error",
            missing_settings=missing_settings,
            error_message=_safe_error_message(exc),
            **provider_metadata,
        )

    return LLMProviderDiagnosticResult(
        provider=provider,
        configured=True,
        client_buildable=True,
        live_check="ok",
        status="ok",
        missing_settings=missing_settings,
        live_response_provider=response.provider,
        live_response_model=response.model,
        live_response_id=response.response_id,
        **provider_metadata,
    )


def _resolve_provider_name(provider_name: str | None) -> str:
    return (provider_name or getattr(settings, "AI_ASSISTANT_LLM_PROVIDER", "fake") or "").strip().lower()


def _missing_settings_for_provider(provider: str) -> tuple[str, ...]:
    if provider == "fake":
        return ()
    if provider == "openai":
        required_settings = {
            "AI_ASSISTANT_OPENAI_API_KEY": getattr(settings, "AI_ASSISTANT_OPENAI_API_KEY", ""),
            "AI_ASSISTANT_OPENAI_MODEL": getattr(settings, "AI_ASSISTANT_OPENAI_MODEL", ""),
            "AI_ASSISTANT_OPENAI_BASE_URL": getattr(settings, "AI_ASSISTANT_OPENAI_BASE_URL", ""),
        }
        return tuple(name for name, value in required_settings.items() if not str(value or "").strip())
    return ("AI_ASSISTANT_LLM_PROVIDER",)


def _provider_metadata(provider: str) -> dict[str, object]:
    if provider == "openai":
        return {
            "model": str(getattr(settings, "AI_ASSISTANT_OPENAI_MODEL", "") or "").strip(),
            "base_url_configured": bool(str(getattr(settings, "AI_ASSISTANT_OPENAI_BASE_URL", "") or "").strip()),
            "timeout_seconds": getattr(settings, "AI_ASSISTANT_OPENAI_TIMEOUT_SECONDS", None),
        }
    if provider == "fake":
        return {"model": "fake-llm"}
    return {}


def _safe_error_message(exc: Exception) -> str:
    message = " ".join(str(exc or "").split())
    if not message:
        return "LLM provider diagnostic failed."
    return message[:240]
