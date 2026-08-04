from __future__ import annotations

from typing import Any, Mapping

from django.conf import settings

from ai_assistant.application.async_jobs import AsyncJobContractError, enqueue_async_job
from ai_assistant.application.chat_engines import ChatEngineRequest
from notas.application.ai_intake.chat_engine import get_nutrition_intake_chat_engine
from notas.application.ai_intake.chat_history import (
    mark_chat_proposal_created,
    sync_chat_from_conversation,
)
from notas.application.ai_intake.dailyplan_generator import (
    DailyPlanGeneratorError,
)
from notas.application.ai_intake.generated_plan_messages import append_iterated_plan_message
from notas.application.ai_intake.nutrition_brief import serialize_conversation
from notas.application.ai_intake.plan_iteration import (
    create_iterated_dailyplan_proposal,
    should_iterate_generated_plan,
)

NUTRITION_INTAKE_TURN_JOB_KIND = "nutrition_intake_turn"
NUTRITION_INTAKE_TURN_RESULT_CONTRACT = "myscoope.nutrition_intake_async_result.v1"


def enqueue_nutrition_intake_turn(
    *,
    user: Any,
    message: str,
    existing_payload: Mapping[str, Any] | None,
    existing_chat_id: int | None,
    idempotency_key: str,
):
    normalized_message = " ".join(str(message or "").split())
    if not normalized_message:
        raise AsyncJobContractError("message is required.")
    max_chars = max(1, int(getattr(settings, "AI_ASSISTANT_MAX_MESSAGE_CHARS", 2000)))
    if len(normalized_message) > max_chars:
        raise AsyncJobContractError(
            "message exceeds the configured character limit.",
            code="message_too_long",
        )
    lane_key = (
        f"nutrition-chat:{existing_chat_id}"
        if existing_chat_id
        else f"nutrition-user:{user.pk}:new-chat"
    )
    return enqueue_async_job(
        user=user,
        kind=NUTRITION_INTAKE_TURN_JOB_KIND,
        idempotency_key=idempotency_key,
        lane_key=lane_key,
        request_payload={
            "message": normalized_message,
            "existing_payload": dict(existing_payload or {}),
            "existing_chat_id": existing_chat_id,
        },
    )


def process_nutrition_intake_turn_job(*, job) -> dict[str, Any]:
    payload = dict(job.request_payload or {})
    message = " ".join(str(payload.get("message") or "").split())
    if not message:
        raise AsyncJobContractError("Stored nutrition intake job has no message.")
    existing_chat_id = payload.get("existing_chat_id") or None
    existing_payload = payload.get("existing_payload") or None

    turn_result = get_nutrition_intake_chat_engine().continue_chat(
        ChatEngineRequest(
            message=message,
            existing_payload=existing_payload,
            user_id=job.user_id,
            metadata={
                "surface": "ai_nutrition_intake",
                "tool_user": job.user,
                "conversation_id": str(existing_chat_id or ""),
                "turn_id": str(job.public_id),
                "action_type": "assistant.ai_nutrition_intake.preview",
                "async_job_id": str(job.public_id),
            },
        )
    )
    conversation = turn_result.state
    chat = sync_chat_from_conversation(
        user=job.user,
        conversation=conversation,
        existing_chat_id=existing_chat_id,
    )

    iteration_error = ""
    if should_iterate_generated_plan(chat=chat, message=message):
        try:
            iteration_result = create_iterated_dailyplan_proposal(
                user=job.user,
                brief=conversation.result.brief,
                previous_proposal=chat.proposal,
                user_message=message,
            )
            conversation = append_iterated_plan_message(
                conversation,
                user_message=message,
                previous_proposal=chat.proposal,
                proposal=iteration_result.proposal,
            )
            chat = sync_chat_from_conversation(
                user=job.user,
                conversation=conversation,
                existing_chat_id=chat.id,
            )
            mark_chat_proposal_created(
                user=job.user,
                chat_id=chat.id,
                proposal=iteration_result.proposal,
            )
        except DailyPlanGeneratorError as exc:
            iteration_error = " ".join(str(exc).split())[:300]

    return {
        "contract": NUTRITION_INTAKE_TURN_RESULT_CONTRACT,
        "conversation": serialize_conversation(conversation),
        "chat_id": chat.id,
        "prompt": conversation.result.prompt,
        "iteration_error": iteration_error,
    }
