"""Capability-oriented read access to the authenticated user's workspace."""

from notas.application.ai_tools.comparison_tools import (
    list_saved_comparisons_tool,
    read_saved_comparison_tool,
)
from notas.application.ai_tools.read_tools import (
    list_user_dailyplans_tool,
    list_user_foods_tool,
    list_user_meals_tool,
    list_user_proposals_tool,
    read_dailyplan_tool,
    read_food_tool,
    read_meal_tool,
    read_proposal_tool,
    search_dailyplans_tool,
    search_foods_tool,
    search_meals_tool,
    search_proposals_tool,
)
from notas.application.ai_tools.results import tool_error
from notas.application.ai_tools.workspace_tools import (
    list_user_programs_tool,
    read_calendarization_tool,
    read_program_tool,
)


def query_workspace_tool(
    user,
    resource: str,
    object_id: int | None = None,
    search: str = "",
    limit: int = 20,
):
    """Translate one provider-facing query into existing owner-scoped read tools."""

    normalized_resource = str(resource or "").strip().lower()
    normalized_search = str(search or "").strip()

    if normalized_resource == "calendarization":
        return read_calendarization_tool(user, history_limit=limit)

    detail_tools = {
        "foods": (read_food_tool, "food_id"),
        "meals": (read_meal_tool, "meal_id"),
        "dailyplans": (read_dailyplan_tool, "dailyplan_id"),
        "programs": (read_program_tool, "program_id"),
        "proposals": (read_proposal_tool, "proposal_id"),
        "saved_comparisons": (read_saved_comparison_tool, "comparison_id"),
    }
    if object_id is not None and normalized_resource in detail_tools:
        tool, id_name = detail_tools[normalized_resource]
        return tool(user, **{id_name: object_id})

    if normalized_resource == "programs":
        return list_user_programs_tool(user, search=normalized_search, limit=limit)
    if normalized_resource == "saved_comparisons":
        return list_saved_comparisons_tool(user, limit=limit)

    list_tools = {
        "foods": (list_user_foods_tool, search_foods_tool),
        "meals": (list_user_meals_tool, search_meals_tool),
        "dailyplans": (list_user_dailyplans_tool, search_dailyplans_tool),
        "proposals": (list_user_proposals_tool, search_proposals_tool),
    }
    if normalized_resource in list_tools:
        list_tool, search_tool = list_tools[normalized_resource]
        if normalized_search:
            return search_tool(user, query=normalized_search)
        return list_tool(user)

    return tool_error(
        code="invalid_workspace_resource",
        message="El recurso solicitado no está disponible para consulta.",
        details={"resource": normalized_resource},
    )
