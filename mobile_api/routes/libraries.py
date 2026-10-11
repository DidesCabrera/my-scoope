from __future__ import annotations

from ninja import Router

from mobile_api.api_support import require_scope, success
from mobile_api.auth import mobile_bearer
from mobile_api.errors import MobileAPIError
from mobile_api.library_actions import bulk_delete_library, perform_library_action, reorder_library
from mobile_api.schema_domains.libraries import (
    CalendarizationProgramOptionsEnvelope,
    CompositionOptionsEnvelope,
    FoodCreateInput,
    FoodItemEnvelope,
    FoodPageEnvelope,
    LibraryActionInput,
    LibraryActionResultEnvelope,
    LibraryBulkDeleteInput,
    LibraryItemEnvelope,
    LibraryListActionResultEnvelope,
    LibraryOrderInput,
    LibraryPageEnvelope,
    NamedLibraryCreateInput,
    ProgramWeekPickerDetailEnvelope,
)
from mobile_api.schemas import ErrorEnvelope
from mobile_api.selectors import (
    calendarization_program_options_payload,
    composition_options_payload,
    library_dailyplans_payload,
    library_foods_payload,
    library_item_detail_payload,
    library_meals_payload,
    library_programs_payload,
    program_week_picker_detail_payload,
)
from notas.application.commercial.limits import CommercialLimitReached
from notas.application.queries.food_picker_queries import (
    build_food_picker_item_dto,
    get_food_picker_queryset,
    list_food_picker_page,
)
from notas.application.services.commands.dailyplan_commands import create_draft_dailyplan
from notas.application.services.commands.food_commands import create_food, update_food
from notas.application.services.commands.meal_commands import create_draft_meal
from notas.application.services.commands.program_commands import create_weekly_program
from notas.application.services.oauth_device_sessions import MOBILE_SCOPE_WRITE
from notas.domain.models import Food

router = Router()


@router.get(
    "/foods",
    operation_id="mobile_api_api_foods",
    auth=mobile_bearer,
    response={200: FoodPageEnvelope, 401: ErrorEnvelope, 403: ErrorEnvelope},
)
def foods(request, search: str | None = None, offset: int = 0, limit: int = 30):
    page = list_food_picker_page(
        user=request.auth.user,
        search=search,
        offset=max(offset, 0),
        limit=min(max(limit, 1), 100),
    )
    return success(
        {
            "items": [_food_picker_item_payload(item) for item in page.foods],
            "total": page.total,
            "offset": page.offset,
            "limit": page.limit,
            "search": page.search,
        }
    )


def _food_picker_item_payload(item):
    return {
        "id": item.id,
        "name": item.name,
        "display_name": item.display_name,
        "protein": item.protein,
        "carbs": item.carbs,
        "fat": item.fat,
        "total_kcal": item.total_kcal,
        "protein_allocation": item.alloc.get("protein", 0),
        "carbs_allocation": item.alloc.get("carbs", 0),
        "fat_allocation": item.alloc.get("fat", 0),
        "source": item.source,
        "is_user_food": item.is_user_food,
        "is_verified": item.is_verified,
        "data_quality_score": item.data_quality_score,
        "quantity_unit": item.quantity_unit,
    }


@router.get(
    "/food-picker-options/{food_id}",
    operation_id="mobile_api_api_food_detail",
    auth=mobile_bearer,
    response={200: FoodItemEnvelope, 401: ErrorEnvelope, 403: ErrorEnvelope, 404: ErrorEnvelope},
)
def food_detail(request, food_id: int):
    food = get_food_picker_queryset(request.auth.user).filter(pk=food_id).first()
    if food is None:
        raise MobileAPIError("picker_selection_not_found", "El alimento seleccionado no está disponible.", 404)
    return success(_food_picker_item_payload(build_food_picker_item_dto(food=food, user=request.auth.user)))


@router.get(
    "/library/programs",
    operation_id="mobile_api_api_library_programs",
    auth=mobile_bearer,
    response={200: LibraryPageEnvelope, 401: ErrorEnvelope, 403: ErrorEnvelope},
)
def library_programs(request, search: str | None = None, offset: int = 0, limit: int = 30):
    return success(library_programs_payload(request.auth.user, search=search, offset=offset, limit=limit))


@router.get(
    "/library/programs/calendarization-options",
    operation_id="mobile_api_api_calendarization_program_options",
    auth=mobile_bearer,
    response={200: CalendarizationProgramOptionsEnvelope, 401: ErrorEnvelope, 403: ErrorEnvelope},
)
def calendarization_program_options(request, search: str | None = None, offset: int = 0, limit: int = 30):
    return success(
        calendarization_program_options_payload(request.auth.user, search=search, offset=offset, limit=limit)
    )


@router.get(
    "/library/{entity}/composition-options",
    operation_id="mobile_api_api_composition_options",
    auth=mobile_bearer,
    response={200: CompositionOptionsEnvelope, 401: ErrorEnvelope, 403: ErrorEnvelope, 422: ErrorEnvelope},
)
def composition_options(request, entity: str, search: str | None = None, offset: int = 0, limit: int = 30):
    try:
        return success(
            composition_options_payload(
                request.auth.user, entity=entity, search=search, offset=offset, limit=limit
            )
        )
    except ValueError as exc:
        raise MobileAPIError(str(exc), "Este tipo de elemento no está disponible para selección.", 422) from exc


@router.get(
    "/library/programs/{program_id}/weeks/{week_number}/picker-detail",
    operation_id="mobile_api_api_program_week_picker_detail",
    auth=mobile_bearer,
    response={200: ProgramWeekPickerDetailEnvelope, 401: ErrorEnvelope, 403: ErrorEnvelope, 404: ErrorEnvelope},
)
def program_week_picker_detail(request, program_id: int, week_number: int):
    week = program_week_picker_detail_payload(
        request.auth.user, program_id=program_id, week_number=week_number
    )
    if week is None:
        raise MobileAPIError("program_week_not_found", "La semana seleccionada no está disponible.", 404)
    return success(week)


@router.get(
    "/library/daily-plans",
    operation_id="mobile_api_api_library_dailyplans",
    auth=mobile_bearer,
    response={200: LibraryPageEnvelope, 401: ErrorEnvelope, 403: ErrorEnvelope},
)
def library_dailyplans(
    request, search: str | None = None, offset: int = 0, limit: int = 30, include_drafts: bool = False
):
    return success(
        library_dailyplans_payload(
            request.auth.user, search=search, offset=offset, limit=limit, include_drafts=include_drafts
        )
    )


@router.get(
    "/library/meals",
    operation_id="mobile_api_api_library_meals",
    auth=mobile_bearer,
    response={200: LibraryPageEnvelope, 401: ErrorEnvelope, 403: ErrorEnvelope},
)
def library_meals(request, search: str | None = None, offset: int = 0, limit: int = 30, include_drafts: bool = False):
    return success(
        library_meals_payload(
            request.auth.user, search=search, offset=offset, limit=limit, include_drafts=include_drafts
        )
    )


@router.get(
    "/library/foods",
    operation_id="mobile_api_api_library_foods",
    auth=mobile_bearer,
    response={200: LibraryPageEnvelope, 401: ErrorEnvelope, 403: ErrorEnvelope},
)
def library_foods(request, search: str | None = None, offset: int = 0, limit: int = 30):
    return success(library_foods_payload(request.auth.user, search=search, offset=offset, limit=limit))


def _clean_creation_name(name: str) -> str:
    clean_name = (name or "").strip()
    if not clean_name:
        raise MobileAPIError("library_name_required", "Ingresa un nombre antes de guardar.", 422)
    return clean_name


@router.post(
    "/library/foods",
    operation_id="mobile_api_api_create_library_food",
    auth=mobile_bearer,
    response={200: LibraryItemEnvelope, 403: ErrorEnvelope, 422: ErrorEnvelope},
)
def create_library_food(request, payload: FoodCreateInput):
    require_scope(request.auth, MOBILE_SCOPE_WRITE)
    result = create_food(
        user=request.auth.user,
        name=_clean_creation_name(payload.name),
        protein=payload.protein,
        carbs=payload.carbs,
        fat=payload.fat,
        portion_unit=payload.portion_unit,
    )
    return success(library_item_detail_payload(request.auth.user, "foods", result.food.id))


@router.put(
    "/library/foods/{food_id}/edit",
    operation_id="mobile_api_api_update_library_food",
    auth=mobile_bearer,
    response={200: LibraryItemEnvelope, 403: ErrorEnvelope, 404: ErrorEnvelope, 422: ErrorEnvelope},
)
def update_library_food(request, food_id: int, payload: FoodCreateInput):
    require_scope(request.auth, MOBILE_SCOPE_WRITE)
    food = Food.objects.filter(pk=food_id, created_by=request.auth.user, is_active=True).first()
    if food is None:
        raise MobileAPIError("library_item_not_found", "El alimento no está disponible para edición.", 404)
    result = update_food(
        food=food,
        name=_clean_creation_name(payload.name),
        protein=payload.protein,
        carbs=payload.carbs,
        fat=payload.fat,
        portion_unit=payload.portion_unit,
    )
    return success(library_item_detail_payload(request.auth.user, "foods", result.food.id))


@router.post(
    "/library/meals",
    operation_id="mobile_api_api_create_library_meal",
    auth=mobile_bearer,
    response={200: LibraryItemEnvelope, 403: ErrorEnvelope, 422: ErrorEnvelope},
)
def create_library_meal(request, payload: NamedLibraryCreateInput):
    require_scope(request.auth, MOBILE_SCOPE_WRITE)
    try:
        result = create_draft_meal(user=request.auth.user, name=_clean_creation_name(payload.name))
    except CommercialLimitReached as exc:
        raise MobileAPIError(str(exc), "El plan actual no permite crear más comidas.", 403) from exc
    return success(library_item_detail_payload(request.auth.user, "meals", result.meal.id))


@router.post(
    "/library/daily-plans",
    operation_id="mobile_api_api_create_library_dailyplan",
    auth=mobile_bearer,
    response={200: LibraryItemEnvelope, 403: ErrorEnvelope, 422: ErrorEnvelope},
)
def create_library_dailyplan(request, payload: NamedLibraryCreateInput):
    require_scope(request.auth, MOBILE_SCOPE_WRITE)
    try:
        result = create_draft_dailyplan(user=request.auth.user, name=_clean_creation_name(payload.name))
    except CommercialLimitReached as exc:
        raise MobileAPIError(str(exc), "El plan actual no permite crear más planes diarios.", 403) from exc
    return success(library_item_detail_payload(request.auth.user, "daily-plans", result.dailyplan.id))


@router.post(
    "/library/programs",
    operation_id="mobile_api_api_create_library_program",
    auth=mobile_bearer,
    response={200: LibraryItemEnvelope, 403: ErrorEnvelope, 422: ErrorEnvelope},
)
def create_library_program(request, payload: NamedLibraryCreateInput):
    require_scope(request.auth, MOBILE_SCOPE_WRITE)
    try:
        result = create_weekly_program(user=request.auth.user, name=_clean_creation_name(payload.name))
    except CommercialLimitReached as exc:
        raise MobileAPIError(str(exc), "El plan actual no permite crear más programas.", 403) from exc
    return success(library_item_detail_payload(request.auth.user, "programs", result.program.id))


@router.put(
    "/library/{entity}/order",
    operation_id="mobile_api_api_library_order",
    auth=mobile_bearer,
    response={200: LibraryListActionResultEnvelope, 403: ErrorEnvelope, 404: ErrorEnvelope, 422: ErrorEnvelope},
)
def library_order(request, entity: str, payload: LibraryOrderInput):
    require_scope(request.auth, MOBILE_SCOPE_WRITE)
    return success(reorder_library(request.auth.user, entity, payload.ordered_ids))


@router.post(
    "/library/{entity}/bulk-delete",
    operation_id="mobile_api_api_library_bulk_delete",
    auth=mobile_bearer,
    response={200: LibraryListActionResultEnvelope, 403: ErrorEnvelope, 404: ErrorEnvelope, 422: ErrorEnvelope},
)
def library_bulk_delete(request, entity: str, payload: LibraryBulkDeleteInput):
    require_scope(request.auth, MOBILE_SCOPE_WRITE)
    return success(bulk_delete_library(request.auth.user, entity, payload.item_ids))


@router.get(
    "/library/{entity}/{item_id}",
    operation_id="mobile_api_api_library_item_detail",
    auth=mobile_bearer,
    response={200: LibraryItemEnvelope, 401: ErrorEnvelope, 403: ErrorEnvelope, 404: ErrorEnvelope},
)
def library_item_detail(request, entity: str, item_id: int):
    if entity not in {"programs", "daily-plans", "meals", "foods"}:
        raise MobileAPIError(
            code="library_item_not_found", message="The requested library item was not found.", status_code=404
        )
    return success(library_item_detail_payload(request.auth.user, entity, item_id))


@router.post(
    "/library/{entity}/{item_id}/actions",
    operation_id="mobile_api_api_library_item_action",
    auth=mobile_bearer,
    response={
        200: LibraryActionResultEnvelope,
        401: ErrorEnvelope,
        403: ErrorEnvelope,
        404: ErrorEnvelope,
        409: ErrorEnvelope,
        422: ErrorEnvelope,
    },
)
def library_item_action(request, entity: str, item_id: int, payload: LibraryActionInput):
    require_scope(request.auth, MOBILE_SCOPE_WRITE)
    if entity not in {"programs", "daily-plans", "meals", "foods"}:
        raise MobileAPIError(
            code="library_item_not_found", message="The requested library item was not found.", status_code=404
        )
    return success(perform_library_action(request, entity, item_id, payload))
