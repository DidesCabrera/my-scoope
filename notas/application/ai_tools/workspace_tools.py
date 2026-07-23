from notas.application.ai_tools.runtime import run_ai_tool
from notas.application.queries.workspace_queries import (
    get_owned_program_detail,
    get_user_calendarization_context,
    list_owned_program_summaries,
    list_user_inbox_summaries,
)


def list_user_programs_tool(user, search: str = "", limit: int = 20):
    return run_ai_tool(
        lambda: {
            "programs": list_owned_program_summaries(
                user,
                search=search,
                limit=limit,
            )
        },
        user=user,
    )

def read_program_tool(user, program_id: int):
    return run_ai_tool(
        lambda: {"program": get_owned_program_detail(user, program_id=program_id)},
        user=user,
    )


def read_calendarization_tool(user, history_limit: int = 5):
    return run_ai_tool(
        lambda: {
            "calendarization": get_user_calendarization_context(
                user,
                history_limit=history_limit,
            )
        },
        user=user,
    )


def list_inbox_items_tool(
    user,
    scope: str = "received",
    favorites_only: bool = False,
    limit: int = 20,
):
    return run_ai_tool(
        lambda: {
            "inbox_items": list_user_inbox_summaries(
                user,
                scope=scope,
                favorites_only=favorites_only,
                limit=limit,
            )
        },
        user=user,
    )
