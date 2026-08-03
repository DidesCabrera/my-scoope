from __future__ import annotations

import json
import time
from collections.abc import Mapping, Sequence

from ai_assistant.application.context_builder import sanitize_provider_context
from ai_assistant.application.limits import validate_provider_request_limits
from ai_assistant.application.model_routing import resolve_model_route_for_turn
from ai_assistant.application.orchestrator_runtime import elapsed_ms as _elapsed_ms
from ai_assistant.application.provider_parsing import AssistantProviderParseResult
from ai_assistant.domain import (
    AssistantIntentName,
    AssistantStructuredResponse,
    AssistantToolRequest,
    AssistantToolResult,
    AssistantToolStatus,
    AssistantTurnRequest,
)
from ai_assistant.infrastructure.providers import LLMProviderError, LLMProviderResponse


def run_provider_turn(orchestrator, request: AssistantTurnRequest) -> AssistantStructuredResponse:
    """Process one semantic assistant turn with a controlled multi-step tool loop."""

    started_at = time.perf_counter()
    model_route = resolve_model_route_for_turn(request)
    try:
        turn_llm_client = orchestrator._llm_client_for_route(model_route)
    except LLMProviderError as exc:
        latency_ms = _elapsed_ms(started_at)
        response = orchestrator._provider_error_response(
            error=exc,
            latency_ms=latency_ms,
            provider_name=model_route.provider,
            model_name=model_route.model,
        )
        return orchestrator._with_usage_observability(
            request=request,
            response=response,
            provider_responses=(),
            latency_ms=latency_ms,
            status="error",
            error_type=exc.__class__.__name__,
            tools_executed=False,
        )

    # Keep legacy helpers that inspect orchestrator.llm_client accurate for this turn.
    orchestrator.llm_client = turn_llm_client
    provider_request = orchestrator.build_provider_request(request, model_route=model_route)
    limit_violation = validate_provider_request_limits(provider_request, limits=orchestrator.config.turn_limits)
    if limit_violation is not None:
        latency_ms = _elapsed_ms(started_at)
        response = orchestrator._limit_blocked_response(
            violation=limit_violation,
            latency_ms=latency_ms,
        )
        return orchestrator._with_usage_observability(
            request=request,
            response=response,
            provider_responses=(),
            latency_ms=latency_ms,
            status="blocked",
            error_type=limit_violation.error_code,
            tools_executed=False,
        )

    credit_check = orchestrator.credit_service.check_turn_allowed(
        request=request,
        provider_request=provider_request,
        provider=getattr(orchestrator.llm_client, "provider_name", ""),
        model=str(getattr(orchestrator.llm_client, "model", "") or ""),
    )
    if not credit_check.allowed:
        latency_ms = _elapsed_ms(started_at)
        response = orchestrator._credit_blocked_response(
            credit_check=credit_check,
            latency_ms=latency_ms,
        )
        return orchestrator._with_usage_observability(
            request=request,
            response=response,
            provider_responses=(),
            latency_ms=latency_ms,
            status="blocked",
            error_type=credit_check.reason or "ai_credit_quota_exceeded",
            tools_executed=False,
        )

    try:
        provider_response = turn_llm_client.generate(provider_request)
    except LLMProviderError as exc:
        latency_ms = _elapsed_ms(started_at)
        response = orchestrator._provider_error_response(
            error=exc,
            latency_ms=latency_ms,
        )
        return orchestrator._with_usage_observability(
            request=request,
            response=response,
            provider_responses=(),
            latency_ms=latency_ms,
            status="error",
            error_type=exc.__class__.__name__,
            tools_executed=False,
        )

    provider_responses: list[LLMProviderResponse] = [provider_response]
    parse_result = orchestrator.parse_provider_response(provider_response)
    contract_repair_attempted = False
    incomplete_reasons: list[str] = []
    initial_incomplete_reason = _provider_incomplete_reason(provider_response)
    if initial_incomplete_reason:
        incomplete_reasons.append(initial_incomplete_reason)
    if _provider_response_needs_contract_repair(
        parse_result,
        provider_response,
        allow_initial_operational_intent_repair=True,
    ):
        repair_request = orchestrator.build_contract_repair_provider_request(
            failed_request=provider_request,
            model_route=model_route,
            require_tool_call=_provider_response_requires_tool_call_repair(parse_result),
        )
        try:
            repaired_provider_response = turn_llm_client.generate(repair_request)
        except LLMProviderError:
            repaired_provider_response = None
        if repaired_provider_response is not None:
            contract_repair_attempted = True
            provider_responses.append(repaired_provider_response)
            repaired_incomplete_reason = _provider_incomplete_reason(repaired_provider_response)
            if repaired_incomplete_reason:
                incomplete_reasons.append(repaired_incomplete_reason)
            provider_response = repaired_provider_response
            parse_result = orchestrator.parse_provider_response(repaired_provider_response)

    all_tool_requests = list(parse_result.response.tool_requests)
    all_ignored_provider_proposal_ids = list(parse_result.ignored_provider_proposal_ids)
    continuation_items = list(provider_response.continuation_items)
    all_tool_results = orchestrator._resolve_tool_results(request, parse_result.response.tool_requests)
    current_tool_results = all_tool_results
    tool_loop_iterations = 0

    while _has_tool_results(current_tool_results) and tool_loop_iterations < orchestrator.config.max_tool_loop_iterations:
        remaining_iterations = orchestrator.config.max_tool_loop_iterations - tool_loop_iterations - 1
        final_provider_request = orchestrator.build_tool_followup_provider_request(
            request=request,
            continuation_items=continuation_items,
            tool_results=current_tool_results,
            model_route=model_route,
            remaining_tool_iterations=remaining_iterations,
        )
        followup_limit_violation = validate_provider_request_limits(
            final_provider_request,
            limits=orchestrator.config.turn_limits,
        )
        if followup_limit_violation is not None:
            # Tool results are already controlled My Scoope state. If the
            # full follow-up prompt is too large, first retry with a compact
            # no-more-tools follow-up. If that is still too large, keep the
            # successful tool results and answer locally from them instead of
            # showing a technical limit error in the user chat.
            compact_provider_request = orchestrator.build_compact_tool_followup_provider_request(
                request=request,
                first_response=parse_result.response,
                tool_results=all_tool_results,
                model_route=model_route,
            )
            compact_limit_violation = validate_provider_request_limits(
                compact_provider_request,
                limits=orchestrator.config.turn_limits,
            )
            if compact_limit_violation is None:
                final_provider_request = compact_provider_request
                remaining_iterations = 0
            else:
                latency_ms = _elapsed_ms(started_at)
                response = orchestrator._tool_results_local_ack_response(
                    provider_response=provider_responses[-1],
                    tool_results=all_tool_results,
                    violation=compact_limit_violation,
                    latency_ms=latency_ms,
                    tool_loop_iterations=tool_loop_iterations,
                    first_provider_response_id=provider_response.response_id,
                )
                return orchestrator._with_usage_observability(
                    request=request,
                    response=response,
                    provider_responses=tuple(provider_responses),
                    latency_ms=latency_ms,
                    status="degraded",
                    error_type="tool_followup_limit_local_ack",
                    tools_executed=True,
                )

        try:
            final_provider_response = turn_llm_client.generate(final_provider_request)
        except LLMProviderError as exc:
            # The function call and its controlled result already exist. A
            # provider failure while wording the follow-up must not erase
            # that evidence or turn a safely resolved tool operation into a
            # generic failed turn. Answer from the typed result, preserve
            # native-call metadata, and record the degradation explicitly.
            latency_ms = _elapsed_ms(started_at)
            response = orchestrator._tool_results_provider_failure_response(
                provider_response=provider_responses[-1],
                tool_results=all_tool_results,
                tool_requests=all_tool_requests,
                error=exc,
                latency_ms=latency_ms,
                tool_loop_iterations=tool_loop_iterations,
                first_provider_response_id=provider_responses[0].response_id,
            )
            return orchestrator._with_usage_observability(
                request=request,
                response=response,
                provider_responses=tuple(provider_responses),
                latency_ms=latency_ms,
                status="degraded",
                error_type=f"tool_followup_{exc.__class__.__name__}",
                tools_executed=True,
            )

        provider_responses.append(final_provider_response)
        parse_result = orchestrator.parse_provider_response(final_provider_response)
        followup_incomplete_reason = _provider_incomplete_reason(final_provider_response)
        if followup_incomplete_reason:
            incomplete_reasons.append(followup_incomplete_reason)
        if _provider_response_needs_contract_repair(parse_result, final_provider_response):
            repair_request = orchestrator.build_contract_repair_provider_request(
                failed_request=final_provider_request,
                model_route=model_route,
                require_tool_call=_provider_response_requires_tool_call_repair(parse_result),
            )
            try:
                repaired_followup_response = turn_llm_client.generate(repair_request)
            except LLMProviderError:
                repaired_followup_response = None
            if repaired_followup_response is not None:
                contract_repair_attempted = True
                provider_responses.append(repaired_followup_response)
                repaired_incomplete_reason = _provider_incomplete_reason(repaired_followup_response)
                if repaired_incomplete_reason:
                    incomplete_reasons.append(repaired_incomplete_reason)
                final_provider_response = repaired_followup_response
                parse_result = orchestrator.parse_provider_response(repaired_followup_response)
        continuation_items.extend(_provider_tool_output_items(current_tool_results))
        continuation_items.extend(final_provider_response.continuation_items)
        all_tool_requests.extend(parse_result.response.tool_requests)
        all_ignored_provider_proposal_ids.extend(parse_result.ignored_provider_proposal_ids)
        tool_loop_iterations += 1

        if not parse_result.response.tool_requests:
            current_tool_results = ()
            break
        if tool_loop_iterations >= orchestrator.config.max_tool_loop_iterations:
            blocked_results = tuple(
                _max_iterations_tool_result(tool_request)
                for tool_request in parse_result.response.tool_requests
            )
            all_tool_results = (*all_tool_results, *blocked_results)
            current_tool_results = ()
            break

        current_tool_results = orchestrator._resolve_tool_results(
            request,
            parse_result.response.tool_requests,
            prior_tool_results=all_tool_results,
        )
        all_tool_results = (*all_tool_results, *current_tool_results)

    latency_ms = _elapsed_ms(started_at)
    tools_executed = _has_ok_tool_results(all_tool_results)
    response = orchestrator._with_policy_metadata(
        parse_result=parse_result,
        provider_response=provider_responses[-1],
        tool_results=all_tool_results,
        latency_ms=latency_ms,
        tools_executed=tools_executed,
        tool_loop_iterations=tool_loop_iterations,
        first_provider_response_id=provider_responses[0].response_id if tool_loop_iterations else "",
        contract_repair_attempted=contract_repair_attempted,
        provider_incomplete_reasons=tuple(dict.fromkeys(incomplete_reasons)),
        tool_requests=tuple(all_tool_requests),
        ignored_provider_proposal_ids=tuple(dict.fromkeys(all_ignored_provider_proposal_ids)),
    )
    return orchestrator._with_usage_observability(
        request=request,
        response=response,
        provider_responses=tuple(provider_responses),
        latency_ms=latency_ms,
        status="completed",
        tools_executed=tools_executed,
    )

def _provider_incomplete_reason(provider_response: LLMProviderResponse) -> str:
    raw = dict(provider_response.raw or {})
    if str(raw.get("status") or "").strip().lower() != "incomplete":
        return ""
    details = raw.get("incomplete_details")
    if isinstance(details, Mapping):
        return str(details.get("reason") or "incomplete")[:80]
    return "incomplete"


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


def _has_tool_results(tool_results: Sequence[AssistantToolResult]) -> bool:
    return bool(tuple(tool_results or ()))


def _has_ok_tool_results(tool_results: Sequence[AssistantToolResult]) -> bool:
    return any(result.ok for result in tuple(tool_results or ()))


def _provider_tool_output_items(
    tool_results: Sequence[AssistantToolResult],
) -> tuple[Mapping[str, object], ...]:
    items = []
    for result in tuple(tool_results or ()):
        if not result.request_id:
            continue
        payload = sanitize_provider_context(result.as_dict())
        items.append(
            {
                "type": "function_call_output",
                "call_id": result.request_id,
                "output": json.dumps(payload, ensure_ascii=False, sort_keys=True),
            }
        )
    return tuple(items)


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

