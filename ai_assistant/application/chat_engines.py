from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Protocol, runtime_checkable


@dataclass(frozen=True)
class ChatEngineRequest:
    """Input contract for a single chat turn.

    The chat UI belongs to My Scoope. A chat engine only receives the minimal
    message/context needed to produce the next conversational state.
    """

    message: str
    existing_payload: Mapping[str, Any] | None = None
    user_id: int | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @property
    def normalized_message(self) -> str:
        return " ".join(str(self.message or "").split())


@dataclass(frozen=True)
class ChatEngineTurnResult:
    """Output contract for a chat engine turn.

    `state` is intentionally opaque in Patch 42. The existing deterministic
    intake engine returns a `NutritionConversationState`; a future LLM engine can
    return a structured assistant state while the view keeps consuming the same
    engine contract.
    """

    state: Any
    assistant_text: str = ""
    is_ready_for_proposal: bool = False
    engine_name: str = "unknown"
    metadata: Mapping[str, Any] = field(default_factory=dict)


@runtime_checkable
class ChatEngine(Protocol):
    """Minimal engine interface used by the existing chat surface."""

    engine_name: str

    def continue_chat(self, request: ChatEngineRequest) -> ChatEngineTurnResult:
        """Process one user turn and return the next chat state."""
        raise NotImplementedError
