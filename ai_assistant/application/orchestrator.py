from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Sequence

from django.conf import settings

from ai_assistant.application.audit import build_audit_snapshot, sanitize_audit_value
from ai_assistant.application.context_builder import sanitize_provider_context
from ai_assistant.application.credits import AICreditCheck, DjangoAICreditService
from ai_assistant.application.limits import (
    AILimitViolation,
    AITurnLimitConfig,
    bounded_text,
    estimate_provider_request_tokens,
    validate_provider_request_limits,
)
from ai_assistant.application.model_routing import (
    AIModelRoute,
    resolve_model_route_for_turn,
    route_max_output_tokens,
)
from ai_assistant.application.product_context import (
    developer_product_capability_policy,
    system_domain_anchor_lines,
)
from ai_assistant.application.tool_governance import (
    extract_provider_tool_selection_reason,
    safe_tool_selection_observability,
    system_tool_restraint_lines,
    tool_selection_reason_error,
)
from ai_assistant.application.response_style import (
    developer_response_style_policy,
    system_response_style_lines,
)
from ai_assistant.application.usage import AIUsageRecorder, DjangoAIUsageRecorder
from ai_assistant.application.tools import (
    AssistantToolCategory,
    ProfileCommitToolExecutor,
    ProfileDraftToolExecutor,
    ReadOnlyToolExecutor,
    ReviewableProposalToolExecutor,
    TOOL_CREATE_NUTRITION_ENGINE_DAILYPLAN_PROPOSAL_FROM_DRAFTS,
    TOOL_SHARE_PREFERENCE_DRAFT_CARD,
    TOOL_SHARE_PROFILE_DRAFT_CARD,
    TOOL_SHARE_PROPOSAL_PREFERENCES_CARD,
    TOOL_READ_PROPOSAL,
    TOOL_UPDATE_PREFERENCE_DRAFT,
    TOOL_UPDATE_PROFILE_DRAFT,
    TOOL_UPDATE_PROPOSAL_PREFERENCES,
    ValidationToolExecutor,
    get_tool_spec,
    list_provider_tool_specs,
    validate_tool_request,
)
from ai_assistant.domain import (
    AssistantContractError,
    AssistantIntent,
    AssistantIntentName,
    AssistantMessage,
    AssistantMessageRole,
    AssistantStructuredResponse,
    AssistantToolRequest,
    AssistantToolResult,
    AssistantToolStatus,
    AssistantTurnRequest,
)
from ai_assistant.infrastructure.providers import (
    LLMClient,
    LLMMessage,
    LLMProviderError,
    LLMProviderRequest,
    LLMProviderResponse,
    LLMProviderToolCall,
    LLMProviderToolOutput,
    get_llm_client,
)


logger = logging.getLogger(__name__)


_EXPANDED_PRODUCT_TOOL_DOMAINS = {
    "read_food": ("alimento", "food"),
    "read_meal": ("comida", "meal"),
    "list_user_foods": ("alimento", "food"),
    "list_user_meals": ("comida", "meal"),
    "search_user_meals": ("comida", "meal"),
    "list_user_dailyplans": ("plan", "dailyplan"),
    "search_user_dailyplans": ("plan", "dailyplan"),
    "list_user_programs": ("programa", "program", "semana"),
    "read_program": ("programa", "program", "semana"),
    "read_calendarization": ("calendario", "calendar", "pausar", "reanudar"),
    "list_inbox_items": ("inbox", "compartid", "recibid", "enviad"),
    "read_account_billing_context": (
        "cuenta",
        "crédito",
        "credito",
        "suscripción",
        "suscripcion",
        "pago",
        "billing",
        "plan comercial",
    ),
    "create_proportional_dailyplan_calorie_proposal": (
        "caloría",
        "caloria",
        "kcal",
        "cantidad",
        "manteniendo los mismos alimentos",
    ),
    "prepare_product_action": (
        "crear",
        "crea",
        "actualizar",
        "actualiza",
        "cambiar",
        "cambia",
        "renombr",
        "elimin",
        "borr",
        "paus",
        "reanud",
        "cancel",
        "aprobar",
        "aprueba",
        "rechaz",
        "aplicar",
        "aplica",
        "duplic",
    ),
}


def _expanded_product_tool_relevant(tool_name: str, *, user_text: str) -> bool:
    keywords = _EXPANDED_PRODUCT_TOOL_DOMAINS.get(tool_name)
    if keywords is None:
        return True
    if tool_name == "prepare_product_action" and (
        "propuesta" in user_text or "proposal" in user_text
    ):
        return False
    return any(keyword in user_text for keyword in keywords)


_MEAL_PROPOSAL_TOOLS = {
    "create_validated_meal_proposal",
    "create_nutrition_solver_meal_proposal",
}
_DAILYPLAN_PROPOSAL_TOOLS = {
    "create_validated_dailyplan_proposal",
    "create_validated_dailyplan_build_proposal",
    "create_nutrition_engine_dailyplan_proposal",
    "create_nutrition_engine_dailyplan_proposal_from_drafts",
    "iterate_nutrition_engine_dailyplan_proposal",
}

_AI_NUTRITION_INTAKE_CORE_TOOLS = {
    TOOL_UPDATE_PROFILE_DRAFT,
    TOOL_UPDATE_PREFERENCE_DRAFT,
    TOOL_UPDATE_PROPOSAL_PREFERENCES,
    TOOL_CREATE_NUTRITION_ENGINE_DAILYPLAN_PROPOSAL_FROM_DRAFTS,
}


def _reviewable_proposal_tool_relevant(tool_name: str, *, user_text: str) -> bool:
    if tool_name == "create_validated_dailyplan_proposal" and not any(
        keyword in user_text
        for keyword in ("objetiv", "target", "ajust", "cantidad", "calor", "kcal")
    ):
        return False
    proposal_names = _MEAL_PROPOSAL_TOOLS | _DAILYPLAN_PROPOSAL_TOOLS
    if tool_name not in proposal_names:
        return True
    mentions_meal = any(keyword in user_text for keyword in ("meal", "comida"))
    mentions_plan = any(
        keyword in f" {user_text} "
        for keyword in ("dailyplan", "plan diario", " plan ")
    )
    if mentions_meal and not mentions_plan:
        return tool_name in _MEAL_PROPOSAL_TOOLS
    if mentions_plan and not mentions_meal:
        return tool_name in _DAILYPLAN_PROPOSAL_TOOLS
    return True


class AssistantOrchestratorError(RuntimeError):
    """Raised when the LLM orchestrator cannot produce a safe response."""


ToolValidator = Callable[[AssistantToolRequest], AssistantToolResult]
ProviderToolSpecProvider = Callable[[], list[dict[str, Any]]]


@dataclass(frozen=True)
class AssistantOrchestratorConfig:
    """Runtime limits for the external LLM orchestrator v1.

    The orchestrator sends bounded history, accepts natural visible text, and
    allows a controlled multi-step native tool loop so the model can operate My
    Scoope objects. Reviewable proposal tools are part of the normal runtime and
    never apply changes directly.
    """

    max_history_messages: int = 20
    max_output_tokens: int = 2400
    max_tool_loop_iterations: int = 4
    enable_reviewable_proposal_tools: bool = True
    max_input_tokens: int = 20000
    max_context_chars: int = 16000
    max_message_chars: int = 2000
    max_tool_requests_per_turn: int = 3
    engine_name: str = "external_llm_orchestrator_v1"
    response_format_version: str = "ai_assistant_natural_response.v1"
    reasoning_effort: str = "low"

    @classmethod
    def from_settings(cls) -> "AssistantOrchestratorConfig":
        return cls(
            max_history_messages=_settings_int("AI_ASSISTANT_MAX_HISTORY_MESSAGES", cls.max_history_messages),
            max_output_tokens=_settings_int("AI_ASSISTANT_MAX_OUTPUT_TOKENS", cls.max_output_tokens),
            max_tool_loop_iterations=_settings_int("AI_ASSISTANT_MAX_TOOL_LOOP_ITERATIONS", cls.max_tool_loop_iterations),
            enable_reviewable_proposal_tools=_settings_bool(
                "AI_ASSISTANT_ENABLE_REVIEWABLE_PROPOSAL_TOOLS",
                cls.enable_reviewable_proposal_tools,
            ),
            max_input_tokens=_settings_int("AI_ASSISTANT_MAX_INPUT_TOKENS", cls.max_input_tokens),
            max_context_chars=_settings_int("AI_ASSISTANT_MAX_CONTEXT_CHARS", cls.max_context_chars),
            max_message_chars=_settings_int("AI_ASSISTANT_MAX_MESSAGE_CHARS", cls.max_message_chars),
            max_tool_requests_per_turn=_settings_int(
                "AI_ASSISTANT_MAX_TOOL_REQUESTS_PER_TURN",
                cls.max_tool_requests_per_turn,
            ),
            reasoning_effort=_settings_choice(
                "AI_ASSISTANT_OPENAI_REASONING_EFFORT",
                cls.reasoning_effort,
                allowed={"none", "minimal", "low", "medium", "high", "xhigh", "max"},
            ),
        )

    @property
    def turn_limits(self) -> AITurnLimitConfig:
        return AITurnLimitConfig(
            max_input_tokens=self.max_input_tokens,
            max_context_chars=self.max_context_chars,
            max_message_chars=self.max_message_chars,
            max_tool_requests_per_turn=self.max_tool_requests_per_turn,
        ).normalized()


@dataclass(frozen=True)
class AssistantProviderParseResult:
    """Result of normalizing provider text into an internal structured response."""

    response: AssistantStructuredResponse
    was_json: bool
    parse_error: str = ""
    ignored_provider_proposal_ids: Sequence[Any] = field(default_factory=tuple)
    declared_tools_required: bool = False


class ExternalLLMOrchestrator:
    """Provider-agnostic AI Assistant orchestrator v1.

    This class calls an external LLM provider through the Patch 43 gateway,
    parses a structured semantic response from Patch 44 and validates tool
    requests through the Patch 45 registry. Since Patch 54 it may execute
    read-only tools through the controlled local executor, then call the
    provider once more with sanitized tool results. Since Patch 55 it can also
    execute reviewable proposal tools behind explicit opt-in. It still never
    applies proposal changes directly.
    """

    def __init__(
        self,
        *,
        llm_client: LLMClient | None = None,
        tool_validator: ToolValidator = validate_tool_request,
        provider_tool_specs: ProviderToolSpecProvider = list_provider_tool_specs,
        profile_commit_tool_executor: ProfileCommitToolExecutor | None = None,
        profile_draft_tool_executor: ProfileDraftToolExecutor | None = None,
        read_only_tool_executor: ReadOnlyToolExecutor | None = None,
        reviewable_proposal_tool_executor: ReviewableProposalToolExecutor | None = None,
        validation_tool_executor: ValidationToolExecutor | None = None,
        config: AssistantOrchestratorConfig | None = None,
        usage_recorder: AIUsageRecorder | None = None,
        credit_service: DjangoAICreditService | None = None,
    ):
        self._llm_client_was_injected = llm_client is not None
        self.llm_client = llm_client or get_llm_client()
        self.tool_validator = tool_validator
        self.provider_tool_specs = provider_tool_specs
        self.profile_commit_tool_executor = profile_commit_tool_executor or ProfileCommitToolExecutor()
        self.profile_draft_tool_executor = profile_draft_tool_executor or ProfileDraftToolExecutor()
        self.read_only_tool_executor = read_only_tool_executor or ReadOnlyToolExecutor()
        self.reviewable_proposal_tool_executor = reviewable_proposal_tool_executor or ReviewableProposalToolExecutor()
        self.validation_tool_executor = validation_tool_executor or ValidationToolExecutor()
        self.config = config or AssistantOrchestratorConfig.from_settings()
        self.usage_recorder = usage_recorder or DjangoAIUsageRecorder()
        self.credit_service = credit_service or DjangoAICreditService()

    def continue_turn(self, request: AssistantTurnRequest) -> AssistantStructuredResponse:
        """Process one semantic assistant turn with a controlled multi-step tool loop."""

        started_at = time.perf_counter()
        model_route = resolve_model_route_for_turn(request)
        try:
            turn_llm_client = self._llm_client_for_route(model_route)
        except LLMProviderError as exc:
            latency_ms = _elapsed_ms(started_at)
            response = self._provider_error_response(
                error=exc,
                latency_ms=latency_ms,
                provider_name=model_route.provider,
                model_name=model_route.model,
            )
            return self._with_usage_observability(
                request=request,
                response=response,
                provider_responses=(),
                latency_ms=latency_ms,
                status="error",
                error_type=exc.__class__.__name__,
                tools_executed=False,
            )

        # Keep legacy helpers that inspect self.llm_client accurate for this turn.
        self.llm_client = turn_llm_client
        provider_request = self.build_provider_request(request, model_route=model_route)
        limit_violation = validate_provider_request_limits(provider_request, limits=self.config.turn_limits)
        if limit_violation is not None:
            latency_ms = _elapsed_ms(started_at)
            response = self._limit_blocked_response(
                violation=limit_violation,
                latency_ms=latency_ms,
            )
            return self._with_usage_observability(
                request=request,
                response=response,
                provider_responses=(),
                latency_ms=latency_ms,
                status="blocked",
                error_type=limit_violation.error_code,
                tools_executed=False,
            )

        credit_check = self.credit_service.check_turn_allowed(
            request=request,
            provider_request=provider_request,
            provider=getattr(self.llm_client, "provider_name", ""),
            model=str(getattr(self.llm_client, "model", "") or ""),
        )
        if not credit_check.allowed:
            latency_ms = _elapsed_ms(started_at)
            response = self._credit_blocked_response(
                credit_check=credit_check,
                latency_ms=latency_ms,
            )
            return self._with_usage_observability(
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
            response = self._provider_error_response(
                error=exc,
                latency_ms=latency_ms,
            )
            return self._with_usage_observability(
                request=request,
                response=response,
                provider_responses=(),
                latency_ms=latency_ms,
                status="error",
                error_type=exc.__class__.__name__,
                tools_executed=False,
            )

        provider_responses: list[LLMProviderResponse] = [provider_response]
        parse_result = self.parse_provider_response(provider_response)
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
            repair_request = self.build_contract_repair_provider_request(
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
                parse_result = self.parse_provider_response(repaired_provider_response)

        all_tool_requests = list(parse_result.response.tool_requests)
        all_ignored_provider_proposal_ids = list(parse_result.ignored_provider_proposal_ids)
        continuation_items = list(provider_response.continuation_items)
        all_tool_results = self._resolve_tool_results(request, parse_result.response.tool_requests)
        current_tool_results = all_tool_results
        tool_loop_iterations = 0

        while _has_tool_results(current_tool_results) and tool_loop_iterations < self.config.max_tool_loop_iterations:
            remaining_iterations = self.config.max_tool_loop_iterations - tool_loop_iterations - 1
            final_provider_request = self.build_tool_followup_provider_request(
                request=request,
                continuation_items=continuation_items,
                tool_results=current_tool_results,
                model_route=model_route,
                remaining_tool_iterations=remaining_iterations,
            )
            followup_limit_violation = validate_provider_request_limits(
                final_provider_request,
                limits=self.config.turn_limits,
            )
            if followup_limit_violation is not None:
                # Tool results are already controlled My Scoope state. If the
                # full follow-up prompt is too large, first retry with a compact
                # no-more-tools follow-up. If that is still too large, keep the
                # successful tool results and answer locally from them instead of
                # showing a technical limit error in the user chat.
                compact_provider_request = self.build_compact_tool_followup_provider_request(
                    request=request,
                    first_response=parse_result.response,
                    tool_results=all_tool_results,
                    model_route=model_route,
                )
                compact_limit_violation = validate_provider_request_limits(
                    compact_provider_request,
                    limits=self.config.turn_limits,
                )
                if compact_limit_violation is None:
                    final_provider_request = compact_provider_request
                    remaining_iterations = 0
                else:
                    latency_ms = _elapsed_ms(started_at)
                    response = self._tool_results_local_ack_response(
                        provider_response=provider_responses[-1],
                        tool_results=all_tool_results,
                        violation=compact_limit_violation,
                        latency_ms=latency_ms,
                        tool_loop_iterations=tool_loop_iterations,
                        first_provider_response_id=provider_response.response_id,
                    )
                    return self._with_usage_observability(
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
                response = self._tool_results_provider_failure_response(
                    provider_response=provider_responses[-1],
                    tool_results=all_tool_results,
                    tool_requests=all_tool_requests,
                    error=exc,
                    latency_ms=latency_ms,
                    tool_loop_iterations=tool_loop_iterations,
                    first_provider_response_id=provider_responses[0].response_id,
                )
                return self._with_usage_observability(
                    request=request,
                    response=response,
                    provider_responses=tuple(provider_responses),
                    latency_ms=latency_ms,
                    status="degraded",
                    error_type=f"tool_followup_{exc.__class__.__name__}",
                    tools_executed=True,
                )

            provider_responses.append(final_provider_response)
            parse_result = self.parse_provider_response(final_provider_response)
            followup_incomplete_reason = _provider_incomplete_reason(final_provider_response)
            if followup_incomplete_reason:
                incomplete_reasons.append(followup_incomplete_reason)
            if _provider_response_needs_contract_repair(parse_result, final_provider_response):
                repair_request = self.build_contract_repair_provider_request(
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
                    parse_result = self.parse_provider_response(repaired_followup_response)
            continuation_items.extend(_provider_tool_output_items(current_tool_results))
            continuation_items.extend(final_provider_response.continuation_items)
            all_tool_requests.extend(parse_result.response.tool_requests)
            all_ignored_provider_proposal_ids.extend(parse_result.ignored_provider_proposal_ids)
            tool_loop_iterations += 1

            if not parse_result.response.tool_requests:
                current_tool_results = ()
                break
            if tool_loop_iterations >= self.config.max_tool_loop_iterations:
                blocked_results = tuple(
                    _max_iterations_tool_result(tool_request)
                    for tool_request in parse_result.response.tool_requests
                )
                all_tool_results = (*all_tool_results, *blocked_results)
                current_tool_results = ()
                break

            current_tool_results = self._resolve_tool_results(
                request,
                parse_result.response.tool_requests,
                prior_tool_results=all_tool_results,
            )
            all_tool_results = (*all_tool_results, *current_tool_results)

        latency_ms = _elapsed_ms(started_at)
        tools_executed = _has_ok_tool_results(all_tool_results)
        response = self._with_policy_metadata(
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
        return self._with_usage_observability(
            request=request,
            response=response,
            provider_responses=tuple(provider_responses),
            latency_ms=latency_ms,
            status="completed",
            tools_executed=tools_executed,
        )

    def build_provider_request(self, request: AssistantTurnRequest, *, model_route: AIModelRoute | None = None) -> LLMProviderRequest:
        """Map an internal semantic request to the transport-level LLM request."""

        tools = self._provider_tools_for_request(request)
        messages: list[LLMMessage] = [
            LLMMessage(role="system", content=self._system_prompt()),
            LLMMessage(role="developer", content=self._developer_prompt(tools)),
        ]
        if request.context:
            messages.append(LLMMessage(role="developer", content=self._context_prompt(request.context)))
        messages.extend(self._history_messages(request.history))
        messages.append(LLMMessage(role="user", content=request.user_message.content))

        model_route = model_route or resolve_model_route_for_turn(request)
        max_output_tokens = _output_tokens_for_request(
            request=request,
            default_max_output_tokens=self.config.max_output_tokens,
            route=model_route,
        )

        estimated_request = LLMProviderRequest(
            messages=messages,
            max_output_tokens=max_output_tokens,
            tools=tools,
        )
        return LLMProviderRequest(
            messages=messages,
            max_output_tokens=max_output_tokens,
            metadata={
                "engine": self.config.engine_name,
                "format": self.config.response_format_version,
                "local_context_keys": sorted(str(key) for key in request.context.keys()),
                "estimated_input_tokens": estimate_provider_request_tokens(estimated_request),
                "model_route": model_route.as_metadata(),
                "reasoning_effort": self.config.reasoning_effort,
                "technical_limits": {
                    "max_input_tokens": self.config.turn_limits.max_input_tokens,
                    "max_context_chars": self.config.turn_limits.max_context_chars,
                    "max_message_chars": self.config.turn_limits.max_message_chars,
                    "max_tool_requests_per_turn": self.config.turn_limits.max_tool_requests_per_turn,
                },
            },
            tools=tools,
            tool_choice=self._initial_tool_choice(request, tools),
            parallel_tool_calls=False,
            max_tool_calls=self.config.turn_limits.max_tool_requests_per_turn,
        )


    def build_tool_followup_provider_request(
        self,
        *,
        request: AssistantTurnRequest,
        continuation_items: Sequence[Mapping[str, Any]],
        tool_results: Sequence[AssistantToolResult],
        model_route: AIModelRoute | None = None,
        remaining_tool_iterations: int = 0,
    ) -> LLMProviderRequest:
        """Continue a stateless Responses API function-call loop.

        The original bounded prompt is followed by provider output items and
        typed ``function_call_output`` entries. This preserves reasoning items
        while ``store=false`` remains enabled and avoids embedding tool results
        in another assistant-authored JSON envelope.
        """

        model_route = model_route or resolve_model_route_for_turn(request)
        base_request = self.build_provider_request(request, model_route=model_route)
        max_output_tokens = _output_tokens_for_request(
            request=request,
            default_max_output_tokens=self.config.max_output_tokens,
            route=model_route,
        )
        tools = tuple(base_request.tools or ()) if remaining_tool_iterations > 0 else ()
        tool_choice: str | None = "auto" if tools else None
        if tools and self._proposal_ready_after_tool_results(request, tool_results):
            proposal_tool = _provider_tool_by_name(
                tools,
                TOOL_CREATE_NUTRITION_ENGINE_DAILYPLAN_PROPOSAL_FROM_DRAFTS,
            )
            if proposal_tool is not None:
                tools = (proposal_tool,)
                tool_choice = "required"
        tool_outputs = _provider_tool_outputs(tool_results)
        estimated_request = LLMProviderRequest(
            messages=base_request.messages,
            max_output_tokens=max_output_tokens,
            tools=tools,
            continuation_items=tuple(continuation_items or ()),
            tool_outputs=tool_outputs,
        )
        return LLMProviderRequest(
            messages=base_request.messages,
            max_output_tokens=max_output_tokens,
            metadata={
                "engine": self.config.engine_name,
                "format": self.config.response_format_version,
                "tool_loop": "native_function_calls.v1",
                "tool_results_count": len(tuple(tool_results or ())),
                "model_route": model_route.as_metadata(),
                "reasoning_effort": self.config.reasoning_effort,
                "estimated_input_tokens": estimate_provider_request_tokens(estimated_request),
            },
            tools=tools,
            tool_choice=tool_choice,
            parallel_tool_calls=False if tools else None,
            max_tool_calls=(
                self.config.turn_limits.max_tool_requests_per_turn if tools else None
            ),
            continuation_items=tuple(continuation_items or ()),
            tool_outputs=tool_outputs,
        )


    def build_compact_tool_followup_provider_request(
        self,
        *,
        request: AssistantTurnRequest,
        first_response: AssistantStructuredResponse,
        tool_results: Sequence[AssistantToolResult],
        model_route: AIModelRoute | None = None,
    ) -> LLMProviderRequest:
        """Build a minimal tool follow-up prompt when the full one exceeds limits.

        The full provider request repeats the complete developer prompt and tool
        catalog so the model can continue operating tools. That is useful, but
        for short intake turns it can exceed the technical input limit after a
        tool result. In that case we only need a natural final response based on
        already-executed My Scoope tool results.
        """

        model_route = model_route or resolve_model_route_for_turn(request)
        messages = [
            LLMMessage(
                role="system",
                content=(
                    "Eres el AI Assistant de My Scoope. Responde natural y breve. "
                    "Usa los resultados de My Scoope como fuente de verdad."
                ),
            ),
            LLMMessage(
                role="developer",
                content=(
                    "Explica el resultado útil, sin mencionar tools ni JSON. "
                    "No repitas datos que el usuario acaba de entregar. "
                    "No solicites otra operación en este turno."
                ),
            ),
            LLMMessage(role="user", content=bounded_text(request.user_message.content, max_chars=600)),
            LLMMessage(
                role="assistant",
                content=json.dumps(first_response.as_dict(), ensure_ascii=False, sort_keys=True),
            ),
            LLMMessage(
                role="developer",
                content=self._compact_tool_results_prompt(tool_results),
            ),
            LLMMessage(
                role="user",
                content=(
                    "Responde al usuario usando esos tool_results. "
                    "No repitas campos ya capturados."
                ),
            ),
        ]
        max_output_tokens = route_max_output_tokens(
            default_max_output_tokens=min(self.config.max_output_tokens, 500),
            route=model_route,
        )
        return LLMProviderRequest(
            messages=messages,
            max_output_tokens=max_output_tokens,
            metadata={
                "engine": self.config.engine_name,
                "format": self.config.response_format_version,
                "tool_loop": "controlled_tools.compact_followup.v1",
                "tool_results_count": len(tuple(tool_results or ())),
                "model_route": model_route.as_metadata(),
                "reasoning_effort": self.config.reasoning_effort,
                "estimated_input_tokens": estimate_provider_request_tokens(
                    LLMProviderRequest(messages=messages, max_output_tokens=max_output_tokens)
                ),
            },
        )

    def build_contract_repair_provider_request(
        self,
        *,
        failed_request: LLMProviderRequest,
        model_route: AIModelRoute | None = None,
        require_tool_call: bool = False,
    ) -> LLMProviderRequest:
        """Retry one incomplete provider turn without changing its tool boundary."""

        model_route = model_route or AIModelRoute(
            action_type="",
            provider=getattr(self.llm_client, "provider_name", ""),
            model=str(getattr(self.llm_client, "model", "") or ""),
        )
        messages = list(failed_request.messages)
        messages.append(
            LLMMessage(
                role="developer",
                content=(
                    "La respuesta anterior quedó incompleta o declaró una operación sin function call. "
                    "Procesa nuevamente la solicitud original y responde con texto natural. "
                    "Cuando el turno requiera leer, actualizar, mostrar o crear un objeto revisable, solicita la function tool "
                    "nativa correspondiente; no sustituyas operaciones por afirmaciones en texto."
                ),
            )
        )
        max_output_tokens = max(
            int(failed_request.max_output_tokens or 0),
            int(self.config.max_output_tokens),
        )
        metadata = {
            **dict(failed_request.metadata or {}),
            "contract_repair": "incomplete_response_retry.v1",
            "reasoning_effort": self.config.reasoning_effort,
            "model_route": model_route.as_metadata(),
        }
        return LLMProviderRequest(
            messages=messages,
            max_output_tokens=max_output_tokens,
            metadata=metadata,
            tools=failed_request.tools,
            tool_choice=(
                "required"
                if require_tool_call and failed_request.tools
                else failed_request.tool_choice
            ),
            parallel_tool_calls=failed_request.parallel_tool_calls,
            max_tool_calls=failed_request.max_tool_calls,
            continuation_items=failed_request.continuation_items,
            tool_outputs=failed_request.tool_outputs,
        )


    def parse_provider_response(self, provider_response: LLMProviderResponse) -> AssistantProviderParseResult:
        """Normalize natural assistant text and provider-native function calls.

        Natural prose is the primary visible transport. The old JSON envelope
        remains readable only for backwards-compatible fake-provider tests.
        """

        native_tool_requests, native_tool_error = _coerce_provider_tool_calls(
            provider_response.tool_calls
        )
        text = provider_response.normalized_text
        payload: dict[str, Any] | None = None
        parse_error = ""
        if text:
            payload, parse_error = _loads_json_object(text)

        if native_tool_error:
            return AssistantProviderParseResult(
                response=AssistantStructuredResponse(
                    assistant_message=AssistantMessage(
                        role=AssistantMessageRole.ASSISTANT,
                        content=(
                            "Recibí una llamada de herramienta incompleta del proveedor. "
                            "Mantendré este turno en revisión."
                        ),
                    ),
                    intent=AssistantIntent(name=AssistantIntentName.UNKNOWN, confidence=0.0),
                    requires_human_review=True,
                    metadata={
                        "provider_response_was_json": bool(payload),
                        "provider_native_tool_transport": True,
                        "provider_native_tool_error": native_tool_error,
                    },
                ),
                was_json=bool(payload),
                parse_error=native_tool_error,
            )

        if native_tool_requests:
            ignored_provider_proposal_ids = tuple(payload.get("proposal_ids") or ()) if payload else ()
            try:
                assistant_message = (
                    _coerce_assistant_message(payload)
                    if payload is not None
                    else AssistantMessage(
                        role=AssistantMessageRole.ASSISTANT,
                        content="Usaré las herramientas de My Scoope para continuar.",
                    )
                )
                intent = (
                    _coerce_intent(payload.get("intent"))
                    if payload is not None
                    else _intent_for_native_tool_requests(native_tool_requests)
                )
                requires_human_review = (
                    _coerce_requires_human_review(payload)
                    if payload is not None
                    else True
                )
            except (AssistantContractError, TypeError, ValueError):
                # A valid native function call is operationally useful even if
                # optional visible text was malformed. The follow-up after tool
                # execution will produce the user-facing answer.
                assistant_message = AssistantMessage(
                    role=AssistantMessageRole.ASSISTANT,
                    content="Usaré las herramientas de My Scoope para continuar.",
                )
                intent = _intent_for_native_tool_requests(native_tool_requests)
                requires_human_review = True

            return AssistantProviderParseResult(
                response=AssistantStructuredResponse(
                    assistant_message=assistant_message,
                    intent=intent,
                    tool_requests=native_tool_requests,
                    tool_results=(),
                    proposal_ids=(),
                    requires_human_review=requires_human_review,
                    metadata={
                        "provider_response_was_json": bool(payload),
                        "provider_format": str(payload.get("format") or "") if payload else "",
                        "provider_native_tool_transport": True,
                        "provider_native_tool_calls": len(native_tool_requests),
                        "provider_text_parse_ignored_due_to_native_tools": bool(parse_error),
                    },
                ),
                was_json=bool(payload),
                ignored_provider_proposal_ids=ignored_provider_proposal_ids,
            )

        if payload is None:
            fallback_content = _extract_jsonish_assistant_content(text)
            visible_content = fallback_content or text
            return AssistantProviderParseResult(
                response=AssistantStructuredResponse(
                    assistant_message=AssistantMessage(
                        role=AssistantMessageRole.ASSISTANT,
                        content=visible_content or "No pude obtener una respuesta útil en este turno.",
                    ),
                    intent=AssistantIntent(
                        name=AssistantIntentName.ANSWER_QUESTION,
                        confidence=0.75 if visible_content else 0.0,
                    ),
                    requires_human_review=False,
                    metadata={
                        "provider_response_was_json": False,
                        "provider_response_format": self.config.response_format_version,
                        "provider_response_jsonish_content_extracted": bool(fallback_content),
                    },
                ),
                was_json=False,
                parse_error="" if visible_content else (parse_error or "empty_provider_text"),
            )

        ignored_provider_proposal_ids = tuple(payload.get("proposal_ids") or ())
        try:
            response = AssistantStructuredResponse(
                assistant_message=_coerce_assistant_message(payload),
                intent=_coerce_intent(payload.get("intent")),
                tool_requests=_coerce_tool_requests(payload.get("tool_requests")),
                tool_results=(),
                # Provider-supplied proposal ids are intentionally ignored. Only
                # My Scoope tool execution may attach real proposals.
                proposal_ids=(),
                requires_human_review=_coerce_requires_human_review(payload),
                metadata={
                    "provider_response_was_json": True,
                    "provider_format": str(payload.get("format") or ""),
                    "provider_native_tool_transport": False,
                },
            )
        except (AssistantContractError, TypeError, ValueError) as exc:
            return AssistantProviderParseResult(
                response=AssistantStructuredResponse(
                    assistant_message=AssistantMessage(
                        role=AssistantMessageRole.ASSISTANT,
                        content=(
                            "Recibí una respuesta del proveedor, pero no cumple el contrato "
                            "interno de My Scoope. Mantendré este turno en revisión."
                        ),
                    ),
                    intent=AssistantIntent(name=AssistantIntentName.UNKNOWN, confidence=0.0),
                    requires_human_review=True,
                    metadata={
                        "provider_response_was_json": True,
                        "provider_contract_error": str(exc),
                    },
                ),
                was_json=True,
                parse_error=str(exc),
                ignored_provider_proposal_ids=ignored_provider_proposal_ids,
                declared_tools_required=_provider_declared_tools_required(payload),
            )

        return AssistantProviderParseResult(
            response=response,
            was_json=True,
            ignored_provider_proposal_ids=ignored_provider_proposal_ids,
            declared_tools_required=_provider_declared_tools_required(payload),
        )

    def _with_policy_metadata(
        self,
        *,
        parse_result: AssistantProviderParseResult,
        provider_response: LLMProviderResponse,
        tool_results: Sequence[AssistantToolResult],
        latency_ms: int | None = None,
        tools_executed: bool = False,
        tool_loop_iterations: int = 0,
        first_provider_response_id: str = "",
        contract_repair_attempted: bool = False,
        provider_incomplete_reasons: Sequence[str] = (),
        tool_requests: Sequence[AssistantToolRequest] | None = None,
        ignored_provider_proposal_ids: Sequence[Any] | None = None,
    ) -> AssistantStructuredResponse:
        blocked_tool_results = [result for result in tool_results if result.status == AssistantToolStatus.BLOCKED]
        proposal_ids = _proposal_ids_from_tool_results(tool_results)
        effective_tool_requests = tuple(
            parse_result.response.tool_requests if tool_requests is None else tool_requests
        )
        effective_ignored_proposal_ids = tuple(
            parse_result.ignored_provider_proposal_ids
            if ignored_provider_proposal_ids is None
            else ignored_provider_proposal_ids
        )
        metadata = {
            **dict(parse_result.response.metadata),
            "engine": self.config.engine_name,
            "provider": provider_response.provider,
            "provider_model": provider_response.model,
            "provider_response_id": provider_response.response_id,
            "provider_usage": sanitize_audit_value(dict(provider_response.usage or {})),
            "tool_requests_validated": len(tool_results),
            "tool_requests_blocked": len(blocked_tool_results),
            "tool_results_ok": len([result for result in tool_results if result.ok]),
            "reviewable_proposal_tools_enabled": self.config.enable_reviewable_proposal_tools,
            "proposal_tool_results_ok": len(_proposal_tool_results(tool_results)),
            "created_reviewable_proposal_ids": list(proposal_ids),
            "tools_executed": bool(tools_executed),
            "tool_loop_iterations": tool_loop_iterations,
            "provider_contract_repair_attempted": bool(contract_repair_attempted),
            "provider_incomplete_reasons": list(provider_incomplete_reasons),
            "provider_final_incomplete_reason": _provider_incomplete_reason(provider_response),
            "provider_declared_tools_required": bool(parse_result.declared_tools_required),
            "provider_native_tool_transport": any(
                request.metadata.get("provider_transport") == "native_function_call.v1"
                for request in effective_tool_requests
            ),
            "provider_native_tool_calls": len(
                [
                    request
                    for request in effective_tool_requests
                    if request.metadata.get("provider_transport") == "native_function_call.v1"
                ]
            ),
            "tool_selection_reasons": [
                {
                    "tool_name": request.tool_name,
                    "request_id": request.request_id,
                    **safe_tool_selection_observability(request.metadata),
                }
                for request in effective_tool_requests
                if request.metadata.get("provider_transport") == "native_function_call.v1"
            ],
        }
        if first_provider_response_id:
            metadata["first_provider_response_id"] = first_provider_response_id
        if parse_result.parse_error:
            metadata["provider_parse_error"] = parse_result.parse_error
        if effective_ignored_proposal_ids:
            metadata["ignored_provider_proposal_ids"] = list(effective_ignored_proposal_ids)

        requires_human_review = bool(
            parse_result.response.requires_human_review
            or _intent_requires_human_review(parse_result.response.intent)
            or parse_result.response.tool_requests
            or blocked_tool_results
            or proposal_ids
            or effective_ignored_proposal_ids
        )

        response = AssistantStructuredResponse(
            assistant_message=parse_result.response.assistant_message,
            intent=parse_result.response.intent,
            tool_requests=effective_tool_requests,
            tool_results=tuple(tool_results),
            proposal_ids=proposal_ids,
            requires_human_review=requires_human_review,
            metadata=metadata,
        )
        audit_snapshot = build_audit_snapshot(
            response=response,
            engine=self.config.engine_name,
            provider=provider_response.provider,
            provider_model=provider_response.model,
            provider_response_id=provider_response.response_id,
            provider_usage=provider_response.usage,
            latency_ms=latency_ms,
            tools_executed=bool(tools_executed),
            provider_parse_error=parse_result.parse_error,
            provider_response_was_json=parse_result.was_json,
            ignored_provider_proposal_ids=effective_ignored_proposal_ids,
            proposal_ids=response.proposal_ids,
        )
        metadata = {
            **metadata,
            "provider_latency_ms": latency_ms,
            "audit_version": audit_snapshot.version,
            "audit": audit_snapshot.as_dict(),
        }
        return AssistantStructuredResponse(
            assistant_message=response.assistant_message,
            intent=response.intent,
            tool_requests=response.tool_requests,
            tool_results=response.tool_results,
            proposal_ids=response.proposal_ids,
            requires_human_review=response.requires_human_review,
            metadata=metadata,
        )

    def _provider_error_response(
        self,
        *,
        error: LLMProviderError,
        latency_ms: int | None = None,
        tool_results: Sequence[AssistantToolResult] = (),
        tools_executed: bool = False,
        provider_name: str = "",
        model_name: str = "",
    ) -> AssistantStructuredResponse:
        error_type = error.__class__.__name__
        provider = provider_name or getattr(self.llm_client, "provider_name", "unknown")
        response = AssistantStructuredResponse(
            assistant_message=AssistantMessage(
                role=AssistantMessageRole.ASSISTANT,
                content=(
                    "No pude completar este turno con el proveedor externo. "
                    "Mantendré la conversación segura y sin aplicar cambios."
                ),
            ),
            intent=AssistantIntent(name=AssistantIntentName.UNKNOWN, confidence=0.0),
            requires_human_review=True,
            tool_results=tuple(tool_results or ()),
            metadata={
                "engine": self.config.engine_name,
                "provider": provider,
                "provider_model": model_name,
                "provider_error_code": "llm_provider_error",
                "provider_error_type": error_type,
                "tools_executed": bool(tools_executed),
            },
        )
        audit_snapshot = build_audit_snapshot(
            response=response,
            engine=self.config.engine_name,
            provider=provider,
            latency_ms=latency_ms,
            tools_executed=bool(tools_executed),
            error_code="llm_provider_error",
            error_type=error_type,
        )
        metadata = {
            **dict(response.metadata),
            "provider_latency_ms": latency_ms,
            "audit_version": audit_snapshot.version,
            "audit": audit_snapshot.as_dict(),
        }
        return AssistantStructuredResponse(
            assistant_message=response.assistant_message,
            intent=response.intent,
            tool_requests=response.tool_requests,
            tool_results=response.tool_results,
            proposal_ids=response.proposal_ids,
            requires_human_review=response.requires_human_review,
            metadata=metadata,
        )


    def _credit_blocked_response(
        self,
        *,
        credit_check: AICreditCheck,
        latency_ms: int | None = None,
    ) -> AssistantStructuredResponse:
        response = AssistantStructuredResponse(
            assistant_message=AssistantMessage(
                role=AssistantMessageRole.ASSISTANT,
                content=(
                    "No pude procesar este turno porque la asistencia IA alcanzó "
                    "el límite de créditos configurado para tu plan."
                ),
            ),
            intent=AssistantIntent(name=AssistantIntentName.UNKNOWN, confidence=0.0),
            requires_human_review=True,
            metadata={
                "engine": self.config.engine_name,
                "provider": getattr(self.llm_client, "provider_name", "unknown"),
                "ai_credit_blocked": True,
                "ai_credit_check": credit_check.as_metadata(),
                "tools_executed": False,
            },
        )
        audit_snapshot = build_audit_snapshot(
            response=response,
            engine=self.config.engine_name,
            provider=getattr(self.llm_client, "provider_name", "unknown"),
            latency_ms=latency_ms,
            tools_executed=False,
            error_code=credit_check.reason or "ai_credit_quota_exceeded",
            error_type="ai_credit_quota",
        )
        metadata = {
            **dict(response.metadata),
            "provider_latency_ms": latency_ms,
            "audit_version": audit_snapshot.version,
            "audit": audit_snapshot.as_dict(),
        }
        return AssistantStructuredResponse(
            assistant_message=response.assistant_message,
            intent=response.intent,
            tool_requests=response.tool_requests,
            tool_results=response.tool_results,
            proposal_ids=response.proposal_ids,
            requires_human_review=response.requires_human_review,
            metadata=metadata,
        )


    def _limit_blocked_response(
        self,
        *,
        violation: AILimitViolation,
        latency_ms: int | None = None,
        tool_results: Sequence[AssistantToolResult] = (),
        tools_executed: bool = False,
    ) -> AssistantStructuredResponse:
        response = AssistantStructuredResponse(
            assistant_message=AssistantMessage(
                role=AssistantMessageRole.ASSISTANT,
                content=(
                    "No pude enviar este turno al proveedor externo porque supera un "
                    "límite técnico de protección. Reduce el contexto o intenta con una "
                    "solicitud más específica."
                ),
            ),
            intent=AssistantIntent(name=AssistantIntentName.UNKNOWN, confidence=0.0),
            requires_human_review=True,
            tool_results=tuple(tool_results or ()),
            metadata={
                "engine": self.config.engine_name,
                "provider": getattr(self.llm_client, "provider_name", "unknown"),
                "technical_limit_blocked": True,
                "technical_limit_error_code": violation.error_code,
                "technical_limit_message": violation.message,
                "technical_limit_details": dict(violation.details or {}),
                "tools_executed": bool(tools_executed),
            },
        )
        audit_snapshot = build_audit_snapshot(
            response=response,
            engine=self.config.engine_name,
            provider=getattr(self.llm_client, "provider_name", "unknown"),
            latency_ms=latency_ms,
            tools_executed=bool(tools_executed),
            error_code=violation.error_code,
            error_type="technical_limit",
        )
        metadata = {
            **dict(response.metadata),
            "provider_latency_ms": latency_ms,
            "audit_version": audit_snapshot.version,
            "audit": audit_snapshot.as_dict(),
        }
        return AssistantStructuredResponse(
            assistant_message=response.assistant_message,
            intent=response.intent,
            tool_requests=response.tool_requests,
            tool_results=response.tool_results,
            proposal_ids=response.proposal_ids,
            requires_human_review=response.requires_human_review,
            metadata=metadata,
        )


    def _tool_results_local_ack_response(
        self,
        *,
        provider_response: LLMProviderResponse,
        tool_results: Sequence[AssistantToolResult],
        violation: AILimitViolation,
        latency_ms: int | None = None,
        tool_loop_iterations: int = 0,
        first_provider_response_id: str = "",
    ) -> AssistantStructuredResponse:
        """Return a user-safe response when tool results succeeded but follow-up is too large."""

        acknowledgement = _local_acknowledgement_from_tool_results(tool_results)
        logger.warning(
            "AI Assistant post-tool follow-up degraded by technical limit: "
            "error_code=%s tool_results=%s",
            violation.error_code,
            len(tuple(tool_results or ())),
        )

        parse_result = AssistantProviderParseResult(
            response=AssistantStructuredResponse(
                assistant_message=AssistantMessage(
                    role=AssistantMessageRole.ASSISTANT,
                    content=acknowledgement,
                ),
                intent=AssistantIntent(
                    name=AssistantIntentName.CAPTURE_NUTRITION_BRIEF,
                    confidence=0.75,
                    summary="My Scoope executed draft tools and answered locally because the provider follow-up exceeded technical limits.",
                ),
                tool_requests=(),
                requires_human_review=False,
                metadata={
                    "provider_response_was_json": True,
                    "tool_followup_local_ack": True,
                    "tool_followup_local_ack_policy": "state_ack_only.v2",
                    "post_tool_degraded": True,
                    "post_tool_degradation_reason": "technical_limit",
                    "technical_limit_blocked_after_tools": True,
                    "technical_limit_error_code": violation.error_code,
                    "technical_limit_details": dict(violation.details or {}),
                },
            ),
            was_json=True,
        )
        return self._with_policy_metadata(
            parse_result=parse_result,
            provider_response=provider_response,
            tool_results=tool_results,
            latency_ms=latency_ms,
            tools_executed=True,
            tool_loop_iterations=tool_loop_iterations,
            first_provider_response_id=first_provider_response_id,
        )


    def _tool_results_provider_failure_response(
        self,
        *,
        provider_response: LLMProviderResponse,
        tool_results: Sequence[AssistantToolResult],
        tool_requests: Sequence[AssistantToolRequest],
        error: LLMProviderError,
        latency_ms: int | None = None,
        tool_loop_iterations: int = 0,
        first_provider_response_id: str = "",
    ) -> AssistantStructuredResponse:
        """Complete a turn safely when only the post-tool provider call fails.

        This is a transport fallback, not a deterministic conversational
        co-author. My Scoope already has the provider-native function call and
        a validated local result, so it can communicate that result without
        inventing new facts, questions or state transitions.
        """

        logger.error(
            "AI Assistant post-tool follow-up degraded: provider=%s error_type=%s "
            "status=%s code=%s param=%s request_id=%s tool_results=%s",
            getattr(self.llm_client, "provider_name", "unknown"),
            error.__class__.__name__,
            getattr(error, "status_code", None),
            getattr(error, "error_code", ""),
            getattr(error, "error_param", ""),
            getattr(error, "request_id", ""),
            len(tuple(tool_results or ())),
        )

        parse_result = AssistantProviderParseResult(
            response=AssistantStructuredResponse(
                assistant_message=AssistantMessage(
                    role=AssistantMessageRole.ASSISTANT,
                    content=_local_acknowledgement_from_tool_results(tool_results),
                ),
                intent=_intent_for_native_tool_requests(tool_requests),
                tool_requests=(),
                requires_human_review=False,
                metadata={
                    "provider_response_was_json": False,
                    "tool_followup_local_ack": True,
                    "tool_followup_local_ack_policy": "state_ack_only.v2",
                    "post_tool_degraded": True,
                    "post_tool_degradation_reason": "provider_followup_failed",
                    "provider_tool_followup_failed": True,
                    "provider_tool_followup_error_type": error.__class__.__name__,
                    **_provider_followup_error_metadata(error),
                },
            ),
            was_json=False,
        )
        return self._with_policy_metadata(
            parse_result=parse_result,
            provider_response=provider_response,
            tool_results=tool_results,
            latency_ms=latency_ms,
            tools_executed=True,
            tool_loop_iterations=tool_loop_iterations,
            first_provider_response_id=first_provider_response_id,
            tool_requests=tool_requests,
        )


    def _with_usage_observability(
        self,
        *,
        request: AssistantTurnRequest,
        response: AssistantStructuredResponse,
        provider_responses: Sequence[LLMProviderResponse],
        latency_ms: int | None,
        status: str,
        error_type: str = "",
        tools_executed: bool = False,
    ) -> AssistantStructuredResponse:
        usage_summary = self.usage_recorder.record_turn(
            request=request,
            response=response,
            provider_responses=provider_responses,
            latency_ms=latency_ms,
            status=status,
            error_type=error_type,
            tools_executed=tools_executed,
        )
        metadata = {
            **dict(response.metadata),
            "usage_observability": dict(usage_summary or {}),
        }
        if bool(request.metadata.get("debug_ai_assistant")):
            metadata["debug_provider_responses"] = [
                {
                    "provider": item.provider,
                    "model": item.model,
                    "response_id": item.response_id,
                    "text": item.normalized_text,
                    "usage": sanitize_audit_value(dict(item.usage or {})),
                }
                for item in tuple(provider_responses or ())
            ]
            metadata["debug_status"] = status
            metadata["debug_error_type"] = error_type
        return AssistantStructuredResponse(
            assistant_message=response.assistant_message,
            intent=response.intent,
            tool_requests=response.tool_requests,
            tool_results=response.tool_results,
            proposal_ids=response.proposal_ids,
            requires_human_review=response.requires_human_review,
            metadata=metadata,
        )


    def _llm_client_for_route(self, model_route: AIModelRoute) -> LLMClient:
        if self._llm_client_was_injected:
            return self.llm_client
        return get_llm_client(provider_name=model_route.provider, model_name=model_route.model)



    def _resolve_tool_results(
        self,
        request: AssistantTurnRequest,
        tool_requests: Sequence[AssistantToolRequest],
        *,
        prior_tool_results: Sequence[AssistantToolResult] = (),
    ) -> tuple[AssistantToolResult, ...]:
        if not tool_requests:
            return ()

        tool_user = _tool_user_from_request(request)
        results: list[AssistantToolResult] = []
        normalized_tool_requests = tuple(tool_requests or ())
        max_tool_requests = self.config.turn_limits.max_tool_requests_per_turn
        executable_tool_requests = normalized_tool_requests[:max_tool_requests]
        overflow_tool_requests = normalized_tool_requests[max_tool_requests:]

        for raw_tool_request in executable_tool_requests:
            tool_request = _enrich_draft_tool_request_from_context(
                raw_tool_request,
                context=request.context,
                prior_tool_results=(*prior_tool_results, *results),
            )
            selection_error = tool_selection_reason_error(tool_request.metadata)
            if selection_error:
                results.append(
                    _tool_selection_reason_blocked_result(
                        tool_request,
                        error_code=selection_error,
                    )
                )
                continue
            validation_result = self.tool_validator(tool_request)
            if validation_result.status != AssistantToolStatus.PENDING:
                results.append(validation_result)
                continue
            if tool_user is None:
                results.append(_missing_user_tool_result(tool_request))
                continue
            results.append(self._execute_validated_tool_request(tool_request, user=tool_user))
        for tool_request in overflow_tool_requests:
            results.append(_tool_requests_limit_result(tool_request, max_tool_requests=max_tool_requests))
        return tuple(results)

    def _execute_validated_tool_request(
        self,
        tool_request: AssistantToolRequest,
        *,
        user: Any,
    ) -> AssistantToolResult:
        spec = get_tool_spec(tool_request.tool_name)
        if spec.category == AssistantToolCategory.COMMIT:
            return self.profile_commit_tool_executor.execute(tool_request, user=user)
        if spec.category == AssistantToolCategory.DRAFT:
            return self.profile_draft_tool_executor.execute(tool_request, user=user)
        if spec.category == AssistantToolCategory.PROPOSAL:
            if not self.config.enable_reviewable_proposal_tools:
                return _proposal_tools_disabled_result(tool_request)
            return self.reviewable_proposal_tool_executor.execute(tool_request, user=user)
        if spec.category == AssistantToolCategory.VALIDATION:
            return self.validation_tool_executor.execute(tool_request, user=user)
        return self.read_only_tool_executor.execute(tool_request, user=user)

    def _tool_results_prompt(
        self,
        tool_results: Sequence[AssistantToolResult],
        *,
        remaining_tool_iterations: int = 0,
    ) -> str:
        payload = {
            "tool_loop": "controlled_tools.v1",
            "tool_results": [
                sanitize_provider_context(result.as_dict())
                for result in tuple(tool_results or ())
            ],
            "policy": {
                "tool_results_are_controlled_by_my_scoope": True,
                "tool_results_update_conversation_memory_after_the_turn": True,
                "assistant_text_must_not_contradict_tool_results": True,
                "writes_are_still_disabled": True,
                "profile_draft_tools_are_non_persistent": True,
                "preference_draft_tools_are_non_persistent": True,
                "proposal_preference_tools_are_proposal_scoped_only": True,
                "profile_commit_tools_require_trusted_user_approval": True,
                "profile_persistence_requires_explicit_user_approval": True,
                "validation_tools_may_compute_comparisons": True,
                "proposal_creation_is_still_disabled": not self.config.enable_reviewable_proposal_tools,
                "reviewable_proposal_tools_may_create_proposals": self.config.enable_reviewable_proposal_tools,
                "created_proposals_still_require_human_review": True,
                "remaining_tool_iterations_after_this_followup": max(0, int(remaining_tool_iterations)),
                "may_request_more_tools_this_turn": remaining_tool_iterations > 0,
                "do_not_request_more_tools_this_turn": remaining_tool_iterations <= 0,
            },
        }
        return json.dumps(payload, ensure_ascii=False, sort_keys=True)

    def _compact_tool_results_prompt(
        self,
        tool_results: Sequence[AssistantToolResult],
    ) -> str:
        """Return the smallest safe post-tool payload for the compact fallback."""

        payload = {
            "tool_results": [
                sanitize_provider_context(result.as_dict())
                for result in tuple(tool_results or ())
            ],
            "policy": {
                "source_of_truth": True,
                "no_more_tools": True,
                "cards_are_visible": True,
                "do_not_echo_fields": True,
                "explain_consequence_not_payload": True,
            },
        }
        return json.dumps(payload, ensure_ascii=False, sort_keys=True)

    def _history_messages(self, history: Sequence[AssistantMessage]) -> list[LLMMessage]:
        allowed_roles = {
            AssistantMessageRole.SYSTEM: "system",
            AssistantMessageRole.DEVELOPER: "developer",
            AssistantMessageRole.USER: "user",
            AssistantMessageRole.ASSISTANT: "assistant",
        }
        bounded_history = list(history or ())[-self.config.max_history_messages :]
        messages: list[LLMMessage] = []
        for message in bounded_history:
            role = allowed_roles.get(message.role)
            if role and message.content:
                messages.append(LLMMessage(role=role, content=bounded_text(message.content, max_chars=self.config.turn_limits.max_message_chars)))
        return messages

    def _system_prompt(self) -> str:
        return "\n".join(
            [
                "Eres el asistente AI de My Scoope: competente, directo, cálido y natural.",
                *system_domain_anchor_lines(),
                "Tu trabajo es llevar la conversación a un resultado útil, no ejecutar un cuestionario.",
                "Usa el historial y el workspace actual como memoria. Nunca vuelvas a pedir un dato conocido.",
                "blocking_fields contiene exactamente lo imprescindible. Si tiene elementos, pregunta solo por el menor bloqueo que no puedas inferir.",
                "Los campos opcionales nunca bloquean: My Scoope aplica los product_defaults del workspace.",
                "Si active_objective pide una propuesta y blocking_fields está vacío, créala en este mismo turno con la herramienta disponible. No te limites a decir que ya está lista.",
                "Cuando el usuario entregue o corrija datos operacionales, regístralos con la herramienta tipada antes de confirmarlos.",
                "Después de resultados de herramientas, continúa hasta completar el objetivo o hasta encontrar un bloqueo real.",
                "Una propuesta es revisable: nunca afirmes que fue aplicada ni inventes IDs.",
                "No menciones nombres de herramientas, contratos internos, JSON ni políticas al usuario.",
                "Responde en el idioma del usuario. Sé breve cuando baste, y explica lo necesario cuando entregue valor.",
                *system_response_style_lines(),
            ]
        )

    def _context_prompt(self, context: Mapping[str, Any]) -> str:
        safe_context = sanitize_provider_context(context)
        payload = {
            "my_scoope_workspace": safe_context,
            "instruction": (
                "Trata los valores presentes como conocidos, los blocking_fields "
                "como la única carencia obligatoria y los resultados de tools como fuente de verdad."
            ),
        }
        text = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        if len(text) <= self.config.turn_limits.max_context_chars:
            return text
        fallback_payload = {
            "provider_context": {
                "context_omitted_by_limit": True,
                "available_context_keys": sorted(str(key) for key in safe_context.keys()),
            },
            "context_was_omitted_due_to_technical_limit": True,
            "max_context_chars": self.config.turn_limits.max_context_chars,
        }
        return json.dumps(fallback_payload, ensure_ascii=False, sort_keys=True)

    def _provider_tools_for_request(
        self,
        request: AssistantTurnRequest,
    ) -> tuple[Mapping[str, Any], ...]:
        """Expose only capabilities that the orchestrator can execute.

        Reviewable proposal tools are intentionally absent when their feature
        flag is disabled. Sending unavailable schemas wastes context and can
        make the model select an operation My Scoope will reject. The selector
        does not infer the user's next conversational step; it only mirrors the
        runtime capability boundary.
        """

        available = tuple(self.provider_tool_specs())
        user_text = str(request.user_message.content or "").strip().lower()
        if (
            str(request.context.get("surface") or "") == "ai_nutrition_intake"
            and not _requests_existing_product_operation(user_text)
        ):
            work_progress = _intake_work_progress(request.context)
            if (
                self.config.enable_reviewable_proposal_tools
                and _work_progress_has_active_proposal_objective(work_progress)
                and not tuple(work_progress.get("blocking_fields") or ())
            ):
                proposal_tool = _provider_tool_by_name(
                    available,
                    TOOL_CREATE_NUTRITION_ENGINE_DAILYPLAN_PROPOSAL_FROM_DRAFTS,
                )
                return (proposal_tool,) if proposal_tool is not None else ()

            return tuple(
                provider_spec
                for provider_spec in available
                if str(provider_spec.get("name") or "") in _AI_NUTRITION_INTAKE_CORE_TOOLS
                and (
                    self.config.enable_reviewable_proposal_tools
                    or str(provider_spec.get("name") or "")
                    != TOOL_CREATE_NUTRITION_ENGINE_DAILYPLAN_PROPOSAL_FROM_DRAFTS
                )
            )

        selected: list[Mapping[str, Any]] = []
        for provider_spec in available:
            name = str(provider_spec.get("name") or "")
            if not _expanded_product_tool_relevant(name, user_text=user_text):
                continue
            if not _reviewable_proposal_tool_relevant(name, user_text=user_text):
                continue
            if not self.config.enable_reviewable_proposal_tools:
                try:
                    local_spec = get_tool_spec(name)
                except ValueError:
                    local_spec = None
                if local_spec is not None and local_spec.category == AssistantToolCategory.PROPOSAL:
                    continue
            selected.append(provider_spec)
        return tuple(selected)

    def _initial_tool_choice(
        self,
        request: AssistantTurnRequest,
        tools: Sequence[Mapping[str, Any]],
    ) -> str | None:
        if not tools:
            return None
        work_progress = _intake_work_progress(request.context)
        if (
            _work_progress_has_active_proposal_objective(work_progress)
            and not tuple(work_progress.get("blocking_fields") or ())
            and _provider_tool_by_name(
                tools,
                TOOL_CREATE_NUTRITION_ENGINE_DAILYPLAN_PROPOSAL_FROM_DRAFTS,
            )
            is not None
        ):
            return "required"
        return "auto"

    def _proposal_ready_after_tool_results(
        self,
        request: AssistantTurnRequest,
        tool_results: Sequence[AssistantToolResult],
    ) -> bool:
        work_progress = _intake_work_progress(request.context)
        if not _work_progress_has_active_proposal_objective(work_progress):
            return False
        if not self.config.enable_reviewable_proposal_tools:
            return False

        workspace = _intake_workspace(request.context)
        try:
            from notas.application.ai_intake.nutrition_brief import required_proposal_fields
            from notas.application.ai_tools.proposal_tools import (
                build_nutrition_brief_from_ai_drafts,
            )

            brief = build_nutrition_brief_from_ai_drafts(
                profile_draft=_latest_draft_for_tool(
                    "profile_draft",
                    context=request.context,
                    prior_tool_results=tool_results,
                ),
                preference_draft=_latest_draft_for_tool(
                    "preference_draft",
                    context=request.context,
                    prior_tool_results=tool_results,
                ),
                proposal_preferences=_latest_draft_for_tool(
                    "proposal_preferences",
                    context=request.context,
                    prior_tool_results=tool_results,
                ),
                current_nutrition_brief=dict(
                    workspace.get("current_nutrition_brief") or {}
                ),
                raw_prompt=request.user_message.content,
            )
        except (TypeError, ValueError):
            return False
        return not required_proposal_fields(brief)

    def _developer_prompt(
        self,
        tool_specs: Sequence[Mapping[str, Any]] | None = None,
    ) -> str:
        tool_specs = tuple(self.provider_tool_specs() if tool_specs is None else tool_specs)
        payload = {
            "native_function_tools": True,
            "product_context": developer_product_capability_policy(),
            "response_style_policy": developer_response_style_policy(),
            "success_criteria": [
                "answer_the_actual_request",
                "never_repeat_known_information",
                "use_at_most_one_blocking_question",
                "complete_a_ready_active_objective_in_the_same_turn",
            ],
            "available_operations": [
                str(spec.get("name") or "") for spec in tool_specs
            ],
            "rules": {
                "tool_results_are_source_of_truth": True,
                "new_facts_require_matching_update_call": True,
                "proposal_cards_are_rendered_automatically": True,
                "proposal_requires_user_review": True,
                "visible_response_is_natural_text": True,
            },
        }
        return json.dumps(payload, ensure_ascii=False, sort_keys=True)


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


def _loads_json_object(text: str) -> tuple[dict[str, Any] | None, str]:
    if not text:
        return None, "empty_provider_response"
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = _strip_code_fence(cleaned)
    try:
        payload = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        return None, f"invalid_json:{exc.msg}"
    if not isinstance(payload, dict):
        return None, "json_root_must_be_object"
    return payload, ""


def _strip_code_fence(text: str) -> str:
    lines = [line for line in text.splitlines() if not line.strip().startswith("```")]
    return "\n".join(lines).strip()


def _extract_jsonish_assistant_content(text: str) -> str:
    """Best-effort extraction for malformed provider JSON.

    The visible chat should never show the full structured payload just because
    the provider returned a near-JSON object with a small syntax issue, such as
    a trailing comma. This fallback only extracts the display text and leaves the
    turn marked as non-JSON for audit/observability.
    """

    cleaned = (text or "").strip()
    if not cleaned:
        return ""
    if cleaned.startswith("```"):
        cleaned = _strip_code_fence(cleaned)

    for field_name in ("content", "assistant_text", "message"):
        value = _extract_jsonish_string_field(cleaned, field_name)
        if value:
            return value
    return ""


def _extract_jsonish_string_field(text: str, field_name: str) -> str:
    marker = f'"{field_name}"'
    field_index = text.find(marker)
    if field_index < 0:
        return ""
    colon_index = text.find(":", field_index + len(marker))
    if colon_index < 0:
        return ""

    candidate = text[colon_index + 1 :].lstrip()
    if not candidate.startswith('"'):
        return ""

    try:
        value, _ = json.JSONDecoder().raw_decode(candidate)
    except json.JSONDecodeError:
        return ""
    if not isinstance(value, str):
        return ""
    return value.strip()


def _loads_json_mapping(value: Any, *, field_name: str) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    try:
        parsed = json.loads(str(value or "{}"))
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise AssistantContractError(f"{field_name} must contain a valid JSON object string.") from exc
    if not isinstance(parsed, Mapping):
        raise AssistantContractError(f"{field_name} must contain a JSON object.")
    return dict(parsed)


def _coerce_assistant_message(payload: Mapping[str, Any]) -> AssistantMessage:
    assistant_message = payload.get("assistant_message")
    if isinstance(assistant_message, Mapping):
        content = assistant_message.get("content") or assistant_message.get("text") or ""
    else:
        content = assistant_message or payload.get("assistant_text") or payload.get("message") or ""
    return AssistantMessage(role=AssistantMessageRole.ASSISTANT, content=str(content or ""))


def _coerce_intent(value: Any) -> AssistantIntent:
    if not isinstance(value, Mapping):
        return AssistantIntent(name=AssistantIntentName.UNKNOWN, confidence=0.0)
    slots = value.get("slots")
    if slots is None and "slots_json" in value:
        slots = _loads_json_mapping(value.get("slots_json"), field_name="intent.slots_json")
    return AssistantIntent(
        name=value.get("name") or AssistantIntentName.UNKNOWN,
        confidence=value.get("confidence") or 0.0,
        summary=value.get("summary") or "",
        slots=slots or {},
        missing_slots=value.get("missing_slots") or (),
        safety_flags=value.get("safety_flags") or (),
    )


def _coerce_tool_requests(value: Any) -> tuple[AssistantToolRequest, ...]:
    if not value:
        return ()
    if not isinstance(value, list | tuple):
        raise AssistantContractError("tool_requests must be a list.")

    requests: list[AssistantToolRequest] = []
    for index, item in enumerate(value, start=1):
        if not isinstance(item, Mapping):
            raise AssistantContractError("Each tool request must be an object.")
        arguments = item.get("arguments")
        if arguments is None and "arguments_json" in item:
            arguments = _loads_json_mapping(
                item.get("arguments_json"),
                field_name=f"tool_requests[{index}].arguments_json",
            )
        requests.append(
            AssistantToolRequest(
                tool_name=item.get("tool_name") or item.get("name") or "",
                arguments=arguments or {},
                request_id=item.get("request_id") or f"tool_request_{index}",
                reason=item.get("reason") or "",
            )
        )
    return tuple(requests)


def _coerce_requires_human_review(payload: Mapping[str, Any]) -> bool:
    value = payload.get("requires_human_review")
    if value is None:
        return True
    return bool(value)


def _settings_int(name: str, default: int) -> int:
    try:
        return int(getattr(settings, name, default))
    except (TypeError, ValueError):
        return default


def _settings_choice(name: str, default: str, *, allowed: set[str]) -> str:
    value = str(getattr(settings, name, default) or default).strip().lower()
    return value if value in allowed else default


def _settings_bool(name: str, default: bool) -> bool:
    value = getattr(settings, name, default)
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _elapsed_ms(started_at: float) -> int:
    return max(0, int(round((time.perf_counter() - started_at) * 1000)))
