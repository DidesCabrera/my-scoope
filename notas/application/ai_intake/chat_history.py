from __future__ import annotations

from typing import Iterable

from django.utils import timezone

from notas.application.ai_intake.nutrition_brief import (
    NutritionConversationState,
    serialize_brief,
    serialize_conversation,
)
from notas.domain.models import AiNutritionChat, NutritionProposal

AI_NUTRITION_CHAT_SESSION_KEY = "ai_nutrition_chat_id"


def sync_chat_from_conversation(
    *,
    user,
    conversation: NutritionConversationState,
    existing_chat_id: int | None = None,
) -> AiNutritionChat:
    """Persist the current guided intake conversation as chat history.

    The conversational state still lives in the session for the active chat UX,
    but this record makes the flow discoverable later from Tools > Chats.
    """
    chat = _get_editable_chat(user=user, chat_id=existing_chat_id)
    payload = serialize_conversation(conversation)
    brief_payload = serialize_brief(conversation.result.brief)

    if chat is None:
        chat = AiNutritionChat(user=user, title=_build_chat_title(conversation))

    chat.title = chat.title or _build_chat_title(conversation)
    chat.brief_payload = brief_payload
    chat.conversation_payload = payload
    chat.last_message_preview = _build_last_message_preview(conversation.messages)
    chat.status = AiNutritionChat.STATUS_ACTIVE
    chat.save()
    return chat


def mark_chat_proposal_created(
    *,
    user,
    chat_id: int | None,
    proposal: NutritionProposal,
) -> None:
    chat = _get_editable_chat(user=user, chat_id=chat_id)
    if chat is None:
        return

    chat.status = AiNutritionChat.STATUS_PROPOSAL_CREATED
    chat.proposal = proposal
    chat.last_message_preview = "Propuesta creada desde el brief nutricional."
    chat.save(update_fields=["status", "proposal", "last_message_preview", "updated_at"])


def _get_editable_chat(*, user, chat_id: int | None) -> AiNutritionChat | None:
    if not chat_id:
        return None

    try:
        return AiNutritionChat.objects.get(id=chat_id, user=user)
    except (AiNutritionChat.DoesNotExist, ValueError, TypeError):
        return None


def _build_chat_title(conversation: NutritionConversationState) -> str:
    first_user_message = next(
        (message.text for message in conversation.messages if message.role == "user" and message.text),
        "",
    )
    if first_user_message:
        return _truncate(first_user_message, 84)

    goal_label = conversation.result.brief.goal_label
    if goal_label and goal_label != "Pendiente":
        return f"Brief nutricional para {goal_label.lower()}"

    return f"Chat nutricional {timezone.localtime().strftime('%d/%m/%Y')}"


def _build_last_message_preview(messages: Iterable) -> str:
    for message in reversed(list(messages)):
        if message.text:
            return _truncate(message.text, 160)
    return "Conversación sin mensajes."


def _truncate(value: str, max_length: int) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= max_length:
        return text
    return text[: max_length - 1].rstrip() + "…"
