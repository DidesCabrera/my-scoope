from ai_assistant.application.prepared_actions import (
    commit_prepared_action,
    prepare_product_action,
    serialize_prepared_action,
)
from notas.application.ai_tools.runtime import run_ai_tool


def prepare_product_action_tool(
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

def commit_prepared_action_tool(user, prepared_action_id: str):
    return run_ai_tool(
        lambda: {
            "prepared_action": serialize_prepared_action(
                commit_prepared_action(
                    user=user,
                    public_id=prepared_action_id,
                )
            )
        },
        user=user,
    )
