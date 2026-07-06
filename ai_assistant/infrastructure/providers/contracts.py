from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Mapping, Protocol, Sequence, runtime_checkable

LLMMessageRole = Literal["system", "developer", "user", "assistant"]


class LLMProviderError(RuntimeError):
    """Base error for external LLM provider gateways."""


class LLMProviderConfigurationError(LLMProviderError):
    """Raised when a provider cannot run because settings are incomplete."""


class LLMProviderRequestError(LLMProviderError):
    """Raised when the provider rejects or cannot process a request."""


@dataclass(frozen=True)
class LLMMessage:
    """Minimal transport-level message sent to an external LLM provider.

    This is not the final structured intent/tool contract. Patch 44 will define
    assistant-level semantic contracts. Patch 43 only needs a safe provider
    gateway contract with a small, explicit payload surface.
    """

    role: LLMMessageRole
    content: str

    def as_openai_input_item(self) -> dict[str, str]:
        return {
            "role": self.role,
            "content": self.content,
        }


@dataclass(frozen=True)
class LLMProviderRequest:
    """Input for a single provider call.

    `metadata` stays internal to My Scoope. Provider adapters must not forward it
    unless a later patch explicitly whitelists a field.
    """

    messages: Sequence[LLMMessage]
    max_output_tokens: int | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @property
    def normalized_messages(self) -> tuple[LLMMessage, ...]:
        return tuple(
            LLMMessage(role=message.role, content=" ".join(str(message.content or "").split()))
            for message in self.messages
            if str(message.content or "").strip()
        )


@dataclass(frozen=True)
class LLMProviderResponse:
    """Normalized response returned by any supported LLM provider."""

    provider: str
    model: str
    text: str
    response_id: str = ""
    usage: Mapping[str, Any] = field(default_factory=dict)
    raw: Mapping[str, Any] = field(default_factory=dict)

    @property
    def normalized_text(self) -> str:
        return " ".join(str(self.text or "").split())


@runtime_checkable
class LLMClient(Protocol):
    """Minimal provider client interface consumed by future orchestrators."""

    provider_name: str

    def generate(self, request: LLMProviderRequest) -> LLMProviderResponse:
        """Generate one provider response from the supplied messages."""
        raise NotImplementedError
