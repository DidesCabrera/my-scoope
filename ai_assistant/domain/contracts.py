from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping, Sequence


class AssistantContractError(ValueError):
    """Raised when an AI Assistant semantic contract is malformed."""


class AssistantMessageRole(str, Enum):
    """Semantic roles used by the AI Assistant orchestration layer."""

    SYSTEM = "system"
    DEVELOPER = "developer"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class AssistantIntentName(str, Enum):
    """Known high-level intents understood by the AI Assistant.

    These intents describe what the assistant believes the user is asking for.
    They do not authorize writes by themselves. Future orchestrators must still
    route every write through explicit tools, application services and proposal
    review.
    """

    UNKNOWN = "unknown"
    SMALL_TALK = "small_talk"
    ANSWER_QUESTION = "answer_question"
    ASK_CLARIFICATION = "ask_clarification"
    CAPTURE_NUTRITION_BRIEF = "capture_nutrition_brief"
    CREATE_MEAL_PROPOSAL = "create_meal_proposal"
    CREATE_DAILYPLAN_PROPOSAL = "create_dailyplan_proposal"
    CREATE_PROGRAM_PROPOSAL = "create_program_proposal"
    ITERATE_PROPOSAL = "iterate_proposal"
    READ_CONTEXT = "read_context"


class AssistantToolStatus(str, Enum):
    """Normalized status for controlled tool executions."""

    PENDING = "pending"
    OK = "ok"
    ERROR = "error"
    BLOCKED = "blocked"


@dataclass(frozen=True)
class AssistantMessage:
    """A normalized semantic message inside an AI Assistant turn.

    This is intentionally provider-agnostic. Mapping these messages to an
    external LLM transport belongs to an application orchestrator, not to the
    domain contract itself.
    """

    role: AssistantMessageRole | str
    content: str
    name: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "role", _coerce_enum(AssistantMessageRole, self.role, field_name="role"))
        object.__setattr__(self, "content", _normalize_message_content(self.content))
        object.__setattr__(self, "name", _normalize_identifier(self.name))
        object.__setattr__(self, "metadata", dict(self.metadata or {}))
        if not self.content:
            raise AssistantContractError("AssistantMessage requires non-empty content.")

    @property
    def normalized_content(self) -> str:
        return self.content

    def as_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "role": self.role.value,
            "content": self.content,
        }
        if self.name:
            payload["name"] = self.name
        if self.metadata:
            payload["metadata"] = dict(self.metadata)
        return payload


@dataclass(frozen=True)
class AssistantIntent:
    """High-level interpretation of the user's current request."""

    name: AssistantIntentName | str = AssistantIntentName.UNKNOWN
    confidence: float = 0.0
    summary: str = ""
    slots: Mapping[str, Any] = field(default_factory=dict)
    missing_slots: Sequence[str] = field(default_factory=tuple)
    safety_flags: Sequence[str] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _coerce_enum(AssistantIntentName, self.name, field_name="name"))
        object.__setattr__(self, "confidence", _coerce_confidence(self.confidence))
        object.__setattr__(self, "summary", _normalize_text(self.summary))
        object.__setattr__(self, "slots", dict(self.slots or {}))
        object.__setattr__(self, "missing_slots", tuple(_normalize_identifier(slot) for slot in self.missing_slots or ()))
        object.__setattr__(self, "safety_flags", tuple(_normalize_identifier(flag) for flag in self.safety_flags or ()))

    @property
    def requires_clarification(self) -> bool:
        return bool(self.missing_slots) or self.name == AssistantIntentName.ASK_CLARIFICATION

    @property
    def is_write_intent(self) -> bool:
        return self.name in {
            AssistantIntentName.CAPTURE_NUTRITION_BRIEF,
            AssistantIntentName.CREATE_MEAL_PROPOSAL,
            AssistantIntentName.CREATE_DAILYPLAN_PROPOSAL,
            AssistantIntentName.CREATE_PROGRAM_PROPOSAL,
            AssistantIntentName.ITERATE_PROPOSAL,
        }

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name.value,
            "confidence": self.confidence,
            "summary": self.summary,
            "slots": dict(self.slots),
            "missing_slots": list(self.missing_slots),
            "safety_flags": list(self.safety_flags),
        }


@dataclass(frozen=True)
class AssistantToolRequest:
    """Request for a future controlled AI Assistant tool.

    Patch 44 only defines the shape. Patch 45 will decide which tool names are
    allowed and how they are registered.
    """

    tool_name: str
    arguments: Mapping[str, Any] = field(default_factory=dict)
    request_id: str = ""
    reason: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "tool_name", _normalize_identifier(self.tool_name))
        object.__setattr__(self, "arguments", dict(self.arguments or {}))
        object.__setattr__(self, "request_id", _normalize_correlation_id(self.request_id))
        object.__setattr__(self, "reason", _normalize_text(self.reason))
        object.__setattr__(self, "metadata", dict(self.metadata or {}))
        if not self.tool_name:
            raise AssistantContractError("AssistantToolRequest requires a tool_name.")

    def as_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "tool_name": self.tool_name,
            "arguments": dict(self.arguments),
        }
        if self.request_id:
            payload["request_id"] = self.request_id
        if self.reason:
            payload["reason"] = self.reason
        if self.metadata:
            payload["metadata"] = dict(self.metadata)
        return payload


@dataclass(frozen=True)
class AssistantToolResult:
    """Normalized result of a future controlled AI Assistant tool."""

    tool_name: str
    status: AssistantToolStatus | str
    data: Mapping[str, Any] = field(default_factory=dict)
    request_id: str = ""
    error_code: str = ""
    error_message: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "tool_name", _normalize_identifier(self.tool_name))
        object.__setattr__(self, "status", _coerce_enum(AssistantToolStatus, self.status, field_name="status"))
        object.__setattr__(self, "data", dict(self.data or {}))
        object.__setattr__(self, "request_id", _normalize_correlation_id(self.request_id))
        object.__setattr__(self, "error_code", _normalize_identifier(self.error_code))
        object.__setattr__(self, "error_message", _normalize_text(self.error_message))
        object.__setattr__(self, "metadata", dict(self.metadata or {}))
        if not self.tool_name:
            raise AssistantContractError("AssistantToolResult requires a tool_name.")
        if self.status in {AssistantToolStatus.ERROR, AssistantToolStatus.BLOCKED} and not (
            self.error_code or self.error_message
        ):
            raise AssistantContractError("Error or blocked tool results require error_code or error_message.")

    @property
    def ok(self) -> bool:
        return self.status == AssistantToolStatus.OK

    def as_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "tool_name": self.tool_name,
            "status": self.status.value,
            "data": dict(self.data),
        }
        if self.request_id:
            payload["request_id"] = self.request_id
        if self.error_code:
            payload["error_code"] = self.error_code
        if self.error_message:
            payload["error_message"] = self.error_message
        if self.metadata:
            payload["metadata"] = dict(self.metadata)
        return payload


@dataclass(frozen=True)
class AssistantStructuredResponse:
    """Provider-agnostic semantic output for a single assistant turn.

    `requires_human_review` defaults to True to preserve My Scoope's current
    proposal-first safety boundary. Future read-only turns may opt out
    explicitly, but write intents should remain reviewable.
    """

    assistant_message: AssistantMessage
    intent: AssistantIntent = field(default_factory=AssistantIntent)
    tool_requests: Sequence[AssistantToolRequest] = field(default_factory=tuple)
    tool_results: Sequence[AssistantToolResult] = field(default_factory=tuple)
    proposal_ids: Sequence[int] = field(default_factory=tuple)
    requires_human_review: bool = True
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.assistant_message.role != AssistantMessageRole.ASSISTANT:
            raise AssistantContractError("AssistantStructuredResponse requires an assistant message.")
        object.__setattr__(self, "tool_requests", tuple(self.tool_requests or ()))
        object.__setattr__(self, "tool_results", tuple(self.tool_results or ()))
        object.__setattr__(self, "proposal_ids", tuple(int(value) for value in self.proposal_ids or ()))
        object.__setattr__(self, "metadata", dict(self.metadata or {}))

    @property
    def assistant_text(self) -> str:
        return self.assistant_message.content

    @property
    def has_tool_requests(self) -> bool:
        return bool(self.tool_requests)

    @property
    def has_proposals(self) -> bool:
        return bool(self.proposal_ids)

    def as_dict(self) -> dict[str, Any]:
        return {
            "assistant_message": self.assistant_message.as_dict(),
            "assistant_text": self.assistant_text,
            "intent": self.intent.as_dict(),
            "tool_requests": [request.as_dict() for request in self.tool_requests],
            "tool_results": [result.as_dict() for result in self.tool_results],
            "proposal_ids": list(self.proposal_ids),
            "requires_human_review": self.requires_human_review,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class AssistantTurnRequest:
    """Semantic input for a future AI Assistant orchestrator turn."""

    user_message: AssistantMessage
    history: Sequence[AssistantMessage] = field(default_factory=tuple)
    context: Mapping[str, Any] = field(default_factory=dict)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.user_message.role != AssistantMessageRole.USER:
            raise AssistantContractError("AssistantTurnRequest requires a user message.")
        object.__setattr__(self, "history", tuple(self.history or ()))
        object.__setattr__(self, "context", dict(self.context or {}))
        object.__setattr__(self, "metadata", dict(self.metadata or {}))

    @property
    def messages(self) -> tuple[AssistantMessage, ...]:
        return (*self.history, self.user_message)

    def as_dict(self) -> dict[str, Any]:
        return {
            "user_message": self.user_message.as_dict(),
            "history": [message.as_dict() for message in self.history],
            "context": dict(self.context),
            "metadata": dict(self.metadata),
        }


def _normalize_text(value: Any) -> str:
    return " ".join(str(value or "").split())


def _normalize_message_content(value: Any) -> str:
    """Normalize visible chat text without destroying readable line breaks."""

    raw_text = str(value or "").replace("\r\n", "\n").replace("\r", "\n")
    lines = [" ".join(line.strip().split()) for line in raw_text.split("\n")]

    normalized_lines: list[str] = []
    previous_blank = False
    for line in lines:
        if not line:
            if normalized_lines and not previous_blank:
                normalized_lines.append("")
            previous_blank = True
            continue
        normalized_lines.append(line)
        previous_blank = False

    return "\n".join(normalized_lines).strip()


def _normalize_identifier(value: Any) -> str:
    return _normalize_text(value).replace(" ", "_").lower()


def _normalize_correlation_id(value: Any) -> str:
    """Preserve opaque provider correlation IDs byte-for-byte apart from edge whitespace.

    Responses API ``call_id`` values are case-sensitive. They must never pass
    through identifier normalization, which lowercases and rewrites spaces for
    My Scoope-owned semantic names such as tool names and error codes.
    """

    return str(value or "").strip()


def _coerce_confidence(value: Any) -> float:
    try:
        confidence = float(value)
    except (TypeError, ValueError) as exc:
        raise AssistantContractError("AssistantIntent confidence must be a number between 0 and 1.") from exc
    if confidence < 0 or confidence > 1:
        raise AssistantContractError("AssistantIntent confidence must be between 0 and 1.")
    return confidence


def _coerce_enum(enum_class: type[Enum], value: Any, *, field_name: str) -> Enum:
    if isinstance(value, enum_class):
        return value
    try:
        return enum_class(str(value))
    except ValueError as exc:
        allowed = ", ".join(member.value for member in enum_class)
        raise AssistantContractError(f"Invalid {field_name}: {value!r}. Allowed values: {allowed}.") from exc
