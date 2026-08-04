from __future__ import annotations

from ai_assistant.application.tools.contracts import (
    AssistantToolCategory,
    AssistantToolRiskLevel,
    AssistantToolSpec,
)
from ai_assistant.application.tools.tool_names import *  # noqa: F403

PROPOSALS_TOOL_SPECS = {
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

__all__ = ["PROPOSALS_TOOL_SPECS"]
