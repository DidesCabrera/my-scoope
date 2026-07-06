from __future__ import annotations

import json
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
from ai_assistant.application.usage import AIUsageRecorder, DjangoAIUsageRecorder
from ai_assistant.application.tools import (
    AssistantToolCategory,
    ReadOnlyToolExecutor,
    ReviewableProposalToolExecutor,
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
    get_llm_client,
)


class AssistantOrchestratorError(RuntimeError):
    """Raised when the LLM orchestrator cannot produce a safe response."""


ToolValidator = Callable[[AssistantToolRequest], AssistantToolResult]
ProviderToolSpecProvider = Callable[[], list[dict[str, Any]]]


@dataclass(frozen=True)
class AssistantOrchestratorConfig:
    """Runtime limits for the external LLM orchestrator v1.

    The orchestrator is intentionally conservative: it sends only a bounded
    amount of history, asks for JSON, and allows at most one controlled tool
    execution loop. Reviewable proposal tools require explicit opt-in and never
    apply changes directly.
    """

    max_history_messages: int = 8
    max_output_tokens: int = 900
    max_tool_loop_iterations: int = 1
    enable_reviewable_proposal_tools: bool = False
    max_input_tokens: int = 6000
    max_context_chars: int = 8000
    max_message_chars: int = 2000
    max_tool_requests_per_turn: int = 3
    engine_name: str = "external_llm_orchestrator_v1"
    response_format_version: str = "ai_assistant_structured_response.v1"

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
        read_only_tool_executor: ReadOnlyToolExecutor | None = None,
        reviewable_proposal_tool_executor: ReviewableProposalToolExecutor | None = None,
        config: AssistantOrchestratorConfig | None = None,
        usage_recorder: AIUsageRecorder | None = None,
        credit_service: DjangoAICreditService | None = None,
    ):
        self._llm_client_was_injected = llm_client is not None
        self.llm_client = llm_client or get_llm_client()
        self.tool_validator = tool_validator
        self.provider_tool_specs = provider_tool_specs
        self.read_only_tool_executor = read_only_tool_executor or ReadOnlyToolExecutor()
        self.reviewable_proposal_tool_executor = reviewable_proposal_tool_executor or ReviewableProposalToolExecutor()
        self.config = config or AssistantOrchestratorConfig.from_settings()
        self.usage_recorder = usage_recorder or DjangoAIUsageRecorder()
        self.credit_service = credit_service or DjangoAICreditService()

    def continue_turn(self, request: AssistantTurnRequest) -> AssistantStructuredResponse:
        """Process one semantic assistant turn with one controlled tool loop."""

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

        parse_result = self.parse_provider_response(provider_response)
        tool_results = self._resolve_tool_results(request, parse_result.response.tool_requests)
        ok_tool_results = tuple(result for result in tool_results if result.ok)

        if ok_tool_results and self.config.max_tool_loop_iterations > 0:
            final_provider_request = self.build_tool_followup_provider_request(
                request=request,
                first_response=parse_result.response,
                tool_results=tool_results,
                model_route=model_route,
            )
            followup_limit_violation = validate_provider_request_limits(
                final_provider_request,
                limits=self.config.turn_limits,
            )
            if followup_limit_violation is not None:
                latency_ms = _elapsed_ms(started_at)
                response = self._limit_blocked_response(
                    violation=followup_limit_violation,
                    latency_ms=latency_ms,
                    tool_results=tool_results,
                    tools_executed=True,
                )
                return self._with_usage_observability(
                    request=request,
                    response=response,
                    provider_responses=(provider_response,),
                    latency_ms=latency_ms,
                    status="blocked",
                    error_type=followup_limit_violation.error_code,
                    tools_executed=True,
                )

            try:
                final_provider_response = turn_llm_client.generate(final_provider_request)
            except LLMProviderError as exc:
                latency_ms = _elapsed_ms(started_at)
                response = self._provider_error_response(
                    error=exc,
                    latency_ms=latency_ms,
                    tool_results=tool_results,
                    tools_executed=True,
                )
                return self._with_usage_observability(
                    request=request,
                    response=response,
                    provider_responses=(provider_response,),
                    latency_ms=latency_ms,
                    status="error",
                    error_type=exc.__class__.__name__,
                    tools_executed=True,
                )

            final_parse_result = self.parse_provider_response(final_provider_response)
            followup_blocked_results = tuple(
                _max_iterations_tool_result(tool_request)
                for tool_request in final_parse_result.response.tool_requests
            )
            latency_ms = _elapsed_ms(started_at)
            response = self._with_policy_metadata(
                parse_result=final_parse_result,
                provider_response=final_provider_response,
                tool_results=(*tool_results, *followup_blocked_results),
                latency_ms=latency_ms,
                tools_executed=True,
                tool_loop_iterations=1,
                first_provider_response_id=provider_response.response_id,
            )
            return self._with_usage_observability(
                request=request,
                response=response,
                provider_responses=(provider_response, final_provider_response),
                latency_ms=latency_ms,
                status="completed",
                tools_executed=True,
            )

        latency_ms = _elapsed_ms(started_at)
        response = self._with_policy_metadata(
            parse_result=parse_result,
            provider_response=provider_response,
            tool_results=tool_results,
            latency_ms=latency_ms,
            tools_executed=False,
            tool_loop_iterations=0,
        )
        return self._with_usage_observability(
            request=request,
            response=response,
            provider_responses=(provider_response,),
            latency_ms=latency_ms,
            status="completed",
            tools_executed=False,
        )

    def build_provider_request(self, request: AssistantTurnRequest, *, model_route: AIModelRoute | None = None) -> LLMProviderRequest:
        """Map an internal semantic request to the transport-level LLM request."""

        messages: list[LLMMessage] = [
            LLMMessage(role="system", content=self._system_prompt()),
            LLMMessage(role="developer", content=self._developer_prompt()),
        ]
        if request.context:
            messages.append(LLMMessage(role="developer", content=self._context_prompt(request.context)))
        messages.extend(self._history_messages(request.history))
        messages.append(LLMMessage(role="user", content=request.user_message.content))

        model_route = model_route or resolve_model_route_for_turn(request)
        max_output_tokens = route_max_output_tokens(
            default_max_output_tokens=self.config.max_output_tokens,
            route=model_route,
        )

        return LLMProviderRequest(
            messages=messages,
            max_output_tokens=max_output_tokens,
            metadata={
                "engine": self.config.engine_name,
                "format": self.config.response_format_version,
                "local_context_keys": sorted(str(key) for key in request.context.keys()),
                "estimated_input_tokens": estimate_provider_request_tokens(
                    LLMProviderRequest(messages=messages, max_output_tokens=self.config.max_output_tokens)
                ),
                "model_route": model_route.as_metadata(),
                "technical_limits": {
                    "max_input_tokens": self.config.turn_limits.max_input_tokens,
                    "max_context_chars": self.config.turn_limits.max_context_chars,
                    "max_message_chars": self.config.turn_limits.max_message_chars,
                    "max_tool_requests_per_turn": self.config.turn_limits.max_tool_requests_per_turn,
                },
            },
        )


    def build_tool_followup_provider_request(
        self,
        *,
        request: AssistantTurnRequest,
        first_response: AssistantStructuredResponse,
        tool_results: Sequence[AssistantToolResult],
        model_route: AIModelRoute | None = None,
    ) -> LLMProviderRequest:
        """Build the second provider call after controlled tools were executed."""

        model_route = model_route or resolve_model_route_for_turn(request)
        messages = list(self.build_provider_request(request, model_route=model_route).messages)
        messages.append(
            LLMMessage(
                role="assistant",
                content=json.dumps(first_response.as_dict(), ensure_ascii=False, sort_keys=True),
            )
        )
        messages.append(LLMMessage(role="developer", content=self._tool_results_prompt(tool_results)))
        messages.append(
            LLMMessage(
                role="user",
                content=(
                    "Usa los tool_results de My Scoope para responder al usuario. "
                    "No solicites más tools en este turno. Devuelve JSON válido con tool_requests vacío."
                ),
            )
        )
        model_route = model_route or resolve_model_route_for_turn(request)
        max_output_tokens = route_max_output_tokens(
            default_max_output_tokens=self.config.max_output_tokens,
            route=model_route,
        )

        return LLMProviderRequest(
            messages=messages,
            max_output_tokens=max_output_tokens,
            metadata={
                "engine": self.config.engine_name,
                "format": self.config.response_format_version,
                "tool_loop": "controlled_tools.v1",
                "tool_results_count": len(tuple(tool_results or ())),
                "model_route": model_route.as_metadata(),
                "estimated_input_tokens": estimate_provider_request_tokens(
                    LLMProviderRequest(messages=messages, max_output_tokens=self.config.max_output_tokens)
                ),
            },
        )

    def parse_provider_response(self, provider_response: LLMProviderResponse) -> AssistantProviderParseResult:
        """Parse provider text into `AssistantStructuredResponse` with safe fallbacks."""

        text = provider_response.normalized_text
        payload, parse_error = _loads_json_object(text)
        if payload is None:
            return AssistantProviderParseResult(
                response=AssistantStructuredResponse(
                    assistant_message=AssistantMessage(
                        role=AssistantMessageRole.ASSISTANT,
                        content=text or "No pude interpretar una respuesta útil del proveedor.",
                    ),
                    intent=AssistantIntent(name=AssistantIntentName.UNKNOWN, confidence=0.0),
                    requires_human_review=True,
                    metadata={"provider_response_was_json": False},
                ),
                was_json=False,
                parse_error=parse_error,
            )

        ignored_provider_proposal_ids = tuple(payload.get("proposal_ids") or ())
        try:
            response = AssistantStructuredResponse(
                assistant_message=_coerce_assistant_message(payload),
                intent=_coerce_intent(payload.get("intent")),
                tool_requests=_coerce_tool_requests(payload.get("tool_requests")),
                tool_results=(),
                # Provider-supplied proposal ids are intentionally ignored. Only
                # future My Scoope tool execution may attach real proposals.
                proposal_ids=(),
                requires_human_review=_coerce_requires_human_review(payload),
                metadata={
                    "provider_response_was_json": True,
                    "provider_format": str(payload.get("format") or ""),
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
            )

        return AssistantProviderParseResult(
            response=response,
            was_json=True,
            ignored_provider_proposal_ids=ignored_provider_proposal_ids,
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
    ) -> AssistantStructuredResponse:
        blocked_tool_results = [result for result in tool_results if result.status == AssistantToolStatus.BLOCKED]
        proposal_ids = _proposal_ids_from_tool_results(tool_results)
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
        }
        if first_provider_response_id:
            metadata["first_provider_response_id"] = first_provider_response_id
        if parse_result.parse_error:
            metadata["provider_parse_error"] = parse_result.parse_error
        if parse_result.ignored_provider_proposal_ids:
            metadata["ignored_provider_proposal_ids"] = list(parse_result.ignored_provider_proposal_ids)

        requires_human_review = bool(
            parse_result.response.requires_human_review
            or parse_result.response.intent.is_write_intent
            or parse_result.response.tool_requests
            or blocked_tool_results
            or proposal_ids
            or parse_result.ignored_provider_proposal_ids
        )

        response = AssistantStructuredResponse(
            assistant_message=parse_result.response.assistant_message,
            intent=parse_result.response.intent,
            tool_requests=parse_result.response.tool_requests,
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
            ignored_provider_proposal_ids=parse_result.ignored_provider_proposal_ids,
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
    ) -> tuple[AssistantToolResult, ...]:
        if not tool_requests:
            return ()

        tool_user = _tool_user_from_request(request)
        results: list[AssistantToolResult] = []
        normalized_tool_requests = tuple(tool_requests or ())
        max_tool_requests = self.config.turn_limits.max_tool_requests_per_turn
        executable_tool_requests = normalized_tool_requests[:max_tool_requests]
        overflow_tool_requests = normalized_tool_requests[max_tool_requests:]

        for tool_request in executable_tool_requests:
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
        if spec.category == AssistantToolCategory.PROPOSAL:
            if not self.config.enable_reviewable_proposal_tools:
                return _proposal_tools_disabled_result(tool_request)
            return self.reviewable_proposal_tool_executor.execute(tool_request, user=user)
        return self.read_only_tool_executor.execute(tool_request, user=user)

    def _tool_results_prompt(self, tool_results: Sequence[AssistantToolResult]) -> str:
        payload = {
            "tool_loop": "controlled_tools.v1",
            "tool_results": [
                sanitize_provider_context(result.as_dict())
                for result in tuple(tool_results or ())
            ],
            "policy": {
                "tool_results_are_controlled_by_my_scoope": True,
                "writes_are_still_disabled": True,
                "proposal_creation_is_still_disabled": not self.config.enable_reviewable_proposal_tools,
                "reviewable_proposal_tools_may_create_proposals": self.config.enable_reviewable_proposal_tools,
                "created_proposals_still_require_human_review": True,
                "do_not_request_more_tools_this_turn": True,
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
                "Eres el AI Assistant de My Scoope.",
                "Interpreta al usuario y conversa con naturalidad, pero no eres fuente de verdad nutricional final.",
                "My Scoope calcula, valida, persiste y aplica cambios solo mediante servicios internos y revisión humana.",
                "No inventes IDs ni proposal_ids. No declares que una propuesta fue creada si no hay tool result de My Scoope.",
                "No uses food_catalog ni catalog_food_id. Las tools alimentarias solo aceptan IDs operacionales de notas.Food.",
                "No pidas ni propongas tools fuera de la allowlist entregada.",
                "Cuando recibas tool_results de My Scoope, úsalos como única fuente para esa información real.",
                "Responde siempre como JSON válido y sin markdown.",
            ]
        )

    def _context_prompt(self, context: Mapping[str, Any]) -> str:
        safe_context = sanitize_provider_context(context)
        payload = {
            "provider_context": safe_context,
            "context_policy": {
                "context_is_bounded": True,
                "context_is_read_only": True,
                "do_not_request_missing_private_data": True,
                "read_only_tools_may_run_internally": True,
                "reviewable_proposal_tools_require_orchestrator_opt_in": True,
                "writes_remain_disabled": True,
            },
        }
        text = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        if len(text) <= self.config.turn_limits.max_context_chars:
            return text
        fallback_payload = {
            "provider_context": {
                "context_omitted_by_limit": True,
                "available_context_keys": sorted(str(key) for key in safe_context.keys()),
            },
            "context_policy": {
                **payload["context_policy"],
                "context_was_omitted_due_to_technical_limit": True,
                "max_context_chars": self.config.turn_limits.max_context_chars,
            },
        }
        return json.dumps(fallback_payload, ensure_ascii=False, sort_keys=True)

    def _developer_prompt(self) -> str:
        schema = {
            "format": self.config.response_format_version,
            "assistant_message": {"content": "texto para mostrar al usuario"},
            "intent": {
                "name": "answer_question|ask_clarification|capture_nutrition_brief|create_meal_proposal|create_dailyplan_proposal|create_program_proposal|iterate_proposal|read_context|small_talk|unknown",
                "confidence": 0.0,
                "summary": "resumen breve",
                "slots": {},
                "missing_slots": [],
                "safety_flags": [],
            },
            "tool_requests": [
                {
                    "tool_name": "nombre_allowlist",
                    "arguments": {},
                    "request_id": "opcional",
                    "reason": "por qué se necesita",
                }
            ],
            "requires_human_review": True,
        }
        payload = {
            "response_schema": schema,
            "allowed_tools": self.provider_tool_specs(),
            "policy": {
                "tools_are_requests_only": True,
                "read_only_tools_may_be_executed_by_my_scoope": True,
                "reviewable_proposal_tools_enabled": self.config.enable_reviewable_proposal_tools,
                "proposal_tools_create_only_reviewable_nutrition_proposals": True,
                "proposal_tools_never_apply_changes": True,
                "tools_are_not_executed_by_the_model": True,
                "provider_proposal_ids_are_ignored": True,
                "food_catalog_is_forbidden": True,
            },
        }
        return json.dumps(payload, ensure_ascii=False, sort_keys=True)



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
        error_message="Patch 54 allows only one read-only/proposal tool loop per turn.",
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
    return AssistantIntent(
        name=value.get("name") or AssistantIntentName.UNKNOWN,
        confidence=value.get("confidence") or 0.0,
        summary=value.get("summary") or "",
        slots=value.get("slots") or {},
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
        requests.append(
            AssistantToolRequest(
                tool_name=item.get("tool_name") or item.get("name") or "",
                arguments=item.get("arguments") or {},
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


def _settings_bool(name: str, default: bool) -> bool:
    value = getattr(settings, name, default)
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _elapsed_ms(started_at: float) -> int:
    return max(0, int(round((time.perf_counter() - started_at) * 1000)))
