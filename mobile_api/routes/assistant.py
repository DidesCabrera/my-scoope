from __future__ import annotations

from ninja import Router

from ai_assistant.application.async_jobs import AsyncJobContractError, async_jobs_enabled
from ai_assistant.models import AIAsyncJob
from core.rate_limits import is_ai_assistant_turn_rate_limited
from mobile_api.ai_chats import chat_detail_payload, chat_list_payload, completed_turn_payload, pending_turn_job
from mobile_api.api_support import require_scope, success
from mobile_api.auth import mobile_bearer
from mobile_api.errors import MobileAPIError
from mobile_api.schema_domains.assistant import (
    AIChatDetailEnvelope,
    AIChatListEnvelope,
    AIJobAcceptedEnvelope,
    AIJobResultEnvelope,
    AIPreparedActionResultEnvelope,
    AITurnInput,
)
from mobile_api.schemas import ErrorEnvelope
from notas.application.ai_intake.async_turns import enqueue_nutrition_intake_turn
from notas.application.ai_tools.prepared_actions import cancel_prepared_action, commit_prepared_action
from notas.application.services.oauth_device_sessions import MOBILE_SCOPE_WRITE
from notas.domain.models import AiNutritionChat, SavedComparison

router = Router()


@router.post(
    "/ai/turns",
    operation_id="mobile_api_api_submit_ai_turn",
    auth=mobile_bearer,
    response={
        202: AIJobAcceptedEnvelope,
        403: ErrorEnvelope,
        409: ErrorEnvelope,
        422: ErrorEnvelope,
        429: ErrorEnvelope,
        503: ErrorEnvelope,
    },
)
def submit_ai_turn(request, payload: AITurnInput):
    require_scope(request.auth, MOBILE_SCOPE_WRITE)
    if is_ai_assistant_turn_rate_limited(request):
        raise MobileAPIError(
            code="ai_turn_rate_limited",
            message="Too many assistant turns were submitted. Try again later.",
            status_code=429,
        )
    if not async_jobs_enabled():
        raise MobileAPIError(
            code="ai_async_unavailable",
            message="The durable AI queue is not available.",
            status_code=503,
        )
    chat = None
    if payload.chat_id is not None:
        chat = AiNutritionChat.objects.filter(id=payload.chat_id, user=request.auth.user).first()
        if chat is None:
            raise MobileAPIError(
                code="ai_chat_not_found",
                message="AI chat was not found.",
                status_code=422,
            )
    product_context = {}
    if payload.comparison_id is not None:
        comparison = SavedComparison.objects.filter(pk=payload.comparison_id, owner=request.auth.user).first()
        if comparison is None:
            raise MobileAPIError(
                code="saved_comparison_not_found",
                message="The saved comparison was not found.",
                status_code=422,
            )
        snapshot = comparison.snapshot_payload if isinstance(comparison.snapshot_payload, list) else []
        product_context = {
            "saved_comparison_card": {
                "type": "saved_comparison_card",
                "comparison_id": comparison.id,
                "title": comparison.name,
                "kind": comparison.kind,
                "item_count": len(snapshot),
            },
            "saved_comparison": {
                "id": comparison.id,
                "title": comparison.name,
                "kind": comparison.kind,
                "items": [str(row.get("name") or "")[:120] for row in snapshot[:8] if isinstance(row, dict)],
            },
        }
    pending_job = pending_turn_job(request.auth.user, chat_id=chat.id if chat else None)
    if pending_job is not None and pending_job.idempotency_key != payload.idempotency_key:
        raise MobileAPIError(
            code="assistant_turn_pending",
            message="A turn is already being processed for this conversation.",
            status_code=409,
            details={"job_id": str(pending_job.public_id)},
        )
    try:
        job, _created = enqueue_nutrition_intake_turn(
            user=request.auth.user,
            message=payload.message,
            existing_payload=chat.conversation_payload if chat else None,
            existing_chat_id=chat.id if chat else None,
            idempotency_key=payload.idempotency_key,
            product_context=product_context,
        )
    except AsyncJobContractError as exc:
        status_code = 409 if exc.code == "idempotency_conflict" else 422
        raise MobileAPIError(
            code=exc.code,
            message=str(exc),
            status_code=status_code,
        ) from exc
    return 202, success(
        {
            "job_id": str(job.public_id),
            "status": job.status,
            "retry_after_ms": 750,
        }
    )


@router.get(
    "/ai/chats",
    operation_id="mobile_api_api_ai_chats",
    auth=mobile_bearer,
    response={200: AIChatListEnvelope, 401: ErrorEnvelope, 403: ErrorEnvelope},
)
def ai_chats(request, offset: int = 0, limit: int = 30):
    return success(chat_list_payload(request.auth.user, offset=offset, limit=limit))


@router.get(
    "/ai/chats/{chat_id}",
    operation_id="mobile_api_api_ai_chat_detail",
    auth=mobile_bearer,
    response={200: AIChatDetailEnvelope, 401: ErrorEnvelope, 403: ErrorEnvelope, 404: ErrorEnvelope},
)
def ai_chat_detail(request, chat_id: int):
    payload = chat_detail_payload(request.auth.user, chat_id)
    if payload is None:
        raise MobileAPIError(code="ai_chat_not_found", message="AI chat was not found.", status_code=404)
    return success(payload)


def _prepared_action_error(exc: ValueError) -> MobileAPIError:
    code = str(exc)
    status = 404 if code == "prepared_action_not_found" else 409
    return MobileAPIError(code=code, message="The prepared action is no longer available.", status_code=status)


@router.post(
    "/ai/prepared-actions/{action_id}/commit",
    operation_id="mobile_api_api_commit_ai_prepared_action",
    auth=mobile_bearer,
    response={200: AIPreparedActionResultEnvelope, 403: ErrorEnvelope, 404: ErrorEnvelope, 409: ErrorEnvelope},
)
def commit_ai_prepared_action(request, action_id: str):
    require_scope(request.auth, MOBILE_SCOPE_WRITE)
    try:
        action = commit_prepared_action(user=request.auth.user, public_id=action_id)
    except ValueError as exc:
        raise _prepared_action_error(exc) from exc
    return success({"action_id": str(action.public_id), "status": action.status, "refresh_chat": True})


@router.post(
    "/ai/prepared-actions/{action_id}/cancel",
    operation_id="mobile_api_api_cancel_ai_prepared_action",
    auth=mobile_bearer,
    response={200: AIPreparedActionResultEnvelope, 403: ErrorEnvelope, 404: ErrorEnvelope, 409: ErrorEnvelope},
)
def cancel_ai_prepared_action(request, action_id: str):
    require_scope(request.auth, MOBILE_SCOPE_WRITE)
    try:
        action = cancel_prepared_action(user=request.auth.user, public_id=action_id)
    except ValueError as exc:
        raise _prepared_action_error(exc) from exc
    return success({"action_id": str(action.public_id), "status": action.status, "refresh_chat": True})


@router.get(
    "/ai/jobs/{job_id}",
    operation_id="mobile_api_api_ai_job",
    auth=mobile_bearer,
    response={
        200: AIJobResultEnvelope,
        202: AIJobResultEnvelope,
        401: ErrorEnvelope,
        403: ErrorEnvelope,
        404: ErrorEnvelope,
        422: ErrorEnvelope,
    },
)
def ai_job(request, job_id: str):
    try:
        job = AIAsyncJob.objects.get(public_id=job_id, user=request.auth.user)
    except (AIAsyncJob.DoesNotExist, ValueError):
        raise MobileAPIError(
            code="ai_job_not_found",
            message="AI job was not found.",
            status_code=404,
        ) from None
    if job.status in {AIAsyncJob.Status.FAILED, AIAsyncJob.Status.CANCELLED}:
        raise MobileAPIError(
            code="assistant_turn_failed",
            message="The assistant turn could not be completed.",
            status_code=422,
            details={"status": job.status, "retryable": False},
        )
    if job.status == AIAsyncJob.Status.SUCCEEDED:
        try:
            result = completed_turn_payload(job)
        except ValueError as exc:
            raise MobileAPIError(
                code="assistant_turn_result_invalid",
                message="The assistant turn completed without a valid conversation.",
                status_code=422,
            ) from exc
        return success(
            {
                "job_id": str(job.public_id),
                "status": job.status,
                "retry_after_ms": None,
                "result": result,
            }
        )
    return 202, success(
        {
            "job_id": str(job.public_id),
            "status": job.status,
            "retry_after_ms": 750,
            "result": None,
        }
    )
