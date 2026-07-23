"""Controlled tool registry for AI Assistant orchestration.

The package exports lazily to keep the canonical catalog importable by the
standalone MCP process without loading Django-backed executors.
"""

from importlib import import_module
from typing import Final


_EXPORTS: Final[dict[str, tuple[str, str]]] = {
    "ReadOnlyToolExecutor": ("ai_assistant.application.tools.executor", "ReadOnlyToolExecutor"),
    "ReadOnlyToolExecutorConfig": (
        "ai_assistant.application.tools.executor",
        "ReadOnlyToolExecutorConfig",
    ),
    "build_default_read_only_tool_dispatch_table": (
        "ai_assistant.application.tools.executor",
        "build_default_read_only_tool_dispatch_table",
    ),
    "execute_read_only_tool": (
        "ai_assistant.application.tools.executor",
        "execute_read_only_tool",
    ),
    "ProfileCommitToolExecutor": (
        "ai_assistant.application.tools.profile_commit_executor",
        "ProfileCommitToolExecutor",
    ),
    "build_default_profile_commit_tool_dispatch_table": (
        "ai_assistant.application.tools.profile_commit_executor",
        "build_default_profile_commit_tool_dispatch_table",
    ),
    "execute_profile_commit_tool": (
        "ai_assistant.application.tools.profile_commit_executor",
        "execute_profile_commit_tool",
    ),
    "ProfileDraftToolExecutor": (
        "ai_assistant.application.tools.profile_executor",
        "ProfileDraftToolExecutor",
    ),
    "build_default_profile_draft_tool_dispatch_table": (
        "ai_assistant.application.tools.profile_executor",
        "build_default_profile_draft_tool_dispatch_table",
    ),
    "execute_profile_draft_tool": (
        "ai_assistant.application.tools.profile_executor",
        "execute_profile_draft_tool",
    ),
    "ReviewableProposalToolExecutor": (
        "ai_assistant.application.tools.proposal_executor",
        "ReviewableProposalToolExecutor",
    ),
    "build_default_reviewable_proposal_tool_dispatch_table": (
        "ai_assistant.application.tools.proposal_executor",
        "build_default_reviewable_proposal_tool_dispatch_table",
    ),
    "execute_reviewable_proposal_tool": (
        "ai_assistant.application.tools.proposal_executor",
        "execute_reviewable_proposal_tool",
    ),
    "ValidationToolExecutor": (
        "ai_assistant.application.tools.validation_executor",
        "ValidationToolExecutor",
    ),
    "build_default_validation_tool_dispatch_table": (
        "ai_assistant.application.tools.validation_executor",
        "build_default_validation_tool_dispatch_table",
    ),
    "execute_validation_tool": (
        "ai_assistant.application.tools.validation_executor",
        "execute_validation_tool",
    ),
    "AssistantToolCategory": (
        "ai_assistant.application.tools.contracts",
        "AssistantToolCategory",
    ),
    "AssistantToolRegistryError": (
        "ai_assistant.application.tools.contracts",
        "AssistantToolRegistryError",
    ),
    "AssistantToolRiskLevel": (
        "ai_assistant.application.tools.contracts",
        "AssistantToolRiskLevel",
    ),
    "AssistantToolSpec": ("ai_assistant.application.tools.contracts", "AssistantToolSpec"),
}

_REGISTRY_EXPORTS = (
    "ALLOWED_TOOL_SPECS",
    "FORBIDDEN_TOOL_NAMES",
    "TOOL_COMMIT_PROFILE_UPDATE",
    "TOOL_COMPARE_DAILYPLAN_TO_TARGETS",
    "TOOL_CREATE_NUTRITION_ENGINE_DAILYPLAN_PROPOSAL",
    "TOOL_CREATE_PROPORTIONAL_DAILYPLAN_CALORIE_PROPOSAL",
    "TOOL_COMMIT_PREPARED_ACTION",
    "TOOL_CREATE_NUTRITION_ENGINE_DAILYPLAN_PROPOSAL_FROM_DRAFTS",
    "TOOL_CREATE_NUTRITION_SOLVER_MEAL_PROPOSAL",
    "TOOL_CREATE_VALIDATED_DAILYPLAN_BUILD_PROPOSAL",
    "TOOL_CREATE_VALIDATED_DAILYPLAN_PROPOSAL",
    "TOOL_CREATE_VALIDATED_MEAL_PROPOSAL",
    "TOOL_ITERATE_NUTRITION_ENGINE_DAILYPLAN_PROPOSAL",
    "TOOL_LIST_OPERATIONAL_FOODS",
    "TOOL_LIST_INBOX_ITEMS",
    "TOOL_LIST_SAVED_COMPARISONS",
    "TOOL_LIST_USER_DAILYPLANS",
    "TOOL_LIST_USER_FOODS",
    "TOOL_LIST_USER_MEALS",
    "TOOL_LIST_USER_PROGRAMS",
    "TOOL_LIST_USER_PROPOSALS",
    "TOOL_PREVIEW_NUTRITION_SOLVER_CANDIDATES",
    "TOOL_PREPARE_PRODUCT_ACTION",
    "TOOL_READ_DAILYPLAN",
    "TOOL_READ_ACCOUNT_BILLING_CONTEXT",
    "TOOL_READ_CALENDARIZATION",
    "TOOL_READ_FOOD",
    "TOOL_READ_MEAL",
    "TOOL_READ_PROGRAM",
    "TOOL_READ_PROPOSAL",
    "TOOL_READ_SAVED_COMPARISON",
    "TOOL_READ_USER_PROFILE_CONTEXT",
    "TOOL_SEARCH_OPERATIONAL_FOODS",
    "TOOL_SEARCH_USER_DAILYPLANS",
    "TOOL_SEARCH_USER_MEALS",
    "TOOL_SHARE_PREFERENCE_DRAFT_CARD",
    "TOOL_SHARE_PROFILE_DRAFT_CARD",
    "TOOL_SHARE_PROPOSAL_PREFERENCES_CARD",
    "TOOL_UPDATE_PREFERENCE_DRAFT",
    "TOOL_UPDATE_PROFILE_DRAFT",
    "TOOL_UPDATE_PROPOSAL_PREFERENCES",
    "get_mcp_tool_spec",
    "get_tool_spec",
    "is_allowed_tool_name",
    "is_forbidden_tool_name",
    "list_allowed_tool_specs",
    "list_mcp_tool_specs",
    "list_provider_tool_specs",
    "normalize_tool_name",
    "validate_tool_request",
)
for _name in _REGISTRY_EXPORTS:
    _EXPORTS[_name] = ("ai_assistant.application.tools.registry", _name)

__all__ = list(_EXPORTS)


def __getattr__(name: str):
    try:
        module_name, attribute_name = _EXPORTS[name]
    except KeyError as exc:
        raise AttributeError(name) from exc
    value = getattr(import_module(module_name), attribute_name)
    globals()[name] = value
    return value
