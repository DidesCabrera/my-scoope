"""Application contracts and orchestration for the AI Assistant app."""

from ai_assistant.application.audit import (
    AUDIT_SCHEMA_VERSION,
    AssistantToolAuditItem,
    AssistantTurnAuditSnapshot,
    build_audit_snapshot,
    sanitize_audit_value,
)
from ai_assistant.application.chat_engines import (
    ChatEngine,
    ChatEngineRequest,
    ChatEngineTurnResult,
)
from ai_assistant.application.context_builder import (
    SafeLLMContext,
    build_safe_llm_context,
    merge_safe_context_into_request,
    sanitize_provider_context,
)
from ai_assistant.application.credits import (
    AICreditCheck,
    AICreditPlan,
    DjangoAICreditService,
    calculate_event_credits,
    estimate_request_credits,
    resolve_credit_plan,
)
from ai_assistant.application.llm_chat_engine import ExternalLLMChatEngine
from ai_assistant.application.model_routing import (
    AIModelRoute,
    action_type_from_request,
    resolve_model_route,
    resolve_model_route_for_turn,
    route_max_output_tokens,
)
from ai_assistant.application.rollout import (
    AIRolloutDecision,
    resolve_ai_llm_rollout,
    stable_user_bucket,
)
from ai_assistant.application.reports import (
    AIUsageDashboardReport,
    AIUsageKpis,
    build_ai_credit_ledger_summary,
    build_ai_usage_dashboard_report,
)
from ai_assistant.application.limits import (
    AILimitViolation,
    AITurnLimitConfig,
    bounded_text,
    estimate_provider_request_tokens,
    estimate_text_tokens,
    validate_provider_request_limits,
)
from ai_assistant.application.usage import (
    AIUsageRecorder,
    AIUsageTokenSummary,
    DjangoAIUsageRecorder,
    aggregate_provider_usage,
    estimate_cost_usd,
    infer_action_type,
)
from ai_assistant.application.orchestrator import (
    AssistantOrchestratorConfig,
    AssistantOrchestratorError,
    AssistantProviderParseResult,
    ExternalLLMOrchestrator,
)

__all__ = [
    "sanitize_audit_value",
    "build_audit_snapshot",
    "AssistantTurnAuditSnapshot",
    "AssistantToolAuditItem",
    "AUDIT_SCHEMA_VERSION",
    "SafeLLMContext",
    "build_safe_llm_context",
    "merge_safe_context_into_request",
    "sanitize_provider_context",
    "AssistantOrchestratorConfig",
    "AssistantOrchestratorError",
    "AssistantProviderParseResult",
    "ChatEngine",
    "ChatEngineRequest",
    "ChatEngineTurnResult",
    "AICreditCheck",
    "AICreditPlan",
    "DjangoAICreditService",
    "calculate_event_credits",
    "estimate_request_credits",
    "resolve_credit_plan",
    "ExternalLLMChatEngine",
    "AIModelRoute",
    "action_type_from_request",
    "resolve_model_route",
    "resolve_model_route_for_turn",
    "route_max_output_tokens",
    "AIRolloutDecision",
    "resolve_ai_llm_rollout",
    "stable_user_bucket",
    "AIUsageDashboardReport",
    "AIUsageKpis",
    "build_ai_credit_ledger_summary",
    "build_ai_usage_dashboard_report",
    "ExternalLLMOrchestrator",
    "AILimitViolation",
    "AITurnLimitConfig",
    "bounded_text",
    "estimate_provider_request_tokens",
    "estimate_text_tokens",
    "validate_provider_request_limits",
    "AIUsageRecorder",
    "AIUsageTokenSummary",
    "DjangoAIUsageRecorder",
    "aggregate_provider_usage",
    "estimate_cost_usd",
    "infer_action_type",
]
