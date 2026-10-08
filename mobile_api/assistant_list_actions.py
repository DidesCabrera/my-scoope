from django.db import transaction

from ai_assistant.models import AIAsyncJob
from mobile_api.errors import MobileAPIError
from notas.application.ai_intake.async_turns import NUTRITION_INTAKE_TURN_JOB_KIND
from notas.application.queries.proposal_queries import get_available_proposal_queryset
from notas.domain.models import AiNutritionChat, NutritionProposal


PENDING_JOB_STATUSES = (
    AIAsyncJob.Status.QUEUED,
    AIAsyncJob.Status.RUNNING,
    AIAsyncJob.Status.RETRYING,
)


@transaction.atomic
def bulk_delete_chats(user, item_ids: list[int]) -> dict:
    requested_ids = list(dict.fromkeys(item_ids))
    chats = {
        chat.id: chat
        for chat in AiNutritionChat.objects.select_for_update().filter(user=user, id__in=requested_ids)
    }
    if set(chats) != set(requested_ids):
        raise MobileAPIError(
            code="assistant_chat_delete_not_allowed",
            message="One or more chats cannot be deleted.",
            status_code=403,
        )
    pending_lane_keys = set(
        AIAsyncJob.objects.filter(
            user=user,
            kind=NUTRITION_INTAKE_TURN_JOB_KIND,
            status__in=PENDING_JOB_STATUSES,
            lane_key__in=[f"nutrition-chat:{chat_id}" for chat_id in requested_ids],
        ).values_list("lane_key", flat=True)
    )
    deleted_ids, skipped_ids = [], []
    for chat_id in requested_ids:
        if f"nutrition-chat:{chat_id}" in pending_lane_keys:
            skipped_ids.append(chat_id)
            continue
        chats[chat_id].delete()
        deleted_ids.append(chat_id)
    message = f"{len(deleted_ids)} chat(s) eliminado(s)."
    if skipped_ids:
        message += f" {len(skipped_ids)} no se pudieron eliminar porque están procesando una respuesta."
    return {"affected_ids": deleted_ids, "skipped_ids": skipped_ids, "message": message}


@transaction.atomic
def bulk_delete_proposals(user, item_ids: list[int]) -> dict:
    requested_ids = list(dict.fromkeys(item_ids))
    available_ids = set(
        get_available_proposal_queryset(user)
        .filter(id__in=requested_ids)
        .values_list("id", flat=True)
    )
    if available_ids != set(requested_ids):
        raise MobileAPIError(
            code="proposal_delete_not_allowed",
            message="One or more proposals cannot be deleted.",
            status_code=403,
        )
    proposals = {
        proposal.id: proposal
        for proposal in NutritionProposal.objects.select_for_update().filter(id__in=available_ids)
    }
    if set(proposals) != set(requested_ids):
        raise MobileAPIError(
            code="proposal_delete_not_allowed",
            message="One or more proposals cannot be deleted.",
            status_code=403,
        )
    for proposal_id in requested_ids:
        proposals[proposal_id].delete()
    return {
        "affected_ids": requested_ids,
        "skipped_ids": [],
        "message": f"{len(requested_ids)} propuesta(s) eliminada(s).",
    }
