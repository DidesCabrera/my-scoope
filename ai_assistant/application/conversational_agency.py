from __future__ import annotations

from typing import Any

ASSISTANT_CONVERSATIONAL_AGENCY_VERSION = "ai_assistant_conversational_agency.v1"


def developer_goal_directed_agency_policy() -> dict[str, Any]:
    """Return the compact provider contract for BA04 conversational progress."""

    return {
        "version": ASSISTANT_CONVERSATIONAL_AGENCY_VERSION,
        "active_objective": True,
        "advance_means_progress": True,
        "ready_work_prefers_proposal": True,
        "blocking_info_only": True,
        "no_fixed_flow_or_parser": True,
    }
