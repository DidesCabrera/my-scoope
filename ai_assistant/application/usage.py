from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any, Mapping, Protocol, Sequence

from django.conf import settings
from django.utils import timezone

from ai_assistant.domain import AssistantIntentName, AssistantStructuredResponse, AssistantTurnRequest
from ai_assistant.application.credits import DjangoAICreditService
from ai_assistant.infrastructure.providers import LLMProviderResponse

logger = logging.getLogger(__name__)

ACTION_ASSISTANT_CHAT = "assistant.chat"
ACTION_TOOL_CALL = "assistant.tool_call"
ACTION_CREATE_MEAL_PROPOSAL = "assistant.create_meal_proposal"
ACTION_CREATE_DAILYPLAN_PROPOSAL = "assistant.create_dailyplan_proposal"
ACTION_MODIFY_PROGRAM = "assistant.modify_program"


@dataclass(frozen=True)
class AIUsageTokenSummary:
    input_tokens: int | None = None
    cached_input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None

    def as_dict(self) -> dict[str, int | None]:
        return {
            "input_tokens": self.input_tokens,
            "cached_input_tokens": self.cached_input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
        }


class AIUsageRecorder(Protocol):
    def record_turn(
        self,
        *,
        request: AssistantTurnRequest,
        response: AssistantStructuredResponse,
        provider_responses: Sequence[LLMProviderResponse],
        latency_ms: int | None,
        status: str,
        error_type: str = "",
        tools_executed: bool = False,
    ) -> Mapping[str, Any]:
        """Persist or collect one sanitized AI usage event."""
        raise NotImplementedError


class DjangoAIUsageRecorder:
    """Persist usage observability in `AIUsageEvent` without blocking the turn.

    The recorder intentionally stores only sanitized economic/operational data:
    action type, provider/model, token counts, estimated cost, status and safe
    metadata. Prompts, tool arguments, headers, API keys and provider raw payloads
    are not persisted here.
    """

    def record_turn(
        self,
        *,
        request: AssistantTurnRequest,
        response: AssistantStructuredResponse,
        provider_responses: Sequence[LLMProviderResponse],
        latency_ms: int | None,
        status: str,
        error_type: str = "",
        tools_executed: bool = False,
    ) -> Mapping[str, Any]:
        if not getattr(settings, "AI_ASSISTANT_USAGE_OBSERVABILITY_ENABLED", True):
            return {"recorded": False, "disabled": True}

        provider_responses = tuple(provider_responses or ())
        tokens = aggregate_provider_usage(provider_responses)
        provider = _first_non_empty(response.metadata.get("provider"), *(item.provider for item in provider_responses))
        model = _first_non_empty(response.metadata.get("provider_model"), *(item.model for item in provider_responses))
        action_type = infer_action_type(request=request, response=response)
        cost = estimate_cost_usd(
            provider=provider,
            model=model,
            input_tokens=tokens.input_tokens,
            cached_input_tokens=tokens.cached_input_tokens,
            output_tokens=tokens.output_tokens,
        )
        user = _user_from_request(request)
        metadata = _safe_usage_metadata(request=request, response=response, tools_executed=tools_executed)
        summary: dict[str, Any] = {
            "recorded": False,
            "action_type": action_type,
            "provider": provider,
            "model": model,
            "status": status,
            "error_type": error_type,
            "estimated_cost_usd": str(cost) if cost is not None else None,
            **tokens.as_dict(),
        }

        try:
            from ai_assistant.models import AIUsageEvent

            event = AIUsageEvent.objects.create(
                user=user if getattr(user, "pk", None) else None,
                period=timezone.localdate().strftime("%Y-%m"),
                conversation_id=_string_from_metadata(request, "conversation_id", "chat_id"),
                turn_id=_string_from_metadata(request, "turn_id", "message_id", "request_id"),
                action_type=action_type,
                provider=provider,
                model_name=model,
                input_tokens=tokens.input_tokens,
                cached_input_tokens=tokens.cached_input_tokens,
                output_tokens=tokens.output_tokens,
                total_tokens=tokens.total_tokens,
                estimated_cost_usd=cost,
                status=status,
                error_type=error_type,
                latency_ms=latency_ms,
                tool_calls_count=len(tuple(response.tool_results or ())),
                usage_payload={
                    "provider_call_count": len(provider_responses),
                    "provider_usage": [dict(item.usage or {}) for item in provider_responses],
                },
                metadata=metadata,
            )
        except Exception as exc:  # pragma: no cover - defensive runtime boundary
            logger.warning("Could not persist AI usage event: %s", exc)
            summary["persist_error_type"] = exc.__class__.__name__
            return summary

        credit_summary = DjangoAICreditService().charge_usage_event(event)
        if credit_summary:
            summary["credits"] = dict(credit_summary)
            if credit_summary.get("charged"):
                summary["charged_credits"] = int(credit_summary.get("credits") or 0)
                summary["credit_plan_code"] = str(credit_summary.get("plan_code") or "")

        summary["recorded"] = True
        summary["event_id"] = event.pk
        return summary


def aggregate_provider_usage(provider_responses: Sequence[LLMProviderResponse]) -> AIUsageTokenSummary:
    totals = {"input": 0, "cached": 0, "output": 0, "total": 0}
    seen = {"input": False, "cached": False, "output": False, "total": False}

    for provider_response in tuple(provider_responses or ()):
        usage = provider_response.usage or {}
        input_tokens = _usage_int(usage, "input_tokens", "prompt_tokens")
        output_tokens = _usage_int(usage, "output_tokens", "completion_tokens")
        total_tokens = _usage_int(usage, "total_tokens")
        cached_tokens = _cached_input_tokens(usage)

        if total_tokens is None and (input_tokens is not None or output_tokens is not None):
            total_tokens = int(input_tokens or 0) + int(output_tokens or 0)

        for key, value in (
            ("input", input_tokens),
            ("cached", cached_tokens),
            ("output", output_tokens),
            ("total", total_tokens),
        ):
            if value is not None:
                totals[key] += value
                seen[key] = True

    return AIUsageTokenSummary(
        input_tokens=totals["input"] if seen["input"] else None,
        cached_input_tokens=totals["cached"] if seen["cached"] else None,
        output_tokens=totals["output"] if seen["output"] else None,
        total_tokens=totals["total"] if seen["total"] else None,
    )


def estimate_cost_usd(
    *,
    provider: str,
    model: str,
    input_tokens: int | None,
    cached_input_tokens: int | None,
    output_tokens: int | None,
) -> Decimal | None:
    """Estimate cost from settings without hard-coding provider prices.

    Expected optional setting shape:

    AI_ASSISTANT_LLM_PRICING_USD_PER_1M_TOKENS = {
        "openai": {
            "model-name": {"input": "0.00", "cached_input": "0.00", "output": "0.00"}
        }
    }
    """

    pricing = getattr(settings, "AI_ASSISTANT_LLM_PRICING_USD_PER_1M_TOKENS", {}) or {}
    model_pricing = _pricing_for_model(pricing, provider=provider, model=model)
    if not model_pricing:
        return None

    try:
        input_rate = Decimal(str(model_pricing.get("input", "0") or "0"))
        cached_rate = Decimal(str(model_pricing.get("cached_input", model_pricing.get("input", "0")) or "0"))
        output_rate = Decimal(str(model_pricing.get("output", "0") or "0"))
    except (InvalidOperation, ValueError):
        return None

    billable_input_tokens = max(0, int(input_tokens or 0) - int(cached_input_tokens or 0))
    cached_tokens = int(cached_input_tokens or 0)
    generated_tokens = int(output_tokens or 0)
    cost = (
        Decimal(billable_input_tokens) * input_rate
        + Decimal(cached_tokens) * cached_rate
        + Decimal(generated_tokens) * output_rate
    ) / Decimal(1_000_000)
    return cost.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)


def infer_action_type(*, request: AssistantTurnRequest, response: AssistantStructuredResponse) -> str:
    metadata = dict(request.metadata or {})
    explicit = _normalize_action_type(metadata.get("action_type") or metadata.get("ai_action_type"))
    if explicit:
        return explicit

    for proposal_id in tuple(response.proposal_ids or ()):
        if proposal_id:
            intent_name = response.intent.name
            if intent_name == AssistantIntentName.CREATE_MEAL_PROPOSAL:
                return ACTION_CREATE_MEAL_PROPOSAL
            if intent_name == AssistantIntentName.CREATE_DAILYPLAN_PROPOSAL:
                return ACTION_CREATE_DAILYPLAN_PROPOSAL
            if intent_name == AssistantIntentName.CREATE_PROGRAM_PROPOSAL:
                return ACTION_MODIFY_PROGRAM
            return ACTION_TOOL_CALL

    if response.tool_results:
        proposal_tool_names = {result.tool_name for result in response.tool_results if "proposal" in result.tool_name}
        if any("meal" in name for name in proposal_tool_names):
            return ACTION_CREATE_MEAL_PROPOSAL
        if any("dailyplan" in name for name in proposal_tool_names):
            return ACTION_CREATE_DAILYPLAN_PROPOSAL
        return ACTION_TOOL_CALL

    intent_name = response.intent.name
    if intent_name == AssistantIntentName.CREATE_MEAL_PROPOSAL:
        return ACTION_CREATE_MEAL_PROPOSAL
    if intent_name == AssistantIntentName.CREATE_DAILYPLAN_PROPOSAL:
        return ACTION_CREATE_DAILYPLAN_PROPOSAL
    if intent_name in {AssistantIntentName.CREATE_PROGRAM_PROPOSAL, AssistantIntentName.ITERATE_PROPOSAL}:
        return ACTION_MODIFY_PROGRAM
    if intent_name == AssistantIntentName.READ_CONTEXT:
        return ACTION_TOOL_CALL
    return ACTION_ASSISTANT_CHAT


def _usage_int(usage: Mapping[str, Any], *keys: str) -> int | None:
    for key in keys:
        value = usage.get(key)
        if value is None:
            continue
        try:
            integer = int(value)
        except (TypeError, ValueError):
            continue
        if integer >= 0:
            return integer
    return None


def _cached_input_tokens(usage: Mapping[str, Any]) -> int | None:
    direct = _usage_int(usage, "cached_input_tokens")
    if direct is not None:
        return direct
    for details_key in ("input_tokens_details", "prompt_tokens_details"):
        details = usage.get(details_key)
        if isinstance(details, Mapping):
            value = _usage_int(details, "cached_tokens")
            if value is not None:
                return value
    return None


def _pricing_for_model(pricing: Mapping[str, Any], *, provider: str, model: str) -> Mapping[str, Any]:
    provider_pricing = pricing.get(provider) if isinstance(pricing, Mapping) else None
    if not isinstance(provider_pricing, Mapping):
        return {}
    exact = provider_pricing.get(model)
    if isinstance(exact, Mapping):
        return exact
    default = provider_pricing.get("default")
    return default if isinstance(default, Mapping) else {}


def _safe_usage_metadata(
    *,
    request: AssistantTurnRequest,
    response: AssistantStructuredResponse,
    tools_executed: bool,
) -> dict[str, Any]:
    request_metadata = dict(request.metadata or {})
    metadata = {
        "chat_engine": str(request_metadata.get("chat_engine") or ""),
        "surface": str(request.context.get("surface") or request_metadata.get("surface") or ""),
        "intent": response.intent.name.value,
        "requires_human_review": response.requires_human_review,
        "tools_executed": bool(tools_executed),
        "tool_results_count": len(tuple(response.tool_results or ())),
        "proposal_count": len(tuple(response.proposal_ids or ())),
    }
    response_metadata = dict(response.metadata or {})
    if bool(response_metadata.get("post_tool_degraded")):
        metadata["post_tool_degradation"] = sanitize_usage_mapping(
            {
                "degraded": True,
                "reason": response_metadata.get("post_tool_degradation_reason"),
                "local_ack_policy": response_metadata.get("tool_followup_local_ack_policy"),
            }
        )
    credit_metadata = response_metadata.get("ai_credit_check")
    if isinstance(credit_metadata, Mapping):
        metadata["ai_credit_check"] = sanitize_usage_mapping(credit_metadata)
    if bool(response_metadata.get("provider_tool_followup_failed")):
        # Persist only stable operational identifiers. The full bounded provider
        # message remains in logs and the explicit live-validation report; it is
        # not copied into the long-lived economic usage event because providers
        # may echo request content in an error message.
        metadata["provider_tool_followup_error"] = sanitize_usage_mapping(
            {
                "status": response_metadata.get("provider_tool_followup_error_status"),
                "type": response_metadata.get("provider_tool_followup_error_provider_type"),
                "code": response_metadata.get("provider_tool_followup_error_code"),
                "param": response_metadata.get("provider_tool_followup_error_param"),
                "request_id": response_metadata.get("provider_tool_followup_error_request_id"),
            }
        )
    return metadata


def sanitize_usage_mapping(value: Mapping[str, Any]) -> dict[str, Any]:
    safe: dict[str, Any] = {}
    for key, item in value.items():
        if isinstance(item, (str, int, float, bool)) or item is None:
            safe[str(key)[:80]] = item
    return safe


def _user_from_request(request: AssistantTurnRequest) -> Any | None:
    metadata = dict(request.metadata or {})
    return metadata.get("tool_user") or metadata.get("user") or metadata.get("current_user")


def _string_from_metadata(request: AssistantTurnRequest, *keys: str) -> str:
    metadata = dict(request.metadata or {})
    for key in keys:
        value = metadata.get(key)
        if value is not None:
            return str(value)[:80]
    return ""


def _first_non_empty(*values: Any) -> str:
    for value in values:
        text = str(value or "").strip()
        if text:
            return text[:120]
    return ""


def _normalize_action_type(value: Any) -> str:
    text = " ".join(str(value or "").split()).replace(" ", "_").lower()
    return text[:80]
