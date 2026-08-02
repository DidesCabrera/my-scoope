"""Application contracts and orchestration for the AI Assistant app.

Exports are resolved lazily so pure contracts (for example the canonical tool
catalog consumed by the standalone MCP server) do not require Django settings
to be configured merely by importing this package.
"""

from importlib import import_module
from typing import Final


_EXPORTS: Final[dict[str, tuple[str, str]]] = {
    "AUDIT_SCHEMA_VERSION": ("ai_assistant.application.audit", "AUDIT_SCHEMA_VERSION"),
    "AssistantToolAuditItem": ("ai_assistant.application.audit", "AssistantToolAuditItem"),
    "AssistantTurnAuditSnapshot": ("ai_assistant.application.audit", "AssistantTurnAuditSnapshot"),
    "build_audit_snapshot": ("ai_assistant.application.audit", "build_audit_snapshot"),
    "sanitize_audit_value": ("ai_assistant.application.audit", "sanitize_audit_value"),
    "ChatEngine": ("ai_assistant.application.chat_engines", "ChatEngine"),
    "ChatEngineRequest": ("ai_assistant.application.chat_engines", "ChatEngineRequest"),
    "ChatEngineTurnResult": ("ai_assistant.application.chat_engines", "ChatEngineTurnResult"),
    "SafeLLMContext": ("ai_assistant.application.context_builder", "SafeLLMContext"),
    "build_safe_llm_context": ("ai_assistant.application.context_builder", "build_safe_llm_context"),
    "merge_safe_context_into_request": (
        "ai_assistant.application.context_builder",
        "merge_safe_context_into_request",
    ),
    "sanitize_provider_context": (
        "ai_assistant.application.context_builder",
        "sanitize_provider_context",
    ),
    "AICreditCheck": ("ai_assistant.application.credits", "AICreditCheck"),
    "AICreditPlan": ("ai_assistant.application.credits", "AICreditPlan"),
    "DjangoAICreditService": ("ai_assistant.application.credits", "DjangoAICreditService"),
    "calculate_event_credits": ("ai_assistant.application.credits", "calculate_event_credits"),
    "estimate_request_credits": ("ai_assistant.application.credits", "estimate_request_credits"),
    "resolve_credit_plan": ("ai_assistant.application.credits", "resolve_credit_plan"),
    "ExternalLLMChatEngine": (
        "ai_assistant.application.llm_chat_engine",
        "ExternalLLMChatEngine",
    ),
    "AIModelRoute": ("ai_assistant.application.model_routing", "AIModelRoute"),
    "action_type_from_request": (
        "ai_assistant.application.model_routing",
        "action_type_from_request",
    ),
    "resolve_model_route": ("ai_assistant.application.model_routing", "resolve_model_route"),
    "resolve_model_route_for_turn": (
        "ai_assistant.application.model_routing",
        "resolve_model_route_for_turn",
    ),
    "route_max_output_tokens": (
        "ai_assistant.application.model_routing",
        "route_max_output_tokens",
    ),
    "AIUsageDashboardReport": (
        "ai_assistant.application.reports",
        "AIUsageDashboardReport",
    ),
    "AIUsageKpis": ("ai_assistant.application.reports", "AIUsageKpis"),
    "build_ai_credit_ledger_summary": (
        "ai_assistant.application.reports",
        "build_ai_credit_ledger_summary",
    ),
    "build_ai_usage_dashboard_report": (
        "ai_assistant.application.reports",
        "build_ai_usage_dashboard_report",
    ),
    "AILimitViolation": ("ai_assistant.application.limits", "AILimitViolation"),
    "AITurnLimitConfig": ("ai_assistant.application.limits", "AITurnLimitConfig"),
    "bounded_text": ("ai_assistant.application.limits", "bounded_text"),
    "estimate_provider_request_tokens": (
        "ai_assistant.application.limits",
        "estimate_provider_request_tokens",
    ),
    "estimate_text_tokens": ("ai_assistant.application.limits", "estimate_text_tokens"),
    "validate_provider_request_limits": (
        "ai_assistant.application.limits",
        "validate_provider_request_limits",
    ),
    "AIUsageRecorder": ("ai_assistant.application.usage", "AIUsageRecorder"),
    "AIUsageTokenSummary": ("ai_assistant.application.usage", "AIUsageTokenSummary"),
    "DjangoAIUsageRecorder": (
        "ai_assistant.application.usage",
        "DjangoAIUsageRecorder",
    ),
    "aggregate_provider_usage": (
        "ai_assistant.application.usage",
        "aggregate_provider_usage",
    ),
    "estimate_cost_usd": ("ai_assistant.application.usage", "estimate_cost_usd"),
    "infer_action_type": ("ai_assistant.application.usage", "infer_action_type"),
    "AssistantOrchestratorConfig": (
        "ai_assistant.application.orchestrator",
        "AssistantOrchestratorConfig",
    ),
    "AssistantOrchestratorError": (
        "ai_assistant.application.orchestrator",
        "AssistantOrchestratorError",
    ),
    "AssistantProviderParseResult": (
        "ai_assistant.application.orchestrator",
        "AssistantProviderParseResult",
    ),
    "ExternalLLMOrchestrator": (
        "ai_assistant.application.orchestrator",
        "ExternalLLMOrchestrator",
    ),
}

__all__ = list(_EXPORTS)


def __getattr__(name: str):
    try:
        module_name, attribute_name = _EXPORTS[name]
    except KeyError as exc:
        raise AttributeError(name) from exc
    value = getattr(import_module(module_name), attribute_name)
    globals()[name] = value
    return value
