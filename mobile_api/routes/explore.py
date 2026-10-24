from ninja import Router

from mobile_api.api_support import require_scope, success
from mobile_api.auth import mobile_bearer
from mobile_api.errors import MobileAPIError
from mobile_api.explore import explore_meal_detail_payload, explore_meals_payload
from mobile_api.schema_domains.explore import (
    ExploreMealItemEnvelope,
    ExploreMealPageEnvelope,
    ExploreMealSaveResultEnvelope,
)
from mobile_api.schemas import ErrorEnvelope
from notas.application.commercial.limits import CommercialLimitReached
from notas.application.services.commands.meal_catalog_commands import save_catalog_meal_to_library
from notas.application.services.oauth_device_sessions import MOBILE_SCOPE_WRITE
from notas.domain.models import Meal, MealCatalogEntry

router = Router()


@router.get(
    "/explore/meals",
    operation_id="mobile_api_api_explore_meals",
    auth=mobile_bearer,
    response={200: ExploreMealPageEnvelope, 401: ErrorEnvelope, 403: ErrorEnvelope},
)
def explore_meals(
    request,
    search: str | None = None,
    occasion: str | None = None,
    dietary_style: str | None = None,
    offset: int = 0,
    limit: int = 30,
):
    return success(
        explore_meals_payload(
            request.auth.user,
            search=search,
            occasion=occasion,
            dietary_style=dietary_style,
            offset=offset,
            limit=limit,
        )
    )


@router.get(
    "/explore/meals/{catalog_id}",
    operation_id="mobile_api_api_explore_meal_detail",
    auth=mobile_bearer,
    response={200: ExploreMealItemEnvelope, 401: ErrorEnvelope, 403: ErrorEnvelope, 404: ErrorEnvelope},
)
def explore_meal_detail(request, catalog_id: int):
    payload = explore_meal_detail_payload(request.auth.user, catalog_id)
    if payload is None:
        raise MobileAPIError("explore_meal_not_found", "Esta comida no está disponible en Explorar.", 404)
    return success(payload)


@router.post(
    "/explore/meals/{catalog_id}/save",
    operation_id="mobile_api_api_save_explore_meal",
    auth=mobile_bearer,
    response={200: ExploreMealSaveResultEnvelope, 401: ErrorEnvelope, 403: ErrorEnvelope, 404: ErrorEnvelope},
)
def save_explore_meal(request, catalog_id: int):
    require_scope(request.auth, MOBILE_SCOPE_WRITE)
    entry = (
        MealCatalogEntry.objects.select_related("meal")
        .filter(
            pk=catalog_id,
            is_published=True,
            meal__is_draft=False,
            meal__scope=Meal.Scope.LIBRARY,
        )
        .first()
    )
    if entry is None:
        raise MobileAPIError("explore_meal_not_found", "Esta comida no está disponible en Explorar.", 404)
    try:
        result = save_catalog_meal_to_library(entry=entry, user=request.auth.user)
    except CommercialLimitReached as exc:
        raise MobileAPIError(str(exc), "Tu plan actual no permite guardar más comidas.", 403) from exc
    return success(
        {
            "saved_meal_id": result.meal.id,
            "already_saved": result.already_saved,
            "message": "La comida ya estaba en tu biblioteca." if result.already_saved else "Comida guardada en tu biblioteca.",
        }
    )
