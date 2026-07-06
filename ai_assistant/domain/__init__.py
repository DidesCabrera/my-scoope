"""Domain contracts for AI Assistant.

The AI Assistant domain stays provider-agnostic and model-free. It defines the
semantic shape that future orchestrators, tool registries and safety layers can
share without importing My Scoope operational domains directly.
"""

from ai_assistant.domain.contracts import (
    AssistantContractError,
    AssistantIntent,
    AssistantIntentName,
    AssistantMessage,
    AssistantMessageRole,
    AssistantStructuredResponse,
    AssistantToolRequest,
    AssistantToolResult,
    AssistantToolStatus,
    AssistantTurnRequest,
)

__all__ = [
    "AssistantContractError",
    "AssistantIntent",
    "AssistantIntentName",
    "AssistantMessage",
    "AssistantMessageRole",
    "AssistantStructuredResponse",
    "AssistantToolRequest",
    "AssistantToolResult",
    "AssistantToolStatus",
    "AssistantTurnRequest",
]
