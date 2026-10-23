from django.shortcuts import get_object_or_404
from ninja import Router

from mobile_api.api_support import calendarization_error, require_scope, success
from mobile_api.auth import mobile_bearer
from mobile_api.schema_domains.calendarization import WeightCreateInput, WeightDeleteEnvelope, WeightEnvelope, WeightListEnvelope
from mobile_api.schemas import ErrorEnvelope
from notas.application.services.commands.calendarization_execution_commands import record_calendarized_weight, update_calendarized_weight
from notas.application.services.oauth_device_sessions import MOBILE_SCOPE_WRITE
from notas.domain.models import WeightLog

router = Router()


def _weight_payload(item, context=None):
    return {
        "id": item.id,
        "measured_on": item.date,
        "measured_time": item.time,
        "weight_kg": item.weight_kg,
        "comment": item.comment,
        "source": item.source,
        "created_at": item.created_at,
        "calendarization_id": context.calendarization_id if context else None,
    }


@router.get(
    "/weights",
    operation_id="mobile_api_api_weights",
    auth=mobile_bearer,
    response={200: WeightListEnvelope, 401: ErrorEnvelope, 403: ErrorEnvelope},
)
def weights(request, limit: int = 30):
    safe_limit = min(max(limit, 1), 100)
    queryset = WeightLog.objects.filter(user=request.auth.user).order_by("-date", "-created_at")[:safe_limit]
    items = [_weight_payload(item) for item in queryset]
    return success({"items": items, "count": len(items)})


@router.post(
    "/weights",
    operation_id="mobile_api_api_create_weight",
    auth=mobile_bearer,
    response={200: WeightEnvelope, 403: ErrorEnvelope, 422: ErrorEnvelope},
)
def create_weight(request, payload: WeightCreateInput):
    require_scope(request.auth, MOBILE_SCOPE_WRITE)
    item, context = record_calendarized_weight(
        user=request.auth.user,
        weight_kg=payload.weight_kg,
        measured_on=payload.measured_on,
        measured_time=payload.measured_time,
        comment=payload.comment or "",
    )
    return success(_weight_payload(item, context))


@router.patch(
    "/weights/{weight_id}",
    operation_id="mobile_api_api_update_weight",
    auth=mobile_bearer,
    response={200: WeightEnvelope, 403: ErrorEnvelope, 404: ErrorEnvelope, 422: ErrorEnvelope},
)
def update_weight(request, weight_id: int, payload: WeightCreateInput):
    require_scope(request.auth, MOBILE_SCOPE_WRITE)
    item = get_object_or_404(WeightLog, id=weight_id, user=request.auth.user)
    try:
        item, context = update_calendarized_weight(
            weight_log=item,
            weight_kg=payload.weight_kg,
            measured_on=payload.measured_on or item.date,
            measured_time=payload.measured_time,
            comment=payload.comment,
        )
    except ValueError as exc:
        raise calendarization_error(exc) from exc
    return success(_weight_payload(item, context))


@router.delete(
    "/weights/{weight_id}",
    operation_id="mobile_api_api_delete_weight",
    auth=mobile_bearer,
    response={200: WeightDeleteEnvelope, 403: ErrorEnvelope, 404: ErrorEnvelope},
)
def delete_weight(request, weight_id: int):
    require_scope(request.auth, MOBILE_SCOPE_WRITE)
    item = get_object_or_404(WeightLog, id=weight_id, user=request.auth.user)
    deleted_id = item.id
    item.delete()
    return success({"deleted_id": deleted_id})
