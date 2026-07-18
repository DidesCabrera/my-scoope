from __future__ import annotations

from pathlib import Path

from django.conf import settings

from core.document_registry import DocumentEntry, build_document_registry
from core.product_portfolio import load_product_portfolio
from core.project_status import build_project_status
from core.transition_registry import load_transition_registry


def build_ai_project_context(
    *, domain: str = "", include_database: bool = True, decision_limit: int = 12,
) -> dict[str, object]:
    root = Path(settings.BASE_DIR)
    status = build_project_status(include_database=include_database).as_dict()
    registry = build_document_registry(root)
    cycles = [entry for entry in registry.entries if entry.kind == "cycle" and _is_live_cycle(entry)]
    decisions = [entry for entry in registry.entries if entry.kind == "decision"]
    if domain:
        decisions = [entry for entry in decisions if entry.domain == domain]
    decisions = sorted(decisions, key=lambda entry: entry.identifier, reverse=True)[:decision_limit]

    return {
        "contract": "myscoope.ai_project_context.v1",
        "client_posture": {
            "ai_is_current_client": True,
            "guidance": (
                "Use project context, objectives, capabilities, feedback, and important boundaries "
                "to exercise judgment; do not turn them into a fixed reasoning script."
            ),
            "welcome_path": "docs/00_current/AI_README.md",
        },
        "source_contracts": {
            "project_status": status["contract"],
            "documents": registry.as_dict()["contract"],
            "transitions": "myscoope.transition_registry.v1",
            "portfolio": "myscoope.product_portfolio.v1",
        },
        "project_status": status,
        "live_cycles": [_document_summary(entry) for entry in cycles],
        "decisions": [_document_summary(entry) for entry in decisions],
        "transitions": [
            {
                "id": entry.identifier, "status": entry.status, "owner": entry.owner,
                "purpose": entry.purpose, "exit_evidence": list(entry.exit_evidence),
                "decision": entry.decision,
            }
            for entry in load_transition_registry(root)
        ],
        "product_bets": [
            {
                "id": bet.identifier, "title": bet.title, "stage": bet.stage,
                "hypothesis": bet.hypothesis, "current_evidence": list(bet.evidence),
                "next_experiment": bet.next_experiment,
                "continue_signals": list(bet.continue_signals),
                "reformulate_signals": list(bet.reformulate_signals),
            }
            for bet in load_product_portfolio(root)
        ],
        "registry_health": {"valid": registry.valid, "finding_count": len(registry.findings)},
        "filters": {"domain": domain or "recent_cross_domain", "decision_limit": decision_limit},
    }


def _is_live_cycle(entry: DocumentEntry) -> bool:
    status = entry.status.lower()
    return entry.status_class in {"active", "planned", "paused"} or "pending" in status or "gated" in status


def _document_summary(entry: DocumentEntry) -> dict[str, str]:
    return {
        "id": entry.identifier, "title": entry.title, "status": entry.status,
        "status_class": entry.status_class, "domain": entry.domain, "path": entry.path,
    }

