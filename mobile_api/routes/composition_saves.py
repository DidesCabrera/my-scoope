from __future__ import annotations

from ninja import Router

from mobile_api.api_support import require_scope, success
from mobile_api.auth import mobile_bearer
from mobile_api.composition import save_dailyplan_from_program, save_meal_from_dailyplan
from mobile_api.errors import MobileAPIError
from mobile_api.schema_domains.composition import CompositionMutationEnvelope
from mobile_api.schemas import ErrorEnvelope
from notas.application.commercial.limits import CommercialLimitReached
from notas.application.services.oauth_device_sessions import MOBILE_SCOPE_WRITE

router = Router()


@router.post(
    "/library/daily-plans/{dailyplan_id}/meals/{dailyplan_meal_id}/save-to-library",
    operation_id="mobile_api_api_dailyplan_meal_save_to_library",
    auth=mobile_bearer,
    response={200: CompositionMutationEnvelope, 403: ErrorEnvelope, 404: ErrorEnvelope},
)
def dailyplan_meal_save_to_library(request, dailyplan_id: int, dailyplan_meal_id: int):
    require_scope(request.auth, MOBILE_SCOPE_WRITE)
    try:
        return success(
            save_meal_from_dailyplan(
                user=request.auth.user,
                dailyplan_id=dailyplan_id,
                dailyplan_meal_id=dailyplan_meal_id,
            )
        )
    except CommercialLimitReached as exc:
        raise MobileAPIError(str(exc), "El plan actual no permite guardar más comidas.", 403) from exc


@router.post(
    "/library/programs/{program_id}/weeks/{week_number}/days/{day_number}/save-to-library",
    operation_id="mobile_api_api_program_dailyplan_save_to_library",
    auth=mobile_bearer,
    response={200: CompositionMutationEnvelope, 403: ErrorEnvelope, 404: ErrorEnvelope},
)
def program_dailyplan_save_to_library(request, program_id: int, week_number: int, day_number: int):
    require_scope(request.auth, MOBILE_SCOPE_WRITE)
    try:
        return success(
            save_dailyplan_from_program(
                user=request.auth.user,
                program_id=program_id,
                week_number=week_number,
                day_number=day_number,
            )
        )
    except CommercialLimitReached as exc:
        raise MobileAPIError(str(exc), "El plan actual no permite guardar más planes diarios.", 403) from exc
