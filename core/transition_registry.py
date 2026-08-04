from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from django.conf import settings

VALID_TRANSITION_STATUSES = {"transitional", "intentionally_durable"}


@dataclass(frozen=True)
class TransitionEntry:
    identifier: str
    status: str
    owner: str
    purpose: str
    current_consumers: tuple[str, ...]
    exit_evidence: tuple[str, ...]
    decision: str

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "TransitionEntry":
        return cls(
            identifier=str(payload.get("id", "")),
            status=str(payload.get("status", "")),
            owner=str(payload.get("owner", "")),
            purpose=str(payload.get("purpose", "")),
            current_consumers=tuple(str(item) for item in payload.get("current_consumers", [])),
            exit_evidence=tuple(str(item) for item in payload.get("exit_evidence", [])),
            decision=str(payload.get("decision", "")),
        )


def load_transition_registry(root: Path | None = None) -> tuple[TransitionEntry, ...]:
    project_root = root or Path(settings.BASE_DIR)
    path = project_root / "docs/00_current/architecture/transition_registry.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    return tuple(TransitionEntry.from_dict(item) for item in payload["transitions"])


def validate_transition_registry(root: Path | None = None) -> list[str]:
    project_root = root or Path(settings.BASE_DIR)
    entries = load_transition_registry(project_root)
    errors = []
    identifiers = [entry.identifier for entry in entries]
    if len(identifiers) != len(set(identifiers)):
        errors.append("Transition identifiers must be unique.")
    for entry in entries:
        if not entry.identifier or not entry.owner or not entry.purpose:
            errors.append(f"Transition {entry.identifier or '<missing>'} lacks identity, owner, or purpose.")
        if entry.status not in VALID_TRANSITION_STATUSES:
            errors.append(f"Transition {entry.identifier} has invalid status {entry.status}.")
        if not entry.current_consumers:
            errors.append(f"Transition {entry.identifier} lacks current consumers.")
        if not entry.exit_evidence:
            errors.append(f"Transition {entry.identifier} lacks exit evidence.")
        if not (project_root / entry.decision).exists():
            errors.append(f"Transition {entry.identifier} references missing decision {entry.decision}.")
    return errors

