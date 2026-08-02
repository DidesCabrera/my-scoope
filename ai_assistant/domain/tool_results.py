"""Provider-neutral result contract shared by AI tool adapters."""

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class AIToolError:
    code: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class AIToolResult:
    ok: bool
    data: dict[str, Any] = field(default_factory=dict)
    error: AIToolError | None = None

    def as_dict(self) -> dict:
        return {
            "ok": self.ok,
            "data": self.data,
            "error": self.error.as_dict() if self.error else None,
        }


def tool_success(data: dict[str, Any] | None = None) -> AIToolResult:
    return AIToolResult(ok=True, data=data or {}, error=None)


def tool_error(
    *,
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> AIToolResult:
    return AIToolResult(
        ok=False,
        data={},
        error=AIToolError(code=code, message=message, details=details or {}),
    )
