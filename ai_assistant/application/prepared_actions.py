"""Stable prepared-action facade backed by registered product ports."""

from ai_assistant.application.prepared_action_contracts import (
    PREPARED_ACTION_SPECS,
    PREPARED_ACTION_TTL,
    PreparedActionSpec,
)
from ai_assistant.application.product_ports import get_ai_product_bindings


def prepare_product_action(**kwargs):
    return get_ai_product_bindings().prepare_product_action(**kwargs)


def commit_prepared_action(**kwargs):
    return get_ai_product_bindings().commit_prepared_action(**kwargs)


def cancel_prepared_action(**kwargs):
    return get_ai_product_bindings().cancel_prepared_action(**kwargs)


def serialize_prepared_action(action):
    return get_ai_product_bindings().serialize_prepared_action(action)


__all__ = [
    "PREPARED_ACTION_SPECS",
    "PREPARED_ACTION_TTL",
    "PreparedActionSpec",
    "cancel_prepared_action",
    "commit_prepared_action",
    "prepare_product_action",
    "serialize_prepared_action",
]
