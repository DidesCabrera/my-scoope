from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from django.conf import settings

from ai_assistant.application.chat_engines import ChatEngineRequest

ROLLOUT_MODE_OFF = "off"
ROLLOUT_MODE_STAFF = "staff"
ROLLOUT_MODE_ALLOWLIST = "allowlist"
ROLLOUT_MODE_PERCENTAGE = "percentage"
ROLLOUT_MODE_ALL = "all"

SUPPORTED_ROLLOUT_MODES = {
    ROLLOUT_MODE_OFF,
    ROLLOUT_MODE_STAFF,
    ROLLOUT_MODE_ALLOWLIST,
    ROLLOUT_MODE_PERCENTAGE,
    ROLLOUT_MODE_ALL,
}


@dataclass(frozen=True)
class AIRolloutDecision:
    """Result of evaluating whether an LLM production surface is enabled."""

    enabled: bool
    mode: str
    reason: str
    user_id: int | None = None
    percent: int = 0
    bucket: int | None = None
    fallback_mode: str = "deterministic"

    def as_metadata(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "mode": self.mode,
            "reason": self.reason,
            "user_id": self.user_id,
            "percent": self.percent,
            "bucket": self.bucket,
            "fallback_mode": self.fallback_mode,
        }


def resolve_ai_llm_rollout(request: ChatEngineRequest | None = None) -> AIRolloutDecision:
    """Resolve the production LLM rollout gate for a chat request.

    This is a product rollout gate, not a credit check. It decides whether a
    user is allowed to use the production LLM mode after the global chat engine
    mode has been set to `llm_production`.
    """

    enabled = bool(getattr(settings, "AI_ASSISTANT_LLM_ROLLOUT_ENABLED", False))
    mode = _normalize_mode(getattr(settings, "AI_ASSISTANT_LLM_ROLLOUT_MODE", ROLLOUT_MODE_OFF))
    user_id = _request_user_id(request)
    percent = _bounded_percent(getattr(settings, "AI_ASSISTANT_LLM_ROLLOUT_PERCENT", 0))

    if not enabled:
        return AIRolloutDecision(
            enabled=False,
            mode=mode,
            reason="rollout_disabled",
            user_id=user_id,
            percent=percent,
        )

    if mode == ROLLOUT_MODE_OFF:
        return AIRolloutDecision(
            enabled=False,
            mode=mode,
            reason="rollout_mode_off",
            user_id=user_id,
            percent=percent,
        )

    if mode == ROLLOUT_MODE_ALL:
        return AIRolloutDecision(
            enabled=True,
            mode=mode,
            reason="rollout_all",
            user_id=user_id,
            percent=percent,
        )

    if mode == ROLLOUT_MODE_STAFF:
        if _request_user_is_staff(request):
            return AIRolloutDecision(
                enabled=True,
                mode=mode,
                reason="rollout_staff",
                user_id=user_id,
                percent=percent,
            )
        return AIRolloutDecision(
            enabled=False,
            mode=mode,
            reason="user_not_staff",
            user_id=user_id,
            percent=percent,
        )

    if mode == ROLLOUT_MODE_ALLOWLIST:
        allowlist = _configured_user_ids(getattr(settings, "AI_ASSISTANT_LLM_ROLLOUT_USER_IDS", ""))
        if user_id is not None and user_id in allowlist:
            return AIRolloutDecision(
                enabled=True,
                mode=mode,
                reason="rollout_allowlist",
                user_id=user_id,
                percent=percent,
            )
        return AIRolloutDecision(
            enabled=False,
            mode=mode,
            reason="user_not_allowlisted",
            user_id=user_id,
            percent=percent,
        )

    if mode == ROLLOUT_MODE_PERCENTAGE:
        bucket = stable_user_bucket(
            user_id=user_id,
            salt=str(getattr(settings, "AI_ASSISTANT_LLM_ROLLOUT_STICKY_SALT", "ai-assistant-rollout-v1")),
        )
        if user_id is not None and bucket < percent:
            return AIRolloutDecision(
                enabled=True,
                mode=mode,
                reason="rollout_percentage",
                user_id=user_id,
                percent=percent,
                bucket=bucket,
            )
        return AIRolloutDecision(
            enabled=False,
            mode=mode,
            reason="user_outside_percentage_rollout",
            user_id=user_id,
            percent=percent,
            bucket=bucket,
        )

    return AIRolloutDecision(
        enabled=False,
        mode=ROLLOUT_MODE_OFF,
        reason="unsupported_rollout_mode",
        user_id=user_id,
        percent=percent,
    )


def stable_user_bucket(*, user_id: int | None, salt: str) -> int | None:
    """Return a deterministic bucket 0-99 for sticky percentage rollout."""

    if user_id is None:
        return None
    digest = hashlib.sha256(f"{salt}:{int(user_id)}".encode("utf-8")).hexdigest()
    return int(digest[:8], 16) % 100


def _normalize_mode(value: Any) -> str:
    mode = str(value or ROLLOUT_MODE_OFF).strip().lower()
    return mode if mode in SUPPORTED_ROLLOUT_MODES else ROLLOUT_MODE_OFF


def _bounded_percent(value: Any) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return 0
    return max(0, min(100, parsed))


def _configured_user_ids(value: Any) -> set[int]:
    if isinstance(value, str):
        raw_values: Iterable[Any] = value.replace(";", ",").split(",")
    elif isinstance(value, Iterable):
        raw_values = value
    else:
        raw_values = ()

    result: set[int] = set()
    for raw in raw_values:
        try:
            parsed = int(str(raw).strip())
        except (TypeError, ValueError):
            continue
        if parsed > 0:
            result.add(parsed)
    return result


def _request_user_id(request: ChatEngineRequest | None) -> int | None:
    if request is None:
        return None
    if request.user_id is not None:
        try:
            return int(request.user_id)
        except (TypeError, ValueError):
            return None
    metadata = dict(request.metadata or {})
    user = metadata.get("user") or metadata.get("tool_user") or metadata.get("current_user")
    user_id = getattr(user, "id", None)
    try:
        return int(user_id) if user_id is not None else None
    except (TypeError, ValueError):
        return None


def _request_user_is_staff(request: ChatEngineRequest | None) -> bool:
    if request is None:
        return False
    metadata: Mapping[str, Any] = dict(request.metadata or {})
    if bool(metadata.get("is_staff")) or bool(metadata.get("user_is_staff")):
        return True
    user = metadata.get("user") or metadata.get("tool_user") or metadata.get("current_user")
    return bool(getattr(user, "is_staff", False))
