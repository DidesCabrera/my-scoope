from __future__ import annotations

from typing import Any, Iterable

from ai_assistant.application.tools.contracts import (
    AssistantToolCategory,
    AssistantToolRegistryError,
    AssistantToolRiskLevel,
    AssistantToolSpec,
)
from ai_assistant.domain.contracts import (
    AssistantToolRequest,
    AssistantToolResult,
    AssistantToolStatus,
)

TOOL_READ_DAILYPLAN = "read_dailyplan"
TOOL_READ_FOOD = "read_food"
TOOL_READ_MEAL = "read_meal"
TOOL_READ_PROPOSAL = "read_proposal"
TOOL_LIST_USER_FOODS = "list_user_foods"
TOOL_LIST_USER_MEALS = "list_user_meals"
TOOL_SEARCH_USER_MEALS = "search_user_meals"
TOOL_LIST_USER_DAILYPLANS = "list_user_dailyplans"
TOOL_SEARCH_USER_DAILYPLANS = "search_user_dailyplans"
TOOL_LIST_USER_PROPOSALS = "list_user_proposals"
TOOL_READ_USER_PROFILE_CONTEXT = "read_user_profile_context"
TOOL_LIST_USER_PROGRAMS = "list_user_programs"
TOOL_READ_PROGRAM = "read_program"
TOOL_READ_CALENDARIZATION = "read_calendarization"
TOOL_LIST_INBOX_ITEMS = "list_inbox_items"
TOOL_READ_ACCOUNT_BILLING_CONTEXT = "read_account_billing_context"
TOOL_SEARCH_OPERATIONAL_FOODS = "search_operational_foods"
TOOL_LIST_OPERATIONAL_FOODS = "list_operational_foods"
TOOL_PREVIEW_NUTRITION_SOLVER_CANDIDATES = "preview_nutrition_solver_candidates"
TOOL_COMPARE_DAILYPLAN_TO_TARGETS = "compare_dailyplan_to_targets"
TOOL_LIST_SAVED_COMPARISONS = "list_saved_comparisons"
TOOL_READ_SAVED_COMPARISON = "read_saved_comparison"
TOOL_UPDATE_PROFILE_DRAFT = "update_profile_draft"
TOOL_SHARE_PROFILE_DRAFT_CARD = "share_profile_draft_card"
TOOL_COMMIT_PROFILE_UPDATE = "commit_profile_update"
TOOL_UPDATE_PREFERENCE_DRAFT = "update_preference_draft"
TOOL_SHARE_PREFERENCE_DRAFT_CARD = "share_preference_draft_card"
TOOL_UPDATE_PROPOSAL_PREFERENCES = "update_proposal_preferences"
TOOL_SHARE_PROPOSAL_PREFERENCES_CARD = "share_proposal_preferences_card"
TOOL_CREATE_VALIDATED_MEAL_PROPOSAL = "create_validated_meal_proposal"
TOOL_CREATE_NUTRITION_SOLVER_MEAL_PROPOSAL = "create_nutrition_solver_meal_proposal"
TOOL_CREATE_VALIDATED_DAILYPLAN_PROPOSAL = "create_validated_dailyplan_proposal"
TOOL_CREATE_PROPORTIONAL_DAILYPLAN_CALORIE_PROPOSAL = "create_proportional_dailyplan_calorie_proposal"
TOOL_CREATE_VALIDATED_DAILYPLAN_BUILD_PROPOSAL = "create_validated_dailyplan_build_proposal"
TOOL_CREATE_NUTRITION_ENGINE_DAILYPLAN_PROPOSAL = "create_nutrition_engine_dailyplan_proposal"
TOOL_CREATE_NUTRITION_ENGINE_DAILYPLAN_PROPOSAL_FROM_DRAFTS = "create_nutrition_engine_dailyplan_proposal_from_drafts"
TOOL_ITERATE_NUTRITION_ENGINE_DAILYPLAN_PROPOSAL = "iterate_nutrition_engine_dailyplan_proposal"
TOOL_PREPARE_PRODUCT_ACTION = "prepare_product_action"
TOOL_COMMIT_PREPARED_ACTION = "commit_prepared_action"

FORBIDDEN_TOOL_NAMES = {
    "apply_approved_proposal",
    "apply_proposal",
    "apply_validated_proposal",
    "create_dailyplan",
    "create_food",
    "create_meal",
    "delete_dailyplan",
    "delete_food",
    "delete_meal",
    "direct_model_write",
    "list_catalog_foods",
    "list_food_catalog",
    "raw_command_execution",
    "raw_model_mutation",
    "raw_sql",
    "read_catalog_food",
    "search_catalog_foods",
    "search_food_catalog",
    "update_dailyplan",
    "update_food",
    "update_meal",
}

FORBIDDEN_ARGUMENT_KEYS = {
    "catalog_food_id",
    "catalogfoodid",
}

ALLOWED_TOOL_SPECS = {
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
    TOOL_UPDATE_PROFILE_DRAFT: AssistantToolSpec(
        name=TOOL_UPDATE_PROFILE_DRAFT,
        description=(
            "Update a non-persistent nutrition profile draft from natural-language user data. "
            "Use this when the user gives or corrects body/profile facts such as age, height, weight, sex or activity. "
            "Request it before confirming that those facts were recorded or will be used. "
            "The result is a draft object for this conversation only; it never updates the permanent ficha and "
            "does not render a card automatically. Use share_profile_draft_card only when showing the object adds value."
        ),
        category=AssistantToolCategory.DRAFT,
        risk_level=AssistantToolRiskLevel.MEDIUM,
        requires_human_review=False,
        allowed_intents=("capture_nutrition_brief", "create_dailyplan_proposal", "answer_question"),
        input_schema={
            "type": "object",
            "required": ["updates"],
            "properties": {
                "current_draft": {
                    "type": "object",
                    "description": "Optional profile draft state already known in this conversation.",
                },
                "updates": {
                    "type": "object",
                    "description": (
                        "LLM-interpreted fields from the user's message. Send normalized values, not raw text. "
                        "Supported keys: weight_kg number in kg, height_cm integer cm, age_years integer, "
                        "sex enum male|female, activity_level enum sedentary|light|moderate|high|very_high, "
                        "training_frequency integer days per week. Interpret user-provided weight as current for "
                        "this proposal unless the user says it is approximate/old. Do not ask for weight date/origin as a required field. "
                        "Example: 'peso 88jg, mido 188 y 38 años' should be sent as "
                        "{weight_kg: 88, height_cm: 188, age_years: 38}."
                    ),
                },
                "field_sources": {
                    "type": "object",
                    "description": "Optional per-field source labels. Defaults to chat_draft for updated fields.",
                },
            },
        },
    ),
    TOOL_SHARE_PROFILE_DRAFT_CARD: AssistantToolSpec(
        name=TOOL_SHARE_PROFILE_DRAFT_CARD,
        description=(
            "Build a chat-renderable profile draft card from a draft object. "
            "Use this when the user asks to review the ficha, when an initial profile object should be made visible, "
            "or after a meaningful grouped completion. Do not call it after every individual field update. "
            "The card shows what is known, what is pending and what would require approval before persistence."
        ),
        category=AssistantToolCategory.DRAFT,
        risk_level=AssistantToolRiskLevel.MEDIUM,
        requires_human_review=False,
        allowed_intents=("capture_nutrition_brief", "create_dailyplan_proposal", "answer_question"),
        input_schema={
            "type": "object",
            "required": ["profile_draft"],
            "properties": {
                "profile_draft": {
                    "type": "object",
                    "description": "Current profile draft to render as a user-visible card.",
                },
            },
        },
    ),
    TOOL_UPDATE_PREFERENCE_DRAFT: AssistantToolSpec(
        name=TOOL_UPDATE_PREFERENCE_DRAFT,
        description=(
            "Update a non-persistent food and meal preference draft from natural-language user data. "
            "Use this when the user declares or changes dietary pattern, foods to avoid, preferred foods, allergies, "
            "meal-count preferences, budget, simplicity, variety or cooking-time preferences. "
            "Request it before confirming that those preferences were recorded or will be used. "
            "This is separate from the personal body profile, never persists preferences directly and does not "
            "render a card automatically. Use share_preference_draft_card only when review is useful."
        ),
        category=AssistantToolCategory.DRAFT,
        risk_level=AssistantToolRiskLevel.MEDIUM,
        requires_human_review=False,
        allowed_intents=("capture_nutrition_brief", "create_dailyplan_proposal", "answer_question", "iterate_proposal"),
        input_schema={
            "type": "object",
            "required": ["updates"],
            "properties": {
                "current_draft": {
                    "type": "object",
                    "description": "Optional preference draft state already known in this conversation.",
                },
                "updates": {
                    "type": "object",
                    "description": (
                        "Fields detected from the user's message. Supported keys: "
                        "dietary_pattern, avoided_foods, preferred_foods, allergies_or_intolerances, "
                        "preferred_meals_per_day, cooking_time_preference, budget_preference, "
                        "simplicity_preference, variety_preference."
                    ),
                },
                "field_sources": {
                    "type": "object",
                    "description": "Optional per-field source labels. Defaults to chat_draft for updated fields.",
                },
            },
        },
    ),
    TOOL_SHARE_PREFERENCE_DRAFT_CARD: AssistantToolSpec(
        name=TOOL_SHARE_PREFERENCE_DRAFT_CARD,
        description=(
            "Build a chat-renderable food and meal preference draft card. "
            "When the user explicitly asks to show or review food/meal preferences, request this tool instead of "
            "rendering a plain-text substitute. Use it after a meaningful grouped completion, not after "
            "every individual preference update. The card is reviewable and non-persistent."
        ),
        category=AssistantToolCategory.DRAFT,
        risk_level=AssistantToolRiskLevel.MEDIUM,
        requires_human_review=False,
        allowed_intents=("capture_nutrition_brief", "create_dailyplan_proposal", "answer_question", "iterate_proposal"),
        input_schema={
            "type": "object",
            "required": ["preference_draft"],
            "properties": {
                "preference_draft": {
                    "type": "object",
                    "description": "Current preference draft to render as a user-visible card.",
                },
            },
        },
    ),



    TOOL_UPDATE_PROPOSAL_PREFERENCES: AssistantToolSpec(
        name=TOOL_UPDATE_PROPOSAL_PREFERENCES,
        description=(
            "Update proposal-scoped preferences for the current nutrition work: "
            "goal, requested entity, meals, complexity, energy adjustment, targets and notes. "
            "Use it before confirming any explicit proposal change. Include complexity_level in the same call "
            "when the user says simple, sencillo, intermedio or elaborado; do not leave it only in prose. "
            "This is not personal profile memory and does not render "
            "a card automatically. Use share_proposal_preferences_card when review is useful."
        ),
        category=AssistantToolCategory.DRAFT,
        risk_level=AssistantToolRiskLevel.MEDIUM,
        requires_human_review=False,
        allowed_intents=("capture_nutrition_brief", "create_dailyplan_proposal", "iterate_proposal"),
        input_schema={
            "type": "object",
            "required": ["updates"],
            "additionalProperties": False,
            "properties": {
                "updates": {
                    "type": "object",
                    "description": "Normalized proposal fields. simple/sencillo -> complexity_level=low.",
                    "additionalProperties": False,
                    "properties": {
                        "goal": {
                            "type": "string",
                            "enum": ["fat_loss", "muscle_gain", "maintenance", "performance", "healthy_eating"],
                        },
                        "requested_entity": {
                            "type": "string",
                            "enum": ["daily_plan", "program"],
                        },
                        "meals_per_day": {"type": "integer", "minimum": 1, "maximum": 8},
                        "complexity_level": {
                            "type": "string",
                            "enum": ["low", "medium", "high"],
                            "description": "algo simple/sencillo=low; intermedio=medium; elaborado/complejo=high",
                        },
                        "energy_adjustment": {"type": "string"},
                        "calorie_target": {"type": "integer"},
                        "protein_target": {"type": "integer"},
                        "carb_target": {"type": "integer"},
                        "fat_target": {"type": "integer"},
                        "notes": {"type": "array", "items": {"type": "string"}},
                    },
                },
                "current_preferences": {"type": "object"},
                "field_sources": {
                    "type": "object",
                    "description": "Optional field-to-source map.",
                },
            },
        },
    ),
    TOOL_SHARE_PROPOSAL_PREFERENCES_CARD: AssistantToolSpec(
        name=TOOL_SHARE_PROPOSAL_PREFERENCES_CARD,
        description=(
            "Return a chat-renderable card for proposal-scoped preferences. "
            "When the user explicitly asks to show or review proposal preferences, request this tool instead of "
            "rendering a plain-text substitute. Use it before a meaningful review/creation step, "
            "not after every individual proposal parameter update."
        ),
        category=AssistantToolCategory.DRAFT,
        risk_level=AssistantToolRiskLevel.MEDIUM,
        requires_human_review=False,
        allowed_intents=("capture_nutrition_brief", "create_dailyplan_proposal", "iterate_proposal"),
        input_schema={
            "type": "object",
            "required": ["proposal_preferences"],
            "properties": {
                "proposal_preferences": {
                    "type": "object",
                    "description": "Proposal preferences draft previously collected in this conversation.",
                },
            },
        },
    ),

    TOOL_COMMIT_PROFILE_UPDATE: AssistantToolSpec(
        name=TOOL_COMMIT_PROFILE_UPDATE,
        description=(
            "Commit approved profile draft fields to the authenticated user's persistent ficha. "
            "This tool is internal-only, requires a trusted user approval event, and is not exposed to the LLM provider."
        ),
        category=AssistantToolCategory.COMMIT,
        risk_level=AssistantToolRiskLevel.REVIEW_REQUIRED,
        requires_human_review=True,
        provider_exposed=False,
        allowed_intents=("capture_nutrition_brief", "create_dailyplan_proposal", "answer_question"),
        input_schema={
            "type": "object",
            "required": ["profile_draft"],
            "properties": {
                "profile_draft": {
                    "type": "object",
                    "description": "Profile draft previously shown to the user in a My Scoope card.",
                },
                "approved_fields": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional approved field allowlist. Defaults to committable chat draft fields.",
                },
            },
        },
    ),
    TOOL_CREATE_VALIDATED_MEAL_PROPOSAL: AssistantToolSpec(
        name=TOOL_CREATE_VALIDATED_MEAL_PROPOSAL,
        description=(
            "Create a reviewable meal proposal through My Scoope services. "
            "This never creates or applies a final Meal directly."
        ),
        category=AssistantToolCategory.PROPOSAL,
        risk_level=AssistantToolRiskLevel.REVIEW_REQUIRED,
        mcp_exposed=True,
        mcp_api_path="/ai-tools/create-validated-meal-proposal/",
        allowed_intents=("create_meal_proposal", "iterate_proposal"),
        input_schema={
            "type": "object",
            "required": ["dailyplan_id", "title", "proposed_payload"],
            "properties": {
                "dailyplan_id": {"type": "integer"},
                "title": {"type": "string"},
                "summary": {"type": "string"},
                "targets": {"type": "object"},
                "proposed_payload": {
                    "type": "object",
                    "description": "Meal proposal payload using operational food_id values only.",
                },
            },
        },
    ),

    TOOL_CREATE_NUTRITION_SOLVER_MEAL_PROPOSAL: AssistantToolSpec(
        name=TOOL_CREATE_NUTRITION_SOLVER_MEAL_PROPOSAL,
        description=(
            "Create a reviewable Meal proposal by running the internal Nutrition Solver "
            "against solver-ready operational food candidates. This never creates or applies a final Meal directly."
        ),
        category=AssistantToolCategory.PROPOSAL,
        risk_level=AssistantToolRiskLevel.REVIEW_REQUIRED,
        allowed_intents=("create_meal_proposal", "iterate_proposal"),
        input_schema={
            "type": "object",
            "required": ["dailyplan_id", "title", "target"],
            "properties": {
                "dailyplan_id": {"type": "integer"},
                "title": {"type": "string"},
                "summary": {"type": "string"},
                "target": {
                    "type": "object",
                    "description": "Meal-level target macros. Supports kcal/total_kcal, protein, carbs and fat.",
                },
                "search": {"type": "string"},
                "limit": {"type": "integer"},
                "include_extended": {"type": "boolean"},
                "meal_slot": {"type": "string"},
            },
        },
    ),
    TOOL_CREATE_VALIDATED_DAILYPLAN_PROPOSAL: AssistantToolSpec(
        name=TOOL_CREATE_VALIDATED_DAILYPLAN_PROPOSAL,
        description=(
            "Create a reviewable proposal that adjusts an existing DailyPlan through "
            "validated quantity operations. This never applies the changes directly."
        ),
        category=AssistantToolCategory.PROPOSAL,
        risk_level=AssistantToolRiskLevel.REVIEW_REQUIRED,
        mcp_exposed=True,
        mcp_api_path="/ai-tools/create-validated-dailyplan-proposal/",
        allowed_intents=("create_dailyplan_proposal", "iterate_proposal"),
        input_schema={
            "type": "object",
            "required": ["dailyplan_id", "title", "targets"],
            "properties": {
                "dailyplan_id": {"type": "integer"},
                "title": {"type": "string"},
                "summary": {"type": "string"},
                "targets": {
                    "type": "object",
                    "description": "Target nutrition metrics for the existing DailyPlan.",
                },
                "tolerances": {
                    "type": "object",
                    "description": "Optional target tolerances.",
                },
                "proposed_payload": {
                    "type": "object",
                    "description": (
                        "Validated adjust_dailyplan_to_targets payload containing "
                        "update_meal_food_quantity operations."
                    ),
                },
            },
        },
    ),
    TOOL_CREATE_PROPORTIONAL_DAILYPLAN_CALORIE_PROPOSAL: AssistantToolSpec(
        name=TOOL_CREATE_PROPORTIONAL_DAILYPLAN_CALORIE_PROPOSAL,
        description=(
            "Prepare a reviewable calorie adjustment for an owned DailyPlan while preserving "
            "the exact foods and meal structure. It changes only quantities in the plan's "
            "independent Meal snapshots and never mutates reusable library Meals."
        ),
        category=AssistantToolCategory.PROPOSAL,
        risk_level=AssistantToolRiskLevel.REVIEW_REQUIRED,
        allowed_intents=("create_dailyplan_proposal", "iterate_proposal"),
        input_schema={
            "type": "object",
            "required": ["dailyplan_id", "calorie_delta"],
            "properties": {
                "dailyplan_id": {"type": "integer", "description": "Owned DailyPlan ID."},
                "calorie_delta": {
                    "type": "number",
                    "description": "Signed calorie change, for example 200 or -150.",
                },
                "title": {"type": "string", "description": "Optional proposal title."},
                "summary": {"type": "string", "description": "Optional review summary."},
            },
        },
    ),
    TOOL_PREPARE_PRODUCT_ACTION: AssistantToolSpec(
        name=TOOL_PREPARE_PRODUCT_ACTION,
        description=(
            "Prepare a reviewable My Scoope product action without mutating its target. "
            "Use only after resolving an unambiguous owned target. The result contains a "
            "before/after preview and requires a trusted user confirmation in the UI."
        ),
        category=AssistantToolCategory.PROPOSAL,
        risk_level=AssistantToolRiskLevel.REVIEW_REQUIRED,
        allowed_intents=(
            "answer_question",
            "create_program_proposal",
            "iterate_proposal",
        ),
        input_schema={
            "type": "object",
            "required": ["action_key"],
            "properties": {
                "action_key": {
                    "type": "string",
                    "enum": [
                        "food.create",
                        "food.update",
                        "food.delete",
                        "meal.create",
                        "meal.rename",
                        "meal.delete",
                        "dailyplan.create",
                        "dailyplan.rename",
                        "dailyplan.delete",
                        "program.create",
                        "program.rename",
                        "program.delete",
                        "program.add_week",
                        "program.duplicate_week",
                        "program.remove_week",
                        "calendar.pause",
                        "calendar.resume",
                        "calendar.cancel",
                        "comparison.rename",
                        "proposal.approve",
                        "proposal.reject",
                        "proposal.cancel",
                        "proposal.delete",
                        "proposal.apply",
                    ],
                    "description": "Controlled product action to prepare.",
                },
                "target_id": {
                    "type": "integer",
                    "description": "Owned target ID; omit only for create actions.",
                },
                "parameters": {
                    "type": "object",
                    "description": "Action-specific values used to build the preview.",
                },
            },
        },
    ),
    TOOL_COMMIT_PREPARED_ACTION: AssistantToolSpec(
        name=TOOL_COMMIT_PREPARED_ACTION,
        description="Commit one prepared action after a trusted server-side user confirmation.",
        category=AssistantToolCategory.COMMIT,
        risk_level=AssistantToolRiskLevel.REVIEW_REQUIRED,
        provider_exposed=False,
        input_schema={
            "type": "object",
            "required": ["prepared_action_id"],
            "properties": {
                "prepared_action_id": {"type": "string"},
            },
        },
    ),
    TOOL_CREATE_VALIDATED_DAILYPLAN_BUILD_PROPOSAL: AssistantToolSpec(
        name=TOOL_CREATE_VALIDATED_DAILYPLAN_BUILD_PROPOSAL,
        description=(
            "Create a reviewable DailyPlan build proposal through My Scoope services. "
            "This never creates or applies a final DailyPlan directly."
        ),
        category=AssistantToolCategory.PROPOSAL,
        risk_level=AssistantToolRiskLevel.REVIEW_REQUIRED,
        mcp_exposed=True,
        mcp_api_path="/ai-tools/create-validated-dailyplan-build-proposal/",
        allowed_intents=("create_dailyplan_proposal", "iterate_proposal"),
        input_schema={
            "type": "object",
            "required": ["dailyplan_id", "title", "proposed_payload"],
            "properties": {
                "dailyplan_id": {"type": "integer"},
                "title": {"type": "string"},
                "summary": {"type": "string"},
                "targets": {"type": "object"},
                "proposed_payload": {
                    "type": "object",
                    "description": "DailyPlan proposal payload using operational food_id values only.",
                },
            },
        },
    ),
    TOOL_CREATE_NUTRITION_ENGINE_DAILYPLAN_PROPOSAL: AssistantToolSpec(
        name=TOOL_CREATE_NUTRITION_ENGINE_DAILYPLAN_PROPOSAL,
        description=(
            "Create a reviewable DailyPlan proposal by running the internal My Scoope "
            "nutrition engine from a structured NutritionBrief. The NutritionBrief should be assembled "
            "from profile_draft, preference_draft and proposal_preferences tool results when available."
        ),
        category=AssistantToolCategory.PROPOSAL,
        risk_level=AssistantToolRiskLevel.REVIEW_REQUIRED,
        mcp_exposed=True,
        mcp_api_path="/ai-tools/create-nutrition-engine-dailyplan-proposal/",
        allowed_intents=("capture_nutrition_brief", "create_dailyplan_proposal"),
        input_schema={
            "type": "object",
            "required": ["nutrition_brief"],
            "properties": {
                "nutrition_brief": {
                    "type": "object",
                    "description": "Structured NutritionBrief consumed by the internal nutrition engine.",
                },
            },
        },
    ),
    TOOL_CREATE_NUTRITION_ENGINE_DAILYPLAN_PROPOSAL_FROM_DRAFTS: AssistantToolSpec(
        name=TOOL_CREATE_NUTRITION_ENGINE_DAILYPLAN_PROPOSAL_FROM_DRAFTS,
        description=(
            "Create a reviewable DailyPlan proposal from the assistant's current draft objects: "
            "profile_draft, preference_draft and proposal_preferences. This tool composes a validated "
            "NutritionBrief internally before running the nutrition engine, so the LLM should prefer it "
            "when those draft tool results are available. It never applies the proposal directly."
        ),
        category=AssistantToolCategory.PROPOSAL,
        risk_level=AssistantToolRiskLevel.REVIEW_REQUIRED,
        allowed_intents=("capture_nutrition_brief", "create_dailyplan_proposal"),
        input_schema={
            "type": "object",
            "required": ["profile_draft", "proposal_preferences"],
            "properties": {
                "profile_draft": {
                    "type": "object",
                    "description": "Conversation profile draft with body/context fields such as weight_kg, height_cm, age_years, sex and activity_level.",
                },
                "preference_draft": {
                    "type": "object",
                    "description": "Optional food and meal preference draft with avoided_foods, preferred_foods and style preferences.",
                },
                "proposal_preferences": {
                    "type": "object",
                    "description": "Proposal-scoped preferences such as goal, meals_per_day, targets and energy_adjustment.",
                },
                "current_nutrition_brief": {
                    "type": "object",
                    "description": "Optional existing NutritionBrief from the conversation state to preserve prior context.",
                },
                "raw_prompt": {
                    "type": "string",
                    "description": "Optional compact summary of the user's request for traceability.",
                },
            },
        },
    ),
    TOOL_ITERATE_NUTRITION_ENGINE_DAILYPLAN_PROPOSAL: AssistantToolSpec(
        name=TOOL_ITERATE_NUTRITION_ENGINE_DAILYPLAN_PROPOSAL,
        description=(
            "Create a new reviewable DailyPlan proposal revision from structured user feedback. "
            "This does not mutate or apply the previous proposal."
        ),
        category=AssistantToolCategory.PROPOSAL,
        risk_level=AssistantToolRiskLevel.REVIEW_REQUIRED,
        mcp_exposed=True,
        mcp_api_path="/ai-tools/iterate-nutrition-engine-dailyplan-proposal/",
        allowed_intents=("iterate_proposal",),
        input_schema={
            "type": "object",
            "required": ["previous_proposal_id", "nutrition_brief", "user_message"],
            "properties": {
                "previous_proposal_id": {"type": "integer"},
                "nutrition_brief": {"type": "object"},
                "user_message": {"type": "string"},
            },
        },
    ),
}


def normalize_tool_name(tool_name: str) -> str:
    return " ".join(str(tool_name or "").split()).replace("-", "_").replace(" ", "_").lower()


def is_forbidden_tool_name(tool_name: str) -> bool:
    normalized = normalize_tool_name(tool_name)
    return normalized in FORBIDDEN_TOOL_NAMES or "food_catalog" in normalized or "catalog_food" in normalized


def is_allowed_tool_name(tool_name: str) -> bool:
    return normalize_tool_name(tool_name) in ALLOWED_TOOL_SPECS


def list_allowed_tool_specs(
    *,
    categories: Iterable[AssistantToolCategory | str] | None = None,
) -> list[AssistantToolSpec]:
    specs = list(ALLOWED_TOOL_SPECS.values())
    if categories is None:
        return specs

    allowed_categories = {
        category if isinstance(category, AssistantToolCategory) else AssistantToolCategory(str(category))
        for category in categories
    }
    return [spec for spec in specs if spec.category in allowed_categories]


def _strict_proposal_preferences_provider_schema() -> dict[str, Any]:
    """Return the compact strict schema used by provider-native calling.

    All update fields are present and nullable so OpenAI strict function
    calling cannot silently omit a user-stated proposal preference such as
    ``algo simple``. My Scoope removes null values before local validation, so
    fields the user did not state remain absent from the effective update.
    """

    nullable_string = {"type": ["string", "null"]}
    nullable_integer = {"type": ["integer", "null"]}
    update_properties: dict[str, Any] = {
        "goal": {
            "type": ["string", "null"],
            "enum": ["fat_loss", "muscle_gain", "maintenance", "performance", "healthy_eating", None],
        },
        "requested_entity": {
            "type": ["string", "null"],
            "enum": ["daily_plan", "program", None],
        },
        "meals_per_day": {**nullable_integer, "minimum": 1, "maximum": 8},
        "complexity_level": {
            "type": ["string", "null"],
            "enum": ["low", "medium", "high", None],
            "description": "Use low for algo simple/sencillo, medium for intermedio, high for elaborado/complejo.",
        },
        "energy_adjustment": dict(nullable_string),
        "calorie_target": dict(nullable_integer),
        "protein_target": dict(nullable_integer),
        "carb_target": dict(nullable_integer),
        "fat_target": dict(nullable_integer),
        "notes": {"type": ["array", "null"], "items": {"type": "string"}},
    }
    return {
        "type": "object",
        "properties": {
            "updates": {
                "type": "object",
                "properties": update_properties,
                "required": list(update_properties),
                "additionalProperties": False,
            },
        },
        "required": ["updates"],
        "additionalProperties": False,
    }


def list_provider_tool_specs() -> list[dict[str, Any]]:
    provider_specs: list[dict[str, Any]] = []
    for spec in list_allowed_tool_specs():
        if not spec.provider_exposed:
            continue
        provider_spec = spec.as_provider_tool()
        if spec.name == TOOL_UPDATE_PROPOSAL_PREFERENCES:
            provider_spec = {
                **provider_spec,
                "parameters": _strict_proposal_preferences_provider_schema(),
                "strict": True,
            }
        if spec.name == TOOL_CREATE_NUTRITION_ENGINE_DAILYPLAN_PROPOSAL_FROM_DRAFTS:
            provider_spec = {
                **provider_spec,
                "description": (
                    "Create the requested reviewable DailyPlan proposal from the "
                    "current conversation workspace. My Scoope supplies all known "
                    "drafts and defaults automatically; never fabricate them."
                ),
                "parameters": {
                    "type": "object",
                    "required": [],
                    "properties": {},
                    "additionalProperties": False,
                },
                "strict": True,
            }
        provider_specs.append(provider_spec)
    return provider_specs


def list_mcp_tool_specs() -> list[AssistantToolSpec]:
    """Return the MCP projection of the canonical Assistant capability catalog."""

    return [
        spec
        for spec in list_allowed_tool_specs()
        if spec.mcp_exposed
    ]


def get_mcp_tool_spec(tool_name: str) -> AssistantToolSpec:
    normalized = normalize_tool_name(tool_name)
    for spec in list_mcp_tool_specs():
        if spec.mcp_name == normalized:
            return spec
    raise AssistantToolRegistryError(f"unsupported_mcp_tool:{normalized}")


def get_tool_spec(tool_name: str) -> AssistantToolSpec:
    normalized = normalize_tool_name(tool_name)
    if is_forbidden_tool_name(normalized):
        raise AssistantToolRegistryError(f"forbidden_ai_assistant_tool:{normalized}")
    try:
        return ALLOWED_TOOL_SPECS[normalized]
    except KeyError as exc:
        raise AssistantToolRegistryError(f"unsupported_ai_assistant_tool:{normalized}") from exc


def validate_tool_request(request: AssistantToolRequest) -> AssistantToolResult:
    """Validate a future tool call against the AI Assistant allowlist.

    The returned result is `pending` when the request is allowed. This function
    does not execute tools; it only creates a safe boundary that Patch 46 can use
    before dispatching to My Scoope services.
    """

    normalized_request = AssistantToolRequest(
        tool_name=request.tool_name,
        arguments=request.arguments,
        request_id=request.request_id,
        reason=request.reason,
        metadata=request.metadata,
    )
    tool_name = normalized_request.tool_name

    if is_forbidden_tool_name(tool_name):
        return _blocked_result(
            normalized_request,
            error_code="forbidden_ai_assistant_tool",
            error_message="This tool is explicitly forbidden for the AI Assistant.",
        )

    spec = ALLOWED_TOOL_SPECS.get(tool_name)
    if spec is None:
        return _blocked_result(
            normalized_request,
            error_code="unsupported_ai_assistant_tool",
            error_message="This tool is not part of the AI Assistant allowlist.",
        )

    missing_arguments = _missing_required_arguments(spec, normalized_request.arguments)
    if missing_arguments:
        return _blocked_result(
            normalized_request,
            error_code="invalid_ai_assistant_tool_arguments",
            error_message="Tool request is missing required arguments.",
            details={"missing_arguments": missing_arguments},
        )

    forbidden_argument_key = _find_forbidden_argument_key(normalized_request.arguments)
    if forbidden_argument_key:
        return _blocked_result(
            normalized_request,
            error_code="forbidden_catalog_reference",
            error_message="AI Assistant tools only accept operational notas.Food identifiers.",
            details={"argument_key": forbidden_argument_key},
        )

    return AssistantToolResult(
        tool_name=tool_name,
        status=AssistantToolStatus.PENDING,
        request_id=normalized_request.request_id,
        data={
            "category": spec.category.value,
            "risk_level": spec.risk_level.value,
            "requires_auth": spec.requires_auth,
            "requires_human_review": spec.requires_human_review,
        },
    )


def _missing_required_arguments(spec: AssistantToolSpec, arguments: dict[str, Any]) -> list[str]:
    required = spec.input_schema.get("required") or []
    return [argument for argument in required if argument not in arguments]


def _find_forbidden_argument_key(value: Any) -> str:
    if isinstance(value, dict):
        for key, nested_value in value.items():
            normalized_key = normalize_tool_name(str(key)).replace("_", "")
            if normalize_tool_name(str(key)) in FORBIDDEN_ARGUMENT_KEYS or normalized_key in FORBIDDEN_ARGUMENT_KEYS:
                return str(key)
            nested_match = _find_forbidden_argument_key(nested_value)
            if nested_match:
                return nested_match
    elif isinstance(value, list | tuple):
        for nested_value in value:
            nested_match = _find_forbidden_argument_key(nested_value)
            if nested_match:
                return nested_match
    return ""


def _blocked_result(
    request: AssistantToolRequest,
    *,
    error_code: str,
    error_message: str,
    details: dict[str, Any] | None = None,
) -> AssistantToolResult:
    metadata = dict(request.metadata or {})
    if details:
        metadata["details"] = details
    return AssistantToolResult(
        tool_name=request.tool_name,
        status=AssistantToolStatus.BLOCKED,
        request_id=request.request_id,
        error_code=error_code,
        error_message=error_message,
        metadata=metadata,
    )
