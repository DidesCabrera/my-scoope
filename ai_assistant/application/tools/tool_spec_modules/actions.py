from __future__ import annotations

from ai_assistant.application.tools.contracts import (
    AssistantToolCategory,
    AssistantToolRiskLevel,
    AssistantToolSpec,
)
from ai_assistant.application.tools.tool_names import *  # noqa: F403


ACTIONS_TOOL_SPECS = {
TOOL_PREPARE_PRODUCT_ACTION: AssistantToolSpec(
        name=TOOL_PREPARE_PRODUCT_ACTION,
        description=(
            "Prepare a reviewable My Scoope product action without mutating its target. "
            "Use only after resolving an unambiguous owned target. The result contains a "
            "before/after preview and requires a trusted user confirmation in the UI."
        ),
        category=AssistantToolCategory.PROPOSAL,
        risk_level=AssistantToolRiskLevel.REVIEW_REQUIRED,
        allowed_intents=(
            "answer_question",
            "create_program_proposal",
            "iterate_proposal",
        ),
        input_schema={
            "type": "object",
            "required": ["action_key"],
            "properties": {
                "action_key": {
                    "type": "string",
                    "enum": [
                        "food.create",
                        "food.update",
                        "food.delete",
                        "meal.create",
                        "meal.rename",
                        "meal.delete",
                        "dailyplan.create",
                        "dailyplan.rename",
                        "dailyplan.delete",
                        "program.create",
                        "program.rename",
                        "program.delete",
                        "program.add_week",
                        "program.duplicate_week",
                        "program.remove_week",
                        "calendar.pause",
                        "calendar.resume",
                        "calendar.cancel",
                        "comparison.rename",
                        "proposal.approve",
                        "proposal.reject",
                        "proposal.cancel",
                        "proposal.delete",
                        "proposal.apply",
                    ],
                    "description": "Controlled product action to prepare.",
                },
                "target_id": {
                    "type": "integer",
                    "description": "Owned target ID; omit only for create actions.",
                },
                "parameters": {
                    "type": "object",
                    "description": "Action-specific values used to build the preview.",
                },
            },
        },
    ),
TOOL_COMMIT_PREPARED_ACTION: AssistantToolSpec(
        name=TOOL_COMMIT_PREPARED_ACTION,
        description="Commit one prepared action after a trusted server-side user confirmation.",
        category=AssistantToolCategory.COMMIT,
        risk_level=AssistantToolRiskLevel.REVIEW_REQUIRED,
        provider_exposed=False,
        input_schema={
            "type": "object",
            "required": ["prepared_action_id"],
            "properties": {
                "prepared_action_id": {"type": "string"},
            },
        },
    ),
}

__all__ = ["ACTIONS_TOOL_SPECS"]
