from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

ProductToolCallable = Callable[..., Any]


@dataclass(frozen=True)
class AIProductBindings:
    """Product-owned implementations consumed through the AI application boundary."""

    read_only_tools: Mapping[str, ProductToolCallable]
    profile_draft_tools: Mapping[str, ProductToolCallable]
    profile_commit_tools: Mapping[str, ProductToolCallable]
    proposal_tools: Mapping[str, ProductToolCallable]
    validation_tools: Mapping[str, ProductToolCallable]
    required_proposal_fields: Callable[[Any], Sequence[str]]
    build_nutrition_brief_from_ai_drafts: ProductToolCallable
    prepare_product_action: ProductToolCallable
    commit_prepared_action: ProductToolCallable
    cancel_prepared_action: ProductToolCallable
    serialize_prepared_action: ProductToolCallable


_bindings: AIProductBindings | None = None


def register_ai_product_bindings(bindings: AIProductBindings) -> None:
    """Register the product adapter once Django's product apps are ready."""

    global _bindings
    _bindings = bindings


def get_ai_product_bindings() -> AIProductBindings:
    if _bindings is None:
        raise RuntimeError("ai_product_bindings_not_registered")
    return _bindings

