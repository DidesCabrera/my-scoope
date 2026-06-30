from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class PlanIterationTrace:
    """Serializable trace of an AI-generated DailyPlan revision.

    Patch 13 stores the raw metadata in ``current_snapshot['iteration']`` and
    ``validation_summary['chat_iteration']``. This helper gives UI, tests and
    future API/MCP surfaces a stable, defensive representation without coupling
    templates to raw JSON shapes.
    """

    previous_proposal_id: int | None
    user_message: str
    command_labels: list[str]
    command_count: int

    @property
    def has_commands(self) -> bool:
        return bool(self.command_labels)

    @property
    def short_label(self) -> str:
        if not self.command_labels:
            return "Propuesta actualizada"

        visible = self.command_labels[:2]
        label = " · ".join(visible)
        hidden_count = len(self.command_labels) - len(visible)
        if hidden_count > 0:
            label += f" · +{hidden_count}"
        return label

    def as_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["has_commands"] = self.has_commands
        payload["short_label"] = self.short_label
        return payload


def extract_plan_iteration_trace(source: Any) -> PlanIterationTrace | None:
    """Return normalized iteration metadata from a model object or DTO dict."""

    metadata = _extract_iteration_metadata(source)
    if not metadata:
        return None

    command_labels = _normalize_labels(metadata.get("command_labels"))
    command_count = _extract_command_count(metadata, fallback=len(command_labels))
    user_message = _safe_str(metadata.get("user_message"))
    previous_proposal_id = _safe_int_or_none(metadata.get("previous_proposal_id"))

    if not any([command_labels, user_message, previous_proposal_id]):
        return None

    return PlanIterationTrace(
        previous_proposal_id=previous_proposal_id,
        user_message=user_message,
        command_labels=command_labels,
        command_count=command_count,
    )


def _extract_iteration_metadata(source: Any) -> dict[str, Any]:
    current_snapshot = _safe_dict(_read_value(source, "current_snapshot"))
    metadata = _safe_dict(current_snapshot.get("iteration"))
    if metadata:
        return metadata

    validation_summary = _safe_dict(_read_value(source, "validation_summary"))
    return _safe_dict(validation_summary.get("chat_iteration"))


def _extract_command_count(metadata: dict[str, Any], *, fallback: int) -> int:
    command_set = _safe_dict(metadata.get("command_set"))
    commands = command_set.get("commands")
    if isinstance(commands, list):
        return len(commands)

    return fallback


def _read_value(source: Any, key: str) -> Any:
    if isinstance(source, dict):
        return source.get(key)

    return getattr(source, key, None)


def _normalize_labels(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []

    labels = []
    for item in value:
        label = _safe_str(item).strip()
        if label:
            labels.append(label)
    return labels


def _safe_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value

    return {}


def _safe_str(value: Any) -> str:
    if isinstance(value, str):
        return " ".join(value.strip().split())

    if value is None:
        return ""

    return " ".join(str(value).strip().split())


def _safe_int_or_none(value: Any) -> int | None:
    if isinstance(value, bool):
        return None

    if isinstance(value, int):
        return value

    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())

    return None
