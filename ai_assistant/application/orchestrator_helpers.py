from __future__ import annotations

import json
from typing import Any, Mapping, Sequence

from ai_assistant.application.context_builder import sanitize_provider_context
from ai_assistant.application.model_routing import AIModelRoute, route_max_output_tokens
from ai_assistant.application.provider_parsing import AssistantProviderParseResult
from ai_assistant.application.tool_governance import (
    extract_provider_tool_selection_reason,
    safe_tool_selection_observability,
)
from ai_assistant.application.tools import (
    TOOL_CREATE_NUTRITION_ENGINE_DAILYPLAN_PROPOSAL_FROM_DRAFTS,
    TOOL_READ_PROPOSAL,
    TOOL_SHARE_PREFERENCE_DRAFT_CARD,
    TOOL_SHARE_PROFILE_DRAFT_CARD,
    TOOL_SHARE_PROPOSAL_PREFERENCES_CARD,
    TOOL_UPDATE_PREFERENCE_DRAFT,
    TOOL_UPDATE_PROFILE_DRAFT,
    TOOL_UPDATE_PROPOSAL_PREFERENCES,
)
from ai_assistant.domain import (
    AssistantIntent,
    AssistantIntentName,
    AssistantToolRequest,
    AssistantToolResult,
    AssistantToolStatus,
    AssistantTurnRequest,
)
from ai_assistant.infrastructure.providers import (
    LLMProviderError,
    LLMProviderResponse,
    LLMProviderToolCall,
    LLMProviderToolOutput,
)


def _intake_workspace(context: Mapping[str, Any]) -> dict[str, Any]:
    metadata = dict((context or {}).get("metadata") or {})
    workspace = metadata.get("tool_oriented_intake")
    return dict(workspace) if isinstance(workspace, Mapping) else {}


def _intake_work_progress(context: Mapping[str, Any]) -> dict[str, Any]:
    progress = _intake_workspace(context).get("work_progress")
    return dict(progress) if isinstance(progress, Mapping) else {}


def _work_progress_has_active_proposal_objective(
    work_progress: Mapping[str, Any],
) -> bool:
    return str(work_progress.get("active_objective") or "") in {
        "create_reviewable_dailyplan_proposal",
        "create_dailyplan_proposal",
    }


def _requests_existing_product_operation(user_text: str) -> bool:
    text = f" {str(user_text or '').strip().lower()} "
    identifies_existing_object = any(
        marker in text
        for marker in (
            " mi plan ",
            " este plan ",
            " dailyplan ",
            " propuesta ",
            " programa ",
            " calendario ",
        )
    )
    requests_change_or_lookup = any(
        marker in text
        for marker in (
            " cambia ",
            " cambiar ",
            " ajusta ",
            " ajustar ",
            " aumenta ",
            " aumentar ",
            " reduce ",
            " reducir ",
            " renombra ",
            " elimina ",
            " borra ",
            " busca ",
            " muestra ",
            " revisa ",
            " compara ",
            " aplica ",
            " aprueba ",
            " rechaza ",
        )
    )
    return identifies_existing_object and requests_change_or_lookup


def _provider_tool_by_name(
    tools: Sequence[Mapping[str, Any]],
    tool_name: str,
) -> Mapping[str, Any] | None:
    return next(
        (
            tool
            for tool in tuple(tools or ())
            if str(tool.get("name") or "") == tool_name
        ),
        None,
    )



def _output_tokens_for_request(
    *,
    request: AssistantTurnRequest,
    default_max_output_tokens: int | None,
    route: AIModelRoute,
) -> int | None:
    """Resolve output budget while keeping CM24's diagnostic cap explicit."""

    if bool(request.metadata.get("cm24_validation")):
        return default_max_output_tokens
    return route_max_output_tokens(
        default_max_output_tokens=default_max_output_tokens,
        route=route,
    )


def _provider_incomplete_reason(provider_response: LLMProviderResponse) -> str:
    raw = dict(provider_response.raw or {})
    if str(raw.get("status") or "").strip().lower() != "incomplete":
        return ""
    details = raw.get("incomplete_details")
    if isinstance(details, Mapping):
        return str(details.get("reason") or "incomplete")[:80]
    return "incomplete"


def _coerce_provider_tool_calls(
    tool_calls: Sequence[LLMProviderToolCall],
) -> tuple[tuple[AssistantToolRequest, ...], str]:
    requests: list[AssistantToolRequest] = []
    for index, call in enumerate(tuple(tool_calls or ()), start=1):
        if call.parse_error:
            return (), f"native_tool_call_{index}:{call.parse_error}"
        if not call.name:
            return (), f"native_tool_call_{index}:missing_function_name"
        local_arguments, selection_reason, selection_metadata = extract_provider_tool_selection_reason(
            _without_none_values(call.arguments),
            tool_name=call.name,
        )
        requests.append(
            AssistantToolRequest(
                tool_name=call.name,
                arguments=local_arguments,
                request_id=call.call_id or f"native_tool_call_{index}",
                reason=selection_reason,
                metadata={
                    "provider_transport": "native_function_call.v1",
                    **selection_metadata,
                },
            )
        )
    return tuple(requests), ""


def _without_none_values(value: Mapping[str, Any]) -> dict[str, Any]:
    def clean(item: Any) -> Any:
        if isinstance(item, Mapping):
            return {str(key): clean(child) for key, child in item.items() if child is not None}
        if isinstance(item, list | tuple):
            return [clean(child) for child in item if child is not None]
        return item

    return clean(dict(value or {}))


def _intent_for_native_tool_requests(
    tool_requests: Sequence[AssistantToolRequest],
) -> AssistantIntent:
    names = {request.tool_name for request in tuple(tool_requests or ())}
    if any(name.startswith("iterate_") for name in names):
        intent_name = AssistantIntentName.ITERATE_PROPOSAL
    elif any("dailyplan" in name and name.startswith("create_") for name in names):
        intent_name = AssistantIntentName.CREATE_DAILYPLAN_PROPOSAL
    elif any("meal" in name and name.startswith("create_") for name in names):
        intent_name = AssistantIntentName.CREATE_MEAL_PROPOSAL
    elif any(name.startswith("update_") or name.startswith("share_") for name in names):
        intent_name = AssistantIntentName.CAPTURE_NUTRITION_BRIEF
    elif names:
        intent_name = AssistantIntentName.READ_CONTEXT
    else:
        intent_name = AssistantIntentName.UNKNOWN
    return AssistantIntent(
        name=intent_name,
        confidence=0.8 if names else 0.0,
        summary="Provider-native function calls selected by the assistant.",
    )


def _provider_tool_outputs(
    tool_results: Sequence[AssistantToolResult],
) -> tuple[LLMProviderToolOutput, ...]:
    outputs: list[LLMProviderToolOutput] = []
    for result in tuple(tool_results or ()):
        if not result.request_id:
            continue
        outputs.append(
            LLMProviderToolOutput(
                call_id=result.request_id,
                output=sanitize_provider_context(result.as_dict()),
            )
        )
    return tuple(outputs)


def _provider_tool_output_items(
    tool_results: Sequence[AssistantToolResult],
) -> tuple[Mapping[str, Any], ...]:
    items: list[Mapping[str, Any]] = []
    for output in _provider_tool_outputs(tool_results):
        payload = output.output
        items.append(
            {
                "type": "function_call_output",
                "call_id": output.call_id,
                "output": (
                    json.dumps(payload, ensure_ascii=False, sort_keys=True)
                    if isinstance(payload, Mapping)
                    else str(payload or "")
                ),
            }
        )
    return tuple(items)


def _provider_response_requires_tool_call_repair(
    parse_result: AssistantProviderParseResult,
) -> bool:
    if parse_result.declared_tools_required:
        return True
    if parse_result.response.metadata.get("provider_native_tool_error"):
        return True
    operational_intents = {
        AssistantIntentName.CAPTURE_NUTRITION_BRIEF,
        AssistantIntentName.CREATE_MEAL_PROPOSAL,
        AssistantIntentName.CREATE_DAILYPLAN_PROPOSAL,
        AssistantIntentName.CREATE_PROGRAM_PROPOSAL,
        AssistantIntentName.ITERATE_PROPOSAL,
        AssistantIntentName.READ_CONTEXT,
    }
    return parse_result.response.intent.name in operational_intents


def _provider_response_needs_contract_repair(
    parse_result: AssistantProviderParseResult,
    provider_response: LLMProviderResponse,
    *,
    allow_initial_operational_intent_repair: bool = False,
) -> bool:
    if str(provider_response.provider or "").strip().lower() == "fake":
        return False
    if parse_result.response.tool_requests and not parse_result.parse_error:
        return False
    if parse_result.parse_error or _provider_incomplete_reason(provider_response):
        return True
    if parse_result.declared_tools_required:
        return True
    operational_intents = {
        AssistantIntentName.CAPTURE_NUTRITION_BRIEF,
        AssistantIntentName.CREATE_MEAL_PROPOSAL,
        AssistantIntentName.CREATE_DAILYPLAN_PROPOSAL,
        AssistantIntentName.CREATE_PROGRAM_PROPOSAL,
        AssistantIntentName.ITERATE_PROPOSAL,
        AssistantIntentName.READ_CONTEXT,
    }
    return bool(
        allow_initial_operational_intent_repair
        and parse_result.response.intent.name in operational_intents
    )


def _provider_declared_tools_required(payload: Mapping[str, Any]) -> bool:
    tool_plan = payload.get("tool_plan")
    return bool(tool_plan.get("required")) if isinstance(tool_plan, Mapping) else False


def _has_tool_results(tool_results: Sequence[AssistantToolResult]) -> bool:
    return bool(tuple(tool_results or ()))


def _has_ok_tool_results(tool_results: Sequence[AssistantToolResult]) -> bool:
    return any(result.ok for result in tuple(tool_results or ()))


def _provider_followup_error_metadata(error: LLMProviderError) -> dict[str, Any]:
    """Surface the preserved provider failure detail into turn metadata.

    Diagnostics only. This is recorded for audit/observability and the
    real-provider gate; it never changes the user-visible, state-only
    acknowledgement. When the error predates PT01 (no structured detail),
    this returns nothing and behavior is unchanged.
    """

    details = getattr(error, "provider_error_details", None)
    if not isinstance(details, Mapping):
        return {}
    return {
        "provider_tool_followup_error_status": details.get("status_code"),
        "provider_tool_followup_error_provider_type": str(details.get("error_type") or ""),
        "provider_tool_followup_error_code": str(details.get("error_code") or ""),
        "provider_tool_followup_error_message": str(details.get("error_message") or "")[:600],
        "provider_tool_followup_error_param": str(details.get("error_param") or "")[:120],
        "provider_tool_followup_error_request_id": str(details.get("request_id") or ""),
    }


def _local_acknowledgement_from_tool_results(tool_results: Sequence[AssistantToolResult]) -> str:
    """Acknowledge validated state without echoing fields or planning the dialogue.

    This path exists only when the provider cannot word the post-tool response.
    It reports a bounded product consequence, never recites card contents, never
    lists values the user just supplied and never selects the next question.
    """

    successful = [result for result in tuple(tool_results or ()) if result.ok]
    errors = [result for result in tuple(tool_results or ()) if not result.ok]
    successful_names = {result.tool_name for result in successful}

    statements: list[str] = []
    if TOOL_UPDATE_PROFILE_DRAFT in successful_names:
        statements.append("Los datos físicos quedaron actualizados para esta conversación.")
    if TOOL_UPDATE_PREFERENCE_DRAFT in successful_names:
        statements.append("Las preferencias alimentarias quedaron actualizadas para esta propuesta.")
    if TOOL_UPDATE_PROPOSAL_PREFERENCES in successful_names:
        statements.append("La dirección de la propuesta quedó actualizada.")

    if successful_names.intersection(
        {
            TOOL_SHARE_PROFILE_DRAFT_CARD,
            TOOL_SHARE_PREFERENCE_DRAFT_CARD,
            TOOL_SHARE_PROPOSAL_PREFERENCES_CARD,
        }
    ):
        statements.append("La información está disponible en la card para revisión.")

    if any(name.startswith("create_") for name in successful_names):
        statements.append("La propuesta quedó creada y disponible para revisión.")
    elif any(name.startswith("iterate_") for name in successful_names):
        statements.append("La propuesta quedó actualizada y disponible para revisión.")
    elif any(name.startswith(("compare_", "validate_", "preview_")) for name in successful_names):
        statements.append("El resultado quedó listo para revisión.")
    elif any(name.startswith(("read_", "list_", "search_")) for name in successful_names):
        statements.append("La información solicitada quedó disponible.")
    elif any(name.startswith(("commit_", "save_", "apply_")) for name in successful_names):
        statements.append("El cambio autorizado quedó guardado.")

    if statements:
        return " ".join(dict.fromkeys(statements))

    if errors:
        for result in errors:
            if result.tool_name == TOOL_READ_PROPOSAL and result.error_code == "not_found":
                return (
                    "No encontré una propuesta disponible con ese identificador. "
                    "Puede que no exista o que no esté visible para tu cuenta. No hice ningún cambio."
                )
        if all(result.tool_name.startswith(("read_", "list_", "search_")) for result in errors):
            return "No encontré esa información con los datos disponibles. No hice ningún cambio."
        return "No pude completar la operación con los datos disponibles. No apliqué ningún cambio."

    return "La información quedó actualizada para esta conversación."




DRAFT_TOOL_CONTEXT_ARGUMENTS = {
    TOOL_UPDATE_PROFILE_DRAFT: ("current_draft", "profile_draft"),
    TOOL_SHARE_PROFILE_DRAFT_CARD: ("profile_draft", "profile_draft"),
    TOOL_UPDATE_PREFERENCE_DRAFT: ("current_draft", "preference_draft"),
    TOOL_SHARE_PREFERENCE_DRAFT_CARD: ("preference_draft", "preference_draft"),
    TOOL_UPDATE_PROPOSAL_PREFERENCES: ("current_preferences", "proposal_preferences"),
    TOOL_SHARE_PROPOSAL_PREFERENCES_CARD: ("proposal_preferences", "proposal_preferences"),
}


def _enrich_draft_tool_request_from_context(
    request: AssistantToolRequest,
    *,
    context: Mapping[str, Any],
    prior_tool_results: Sequence[AssistantToolResult] = (),
) -> AssistantToolRequest:
    """Fill omitted draft arguments from current My Scoope state.

    In the LLM-led runtime, the model interprets user facts and chooses tools,
    but it should not have to resend the entire draft on every update. If the
    model requests `update_profile_draft({updates: {...}})` without
    `current_draft`, My Scoope must merge those updates into the known draft
    from the current safe context or previous tool results. Otherwise every
    partial update rewrites the card as if all prior fields were unknown.
    """

    if (
        request.tool_name
        == TOOL_CREATE_NUTRITION_ENGINE_DAILYPLAN_PROPOSAL_FROM_DRAFTS
    ):
        workspace = _intake_workspace(context)
        arguments = dict(request.arguments or {})
        for draft_key in (
            "profile_draft",
            "preference_draft",
            "proposal_preferences",
        ):
            if not isinstance(arguments.get(draft_key), Mapping):
                arguments[draft_key] = _latest_draft_for_tool(
                    draft_key,
                    context=context,
                    prior_tool_results=prior_tool_results,
                )
        if not isinstance(arguments.get("current_nutrition_brief"), Mapping):
            arguments["current_nutrition_brief"] = dict(
                workspace.get("current_nutrition_brief") or {}
            )
        arguments.setdefault("raw_prompt", "")
        metadata = dict(request.metadata or {})
        metadata["proposal_workspace_injected_from_context"] = True
        return AssistantToolRequest(
            tool_name=request.tool_name,
            arguments=arguments,
            request_id=request.request_id,
            reason=request.reason,
            metadata=metadata,
        )

    argument_name_and_key = DRAFT_TOOL_CONTEXT_ARGUMENTS.get(request.tool_name)
    if not argument_name_and_key:
        return request

    argument_name, draft_key = argument_name_and_key
    arguments = dict(request.arguments or {})
    if isinstance(arguments.get(argument_name), Mapping):
        return request

    draft = _latest_draft_for_tool(
        draft_key,
        context=context,
        prior_tool_results=prior_tool_results,
    )
    if not draft:
        return request

    arguments[argument_name] = draft
    metadata = dict(request.metadata or {})
    metadata["current_draft_injected_from_context"] = True
    metadata["current_draft_key"] = draft_key
    return AssistantToolRequest(
        tool_name=request.tool_name,
        arguments=arguments,
        request_id=request.request_id,
        reason=request.reason,
        metadata=metadata,
    )


def _latest_draft_for_tool(
    draft_key: str,
    *,
    context: Mapping[str, Any],
    prior_tool_results: Sequence[AssistantToolResult],
) -> dict[str, Any]:
    draft = _context_current_draft(context, draft_key)
    for tool_result in tuple(prior_tool_results or ()):
        if not getattr(tool_result, "ok", False):
            continue
        data = dict(tool_result.data or {})
        candidate = data.get(draft_key)
        if isinstance(candidate, Mapping) and candidate:
            draft = dict(candidate)
    return draft


def _context_current_draft(context: Mapping[str, Any], draft_key: str) -> dict[str, Any]:
    metadata = dict((context or {}).get("metadata") or {})
    tool_oriented = dict(metadata.get("tool_oriented_intake") or {})
    current_drafts = dict(tool_oriented.get("current_drafts") or {})
    draft = current_drafts.get(draft_key)
    return dict(draft) if isinstance(draft, Mapping) else {}


def _tool_selection_reason_blocked_result(
    request: AssistantToolRequest,
    *,
    error_code: str,
) -> AssistantToolResult:
    return AssistantToolResult(
        tool_name=request.tool_name,
        status=AssistantToolStatus.BLOCKED,
        request_id=request.request_id,
        error_code=error_code,
        error_message=(
            "Provider-native tool execution requires a clear, observable selection basis. "
            "The assistant should clarify the user's intent instead of guessing."
        ),
        metadata={
            "executor": "controlled_tool_loop.v1",
            "tool_governance": "ambiguous_intent_restraint.v1",
            "writes_allowed": False,
            "applies_changes": False,
            **safe_tool_selection_observability(request.metadata),
        },
    )


def _tool_requests_limit_result(request: AssistantToolRequest, *, max_tool_requests: int) -> AssistantToolResult:
    return AssistantToolResult(
        tool_name=request.tool_name,
        status=AssistantToolStatus.BLOCKED,
        request_id=request.request_id,
        error_code="tool_requests_per_turn_limit_exceeded",
        error_message="This turn requested more tools than the current My Scoope technical limit allows.",
        metadata={
            "executor": "controlled_tool_loop.v1",
            "writes_allowed": False,
            "applies_changes": False,
            "max_tool_requests_per_turn": max_tool_requests,
        },
    )


def _tool_user_from_request(request: AssistantTurnRequest) -> Any | None:
    metadata = dict(request.metadata or {})
    return metadata.get("tool_user") or metadata.get("user") or metadata.get("current_user")


def _missing_user_tool_result(request: AssistantToolRequest) -> AssistantToolResult:
    return AssistantToolResult(
        tool_name=request.tool_name,
        status=AssistantToolStatus.BLOCKED,
        request_id=request.request_id,
        error_code="tool_user_required",
        error_message="Read-only tool execution requires an authenticated My Scoope user.",
        metadata={
            "executor": "read_only_tool_loop.v1",
            "writes_allowed": False,
        },
    )


def _max_iterations_tool_result(request: AssistantToolRequest) -> AssistantToolResult:
    return AssistantToolResult(
        tool_name=request.tool_name,
        status=AssistantToolStatus.BLOCKED,
        request_id=request.request_id,
        error_code="tool_loop_max_iterations_reached",
        error_message="This turn reached the configured My Scoope tool loop iteration limit.",
        metadata={
            "executor": "controlled_tool_loop.v1",
            "writes_allowed": False,
            "applies_changes": False,
        },
    )


def _proposal_tools_disabled_result(request: AssistantToolRequest) -> AssistantToolResult:
    return AssistantToolResult(
        tool_name=request.tool_name,
        status=AssistantToolStatus.BLOCKED,
        request_id=request.request_id,
        error_code="reviewable_proposal_tools_disabled",
        error_message="Reviewable proposal tools require explicit orchestrator opt-in.",
        metadata={
            "executor": "controlled_tool_loop.v1",
            "writes_allowed": False,
            "applies_changes": False,
            "creates_reviewable_proposal": False,
        },
    )


def _proposal_tool_results(tool_results: Sequence[AssistantToolResult]) -> tuple[AssistantToolResult, ...]:
    return tuple(
        result
        for result in tuple(tool_results or ())
        if dict(result.metadata or {}).get("creates_reviewable_proposal") is True
    )




def _intent_requires_human_review(intent: AssistantIntent) -> bool:
    """Return whether an intent itself crosses a human-review boundary.

    Capturing a nutrition brief is now a draft-oriented conversational action.
    It can update non-persistent tool drafts and chat cards, but it does not
    persist user profile data or create reviewable proposals by itself. Proposal
    creation and iteration intents still require review regardless of provider
    claims.
    """

    return intent.name in {
        AssistantIntentName.CREATE_MEAL_PROPOSAL,
        AssistantIntentName.CREATE_DAILYPLAN_PROPOSAL,
        AssistantIntentName.CREATE_PROGRAM_PROPOSAL,
        AssistantIntentName.ITERATE_PROPOSAL,
    }

def _proposal_ids_from_tool_results(tool_results: Sequence[AssistantToolResult]) -> tuple[int, ...]:
    proposal_ids: list[int] = []
    for result in _proposal_tool_results(tool_results):
        for raw_id in dict(result.metadata or {}).get("proposal_ids") or ():
            try:
                proposal_id = int(raw_id)
            except (TypeError, ValueError):
                proposal_id = 0
            if proposal_id > 0 and proposal_id not in proposal_ids:
                proposal_ids.append(proposal_id)
    return tuple(proposal_ids)
