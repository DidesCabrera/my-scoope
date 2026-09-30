from __future__ import annotations

from typing import Any

ASSISTANT_PROMPT_CONTRACT_VERSION = "ai_assistant_prompt.v4"

_SYSTEM_OUTCOME_CONTRACT_LINES = (
    "active_work guía continuidad; nunca autoriza escrituras ni omite confirmaciones.",
    "Si pide una propuesta nutricional y no hay blocking_fields, créala con la tool; no sólo la anuncies.",
    "Consultas: lectura. Cambios persistentes: patch revisable, nunca commit directo.",
    "Detente al cumplir active_work.expected_outcome; no agregues preguntas genéricas.",
)

_DEVELOPER_OUTCOME_RULES = {
    "objective_inference_never_grants_write_authority": True,
    "queries_use_read_tools_not_workspace_patches": True,
    "persistent_changes_are_prepared_for_trusted_ui_review": True,
}

_OUTCOME_CONTRACT = {
    "response_only": "answer_naturally_without_unneeded_tool_calls",
    "workspace_query": "return_grounded_information_from_a_successful_read",
    "workspace_advanced": "record_or_share_the_requested_conversation_state",
    "nutrition_proposal": "create_a_reviewable_nutrition_proposal",
    "prepared_patch": "prepare_a_reviewable_patch_without_committing_it",
    "clarification_required": "ask_only_for_materially_blocking_information",
}


def system_outcome_contract_lines() -> tuple[str, ...]:
    return _SYSTEM_OUTCOME_CONTRACT_LINES


def developer_outcome_contract_policy() -> dict[str, Any]:
    return {
        "prompt_contract_version": ASSISTANT_PROMPT_CONTRACT_VERSION,
        "outcome_contract": dict(_OUTCOME_CONTRACT),
    }


def developer_outcome_contract_rules() -> dict[str, bool]:
    return dict(_DEVELOPER_OUTCOME_RULES)
