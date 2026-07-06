from notas.application.ai_tools.runtime import run_ai_tool
from notas.application.queries.dailyplan_queries import (
    get_dailyplan_detail,
    list_available_dailyplans,
    list_user_dailyplans,
    search_dailyplans,
)
from notas.application.queries.food_queries import (
    get_food_detail,
    list_available_foods,
    list_user_foods,
    search_foods,
)
from notas.application.queries.meal_queries import (
    get_meal_detail,
    list_available_meals,
    list_user_meals,
    search_meals,
)
from notas.application.queries.proposal_queries import (
    get_proposal_detail,
    list_dailyplan_proposals,
    list_user_proposals,
    search_proposals,
)
from notas.application.queries.solver_food_candidates import (
    list_solver_food_candidates,
)

from notas.application.queries.food_catalog_queries import (
    list_food_catalog_for_planning,
)

def _serialize_dto_list(items) -> list[dict]:
    return [
        item.as_dict()
        for item in items
    ]

# FOOD TOOLS -------------------------------------------------


def _list_user_foods_data(user) -> dict:
    return {
        "foods": _serialize_dto_list(
            list_user_foods(user),
        ),
    }


def list_user_foods_tool(user):
    return run_ai_tool(
        _list_user_foods_data,
        user,
        user=user,
    )


def _list_available_foods_data(user) -> dict:
    return {
        "foods": _serialize_dto_list(
            list_available_foods(user),
        ),
    }


def list_available_foods_tool(user):
    return run_ai_tool(
        _list_available_foods_data,
        user,
        user=user,
    )


def _search_foods_data(user, query: str) -> dict:
    return {
        "foods": _serialize_dto_list(
            search_foods(
                user,
                query,
            ),
        ),
        "query": query,
    }


def search_foods_tool(user, query: str):
    return run_ai_tool(
        _search_foods_data,
        user,
        query,
        user=user,
    )


def _read_food_data(user, food_id: int) -> dict:
    return {
        "food": get_food_detail(
            user,
            food_id,
        ).as_dict(),
    }


def read_food_tool(user, food_id: int):
    return run_ai_tool(
        _read_food_data,
        user,
        food_id,
        user=user,
    )

def _list_food_catalog_data(
    user,
    search: str | None = None,
    limit: int = 50,
) -> dict:
    return {
        "catalog": list_food_catalog_for_planning(
            user=user,
            search=search,
            limit=limit,
        ).as_dict(),
    }


def list_food_catalog_tool(
    user,
    search: str | None = None,
    limit: int = 50,
):
    return run_ai_tool(
        _list_food_catalog_data,
        user,
        search=search,
        limit=limit,
        user=user,
    )


def _preview_nutrition_solver_candidates_data(
    user,
    search: str | None = None,
    limit: int = 20,
    include_extended: bool = True,
) -> dict:
    preview = list_solver_food_candidates(
        user,
        search=search,
        limit=limit,
        include_extended=include_extended,
    ).as_dict()
    return {
        "solver_candidate_preview": preview,
        "source_boundary": {
            "source": "notas.Food",
            "candidate_contract": "nutrition_solver.domain.models.SolverFood",
            "catalog_fields_exposed": False,
            "external_payloads_exposed": False,
            "writes_allowed": False,
        },
    }


def preview_nutrition_solver_candidates_tool(
    user,
    search: str | None = None,
    limit: int = 20,
    include_extended: bool = True,
):
    return run_ai_tool(
        _preview_nutrition_solver_candidates_data,
        user,
        search=search,
        limit=limit,
        include_extended=include_extended,
        user=user,
    )


# MEAL TOOLS -------------------------------------------------


def _list_user_meals_data(user) -> dict:
    return {
        "meals": _serialize_dto_list(
            list_user_meals(user),
        ),
    }


def list_user_meals_tool(user):
    return run_ai_tool(
        _list_user_meals_data,
        user,
        user=user,
    )


def _list_available_meals_data(user) -> dict:
    return {
        "meals": _serialize_dto_list(
            list_available_meals(user),
        ),
    }


def list_available_meals_tool(user):
    return run_ai_tool(
        _list_available_meals_data,
        user,
        user=user,
    )


def _search_meals_data(user, query: str) -> dict:
    return {
        "meals": _serialize_dto_list(
            search_meals(
                user,
                query,
            ),
        ),
        "query": query,
    }


def search_meals_tool(user, query: str):
    return run_ai_tool(
        _search_meals_data,
        user,
        query,
        user=user,
    )


def _read_meal_data(user, meal_id: int) -> dict:
    return {
        "meal": get_meal_detail(
            user,
            meal_id,
        ).as_dict(),
    }


def read_meal_tool(user, meal_id: int):
    return run_ai_tool(
        _read_meal_data,
        user,
        meal_id,
        user=user,
    )


# DAILYPLAN TOOLS --------------------------------------------


def _list_user_dailyplans_data(user) -> dict:
    return {
        "dailyplans": _serialize_dto_list(
            list_user_dailyplans(user),
        ),
    }


def list_user_dailyplans_tool(user):
    return run_ai_tool(
        _list_user_dailyplans_data,
        user,
        user=user,
    )


def _list_available_dailyplans_data(user) -> dict:
    return {
        "dailyplans": _serialize_dto_list(
            list_available_dailyplans(user),
        ),
    }


def list_available_dailyplans_tool(user):
    return run_ai_tool(
        _list_available_dailyplans_data,
        user,
        user=user,
    )


def _search_dailyplans_data(user, query: str) -> dict:
    return {
        "dailyplans": _serialize_dto_list(
            search_dailyplans(
                user,
                query,
            ),
        ),
        "query": query,
    }


def search_dailyplans_tool(user, query: str):
    return run_ai_tool(
        _search_dailyplans_data,
        user,
        query,
        user=user,
    )


def _read_dailyplan_data(user, dailyplan_id: int) -> dict:
    return {
        "dailyplan": get_dailyplan_detail(
            user,
            dailyplan_id,
        ).as_dict(),
    }


def read_dailyplan_tool(user, dailyplan_id: int):
    return run_ai_tool(
        _read_dailyplan_data,
        user,
        dailyplan_id,
        user=user,
    )


# PROPOSAL TOOLS ---------------------------------------------


def _list_user_proposals_data(user) -> dict:
    return {
        "proposals": _serialize_dto_list(
            list_user_proposals(user),
        ),
    }


def list_user_proposals_tool(user):
    return run_ai_tool(
        _list_user_proposals_data,
        user,
        user=user,
    )


def _list_dailyplan_proposals_data(user, dailyplan_id: int) -> dict:
    return {
        "dailyplan_id": dailyplan_id,
        "proposals": _serialize_dto_list(
            list_dailyplan_proposals(
                user,
                dailyplan_id,
            ),
        ),
    }


def list_dailyplan_proposals_tool(user, dailyplan_id: int):
    return run_ai_tool(
        _list_dailyplan_proposals_data,
        user,
        dailyplan_id,
        user=user,
    )


def _search_proposals_data(user, query: str) -> dict:
    return {
        "proposals": _serialize_dto_list(
            search_proposals(
                user,
                query,
            ),
        ),
        "query": query,
    }


def search_proposals_tool(user, query: str):
    return run_ai_tool(
        _search_proposals_data,
        user,
        query,
        user=user,
    )


def _read_proposal_data(user, proposal_id: int) -> dict:
    return {
        "proposal": get_proposal_detail(
            user,
            proposal_id,
        ).as_dict(),
    }


def read_proposal_tool(user, proposal_id: int):
    return run_ai_tool(
        _read_proposal_data,
        user,
        proposal_id,
        user=user,
    )