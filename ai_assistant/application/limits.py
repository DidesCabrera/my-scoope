from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from ai_assistant.infrastructure.providers import LLMProviderRequest


APPROX_CHARS_PER_TOKEN = 4


@dataclass(frozen=True)
class AILimitViolation:
    """A technical guardrail violation detected before calling the LLM."""

    error_code: str
    message: str
    details: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AITurnLimitConfig:
    """Technical per-turn limits for external LLM calls.

    These limits are not commercial credits or membership quotas. They protect
    My Scoope from accidentally sending oversized prompts, excessive context,
    or too many tool calls while the product-level credit layer is still being
    designed from real usage data.
    """

    max_input_tokens: int = 6000
    max_context_chars: int = 8000
    max_message_chars: int = 2000
    max_tool_requests_per_turn: int = 3

    def normalized(self) -> "AITurnLimitConfig":
        return AITurnLimitConfig(
            max_input_tokens=max(1, int(self.max_input_tokens or 1)),
            max_context_chars=max(256, int(self.max_context_chars or 256)),
            max_message_chars=max(256, int(self.max_message_chars or 256)),
            max_tool_requests_per_turn=max(0, int(self.max_tool_requests_per_turn or 0)),
        )


def estimate_text_tokens(text: Any) -> int:
    """Return a deterministic, conservative-enough token estimate.

    Provider usage remains the source of truth after a call. Before the call,
    My Scoope only needs a stable estimate to avoid runaway context. The
    approximation intentionally avoids provider-specific tokenizers.
    """

    normalized = " ".join(str(text or "").split())
    if not normalized:
        return 0
    return max(1, int(math.ceil(len(normalized) / APPROX_CHARS_PER_TOKEN)))


def estimate_provider_request_tokens(request: LLMProviderRequest) -> int:
    return sum(estimate_text_tokens(message.content) for message in request.normalized_messages)


def validate_provider_request_limits(
    request: LLMProviderRequest,
    *,
    limits: AITurnLimitConfig,
) -> AILimitViolation | None:
    normalized_limits = limits.normalized()
    estimated_tokens = estimate_provider_request_tokens(request)
    if estimated_tokens > normalized_limits.max_input_tokens:
        return AILimitViolation(
            error_code="ai_input_token_limit_exceeded",
            message="La solicitud supera el límite técnico de contexto IA para este turno.",
            details={
                "estimated_input_tokens": estimated_tokens,
                "max_input_tokens": normalized_limits.max_input_tokens,
                "message_count": len(request.normalized_messages),
            },
        )
    return None


def bounded_text(value: Any, *, max_chars: int) -> str:
    text = " ".join(str(value or "").split())
    max_chars = max(1, int(max_chars or 1))
    if len(text) <= max_chars:
        return text
    return f"{text[: max_chars - 1]}…"


__all__ = [
    "AILimitViolation",
    "AITurnLimitConfig",
    "bounded_text",
    "estimate_provider_request_tokens",
    "estimate_text_tokens",
    "validate_provider_request_limits",
]
