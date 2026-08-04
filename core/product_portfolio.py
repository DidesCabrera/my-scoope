from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from django.conf import settings

VALID_STAGES = {"explore", "build", "validate", "scale", "maintain", "planned", "paused"}
VALID_REVERSIBILITY = {"low", "medium", "high"}


@dataclass(frozen=True)
class ProductBet:
    identifier: str
    title: str
    stage: str
    problem: str
    hypothesis: str
    evidence: tuple[str, ...]
    next_experiment: str
    continue_signals: tuple[str, ...]
    reformulate_signals: tuple[str, ...]
    dependencies: tuple[str, ...]
    reversibility: str

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "ProductBet":
        return cls(
            identifier=str(payload.get("id", "")), title=str(payload.get("title", "")),
            stage=str(payload.get("stage", "")), problem=str(payload.get("problem", "")),
            hypothesis=str(payload.get("hypothesis", "")),
            evidence=tuple(str(item) for item in payload.get("evidence", [])),
            next_experiment=str(payload.get("next_experiment", "")),
            continue_signals=tuple(str(item) for item in payload.get("continue_signals", [])),
            reformulate_signals=tuple(str(item) for item in payload.get("reformulate_signals", [])),
            dependencies=tuple(str(item) for item in payload.get("dependencies", [])),
            reversibility=str(payload.get("reversibility", "")),
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.identifier, "title": self.title, "stage": self.stage,
            "problem": self.problem, "hypothesis": self.hypothesis,
            "evidence": list(self.evidence), "next_experiment": self.next_experiment,
            "continue_signals": list(self.continue_signals),
            "reformulate_signals": list(self.reformulate_signals),
            "dependencies": list(self.dependencies), "reversibility": self.reversibility,
        }


def load_product_portfolio(root: Path | None = None) -> tuple[ProductBet, ...]:
    project_root = root or Path(settings.BASE_DIR)
    path = project_root / "docs/00_current/product_portfolio.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    return tuple(ProductBet.from_dict(item) for item in payload["bets"])


def validate_product_portfolio(root: Path | None = None) -> list[str]:
    bets = load_product_portfolio(root)
    errors = []
    identifiers = [bet.identifier for bet in bets]
    if len(identifiers) != len(set(identifiers)):
        errors.append("Product bet identifiers must be unique.")
    for bet in bets:
        if not all((bet.identifier, bet.title, bet.problem, bet.hypothesis, bet.next_experiment)):
            errors.append(f"Product bet {bet.identifier or '<missing>'} lacks required context.")
        if bet.stage not in VALID_STAGES:
            errors.append(f"Product bet {bet.identifier} has invalid stage {bet.stage}.")
        if bet.reversibility not in VALID_REVERSIBILITY:
            errors.append(f"Product bet {bet.identifier} has invalid reversibility {bet.reversibility}.")
        if not bet.evidence or not bet.continue_signals or not bet.reformulate_signals:
            errors.append(f"Product bet {bet.identifier} lacks evidence or decision signals.")
    return errors

