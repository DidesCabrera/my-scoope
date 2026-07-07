from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from django.conf import settings
from django.core.checks import Error, Tags, Warning, register


PRODUCTION_ENGINE_MODE = "llm_production"
SAFE_ROLLOUT_MODES = {"off", ""}
REQUIRED_TECHNICAL_LIMITS = (
    "AI_ASSISTANT_MAX_HISTORY_MESSAGES",
    "AI_ASSISTANT_MAX_OUTPUT_TOKENS",
    "AI_ASSISTANT_MAX_TOOL_LOOP_ITERATIONS",
    "AI_ASSISTANT_MAX_INPUT_TOKENS",
    "AI_ASSISTANT_MAX_CONTEXT_CHARS",
    "AI_ASSISTANT_MAX_MESSAGE_CHARS",
    "AI_ASSISTANT_MAX_TOOL_REQUESTS_PER_TURN",
)


def _setting_bool(name: str, default: bool = False) -> bool:
    value = getattr(settings, name, default)
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _positive_decimal(value: Any) -> bool:
    try:
        return Decimal(str(value)) > 0
    except (InvalidOperation, TypeError, ValueError):
        return False


def _positive_int_setting(name: str) -> bool:
    try:
        return int(getattr(settings, name, 0)) > 0
    except (TypeError, ValueError):
        return False


def _production_llm_requested() -> bool:
    engine_mode = str(getattr(settings, "AI_ASSISTANT_CHAT_ENGINE_MODE", "") or "").strip()
    rollout_enabled = _setting_bool("AI_ASSISTANT_LLM_ROLLOUT_ENABLED", False)
    rollout_mode = str(getattr(settings, "AI_ASSISTANT_LLM_ROLLOUT_MODE", "") or "").strip().lower()
    return engine_mode == PRODUCTION_ENGINE_MODE or (
        rollout_enabled and rollout_mode not in SAFE_ROLLOUT_MODES
    )


def _credit_plans_are_limited(plans: Any) -> bool:
    if not isinstance(plans, dict) or not plans:
        return False
    for plan in plans.values():
        if not isinstance(plan, dict):
            continue
        try:
            monthly_limit = int(plan.get("monthly_credit_limit") or 0)
            daily_limit = int(plan.get("daily_credit_limit") or 0)
        except (TypeError, ValueError):
            continue
        blocks = bool(plan.get("block_on_exhaustion"))
        if monthly_limit > 0 and daily_limit > 0 and blocks:
            return True
    return False


@register(Tags.security, deploy=True)
def check_ai_assistant_production_guard(app_configs, **kwargs):
    if not _production_llm_requested():
        return []

    issues = []
    if not _setting_bool("AI_ASSISTANT_CREDITS_ENABLED", False):
        issues.append(
            Error(
                "AI Assistant production LLM is enabled without credit enforcement.",
                hint=(
                    "Set AI_ASSISTANT_CREDITS_ENABLED=true before enabling "
                    "AI_ASSISTANT_CHAT_ENGINE_MODE=llm_production or an active rollout."
                ),
                id="ai_assistant.E001",
            )
        )

    if not _positive_decimal(getattr(settings, "AI_ASSISTANT_USD_PER_AI_CREDIT", "0")):
        issues.append(
            Error(
                "AI Assistant production LLM requires a positive USD-per-credit value.",
                hint="Set AI_ASSISTANT_USD_PER_AI_CREDIT to a decimal greater than 0.",
                id="ai_assistant.E002",
            )
        )

    if not _credit_plans_are_limited(getattr(settings, "AI_ASSISTANT_CREDIT_PLANS", {})):
        issues.append(
            Warning(
                "AI Assistant production LLM has no clearly limited credit plan configured.",
                hint=(
                    "Configure AI_ASSISTANT_CREDIT_PLANS with monthly and daily limits "
                    "and block_on_exhaustion=True for at least one plan."
                ),
                id="ai_assistant.W001",
            )
        )

    missing_limits = [
        name for name in REQUIRED_TECHNICAL_LIMITS if not _positive_int_setting(name)
    ]
    if missing_limits:
        issues.append(
            Error(
                "AI Assistant production LLM requires positive technical guardrail limits.",
                hint="Configure positive values for: " + ", ".join(missing_limits),
                id="ai_assistant.E003",
            )
        )

    return issues
