from __future__ import annotations

from ai_assistant.application.tools.contracts import (
    AssistantToolCategory,
    AssistantToolRiskLevel,
    AssistantToolSpec,
)
from ai_assistant.application.tools.tool_names import *  # noqa: F403


READ_TOOL_SPECS = {
TOOL_READ_FOOD: AssistantToolSpec(
        name=TOOL_READ_FOOD,
        description="Read one operational Food visible to the authenticated user.",
        category=AssistantToolCategory.READ,
        risk_level=AssistantToolRiskLevel.LOW,
        requires_human_review=False,
        allowed_intents=("read_context", "answer_question"),
        input_schema={
            "type": "object",
            "required": ["food_id"],
            "properties": {
                "food_id": {
                    "type": "integer",
                    "description": "Operational Food ID to read.",
                },
            },
        },
    ),
TOOL_READ_MEAL: AssistantToolSpec(
        name=TOOL_READ_MEAL,
        description="Read one operational Meal visible to the authenticated user, including its foods and quantities.",
        category=AssistantToolCategory.READ,
        risk_level=AssistantToolRiskLevel.LOW,
        requires_human_review=False,
        allowed_intents=("read_context", "answer_question"),
        input_schema={
            "type": "object",
            "required": ["meal_id"],
            "properties": {
                "meal_id": {
                    "type": "integer",
                    "description": "Operational Meal ID to read.",
                },
            },
        },
    ),
TOOL_READ_DAILYPLAN: AssistantToolSpec(
        name=TOOL_READ_DAILYPLAN,
        description="Read one operational DailyPlan visible to the authenticated user.",
        category=AssistantToolCategory.READ,
        risk_level=AssistantToolRiskLevel.LOW,
        requires_human_review=False,
        allowed_intents=("read_context", "answer_question"),
        mcp_exposed=True,
        mcp_api_path="/ai-tools/read-dailyplan/",
        input_schema={
            "type": "object",
            "required": ["dailyplan_id"],
            "properties": {
                "dailyplan_id": {
                    "type": "integer",
                    "description": "Operational DailyPlan ID to read.",
                },
            },
        },
    ),
TOOL_LIST_USER_FOODS: AssistantToolSpec(
        name=TOOL_LIST_USER_FOODS,
        description="List operational foods owned by the authenticated user.",
        category=AssistantToolCategory.READ,
        risk_level=AssistantToolRiskLevel.LOW,
        requires_human_review=False,
        allowed_intents=("read_context", "answer_question"),
        input_schema={
            "type": "object",
            "required": [],
            "properties": {
                "limit": {"type": "integer", "description": "Optional maximum result count."},
            },
        },
    ),
TOOL_LIST_USER_MEALS: AssistantToolSpec(
        name=TOOL_LIST_USER_MEALS,
        description="List reusable Meals owned by the authenticated user.",
        category=AssistantToolCategory.READ,
        risk_level=AssistantToolRiskLevel.LOW,
        requires_human_review=False,
        allowed_intents=("read_context", "answer_question"),
        input_schema={
            "type": "object",
            "required": [],
            "properties": {
                "limit": {"type": "integer", "description": "Optional maximum result count."},
            },
        },
    ),
TOOL_SEARCH_USER_MEALS: AssistantToolSpec(
        name=TOOL_SEARCH_USER_MEALS,
        description="Resolve a reusable Meal by name among Meals visible to the authenticated user.",
        category=AssistantToolCategory.READ,
        risk_level=AssistantToolRiskLevel.LOW,
        requires_human_review=False,
        allowed_intents=("read_context", "answer_question"),
        input_schema={
            "type": "object",
            "required": ["query"],
            "properties": {
                "query": {"type": "string", "description": "Meal name or partial name."},
                "limit": {"type": "integer", "description": "Optional maximum result count."},
            },
        },
    ),
TOOL_LIST_USER_DAILYPLANS: AssistantToolSpec(
        name=TOOL_LIST_USER_DAILYPLANS,
        description="List DailyPlans owned by the authenticated user.",
        category=AssistantToolCategory.READ,
        risk_level=AssistantToolRiskLevel.LOW,
        requires_human_review=False,
        allowed_intents=("read_context", "answer_question", "create_dailyplan_proposal"),
        input_schema={
            "type": "object",
            "required": [],
            "properties": {
                "limit": {"type": "integer", "description": "Optional maximum result count."},
            },
        },
    ),
TOOL_SEARCH_USER_DAILYPLANS: AssistantToolSpec(
        name=TOOL_SEARCH_USER_DAILYPLANS,
        description=(
            "Resolve a DailyPlan by name among plans visible to the authenticated user. "
            "For a future change, only a result whose created_by_id is the current user may be targeted."
        ),
        category=AssistantToolCategory.READ,
        risk_level=AssistantToolRiskLevel.LOW,
        requires_human_review=False,
        allowed_intents=("read_context", "answer_question", "create_dailyplan_proposal", "iterate_proposal"),
        input_schema={
            "type": "object",
            "required": ["query"],
            "properties": {
                "query": {"type": "string", "description": "DailyPlan name or partial name."},
                "limit": {"type": "integer", "description": "Optional maximum result count."},
            },
        },
    ),
TOOL_READ_PROPOSAL: AssistantToolSpec(
        name=TOOL_READ_PROPOSAL,
        description=(
            "Read one NutritionProposal visible to the authenticated user. "
            "When the user explicitly asks to inspect a proposal id or names read_proposal, request this tool; "
            "do not claim that tools are unavailable when it is present in the allowlist."
        ),
        category=AssistantToolCategory.READ,
        risk_level=AssistantToolRiskLevel.LOW,
        requires_human_review=False,
        allowed_intents=("read_context", "answer_question", "iterate_proposal"),
        mcp_exposed=True,
        mcp_api_path="/ai-tools/read-proposal/",
        input_schema={
            "type": "object",
            "required": ["proposal_id"],
            "properties": {
                "proposal_id": {
                    "type": "integer",
                    "description": "NutritionProposal ID to read.",
                },
            },
        },
    ),
TOOL_LIST_USER_PROPOSALS: AssistantToolSpec(
        name=TOOL_LIST_USER_PROPOSALS,
        description="List reviewable proposals visible to the authenticated user.",
        category=AssistantToolCategory.READ,
        risk_level=AssistantToolRiskLevel.LOW,
        requires_human_review=False,
        allowed_intents=("read_context", "answer_question", "iterate_proposal"),
        mcp_exposed=True,
        mcp_api_path="/ai-tools/list-user-proposals/",
        input_schema={
            "type": "object",
            "required": [],
            "properties": {},
        },
    ),
TOOL_READ_USER_PROFILE_CONTEXT: AssistantToolSpec(
        name=TOOL_READ_USER_PROFILE_CONTEXT,
        description=(
            "Read the authenticated user's nutrition profile context for AI-assisted planning. "
            "Use this immediately when the user says to use their ficha, profile, perfil, personal data or mis datos. "
            "This returns persisted body basics, a non-persistent profile_draft/card for the current chat, "
            "latest weight and explicit missing fields; it never writes profile data."
        ),
        category=AssistantToolCategory.READ,
        risk_level=AssistantToolRiskLevel.LOW,
        requires_human_review=False,
        allowed_intents=("read_context", "capture_nutrition_brief", "create_dailyplan_proposal", "answer_question"),
        input_schema={
            "type": "object",
            "required": [],
            "properties": {},
        },
    ),
TOOL_LIST_USER_PROGRAMS: AssistantToolSpec(
        name=TOOL_LIST_USER_PROGRAMS,
        description="List or search weekly Programs owned by the authenticated user.",
        category=AssistantToolCategory.READ,
        risk_level=AssistantToolRiskLevel.LOW,
        requires_human_review=False,
        allowed_intents=("read_context", "answer_question", "create_program_proposal"),
        input_schema={
            "type": "object",
            "required": [],
            "properties": {
                "search": {"type": "string", "description": "Optional program name search."},
                "limit": {"type": "integer", "description": "Optional maximum result count."},
            },
        },
    ),
TOOL_READ_PROGRAM: AssistantToolSpec(
        name=TOOL_READ_PROGRAM,
        description="Read one owned weekly Program, its slots and independent DailyPlan snapshots.",
        category=AssistantToolCategory.READ,
        risk_level=AssistantToolRiskLevel.LOW,
        requires_human_review=False,
        allowed_intents=("read_context", "answer_question", "create_program_proposal"),
        input_schema={
            "type": "object",
            "required": ["program_id"],
            "properties": {
                "program_id": {"type": "integer", "description": "Owned Program ID."},
            },
        },
    ),
TOOL_READ_CALENDARIZATION: AssistantToolSpec(
        name=TOOL_READ_CALENDARIZATION,
        description="Read the user's current program calendarization and recent history.",
        category=AssistantToolCategory.READ,
        risk_level=AssistantToolRiskLevel.LOW,
        requires_human_review=False,
        allowed_intents=("read_context", "answer_question"),
        input_schema={
            "type": "object",
            "required": [],
            "properties": {
                "history_limit": {"type": "integer", "description": "Optional history count."},
            },
        },
    ),
TOOL_LIST_INBOX_ITEMS: AssistantToolSpec(
        name=TOOL_LIST_INBOX_ITEMS,
        description="List received or sent My Scoope shares in the authenticated user's Inbox.",
        category=AssistantToolCategory.READ,
        risk_level=AssistantToolRiskLevel.LOW,
        requires_human_review=False,
        allowed_intents=("read_context", "answer_question"),
        input_schema={
            "type": "object",
            "required": [],
            "properties": {
                "scope": {
                    "type": "string",
                    "enum": ["received", "sent"],
                    "description": "Inbox direction.",
                },
                "favorites_only": {"type": "boolean"},
                "limit": {"type": "integer", "description": "Optional maximum result count."},
            },
        },
    ),
TOOL_READ_ACCOUNT_BILLING_CONTEXT: AssistantToolSpec(
        name=TOOL_READ_ACCOUNT_BILLING_CONTEXT,
        description=(
            "Read the user's commercial plan, credits, subscription and payment summary. "
            "Checkout and cancellation remain trusted billing UI actions."
        ),
        category=AssistantToolCategory.READ,
        risk_level=AssistantToolRiskLevel.MEDIUM,
        requires_human_review=False,
        allowed_intents=("read_context", "answer_question"),
        input_schema={"type": "object", "required": [], "properties": {}},
    ),
TOOL_SEARCH_OPERATIONAL_FOODS: AssistantToolSpec(
        name=TOOL_SEARCH_OPERATIONAL_FOODS,
        description=(
            "Search operational My Scoope foods available for planning. "
            "Returned IDs are notas.Food IDs, never master catalog IDs."
        ),
        category=AssistantToolCategory.READ,
        risk_level=AssistantToolRiskLevel.LOW,
        requires_human_review=False,
        allowed_intents=(
            "answer_question",
            "capture_nutrition_brief",
            "create_meal_proposal",
            "create_dailyplan_proposal",
            "iterate_proposal",
        ),
        input_schema={
            "type": "object",
            "required": ["query"],
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Food name search over operational foods.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Optional maximum number of foods to return.",
                },
            },
        },
    ),
TOOL_LIST_OPERATIONAL_FOODS: AssistantToolSpec(
        name=TOOL_LIST_OPERATIONAL_FOODS,
        description=(
            "List operational foods in My Scoope that are available for planning. "
            "Returned identifiers are operational My Scoope Food IDs (notas.Food), "
            "never master catalog IDs."
        ),
        category=AssistantToolCategory.READ,
        risk_level=AssistantToolRiskLevel.MEDIUM,
        requires_human_review=False,
        mcp_exposed=True,
        mcp_name="list_food_catalog",
        mcp_api_path="/ai-tools/list-food-catalog/",
        mcp_input_schema={
            "type": "object",
            "required": [],
            "properties": {
                "search": {
                    "type": "string",
                    "description": "Optional operational food name search.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Optional maximum number of foods to return.",
                },
            },
        },
        allowed_intents=(
            "capture_nutrition_brief",
            "create_meal_proposal",
            "create_dailyplan_proposal",
            "iterate_proposal",
        ),
        input_schema={
            "type": "object",
            "required": [],
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Optional maximum number of foods to return.",
                },
            },
        },
    ),
TOOL_PREVIEW_NUTRITION_SOLVER_CANDIDATES: AssistantToolSpec(
        name=TOOL_PREVIEW_NUTRITION_SOLVER_CANDIDATES,
        description=(
            "Preview solver-ready operational food candidates for the internal nutrition solver. "
            "Returned IDs are notas.Food IDs and the payload never exposes master catalog or external provider fields."
        ),
        category=AssistantToolCategory.READ,
        risk_level=AssistantToolRiskLevel.MEDIUM,
        requires_human_review=False,
        allowed_intents=(
            "answer_question",
            "capture_nutrition_brief",
            "create_dailyplan_proposal",
            "iterate_proposal",
        ),
        input_schema={
            "type": "object",
            "required": [],
            "properties": {
                "search": {
                    "type": "string",
                    "description": "Optional food name search over solver-ready operational foods.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Optional maximum number of solver candidates to preview.",
                },
                "include_extended": {
                    "type": "boolean",
                    "description": "Whether extended operational foods may be included alongside core foods.",
                },
            },
        },
    ),
TOOL_COMPARE_DAILYPLAN_TO_TARGETS: AssistantToolSpec(
        name=TOOL_COMPARE_DAILYPLAN_TO_TARGETS,
        description="Compare an operational DailyPlan against nutritional targets using My Scoope validation.",
        category=AssistantToolCategory.VALIDATION,
        risk_level=AssistantToolRiskLevel.MEDIUM,
        requires_human_review=False,
        mcp_exposed=True,
        mcp_api_path="/ai-tools/compare-dailyplan-to-targets/",
        allowed_intents=("answer_question", "create_dailyplan_proposal", "iterate_proposal"),
        input_schema={
            "type": "object",
            "required": ["dailyplan_id", "targets"],
            "properties": {
                "dailyplan_id": {
                    "type": "integer",
                    "description": "Operational DailyPlan ID to validate.",
                },
                "targets": {
                    "type": "object",
                    "description": "Target nutrition metrics.",
                },
                "tolerances": {
                    "type": "object",
                    "description": "Optional tolerance values.",
                },
            },
        },
    ),
TOOL_LIST_SAVED_COMPARISONS: AssistantToolSpec(
        name=TOOL_LIST_SAVED_COMPARISONS,
        description=(
            "List saved comparisons owned by the authenticated user. "
            "Use this when the user asks what comparisons exist or wants to choose one to review."
        ),
        category=AssistantToolCategory.READ,
        risk_level=AssistantToolRiskLevel.LOW,
        requires_human_review=False,
        allowed_intents=("read_context", "answer_question", "iterate_proposal"),
        input_schema={
            "type": "object",
            "required": [],
            "properties": {
                "kind": {
                    "type": "string",
                    "description": "Optional comparison kind filter: foods, meals or dailyplans.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Optional maximum number of saved comparisons to return.",
                },
            },
        },
    ),
TOOL_READ_SAVED_COMPARISON: AssistantToolSpec(
        name=TOOL_READ_SAVED_COMPARISON,
        description=(
            "Read one saved comparison owned by the authenticated user, including its stable snapshot payload "
            "and a chat-renderable comparison card. This never mutates source foods, meals or plans."
        ),
        category=AssistantToolCategory.READ,
        risk_level=AssistantToolRiskLevel.LOW,
        requires_human_review=False,
        allowed_intents=("read_context", "answer_question", "iterate_proposal"),
        input_schema={
            "type": "object",
            "required": ["comparison_id"],
            "properties": {
                "comparison_id": {
                    "type": "integer",
                    "description": "SavedComparison ID to read.",
                },
            },
        },
    ),
}

__all__ = ["READ_TOOL_SPECS"]
