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

    ``tools`` contains provider-agnostic function declarations. Provider
    adapters may forward only this explicit field and the small tool-selection
    controls below; arbitrary ``metadata`` remains internal to My Scoope.
    """

    messages: Sequence[LLMMessage]
    max_output_tokens: int | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)
    tools: Sequence[Mapping[str, Any]] = field(default_factory=tuple)
    tool_choice: str | Mapping[str, Any] | None = None
    parallel_tool_calls: bool | None = None
    max_tool_calls: int | None = None
    continuation_items: Sequence[Mapping[str, Any]] = field(default_factory=tuple)
    tool_outputs: Sequence["LLMProviderToolOutput"] = field(default_factory=tuple)

    @property
    def normalized_messages(self) -> tuple[LLMMessage, ...]:
        return tuple(
            LLMMessage(role=message.role, content=" ".join(str(message.content or "").split()))
            for message in self.messages
            if str(message.content or "").strip()
        )


@dataclass(frozen=True)
class LLMProviderToolOutput:
    """One controlled My Scoope result returned to a provider function call."""

    call_id: str
    output: Mapping[str, Any] | str = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "call_id", str(self.call_id or "").strip())
        if isinstance(self.output, Mapping):
            object.__setattr__(self, "output", dict(self.output))
        else:
            object.__setattr__(self, "output", str(self.output or ""))


@dataclass(frozen=True)
class LLMProviderToolCall:
    """One provider-native function call, before My Scoope validation."""

    name: str
    arguments: Mapping[str, Any] = field(default_factory=dict)
    call_id: str = ""
    parse_error: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", "_".join(str(self.name or "").strip().lower().split()))
        object.__setattr__(self, "arguments", dict(self.arguments or {}))
        object.__setattr__(self, "call_id", str(self.call_id or "").strip())
        object.__setattr__(self, "parse_error", " ".join(str(self.parse_error or "").split()))


@dataclass(frozen=True)
class LLMProviderResponse:
    """Normalized response returned by any supported LLM provider."""

    provider: str
    model: str
    text: str
    response_id: str = ""
    usage: Mapping[str, Any] = field(default_factory=dict)
    raw: Mapping[str, Any] = field(default_factory=dict)
    tool_calls: Sequence[LLMProviderToolCall] = field(default_factory=tuple)
    continuation_items: Sequence[Mapping[str, Any]] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(self, "tool_calls", tuple(self.tool_calls or ()))
        object.__setattr__(
            self,
            "continuation_items",
            tuple(dict(item) for item in self.continuation_items or () if isinstance(item, Mapping)),
        )

    @property
    def normalized_text(self) -> str:
        raw_text = str(self.text or "").replace("\r\n", "\n").replace("\r", "\n")
        lines = [" ".join(line.strip().split()) for line in raw_text.split("\n")]
        return "\n".join(lines).strip()


@runtime_checkable
class LLMClient(Protocol):
    """Minimal provider client interface consumed by future orchestrators."""

    provider_name: str

    def generate(self, request: LLMProviderRequest) -> LLMProviderResponse:
        """Generate one provider response from the supplied messages."""
        raise NotImplementedError
