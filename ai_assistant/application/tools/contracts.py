from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping, Sequence


class AssistantToolRegistryError(ValueError):
    """Raised when the controlled AI Assistant tool registry is malformed."""


class AssistantToolCategory(str, Enum):
    """Stable categories for AI Assistant tools."""

    READ = "read"
    DRAFT = "draft"
    VALIDATION = "validation"
    PROPOSAL = "proposal"
    COMMIT = "commit"


class AssistantToolRiskLevel(str, Enum):
    """Risk policy attached to a tool exposed to an external LLM orchestrator."""

    LOW = "low"
    MEDIUM = "medium"
    REVIEW_REQUIRED = "review_required"


@dataclass(frozen=True)
class AssistantToolSpec:
    """Allowlisted tool metadata for future AI Assistant orchestration.

    This is a provider-agnostic registry contract. It describes which tools may
    be requested by a future LLM orchestrator; it does not execute the tool and
    it does not grant the LLM direct access to Django models.
    """

    name: str
    description: str
    category: AssistantToolCategory | str
    input_schema: Mapping[str, Any] = field(default_factory=dict)
    risk_level: AssistantToolRiskLevel | str = AssistantToolRiskLevel.LOW
    requires_auth: bool = True
    requires_human_review: bool = True
    allowed_intents: Sequence[str] = field(default_factory=tuple)
    provider_exposed: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _normalize_identifier(self.name))
        object.__setattr__(self, "description", _normalize_text(self.description))
        object.__setattr__(
            self,
            "category",
            _coerce_enum(AssistantToolCategory, self.category, field_name="category"),
        )
        object.__setattr__(
            self,
            "risk_level",
            _coerce_enum(AssistantToolRiskLevel, self.risk_level, field_name="risk_level"),
        )
        object.__setattr__(self, "input_schema", dict(self.input_schema or {}))
        object.__setattr__(
            self,
            "allowed_intents",
            tuple(_normalize_identifier(intent) for intent in self.allowed_intents or ()),
        )

        if not self.name:
            raise AssistantToolRegistryError("AssistantToolSpec requires a name.")
        if not self.description:
            raise AssistantToolRegistryError("AssistantToolSpec requires a description.")
        if self.category == AssistantToolCategory.PROPOSAL and not self.requires_human_review:
            raise AssistantToolRegistryError("Proposal tools must require human review.")
        if self.category == AssistantToolCategory.DRAFT and self.requires_human_review:
            raise AssistantToolRegistryError("Draft tools must not require human review; persistence approval is handled by commit tools.")
        if self.category == AssistantToolCategory.COMMIT and not self.requires_human_review:
            raise AssistantToolRegistryError("Commit tools must require human review.")

    @property
    def is_read_only(self) -> bool:
        return self.category == AssistantToolCategory.READ

    @property
    def is_draft_tool(self) -> bool:
        return self.category == AssistantToolCategory.DRAFT

    @property
    def is_proposal_tool(self) -> bool:
        return self.category == AssistantToolCategory.PROPOSAL

    @property
    def is_commit_tool(self) -> bool:
        return self.category == AssistantToolCategory.COMMIT

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "input_schema": dict(self.input_schema),
            "risk_level": self.risk_level.value,
            "requires_auth": self.requires_auth,
            "requires_human_review": self.requires_human_review,
            "allowed_intents": list(self.allowed_intents),
            "provider_exposed": bool(self.provider_exposed),
        }

    def as_provider_tool(self) -> dict[str, Any]:
        """Return a minimal provider-facing tool declaration.

        The provider receives names, descriptions and input schemas only. Local
        policy flags remain in My Scoope and are not presented as something the
        model can override.
        """

        return {
            "name": self.name,
            "description": self.description,
            "parameters": dict(self.input_schema),
        }


def _normalize_text(value: Any) -> str:
    return " ".join(str(value or "").split())


def _normalize_identifier(value: Any) -> str:
    return _normalize_text(value).replace("-", "_").replace(" ", "_").lower()


def _coerce_enum(enum_class: type[Enum], value: Any, *, field_name: str) -> Enum:
    if isinstance(value, enum_class):
        return value
    try:
        return enum_class(str(value))
    except ValueError as exc:
        allowed = ", ".join(member.value for member in enum_class)
        raise AssistantToolRegistryError(
            f"Invalid {field_name}: {value!r}. Allowed values: {allowed}."
        ) from exc
