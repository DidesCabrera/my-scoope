"""Capability-oriented read access to the authenticated user's workspace."""

from notas.application.ai_tools.comparison_tools import (
    list_saved_comparisons_tool,
    read_saved_comparison_tool,
)
from notas.application.ai_tools.read_tools import (
    list_user_proposals_tool,
    read_dailyplan_tool,
    read_food_tool,
    read_meal_tool,
    read_proposal_tool,
    search_proposals_tool,
)
from notas.application.ai_tools.results import tool_error
from notas.application.ai_tools.runtime import run_ai_tool
from notas.application.ai_tools.workspace_tools import (
    read_calendarization_tool,
    read_program_tool,
)
from notas.application.queries.dailyplan_queries import build_dailyplan_list_item_dto
from notas.application.queries.food_queries import build_food_list_item_dto
from notas.application.queries.library_queries import (
    dailyplan_library_queryset,
    food_library_queryset,
    meal_library_queryset,
    program_library_queryset,
)
from notas.application.queries.meal_queries import build_meal_list_item_dto


def _bounded_page(limit: int, offset: int) -> tuple[int, int]:
    try:
        normalized_limit = max(1, min(int(limit), 50))
    except (TypeError, ValueError):
        normalized_limit = 20
    try:
        normalized_offset = max(0, int(offset))
    except (TypeError, ValueError):
        normalized_offset = 0
    return normalized_limit, normalized_offset


def _collection_envelope(
    *,
    resource: str,
    key: str,
    items: list[dict],
    total_count: int,
    limit: int,
    offset: int,
) -> dict:
    returned_count = len(items)
    next_offset = offset + returned_count
    has_more = next_offset < total_count
    return {
        "resource": resource,
        "scope": "library",
        key: items,
        "total_count": total_count,
        "returned_count": returned_count,
        "limit": limit,
        "offset": offset,
        "has_more": has_more,
        "next_offset": next_offset if has_more else None,
        "truncated": has_more,
    }


def _query_library_collection_data(
    user,
    *,
    resource: str,
    search: str,
    limit: int,
    offset: int,
) -> dict:
    limit, offset = _bounded_page(limit, offset)
    if resource == "foods":
        queryset = food_library_queryset(user)
        if search:
            queryset = queryset.filter(name__icontains=search)
        total_count = queryset.count()
        rows = list(queryset.select_related("created_by")[offset:offset + limit])
        items = [build_food_list_item_dto(row).as_dict() for row in rows]
        key = "foods"
    elif resource == "meals":
        queryset = meal_library_queryset(user)
        if search:
            queryset = queryset.filter(name__icontains=search)
        total_count = queryset.count()
        rows = list(queryset.prefetch_related("meal_food_set")[offset:offset + limit])
        items = [build_meal_list_item_dto(row, user).as_dict() for row in rows]
        key = "meals"
    elif resource == "dailyplans":
        queryset = dailyplan_library_queryset(user)
        if search:
            queryset = queryset.filter(name__icontains=search)
        total_count = queryset.count()
        rows = list(queryset.prefetch_related("dailyplan_meals__meal")[offset:offset + limit])
        items = [build_dailyplan_list_item_dto(row, user).as_dict() for row in rows]
        key = "dailyplans"
    else:
        queryset = program_library_queryset(user)
        if search:
            queryset = queryset.filter(name__icontains=search)
        total_count = queryset.count()
        rows = list(queryset.prefetch_related("program_dailyplan")[offset:offset + limit])
        items = [
            {
                "id": row.id,
                "name": row.name,
                "created_by_id": row.created_by_id,
                "duration_weeks": row.normalized_duration_weeks,
                "filled_days_count": row.filled_days_count,
                "empty_days_count": row.empty_days_count,
                "is_draft": row.is_draft,
                "is_public": row.is_public,
                "editable": row.created_by_id == user.id,
            }
            for row in rows
        ]
        key = "programs"
    return _collection_envelope(
        resource=resource,
        key=key,
        items=items,
        total_count=total_count,
        limit=limit,
        offset=offset,
    )


def query_workspace_tool(
    user,
    resource: str,
    object_id: int | None = None,
    search: str = "",
    limit: int = 20,
    offset: int = 0,
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

    if normalized_resource in {"foods", "meals", "dailyplans", "programs"}:
        return run_ai_tool(
            _query_library_collection_data,
            user,
            resource=normalized_resource,
            search=normalized_search,
            limit=limit,
            offset=offset,
            user=user,
        )
    if normalized_resource == "saved_comparisons":
        return list_saved_comparisons_tool(user, limit=limit)

    list_tools = {
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
