"""Composition root for product implementations exposed to AI Assistant ports."""

from __future__ import annotations

from ai_assistant.application.product_ports import (
    AIProductBindings,
    register_ai_product_bindings,
)
from ai_assistant.application.tools.tool_names import (
    TOOL_COMMIT_PREPARED_ACTION,
    TOOL_COMMIT_PROFILE_UPDATE,
    TOOL_COMPARE_DAILYPLAN_TO_TARGETS,
    TOOL_CREATE_NUTRITION_ENGINE_DAILYPLAN_PROPOSAL,
    TOOL_CREATE_NUTRITION_ENGINE_DAILYPLAN_PROPOSAL_FROM_DRAFTS,
    TOOL_CREATE_NUTRITION_SOLVER_MEAL_PROPOSAL,
    TOOL_CREATE_PROPORTIONAL_DAILYPLAN_CALORIE_PROPOSAL,
    TOOL_CREATE_VALIDATED_DAILYPLAN_BUILD_PROPOSAL,
    TOOL_CREATE_VALIDATED_DAILYPLAN_PROPOSAL,
    TOOL_CREATE_VALIDATED_MEAL_PROPOSAL,
    TOOL_ITERATE_NUTRITION_ENGINE_DAILYPLAN_PROPOSAL,
    TOOL_LIST_INBOX_ITEMS,
    TOOL_LIST_OPERATIONAL_FOODS,
    TOOL_LIST_SAVED_COMPARISONS,
    TOOL_LIST_USER_DAILYPLANS,
    TOOL_LIST_USER_FOODS,
    TOOL_LIST_USER_MEALS,
    TOOL_LIST_USER_PROGRAMS,
    TOOL_LIST_USER_PROPOSALS,
    TOOL_PREPARE_PRODUCT_ACTION,
    TOOL_PREVIEW_NUTRITION_SOLVER_CANDIDATES,
    TOOL_READ_CALENDARIZATION,
    TOOL_READ_DAILYPLAN,
    TOOL_READ_FOOD,
    TOOL_READ_MEAL,
    TOOL_READ_PROGRAM,
    TOOL_READ_PROPOSAL,
    TOOL_READ_SAVED_COMPARISON,
    TOOL_READ_USER_PROFILE_CONTEXT,
    TOOL_SEARCH_OPERATIONAL_FOODS,
    TOOL_SEARCH_USER_DAILYPLANS,
    TOOL_SEARCH_USER_MEALS,
    TOOL_SHARE_PREFERENCE_DRAFT_CARD,
    TOOL_SHARE_PROFILE_DRAFT_CARD,
    TOOL_SHARE_PROPOSAL_PREFERENCES_CARD,
    TOOL_UPDATE_PREFERENCE_DRAFT,
    TOOL_UPDATE_PROFILE_DRAFT,
    TOOL_UPDATE_PROPOSAL_PREFERENCES,
)
from notas.application.ai_intake.nutrition_brief import required_proposal_fields
from notas.application.ai_tools.comparison_tools import (
    list_saved_comparisons_tool,
    read_saved_comparison_tool,
)
from notas.application.ai_tools.preference_tools import (
    share_preference_draft_card_tool,
    update_preference_draft_tool,
)
from notas.application.ai_tools.prepared_actions import (
    cancel_prepared_action,
    commit_prepared_action,
    prepare_product_action,
    serialize_prepared_action,
)
from notas.application.ai_tools.profile_tools import (
    commit_profile_update_tool,
    read_user_profile_context_tool,
    share_profile_draft_card_tool,
    update_profile_draft_tool,
)
from notas.application.ai_tools.proposal_preference_tools import (
    share_proposal_preferences_card_tool,
    update_proposal_preferences_tool,
)
from notas.application.ai_tools.proposal_tools import (
    build_nutrition_brief_from_ai_drafts,
    create_nutrition_engine_dailyplan_proposal_from_drafts_tool,
    create_nutrition_engine_dailyplan_proposal_tool,
    create_nutrition_solver_meal_proposal_tool,
    create_proportional_dailyplan_calorie_proposal_tool,
    create_validated_dailyplan_build_proposal_tool,
    create_validated_dailyplan_proposal_tool,
    create_validated_meal_proposal_tool,
    iterate_nutrition_engine_dailyplan_proposal_tool,
)
from notas.application.ai_tools.read_tools import (
    list_available_foods_tool,
    list_user_dailyplans_tool,
    list_user_foods_tool,
    list_user_meals_tool,
    list_user_proposals_tool,
    preview_nutrition_solver_candidates_tool,
    read_dailyplan_tool,
    read_food_tool,
    read_meal_tool,
    read_proposal_tool,
    search_dailyplans_tool,
    search_foods_tool,
    search_meals_tool,
)
from notas.application.ai_tools.runtime import run_ai_tool
from notas.application.ai_tools.validation_tools import compare_dailyplan_to_targets_tool
from notas.application.ai_tools.workspace_tools import (
    list_inbox_items_tool,
    list_user_programs_tool,
    read_calendarization_tool,
    read_program_tool,
)


def _prepare_product_action_tool(
    user,
    action_key: str,
    target_id: int | None = None,
    parameters: dict | None = None,
):
    return run_ai_tool(
        lambda: {
            "prepared_action": serialize_prepared_action(
                prepare_product_action(
                    user=user,
                    action_key=action_key,
                    target_id=target_id,
                    parameters=parameters,
                )
            )
        },
        user=user,
    )


def _commit_prepared_action_tool(user, prepared_action_id: str):
    return run_ai_tool(
        lambda: {
            "prepared_action": serialize_prepared_action(
                commit_prepared_action(user=user, public_id=prepared_action_id)
            )
        },
        user=user,
    )


def register_product_ai_bindings() -> None:
    register_ai_product_bindings(
        AIProductBindings(
            read_only_tools={
                TOOL_READ_DAILYPLAN: read_dailyplan_tool,
                TOOL_READ_CALENDARIZATION: read_calendarization_tool,
                TOOL_READ_FOOD: read_food_tool,
                TOOL_READ_MEAL: read_meal_tool,
                TOOL_READ_PROGRAM: read_program_tool,
                TOOL_READ_PROPOSAL: read_proposal_tool,
                TOOL_LIST_SAVED_COMPARISONS: list_saved_comparisons_tool,
                TOOL_READ_SAVED_COMPARISON: read_saved_comparison_tool,
                TOOL_LIST_USER_PROPOSALS: list_user_proposals_tool,
                TOOL_READ_USER_PROFILE_CONTEXT: read_user_profile_context_tool,
                TOOL_SEARCH_OPERATIONAL_FOODS: search_foods_tool,
                TOOL_SEARCH_USER_DAILYPLANS: search_dailyplans_tool,
                TOOL_SEARCH_USER_MEALS: search_meals_tool,
                TOOL_LIST_OPERATIONAL_FOODS: list_available_foods_tool,
                TOOL_LIST_USER_DAILYPLANS: list_user_dailyplans_tool,
                TOOL_LIST_USER_FOODS: list_user_foods_tool,
                TOOL_LIST_USER_MEALS: list_user_meals_tool,
                TOOL_LIST_USER_PROGRAMS: list_user_programs_tool,
                TOOL_LIST_INBOX_ITEMS: list_inbox_items_tool,
                TOOL_PREVIEW_NUTRITION_SOLVER_CANDIDATES: preview_nutrition_solver_candidates_tool,
            },
            profile_draft_tools={
                TOOL_UPDATE_PROFILE_DRAFT: update_profile_draft_tool,
                TOOL_SHARE_PROFILE_DRAFT_CARD: share_profile_draft_card_tool,
                TOOL_UPDATE_PREFERENCE_DRAFT: update_preference_draft_tool,
                TOOL_SHARE_PREFERENCE_DRAFT_CARD: share_preference_draft_card_tool,
                TOOL_UPDATE_PROPOSAL_PREFERENCES: update_proposal_preferences_tool,
                TOOL_SHARE_PROPOSAL_PREFERENCES_CARD: share_proposal_preferences_card_tool,
            },
            profile_commit_tools={
                TOOL_COMMIT_PROFILE_UPDATE: commit_profile_update_tool,
                TOOL_COMMIT_PREPARED_ACTION: _commit_prepared_action_tool,
            },
            proposal_tools={
                TOOL_CREATE_PROPORTIONAL_DAILYPLAN_CALORIE_PROPOSAL: create_proportional_dailyplan_calorie_proposal_tool,
                TOOL_PREPARE_PRODUCT_ACTION: _prepare_product_action_tool,
                TOOL_CREATE_VALIDATED_MEAL_PROPOSAL: create_validated_meal_proposal_tool,
                TOOL_CREATE_NUTRITION_SOLVER_MEAL_PROPOSAL: create_nutrition_solver_meal_proposal_tool,
                TOOL_CREATE_VALIDATED_DAILYPLAN_PROPOSAL: create_validated_dailyplan_proposal_tool,
                TOOL_CREATE_VALIDATED_DAILYPLAN_BUILD_PROPOSAL: create_validated_dailyplan_build_proposal_tool,
                TOOL_CREATE_NUTRITION_ENGINE_DAILYPLAN_PROPOSAL: create_nutrition_engine_dailyplan_proposal_tool,
                TOOL_CREATE_NUTRITION_ENGINE_DAILYPLAN_PROPOSAL_FROM_DRAFTS: create_nutrition_engine_dailyplan_proposal_from_drafts_tool,
                TOOL_ITERATE_NUTRITION_ENGINE_DAILYPLAN_PROPOSAL: iterate_nutrition_engine_dailyplan_proposal_tool,
            },
            validation_tools={
                TOOL_COMPARE_DAILYPLAN_TO_TARGETS: compare_dailyplan_to_targets_tool,
            },
            required_proposal_fields=required_proposal_fields,
            build_nutrition_brief_from_ai_drafts=build_nutrition_brief_from_ai_drafts,
            prepare_product_action=prepare_product_action,
            commit_prepared_action=commit_prepared_action,
            cancel_prepared_action=cancel_prepared_action,
            serialize_prepared_action=serialize_prepared_action,
        )
    )

