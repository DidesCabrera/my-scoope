from __future__ import annotations

from ninja import Router

from mobile_api.api_support import require_scope, success
from mobile_api.auth import mobile_bearer
from mobile_api.composition import remove_dailyplan_from_program, reorder_days_in_program_week
from mobile_api.schema_domains.composition import CompositionMutationEnvelope, CompositionOrderInput
from mobile_api.schemas import ErrorEnvelope
from notas.application.services.oauth_device_sessions import MOBILE_SCOPE_WRITE

router = Router()


@router.put(
    "/library/programs/{program_id}/weeks/{week_number}/days/order",
    operation_id="mobile_api_api_program_day_order",
    auth=mobile_bearer,
    response={200: CompositionMutationEnvelope, 403: ErrorEnvelope, 404: ErrorEnvelope, 422: ErrorEnvelope},
)
def program_day_order(request, program_id: int, week_number: int, payload: CompositionOrderInput):
    require_scope(request.auth, MOBILE_SCOPE_WRITE)
    return success(
        reorder_days_in_program_week(
            user=request.auth.user,
            program_id=program_id,
            week_number=week_number,
            ordered_days=payload.ordered_ids,
        )
    )


@router.delete(
    "/library/programs/{program_id}/weeks/{week_number}/days/{day_number}",
    operation_id="mobile_api_api_program_day_delete",
    auth=mobile_bearer,
    response={200: CompositionMutationEnvelope, 403: ErrorEnvelope, 404: ErrorEnvelope},
)
def program_day_delete(request, program_id: int, week_number: int, day_number: int):
    require_scope(request.auth, MOBILE_SCOPE_WRITE)
    return success(
        remove_dailyplan_from_program(
            user=request.auth.user,
            program_id=program_id,
            week_number=week_number,
            day_number=day_number,
        )
    )
