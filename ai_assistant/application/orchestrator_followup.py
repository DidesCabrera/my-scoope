from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import replace
from typing import Any

from ai_assistant.application.context_builder import sanitize_provider_context
from ai_assistant.application.limits import estimate_provider_request_tokens
from ai_assistant.application.model_routing import AIModelRoute, resolve_model_route_for_turn
from ai_assistant.application.orchestrator_helpers import (
    _output_tokens_for_request,
    _provider_tool_by_name,
    _provider_tool_outputs,
)
from ai_assistant.application.program_capture import weekly_capture_instruction, weekly_specification_missing
from ai_assistant.application.tool_selection import next_intake_presentation_tool
from ai_assistant.application.tools import (
    TOOL_CREATE_NUTRITION_ENGINE_DAILYPLAN_PROPOSAL_FROM_DRAFTS,
    TOOL_READ_PROPOSAL,
    TOOL_UPDATE_PROFILE_DRAFT,
    TOOL_UPDATE_PROPOSAL_PREFERENCES,
)
from ai_assistant.domain import AssistantToolResult, AssistantTurnRequest
from ai_assistant.infrastructure.providers import LLMMessage, LLMProviderRequest


def build_tool_followup_provider_request(
    orchestrator: Any,
    *,
    request: AssistantTurnRequest,
    continuation_items: Sequence[Mapping[str, Any]],
    tool_results: Sequence[AssistantToolResult],
    accumulated_tool_results: Sequence[AssistantToolResult] | None = None,
    model_route: AIModelRoute | None = None,
    remaining_tool_iterations: int = 0,
) -> LLMProviderRequest:
    """Continue one stateless native function-call loop."""

    model_route = model_route or resolve_model_route_for_turn(request)
    base_request = orchestrator.build_provider_request(request, model_route=model_route)
    max_output_tokens = _output_tokens_for_request(
        request=request,
        default_max_output_tokens=orchestrator.config.max_output_tokens,
        route=model_route,
    )
    tools = tuple(base_request.tools or ()) if remaining_tool_iterations > 0 else ()
    tool_choice: str | Mapping[str, Any] | None = "auto" if tools else None
    decision_results = tuple(accumulated_tool_results or tool_results)
    presentation_tool_name = next_intake_presentation_tool(request, decision_results)
    capture_tool_name = orchestrator._fact_capture_tool_after_tool_results(
        request,
        decision_results,
    )
    if tools and capture_tool_name:
        tools, tool_choice = _select_exact_tool(
            tools,
            capture_tool_name,
            fallback_choice=tool_choice,
        )
    elif tools and presentation_tool_name:
        tools, tool_choice = _select_exact_tool(
            tools,
            presentation_tool_name,
            fallback_choice=tool_choice,
        )
    elif tools and not tool_results_complete_nutrition_proposal(decision_results) and orchestrator._proposal_ready_after_tool_results(
        request,
        decision_results,
    ):
        proposal_tool = _provider_tool_by_name(
            orchestrator.provider_tool_specs(),
            TOOL_CREATE_NUTRITION_ENGINE_DAILYPLAN_PROPOSAL_FROM_DRAFTS,
        )
        if proposal_tool is not None:
            tools = (proposal_tool,)
            tool_choice = _named_function_tool_choice(
                TOOL_CREATE_NUTRITION_ENGINE_DAILYPLAN_PROPOSAL_FROM_DRAFTS
            )
    elif _tool_results_satisfy_or_end_objective(request, decision_results):
        tools = ()
        tool_choice = None

    messages = list(base_request.messages)
    if len(messages) >= 2:
        messages[1] = LLMMessage(
            role="developer",
            content=orchestrator._developer_prompt(tools),
        )
    if request.context and len(messages) >= 3:
        messages[2] = LLMMessage(
            role="developer",
            content=compact_context_prompt(request.context),
        )

    tool_outputs = _provider_tool_outputs(tool_results)
    if weekly_specification_missing(request, decision_results):
        messages.append(LLMMessage(role="developer", content=weekly_capture_instruction(request)))
    estimated_request = LLMProviderRequest(
        messages=messages,
        max_output_tokens=max_output_tokens,
        tools=tools,
        continuation_items=tuple(continuation_items or ()),
        tool_outputs=tool_outputs,
    )
    followup = LLMProviderRequest(
        messages=messages,
        max_output_tokens=max_output_tokens,
        metadata={
            "engine": orchestrator.config.engine_name,
            "format": orchestrator.config.response_format_version,
            "tool_loop": "native_function_calls.v1",
            "tool_results_count": len(tuple(tool_results or ())),
            "model_route": model_route.as_metadata(),
            "reasoning_effort": orchestrator.config.reasoning_effort,
            "estimated_input_tokens": estimate_provider_request_tokens(estimated_request),
        },
        tools=tools,
        tool_choice=tool_choice,
        parallel_tool_calls=False if tools else None,
        max_tool_calls=(
            orchestrator.config.turn_limits.max_tool_requests_per_turn if tools else None
        ),
        continuation_items=tuple(continuation_items or ()),
        tool_outputs=tool_outputs,
    )
    return _compact_pending_proposal_followup(orchestrator, followup, decision_results)


def _compact_pending_proposal_followup(orchestrator, followup, results):
    """Keep pending typed capture/creation executable when history exceeds budget.

    The executor retains all original results and enriches arguments from them.
    Only duplicate transport history is replaced; the user request, policies,
    exact tool choice, and the latest complete typed drafts remain available.
    The caller still validates the resulting request against the same limit.
    """
    choice = followup.tool_choice
    pending_tools = {TOOL_CREATE_NUTRITION_ENGINE_DAILYPLAN_PROPOSAL_FROM_DRAFTS,
                     TOOL_UPDATE_PROFILE_DRAFT, TOOL_UPDATE_PROPOSAL_PREFERENCES}
    if not isinstance(choice, Mapping) or choice.get("name") not in pending_tools:
        return followup
    if estimate_provider_request_tokens(followup) <= orchestrator.config.turn_limits.max_input_tokens:
        return followup
    drafts = {}
    for result in results:
        if result.ok:
            for key in ("profile_draft", "preference_draft", "proposal_preferences"):
                candidate = dict(result.data or {}).get(key)
                if isinstance(candidate, Mapping):
                    drafts[key] = dict(candidate)
    messages = (*followup.messages, LLMMessage(role="developer", content=json.dumps({
        "latest_typed_drafts": sanitize_provider_context(drafts),
        "instruction": "Estos son los drafts vigentes capturados por herramientas. La propuesta aún no existe; completa la captura tipada pendiente y la creación revisable solicitada. No la apliques.",
    }, ensure_ascii=False)))
    compact = replace(followup, messages=messages, continuation_items=(), tool_outputs=())
    import logging

    logging.getLogger("myscoope.assistant.runtime").info("tool_history_compacted pending=%s", choice.get("name"))
    return replace(compact, metadata={**dict(compact.metadata),
        "tool_loop": "controlled_tools.pending_proposal_followup.v1",
        "estimated_input_tokens": estimate_provider_request_tokens(compact)})


def compact_context_prompt(context: Mapping[str, Any]) -> str:
    """Preserve operational memory while removing duplicated display context."""

    safe_context = sanitize_provider_context(context)
    metadata = dict(safe_context.get("metadata") or {})
    workspace = dict(metadata.get("tool_oriented_intake") or {})
    conversation = dict(safe_context.get("conversation") or {})
    compact_workspace = {
        key: workspace[key]
        for key in ("version", "current_drafts", "work_progress", "work_context")
        if key in workspace
    }
    compact_conversation = {
        key: conversation[key]
        for key in ("message_count", "recent_chat_objects", "last_shared_object")
        if key in conversation
    }
    payload = {
        "my_scoope_workspace": {
            "surface": safe_context.get("surface"),
            "conversation": compact_conversation,
            "metadata": {"tool_oriented_intake": compact_workspace},
        },
        "instruction": (
            "Los drafts y work_progress son la memoria vigente. Usa blocking_fields "
            "como única carencia obligatoria y los resultados de tools como verdad."
        ),
        "context_compacted_to_fit_technical_limit": True,
    }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def _select_exact_tool(
    tools: Sequence[Mapping[str, Any]],
    tool_name: str,
    *,
    fallback_choice: str | Mapping[str, Any] | None,
) -> tuple[tuple[Mapping[str, Any], ...], str | Mapping[str, Any] | None]:
    selected = _provider_tool_by_name(tools, tool_name)
    if selected is None:
        return tuple(tools), fallback_choice
    return (selected,), _named_function_tool_choice(tool_name)


def _named_function_tool_choice(tool_name: str) -> Mapping[str, str]:
    return {"type": "function", "name": tool_name}


def _tool_results_satisfy_or_end_objective(
    request: AssistantTurnRequest,
    tool_results: Sequence[AssistantToolResult],
) -> bool:
    results = tuple(tool_results or ())
    if any(
        result.tool_name == TOOL_READ_PROPOSAL and result.error_code == "not_found"
        for result in results
    ):
        return True
    successful = {result.tool_name for result in results if result.ok}
    if not successful:
        return False
    if any(name.startswith("share_") for name in successful):
        return True
    workspace = dict((request.context.get("metadata") or {}).get("tool_oriented_intake") or {})
    progress = dict(workspace.get("work_progress") or {})
    active_work = dict(progress.get("active_work") or {})
    expected = str(active_work.get("expected_outcome") or "")
    if expected == "workspace_query":
        return any(
            name.startswith(("query_", "read_", "list_", "search_", "compare_"))
            for name in successful
        )
    if expected == "prepared_patch":
        return bool(
            successful.intersection({"propose_workspace_patch", "prepare_product_action"})
        )
    if expected == "nutrition_proposal":
        return tool_results_complete_nutrition_proposal(results)
    if expected == "workspace_advanced":
        return any(name.startswith(("update_", "share_")) for name in successful)
    return False


def tool_results_complete_nutrition_proposal(
    tool_results: Sequence[AssistantToolResult],
) -> bool:
    """Return whether a typed result already created the requested proposal."""

    return any(
        result.ok
        and result.tool_name.startswith(("create_nutrition_", "create_validated_"))
        for result in tuple(tool_results or ())
    )


__all__ = [
    "build_tool_followup_provider_request",
    "compact_context_prompt",
    "tool_results_complete_nutrition_proposal",
]
