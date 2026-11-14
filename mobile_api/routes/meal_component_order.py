"""Order food and preparation rows together within a meal."""

from __future__ import annotations

from ninja import Router

from mobile_api.api_support import require_scope, success
from mobile_api.auth import mobile_bearer
from mobile_api.composition import reorder_components_in_meal
from mobile_api.schema_domains.composition import CompositionMutationEnvelope, MealComponentOrderInput
from mobile_api.schemas import ErrorEnvelope
from notas.application.services.oauth_device_sessions import MOBILE_SCOPE_WRITE

router = Router()


@router.put(
    "/library/meals/{meal_id}/components/order",
    operation_id="mobile_api_api_meal_component_order",
    auth=mobile_bearer,
    response={200: CompositionMutationEnvelope, 403: ErrorEnvelope, 404: ErrorEnvelope, 422: ErrorEnvelope},
)
def meal_component_order(request, meal_id: int, payload: MealComponentOrderInput):
    require_scope(request.auth, MOBILE_SCOPE_WRITE)
    return success(reorder_components_in_meal(user=request.auth.user, meal_id=meal_id, ordered_keys=payload.ordered_keys))
