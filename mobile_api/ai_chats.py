from __future__ import annotations

from django.conf import settings

from accounts.services.profile import build_account_credit_display
from ai_assistant.application.async_jobs import async_jobs_enabled
from ai_assistant.models import AIAsyncJob
from notas.application.ai_intake.async_turns import NUTRITION_INTAKE_TURN_JOB_KIND
from notas.application.ai_intake.chat_engine import build_ai_nutrition_intake_engine_status
from notas.application.ai_tools.prepared_actions import serialize_prepared_action
from notas.domain.models import AiNutritionChat

PENDING_JOB_STATUSES = (
    AIAsyncJob.Status.QUEUED,
    AIAsyncJob.Status.RUNNING,
    AIAsyncJob.Status.RETRYING,
)


def _card_items(raw_items) -> list[dict]:
    if not isinstance(raw_items, list):
        return []
    return [
        {
            "key": str(item.get("key") or "")[:80],
            "label": str(item.get("label") or "")[:120],
            "value": str(item.get("value") or "")[:500],
            "is_pending": bool(item.get("is_pending")),
        }
        for item in raw_items[:30]
        if isinstance(item, dict) and item.get("label")
    ]


def _draft_card(raw: dict, card_type: str) -> dict:
    items = _card_items(raw.get("items"))
    for section in raw.get("sections") if isinstance(raw.get("sections"), list) else []:
        if isinstance(section, dict):
            items.extend(_card_items(section.get("items")))
    return {
        "type": card_type,
        "title": str(raw.get("title") or "Información de la conversación")[:180],
        "subtitle": str(raw.get("subtitle") or "")[:500],
        "items": items[:40],
        "status": str(raw.get("status") or "")[:40],
    }


def _proposal_id_from_url(value) -> int | None:
    parts = str(value or "").strip("/").split("/")
    try:
        return int(parts[-1])
    except (TypeError, ValueError):
        return None


def _message_cards(user, raw: dict) -> list[dict]:
    cards = []
    draft_keys = {
        "profile_draft_card": "profile_draft",
        "preference_draft_card": "preference_draft",
        "proposal_preferences_card": "proposal_preferences",
    }
    for key, card_type in draft_keys.items():
        value = raw.get(key)
        if isinstance(value, dict) and value:
            cards.append(_draft_card(value, card_type))

    review = raw.get("proposal_review_card")
    if isinstance(review, dict) and review.get("proposal_id"):
        cards.append({
            "type": "proposal_review",
            "proposal_id": int(review["proposal_id"]),
            "title": str(review.get("title") or "Propuesta para revisar")[:180],
            "summary": str(review.get("summary") or "")[:1000],
            "status": str(review.get("status") or "")[:80],
        })

    plan = raw.get("generated_plan_card")
    if isinstance(plan, dict) and plan:
        cards.append({
            "type": "generated_plan",
            "proposal_id": _proposal_id_from_url(plan.get("url")),
            "title": str(plan.get("title") or "Plan generado")[:180],
            "summary": str(plan.get("summary") or "")[:1000],
            "is_current": bool(plan.get("is_current")),
            "items": _card_items(plan.get("target_items")),
        })

    comparison = raw.get("saved_comparison_card") or raw.get("comparison_card")
    if isinstance(comparison, dict) and comparison.get("comparison_id"):
        cards.append({
            "type": "saved_comparison",
            "comparison_id": int(comparison["comparison_id"]),
            "kind": str(comparison.get("kind") or "foods"),
            "title": str(comparison.get("title") or "Comparación guardada")[:180],
        })

    prepared = raw.get("prepared_action_card")
    if isinstance(prepared, dict) and prepared.get("id"):
        from ai_assistant.models import AIPreparedAction
        action = AIPreparedAction.objects.filter(public_id=prepared["id"], user=user).first()
        if action is not None:
            trusted = serialize_prepared_action(action)
            cards.append({
                "type": "prepared_action",
                "action_id": trusted["id"],
                "title": trusted["title"][:180],
                "summary": trusted["summary"][:1000],
                "status": trusted["status"],
                "destructive": trusted["destructive"],
                "expires_at": trusted["expires_at"],
            })
    return cards


def assistant_availability_payload(user) -> dict:
    engine = build_ai_nutrition_intake_engine_status()
    account = build_account_credit_display(user)
    queue_available = async_jobs_enabled()
    return {
        "is_available": bool(engine.get("is_active")) and queue_available,
        "label": engine.get("label") or "Asistente AI",
        "queue_available": queue_available,
        "available_credits": account.available_credits,
        "monthly_credit_limit": account.monthly_credit_limit,
        "daily_credit_limit": account.daily_credit_limit,
        "max_message_chars": max(1, int(getattr(settings, "AI_ASSISTANT_MAX_MESSAGE_CHARS", 2000))),
    }


def _message_payloads(chat: AiNutritionChat) -> list[dict]:
    conversation = chat.conversation_payload if isinstance(chat.conversation_payload, dict) else {}
    raw_messages = conversation.get("messages") if isinstance(conversation.get("messages"), list) else []
    messages = []
    for index, raw in enumerate(raw_messages[-24:], start=1):
        if not isinstance(raw, dict):
            continue
        role = str(raw.get("role") or "").strip()
        if role not in {"user", "assistant"}:
            continue
        text = " ".join(str(raw.get("text") or "").split())[:8000]
        cards = _message_cards(chat.user, raw)
        has_structured_content = any(
            isinstance(raw.get(key), dict) and bool(raw.get(key))
            for key in (
                "generated_plan_card",
                "profile_draft_card",
                "preference_draft_card",
                "proposal_preferences_card",
                "proposal_review_card",
                "prepared_action_card",
                "saved_comparison_card",
            )
        )
        if not text and not cards:
            continue
        messages.append(
            {
                "id": f"{chat.id}:{index}",
                "role": role,
                "text": text,
                "created_at": None,
                "has_structured_content": has_structured_content,
                "cards": cards,
            }
        )
    return messages


def _pending_jobs(user):
    return AIAsyncJob.objects.filter(
        user=user,
        kind=NUTRITION_INTAKE_TURN_JOB_KIND,
        status__in=PENDING_JOB_STATUSES,
    ).order_by("-created_at", "-id")


def pending_turn_job(user, *, chat_id: int | None) -> AIAsyncJob | None:
    lane_key = f"nutrition-chat:{chat_id}" if chat_id else f"nutrition-user:{user.pk}:new-chat"
    return _pending_jobs(user).filter(lane_key=lane_key).first()


def pending_turn_payload(job: AIAsyncJob | None) -> dict | None:
    if job is None:
        return None
    return {
        "job_id": str(job.public_id),
        "status": job.status,
        "retry_after_ms": 750,
    }


def _summary_payload(chat: AiNutritionChat) -> dict:
    messages = _message_payloads(chat)
    return {
        "id": chat.id,
        "title": chat.title or "Chat nutricional",
        "status": chat.status,
        "status_label": chat.get_status_display(),
        "last_message_preview": chat.last_message_preview or "Sin mensajes guardados.",
        "message_count": len(messages),
        "proposal_id": chat.proposal_id,
        "updated_at": chat.updated_at,
    }


def chat_list_payload(user, *, offset=0, limit=30) -> dict:
    queryset = AiNutritionChat.objects.filter(user=user).select_related("proposal")
    safe_offset = max(int(offset or 0), 0)
    safe_limit = min(max(int(limit or 30), 1), 50)
    total = queryset.count()
    pending_new = next(
        (
            job
            for job in _pending_jobs(user)[:50]
            if not (job.request_payload or {}).get("existing_chat_id")
        ),
        None,
    )
    return {
        "items": [_summary_payload(chat) for chat in queryset[safe_offset:safe_offset + safe_limit]],
        "total": total,
        "offset": safe_offset,
        "limit": safe_limit,
        "availability": assistant_availability_payload(user),
        "pending_new_turn": pending_turn_payload(pending_new),
    }


def chat_detail_payload(user, chat_id: int) -> dict | None:
    chat = AiNutritionChat.objects.filter(pk=chat_id, user=user).select_related("proposal").first()
    if chat is None:
        return None
    pending = next(
        (
            job
            for job in _pending_jobs(user)[:50]
            if (job.request_payload or {}).get("existing_chat_id") == chat.id
        ),
        None,
    )
    return {
        **_summary_payload(chat),
        "messages": _message_payloads(chat),
        "availability": assistant_availability_payload(user),
        "pending_turn": pending_turn_payload(pending),
    }


def completed_turn_payload(job: AIAsyncJob) -> dict:
    result = job.result_payload if isinstance(job.result_payload, dict) else {}
    try:
        chat_id = int(result.get("chat_id"))
    except (TypeError, ValueError) as exc:
        raise ValueError("assistant_turn_result_invalid") from exc
    if not AiNutritionChat.objects.filter(pk=chat_id, user=job.user).exists():
        raise ValueError("assistant_turn_result_invalid")
    return {
        "chat_id": chat_id,
        "conversation_updated": True,
        "has_iteration_warning": bool(result.get("iteration_error")),
    }
