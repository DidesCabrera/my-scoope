from __future__ import annotations

import hashlib
from datetime import timedelta
from typing import Any

from django.db.models import Count
from django.utils import timezone

from notas.application.ai_intake.nutrition_brief import deserialize_conversation
from notas.domain.models import AiAssistantMessageFeedback, AiNutritionChat

AI_ASSISTANT_FEEDBACK_VERSION = "ai_assistant.message_feedback.v1"


def record_message_feedback(
    *,
    user: Any,
    chat: AiNutritionChat,
    message_index: int,
    rating: str,
    reason: str = "",
    comment: str = "",
) -> AiAssistantMessageFeedback:
    """Upsert feedback for one owned, visible assistant text response."""

    if chat.user_id != getattr(user, "id", None):
        raise ValueError("feedback_chat_not_owned")
    conversation = deserialize_conversation(chat.conversation_payload)
    if conversation is None:
        raise ValueError("feedback_conversation_unavailable")
    try:
        index = int(message_index)
        message = conversation.messages[index]
    except (IndexError, TypeError, ValueError):
        raise ValueError("feedback_message_not_found") from None
    text = " ".join(str(getattr(message, "text", "") or "").split())
    if getattr(message, "role", "") != "assistant" or not text:
        raise ValueError("feedback_message_not_rateable")

    valid_ratings = {choice[0] for choice in AiAssistantMessageFeedback.RATING_CHOICES}
    valid_reasons = {choice[0] for choice in AiAssistantMessageFeedback.REASON_CHOICES}
    normalized_rating = str(rating or "").strip()
    normalized_reason = str(reason or "").strip()
    if normalized_rating not in valid_ratings:
        raise ValueError("feedback_rating_invalid")
    if normalized_reason and normalized_reason not in valid_reasons:
        raise ValueError("feedback_reason_invalid")
    if normalized_rating == AiAssistantMessageFeedback.RATING_HELPFUL:
        normalized_reason = ""

    feedback, _ = AiAssistantMessageFeedback.objects.update_or_create(
        user=user,
        chat=chat,
        message_index=index,
        defaults={
            "rating": normalized_rating,
            "reason": normalized_reason,
            "comment": " ".join(str(comment or "").split())[:500],
            "response_fingerprint": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        },
    )
    return feedback


def summarize_message_feedback(*, days: int = 30, user: Any | None = None) -> dict[str, Any]:
    """Return aggregate-only product feedback suitable for quality review."""

    bounded_days = max(1, min(int(days), 365))
    since = timezone.now() - timedelta(days=bounded_days)
    queryset = AiAssistantMessageFeedback.objects.filter(created_at__gte=since)
    if user is not None:
        queryset = queryset.filter(user=user)
    rating_counts = {
        row["rating"]: row["count"]
        for row in queryset.values("rating").annotate(count=Count("id"))
    }
    reason_counts = {
        row["reason"]: row["count"]
        for row in queryset.exclude(reason="").values("reason").annotate(count=Count("id"))
    }
    total = sum(rating_counts.values())
    helpful = rating_counts.get(AiAssistantMessageFeedback.RATING_HELPFUL, 0)
    return {
        "version": AI_ASSISTANT_FEEDBACK_VERSION,
        "window_days": bounded_days,
        "total": total,
        "helpful": helpful,
        "not_helpful": rating_counts.get(
            AiAssistantMessageFeedback.RATING_NOT_HELPFUL,
            0,
        ),
        "helpful_rate": round(helpful / total, 4) if total else None,
        "reason_counts": reason_counts,
        "contains_message_content": False,
        "contains_comments": False,
        "scope": "selected_user" if user is not None else "all_users",
    }
