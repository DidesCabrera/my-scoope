from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any


def serialize_conversation_state(
    state: Any,
    *,
    card_fields: Sequence[str],
    card_list_fields: Sequence[str],
    serialize_brief: Callable[[Any], dict],
) -> dict:
    serialized_messages = []
    for message in state.messages:
        cards = {
            name: value
            for name in (*card_fields, *card_list_fields)
            if (value := getattr(message, name))
        }
        if not message.text and not cards:
            continue
        timestamp = {"created_at": message.created_at} if message.created_at else {}
        serialized_messages.append({"role": message.role, "text": message.text, **timestamp, **cards})
    return {"brief": serialize_brief(state.result.brief), "messages": serialized_messages}


def deserialize_conversation_state(
    payload: dict | None,
    *,
    build_result: Callable[[Any], Any],
    card_fields: Sequence[str],
    card_list_fields: Sequence[str],
    deserialize_brief: Callable[[Any], Any],
    max_card_items: int,
    max_messages: int,
    message_factory: Callable[..., Any],
    state_factory: Callable[..., Any],
) -> Any | None:
    if not payload or not (brief := deserialize_brief(payload.get("brief"))):
        return None
    messages = []
    for item in payload.get("messages") or []:
        role = str(item.get("role") or "").strip()
        text = str(item.get("text") or "").strip()
        cards = {name: value for name in card_fields if isinstance((value := item.get(name)), dict)}
        cards.update({
            name: [card for card in value[:max_card_items] if isinstance(card, dict)]
            for name in card_list_fields
            if isinstance((value := item.get(name)), list) and value
        })
        if role in {"user", "assistant"} and (text or cards):
            created_at = str(item.get("created_at") or "").strip()[:64] or None
            messages.append(message_factory(role=role, text=text, created_at=created_at, **cards))
    return state_factory(
        messages=messages[-max_messages:],
        result=build_result(brief),
    )
