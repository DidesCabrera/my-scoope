from __future__ import annotations

import time
from dataclasses import dataclass

from django.conf import settings

from ai_assistant.application.limits import AITurnLimitConfig

@dataclass(frozen=True)
class AssistantOrchestratorConfig:
    """Runtime limits for the external LLM orchestrator v1.

    The orchestrator sends bounded history, accepts natural visible text, and
    allows a controlled multi-step native tool loop so the model can operate My
    Scoope objects. Reviewable proposal tools are part of the normal runtime and
    never apply changes directly.
    """

    max_history_messages: int = 20
    max_output_tokens: int = 2400
    max_tool_loop_iterations: int = 4
    enable_reviewable_proposal_tools: bool = True
    max_input_tokens: int = 20000
    max_context_chars: int = 16000
    max_message_chars: int = 2000
    max_tool_requests_per_turn: int = 3
    engine_name: str = "external_llm_orchestrator_v1"
    response_format_version: str = "ai_assistant_natural_response.v1"
    reasoning_effort: str = "low"

    @classmethod
    def from_settings(cls) -> "AssistantOrchestratorConfig":
        return cls(
            max_history_messages=_settings_int("AI_ASSISTANT_MAX_HISTORY_MESSAGES", cls.max_history_messages),
            max_output_tokens=_settings_int("AI_ASSISTANT_MAX_OUTPUT_TOKENS", cls.max_output_tokens),
            max_tool_loop_iterations=_settings_int("AI_ASSISTANT_MAX_TOOL_LOOP_ITERATIONS", cls.max_tool_loop_iterations),
            enable_reviewable_proposal_tools=_settings_bool(
                "AI_ASSISTANT_ENABLE_REVIEWABLE_PROPOSAL_TOOLS",
                cls.enable_reviewable_proposal_tools,
            ),
            max_input_tokens=_settings_int("AI_ASSISTANT_MAX_INPUT_TOKENS", cls.max_input_tokens),
            max_context_chars=_settings_int("AI_ASSISTANT_MAX_CONTEXT_CHARS", cls.max_context_chars),
            max_message_chars=_settings_int("AI_ASSISTANT_MAX_MESSAGE_CHARS", cls.max_message_chars),
            max_tool_requests_per_turn=_settings_int(
                "AI_ASSISTANT_MAX_TOOL_REQUESTS_PER_TURN",
                cls.max_tool_requests_per_turn,
            ),
            reasoning_effort=_settings_choice(
                "AI_ASSISTANT_OPENAI_REASONING_EFFORT",
                cls.reasoning_effort,
                allowed={"none", "minimal", "low", "medium", "high", "xhigh", "max"},
            ),
        )

    @property
    def turn_limits(self) -> AITurnLimitConfig:
        return AITurnLimitConfig(
            max_input_tokens=self.max_input_tokens,
            max_context_chars=self.max_context_chars,
            max_message_chars=self.max_message_chars,
            max_tool_requests_per_turn=self.max_tool_requests_per_turn,
        ).normalized()


def _settings_int(name: str, default: int) -> int:
    try:
        return int(getattr(settings, name, default))
    except (TypeError, ValueError):
        return default


def _settings_choice(name: str, default: str, *, allowed: set[str]) -> str:
    value = str(getattr(settings, name, default) or default).strip().lower()
    return value if value in allowed else default


def _settings_bool(name: str, default: bool) -> bool:
    value = getattr(settings, name, default)
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def elapsed_ms(started_at: float) -> int:
    return max(0, int(round((time.perf_counter() - started_at) * 1000)))
