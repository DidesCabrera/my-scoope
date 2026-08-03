"""Compatibility tool functions backed by registered product ports."""

from ai_assistant.application.product_ports import get_ai_product_bindings
from ai_assistant.application.tools.tool_names import (
    TOOL_COMMIT_PREPARED_ACTION,
    TOOL_PREPARE_PRODUCT_ACTION,
)


def prepare_product_action_tool(
    user,
    action_key: str,
    target_id: int | None = None,
    parameters: dict | None = None,
):
    tool = get_ai_product_bindings().proposal_tools[TOOL_PREPARE_PRODUCT_ACTION]
    return tool(
        user,
        action_key=action_key,
        target_id=target_id,
        parameters=parameters,
    )


def commit_prepared_action_tool(user, prepared_action_id: str):
    tool = get_ai_product_bindings().profile_commit_tools[TOOL_COMMIT_PREPARED_ACTION]
    return tool(user, prepared_action_id=prepared_action_id)
