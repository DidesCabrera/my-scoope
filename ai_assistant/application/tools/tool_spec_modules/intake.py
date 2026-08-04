from __future__ import annotations

from ai_assistant.application.tools.contracts import (
    AssistantToolCategory,
    AssistantToolRiskLevel,
    AssistantToolSpec,
)
from ai_assistant.application.tools.tool_names import *  # noqa: F403

INTAKE_TOOL_SPECS = {
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
}

__all__ = ["INTAKE_TOOL_SPECS"]
