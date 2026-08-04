from django.urls import path

from notas.interface.api.ai_tools import (
    ai_tools_compare_dailyplan_to_targets,
    ai_tools_create_nutrition_engine_dailyplan_proposal,
    ai_tools_create_validated_dailyplan_build_proposal,
    ai_tools_create_validated_dailyplan_proposal,
    ai_tools_create_validated_meal_proposal,
    ai_tools_health,
    ai_tools_iterate_nutrition_engine_dailyplan_proposal,
    ai_tools_list_food_catalog,
    ai_tools_list_user_proposals,
    ai_tools_read_dailyplan,
    ai_tools_read_food,
    ai_tools_read_meal,
    ai_tools_read_proposal,
)

urlpatterns = [
    path("ai-tools/health/", ai_tools_health, name="ai_tools_health"),
    path("ai-tools/read-food/", ai_tools_read_food, name="ai_tools_read_food"),
    path("ai-tools/read-meal/", ai_tools_read_meal, name="ai_tools_read_meal"),
    path("ai-tools/read-dailyplan/", ai_tools_read_dailyplan, name="ai_tools_read_dailyplan"),
    path("ai-tools/read-proposal/", ai_tools_read_proposal, name="ai_tools_read_proposal"),
    path("ai-tools/list-user-proposals/", ai_tools_list_user_proposals, name="ai_tools_list_user_proposals"),
    path("ai-tools/compare-dailyplan-to-targets/", ai_tools_compare_dailyplan_to_targets, name="ai_tools_compare_dailyplan_to_targets"),
    path("ai-tools/create-validated-dailyplan-proposal/", ai_tools_create_validated_dailyplan_proposal, name="ai_tools_create_validated_dailyplan_proposal"),
    path("ai-tools/list-food-catalog/", ai_tools_list_food_catalog, name="ai_tools_list_food_catalog"),
    path("ai-tools/create-validated-meal-proposal/", ai_tools_create_validated_meal_proposal, name="ai_tools_create_validated_meal_proposal"),
    path("ai-tools/create-validated-dailyplan-build-proposal/", ai_tools_create_validated_dailyplan_build_proposal, name="ai_tools_create_validated_dailyplan_build_proposal"),
    path("ai-tools/create-nutrition-engine-dailyplan-proposal/", ai_tools_create_nutrition_engine_dailyplan_proposal, name="ai_tools_create_nutrition_engine_dailyplan_proposal"),
    path("ai-tools/iterate-nutrition-engine-dailyplan-proposal/", ai_tools_iterate_nutrition_engine_dailyplan_proposal, name="ai_tools_iterate_nutrition_engine_dailyplan_proposal"),
]
