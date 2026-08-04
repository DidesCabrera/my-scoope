from __future__ import annotations

import json
import logging
import time
from typing import Any, Callable, Mapping, Sequence

from ai_assistant.application.audit import build_audit_snapshot, sanitize_audit_value
from ai_assistant.application.context_builder import sanitize_provider_context
from ai_assistant.application.credits import AICreditCheck, DjangoAICreditService
from ai_assistant.application.limits import (
    AILimitViolation,
    bounded_text,
    estimate_provider_request_tokens,
    validate_provider_request_limits,
)
from ai_assistant.application.model_routing import (
    AIModelRoute,
    resolve_model_route_for_turn,
    route_max_output_tokens,
)
from ai_assistant.application.orchestrator_helpers import (
    _coerce_provider_tool_calls,
    _enrich_draft_tool_request_from_context,
    _intent_for_native_tool_requests,
    _intent_requires_human_review,
    _local_acknowledgement_from_tool_results,
    _missing_user_tool_result,
    _output_tokens_for_request,
    _proposal_ids_from_tool_results,
    _proposal_tool_results,
    _proposal_tools_disabled_result,
    _provider_declared_tools_required,
    _provider_followup_error_metadata,
    _provider_incomplete_reason,
    _provider_tool_by_name,
    _provider_tool_outputs,
    _tool_requests_limit_result,
    _tool_selection_reason_blocked_result,
    _tool_user_from_request,
)
from ai_assistant.application.orchestrator_runtime import AssistantOrchestratorConfig
from ai_assistant.application.orchestrator_runtime import elapsed_ms as _elapsed_ms
from ai_assistant.application.product_context import (
    developer_product_capability_policy,
    system_domain_anchor_lines,
)
from ai_assistant.application.product_ports import get_ai_product_bindings
from ai_assistant.application.provider_parsing import (
    AssistantProviderParseResult,
    _coerce_assistant_message,
    _coerce_intent,
    _coerce_requires_human_review,
    _coerce_tool_requests,
    _extract_jsonish_assistant_content,
    _loads_json_object,
)
from ai_assistant.application.response_style import (
    developer_response_style_policy,
    system_response_style_lines,
)
from ai_assistant.application.tool_governance import (
    extract_provider_tool_selection_reason,
    safe_tool_selection_observability,
    tool_selection_reason_error,
)
from ai_assistant.application.tool_selection import (
    initial_tool_choice,
    proposal_ready_after_tool_results,
    select_provider_tools,
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
    AssistantToolCategory,
    ProfileCommitToolExecutor,
    ProfileDraftToolExecutor,
    ReadOnlyToolExecutor,
    ReviewableProposalToolExecutor,
    ValidationToolExecutor,
    get_tool_spec,
    list_provider_tool_specs,
    validate_tool_request,
)
from ai_assistant.application.usage import AIUsageRecorder, DjangoAIUsageRecorder
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


class AssistantOrchestratorError(RuntimeError):
    """Raised when the LLM orchestrator cannot produce a safe response."""


ToolValidator = Callable[[AssistantToolRequest], AssistantToolResult]
ProviderToolSpecProvider = Callable[[], list[dict[str, Any]]]


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
        """Process one semantic assistant turn through the provider coordinator."""

        from ai_assistant.application.orchestrator_turn import run_provider_turn

        return run_provider_turn(self, request)

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

        return select_provider_tools(
            request,
            available=self.provider_tool_specs(),
            enable_reviewable_proposal_tools=self.config.enable_reviewable_proposal_tools,
        )

    def _initial_tool_choice(
        self,
        request: AssistantTurnRequest,
        tools: Sequence[Mapping[str, Any]],
    ) -> str | None:
        return initial_tool_choice(request, tools)

    def _proposal_ready_after_tool_results(
        self,
        request: AssistantTurnRequest,
        tool_results: Sequence[AssistantToolResult],
    ) -> bool:
        return proposal_ready_after_tool_results(
            request,
            tool_results,
            enable_reviewable_proposal_tools=self.config.enable_reviewable_proposal_tools,
            product_bindings=get_ai_product_bindings(),
        )

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
