from __future__ import annotations

from pathlib import Path
from typing import Any

from django.conf import settings

from core.document_registry import DocumentEntry, build_document_registry
from core.product_portfolio import load_product_portfolio
from core.project_status import build_project_status
from core.transition_registry import load_transition_registry

TASK_MODES = {
    "consult": {
        "destination": "local",
        "fresh_checkout": False,
        "remote_refresh": False,
        "validation": "none unless a claim needs a focused executable check",
    },
    "iterate": {
        "destination": "local",
        "fresh_checkout": True,
        "remote_refresh": "once when the task checkout is created",
        "validation": "focused checks owned by the changed risk",
    },
    "integrate": {
        "destination": "staging",
        "fresh_checkout": True,
        "remote_refresh": "before integration and again immediately before publication",
        "validation": "changed-path tier: docs, mobile, staging-fast, or full",
    },
    "production": {
        "destination": "production",
        "fresh_checkout": True,
        "remote_refresh": "before integration and before the staging-to-main boundary",
        "validation": "full repository gate before main plus deployment evidence after merge",
    },
}


def build_ai_project_context(
    *, domain: str = "", include_database: bool = True, decision_limit: int = 12,
) -> dict[str, Any]:
    root = Path(settings.BASE_DIR)
    status = build_project_status(include_database=include_database).as_dict()
    registry = build_document_registry(root)
    cycle_groups = _group_cycles(
        [entry for entry in registry.entries if entry.kind == "cycle"]
    )
    live_cycles = [
        *cycle_groups["active"],
        *cycle_groups["planned"],
        *cycle_groups["paused"],
        *cycle_groups["external_evidence_pending"],
    ]
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
        # Compatibility field for existing clients. New consumers should use
        # cycle_groups so completed work is not presented as active delivery.
        "live_cycles": [_document_summary(entry) for entry in live_cycles],
        "cycle_groups": {
            name: [_document_summary(entry) for entry in entries]
            for name, entries in cycle_groups.items()
        },
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


def build_ai_task_packet(
    *,
    task_mode: str,
    domain: str = "",
    surface: str = "",
    include_database: bool = True,
    decision_limit: int = 5,
) -> dict[str, Any]:
    if task_mode not in TASK_MODES:
        raise ValueError(f"Unknown task mode: {task_mode}")

    context = build_ai_project_context(
        domain=domain,
        include_database=include_database,
        decision_limit=decision_limit,
    )
    cycle_groups = context["cycle_groups"]
    transitions = context["transitions"]
    if domain:
        transitions = [item for item in transitions if item["owner"] == domain]

    def relevant(items: list[dict[str, str]], limit: int) -> list[dict[str, str]]:
        if domain:
            items = [item for item in items if item["domain"] == domain]
        return items[:limit]

    project_status = context["project_status"]
    environment = project_status["environment"]
    return {
        "contract": "myscoope.ai_task_packet.v1",
        "task": {
            "mode": task_mode,
            "domain": domain or "cross_cutting",
            "surface": surface or "unspecified",
        },
        "workflow": TASK_MODES[task_mode],
        "navigation": {
            "entrypoint": "docs/00_current/AI_README.md",
            "current_state": "docs/00_current/PROJECT_STATE.md",
            "validation_authority": "docs/40_technical/operations/testing_and_ci_policy.md",
            "instruction_boundary": "AGENTS.md",
        },
        "attention": environment["attention"],
        "environment": {
            "name": environment["name"],
            "status": environment["status"],
        },
        "cycles": {
            "active": relevant(cycle_groups["active"], 5),
            "planned": relevant(cycle_groups["planned"], 3),
            "external_evidence_pending": relevant(
                cycle_groups["external_evidence_pending"], 5
            ),
        },
        "decisions": context["decisions"],
        "transitions": [
            {
                "id": item["id"],
                "status": item["status"],
                "owner": item["owner"],
                "purpose": item["purpose"],
            }
            for item in transitions
        ],
        "product_bets": [
            {
                "id": item["id"],
                "title": item["title"],
                "stage": item["stage"],
                "next_experiment": item["next_experiment"],
            }
            for item in (context["product_bets"] if not domain else [])
        ],
        "registry_health": context["registry_health"],
    }


def _group_cycles(entries: list[DocumentEntry]) -> dict[str, list[DocumentEntry]]:
    groups: dict[str, list[DocumentEntry]] = {
        "active": [],
        "planned": [],
        "paused": [],
        "external_evidence_pending": [],
        "completed": [],
    }
    for entry in entries:
        if entry.status_class in {"active", "planned", "paused"}:
            groups[entry.status_class].append(entry)
        elif _has_external_evidence_pending(entry):
            groups["external_evidence_pending"].append(entry)
        elif entry.status_class == "completed":
            groups["completed"].append(entry)
    return groups


def _has_external_evidence_pending(entry: DocumentEntry) -> bool:
    status = entry.status.lower()
    return "pending" in status or "gated" in status


def _document_summary(entry: DocumentEntry) -> dict[str, str]:
    return {
        "id": entry.identifier, "title": entry.title, "status": entry.status,
        "status_class": entry.status_class, "domain": entry.domain, "path": entry.path,
    }

