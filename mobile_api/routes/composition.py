from __future__ import annotations

from ninja import Router

from mobile_api.api_support import require_scope, success
from mobile_api.auth import mobile_bearer
from mobile_api.composition import (
    add_dailyplan_from_picker,
    add_food_from_picker,
    add_meal_from_picker,
    add_week_from_picker,
    duplicate_program_week,
    preview_dailyplan_for_program,
    preview_food_for_meal,
    preview_meal_for_dailyplan,
    preview_week_for_program,
    remove_dailyplan_from_program,
    remove_food_from_meal,
    remove_meal_from_dailyplan,
    remove_program_week,
    reorder_foods_in_meal,
    reorder_meals_in_dailyplan,
    reorder_weeks_in_program,
    update_food_in_meal,
    update_meal_in_dailyplan,
)
from mobile_api.schema_domains.composition import (
    CompositionMutationEnvelope,
    CompositionOrderInput,
    DailyPlanMealUpdateInput,
    DailyPlanPickerInput,
    FoodPickerInput,
    MealFoodUpdateInput,
    MealPickerInput,
    PickerCommitEnvelope,
)
from mobile_api.schema_domains.composition_preview import PickerPreviewEnvelope
from mobile_api.schemas import ErrorEnvelope
from notas.application.services.oauth_device_sessions import MOBILE_SCOPE_WRITE

router = Router()


@router.put(
    "/library/meals/{meal_id}/foods/order",
    operation_id="mobile_api_api_meal_food_order",
    auth=mobile_bearer,
    response={200: CompositionMutationEnvelope, 403: ErrorEnvelope, 404: ErrorEnvelope, 422: ErrorEnvelope},
)
def meal_food_order(request, meal_id: int, payload: CompositionOrderInput):
    require_scope(request.auth, MOBILE_SCOPE_WRITE)
    return success(reorder_foods_in_meal(user=request.auth.user, meal_id=meal_id, ordered_ids=payload.ordered_ids))


@router.patch(
    "/library/meals/{meal_id}/foods/{meal_food_id}",
    operation_id="mobile_api_api_meal_food_update",
    auth=mobile_bearer,
    response={200: CompositionMutationEnvelope, 403: ErrorEnvelope, 404: ErrorEnvelope, 422: ErrorEnvelope},
)
def meal_food_update(request, meal_id: int, meal_food_id: int, payload: MealFoodUpdateInput):
    require_scope(request.auth, MOBILE_SCOPE_WRITE)
    return success(
        update_food_in_meal(
            user=request.auth.user, meal_id=meal_id, meal_food_id=meal_food_id, quantity=payload.quantity
        )
    )


@router.delete(
    "/library/meals/{meal_id}/foods/{meal_food_id}",
    operation_id="mobile_api_api_meal_food_delete",
    auth=mobile_bearer,
    response={200: CompositionMutationEnvelope, 403: ErrorEnvelope, 404: ErrorEnvelope},
)
def meal_food_delete(request, meal_id: int, meal_food_id: int):
    require_scope(request.auth, MOBILE_SCOPE_WRITE)
    return success(remove_food_from_meal(user=request.auth.user, meal_id=meal_id, meal_food_id=meal_food_id))


@router.put(
    "/library/daily-plans/{dailyplan_id}/meals/order",
    operation_id="mobile_api_api_dailyplan_meal_order",
    auth=mobile_bearer,
    response={200: CompositionMutationEnvelope, 403: ErrorEnvelope, 404: ErrorEnvelope, 422: ErrorEnvelope},
)
def dailyplan_meal_order(request, dailyplan_id: int, payload: CompositionOrderInput):
    require_scope(request.auth, MOBILE_SCOPE_WRITE)
    return success(
        reorder_meals_in_dailyplan(user=request.auth.user, dailyplan_id=dailyplan_id, ordered_ids=payload.ordered_ids)
    )


@router.patch(
    "/library/daily-plans/{dailyplan_id}/meals/{dailyplan_meal_id}",
    operation_id="mobile_api_api_dailyplan_meal_update",
    auth=mobile_bearer,
    response={200: CompositionMutationEnvelope, 403: ErrorEnvelope, 404: ErrorEnvelope, 422: ErrorEnvelope},
)
def dailyplan_meal_update(request, dailyplan_id: int, dailyplan_meal_id: int, payload: DailyPlanMealUpdateInput):
    require_scope(request.auth, MOBILE_SCOPE_WRITE)
    return success(
        update_meal_in_dailyplan(
            user=request.auth.user,
            dailyplan_id=dailyplan_id,
            dailyplan_meal_id=dailyplan_meal_id,
            hour=payload.hour,
            note=payload.note,
        )
    )


@router.delete(
    "/library/daily-plans/{dailyplan_id}/meals/{dailyplan_meal_id}",
    operation_id="mobile_api_api_dailyplan_meal_delete",
    auth=mobile_bearer,
    response={200: CompositionMutationEnvelope, 403: ErrorEnvelope, 404: ErrorEnvelope},
)
def dailyplan_meal_delete(request, dailyplan_id: int, dailyplan_meal_id: int):
    require_scope(request.auth, MOBILE_SCOPE_WRITE)
    return success(
        remove_meal_from_dailyplan(
            user=request.auth.user, dailyplan_id=dailyplan_id, dailyplan_meal_id=dailyplan_meal_id
        )
    )


@router.put(
    "/library/programs/{program_id}/weeks/order",
    operation_id="mobile_api_api_program_week_order",
    auth=mobile_bearer,
    response={200: CompositionMutationEnvelope, 403: ErrorEnvelope, 404: ErrorEnvelope, 422: ErrorEnvelope},
)
def program_week_order(request, program_id: int, payload: CompositionOrderInput):
    require_scope(request.auth, MOBILE_SCOPE_WRITE)
    return success(
        reorder_weeks_in_program(user=request.auth.user, program_id=program_id, ordered_weeks=payload.ordered_ids)
    )


@router.post(
    "/library/programs/{program_id}/weeks/{week_number}/duplicate",
    operation_id="mobile_api_api_program_week_duplicate",
    auth=mobile_bearer,
    response={200: CompositionMutationEnvelope, 403: ErrorEnvelope, 404: ErrorEnvelope, 422: ErrorEnvelope},
)
def program_week_duplicate(request, program_id: int, week_number: int):
    require_scope(request.auth, MOBILE_SCOPE_WRITE)
    return success(duplicate_program_week(user=request.auth.user, program_id=program_id, week_number=week_number))


@router.delete(
    "/library/programs/{program_id}/weeks/{week_number}",
    operation_id="mobile_api_api_program_week_delete",
    auth=mobile_bearer,
    response={200: CompositionMutationEnvelope, 403: ErrorEnvelope, 404: ErrorEnvelope, 422: ErrorEnvelope},
)
def program_week_delete(request, program_id: int, week_number: int):
    require_scope(request.auth, MOBILE_SCOPE_WRITE)
    return success(remove_program_week(user=request.auth.user, program_id=program_id, week_number=week_number))


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
            user=request.auth.user, program_id=program_id, week_number=week_number, day_number=day_number
        )
    )


@router.post(
    "/library/meals/{meal_id}/food-picker/preview",
    operation_id="mobile_api_api_meal_food_picker_preview",
    auth=mobile_bearer,
    response={
        200: PickerPreviewEnvelope,
        401: ErrorEnvelope,
        403: ErrorEnvelope,
        404: ErrorEnvelope,
        422: ErrorEnvelope,
    },
)
def meal_food_picker_preview(request, meal_id: int, payload: FoodPickerInput):
    return success(
        preview_food_for_meal(
            user=request.auth.user, meal_id=meal_id, food_id=payload.food_id,
            meal_food_id=payload.meal_food_id, quantity=payload.quantity,
        )
    )


@router.post(
    "/library/meals/{meal_id}/food-picker/commit",
    operation_id="mobile_api_api_meal_food_picker_commit",
    auth=mobile_bearer,
    response={
        200: PickerCommitEnvelope,
        401: ErrorEnvelope,
        403: ErrorEnvelope,
        404: ErrorEnvelope,
        422: ErrorEnvelope,
    },
)
def meal_food_picker_commit(request, meal_id: int, payload: FoodPickerInput):
    require_scope(request.auth, MOBILE_SCOPE_WRITE)
    return success(
        add_food_from_picker(
            user=request.auth.user, meal_id=meal_id, food_id=payload.food_id,
            meal_food_id=payload.meal_food_id, quantity=payload.quantity,
        )
    )


@router.post(
    "/library/daily-plans/{dailyplan_id}/meal-picker/preview",
    operation_id="mobile_api_api_dailyplan_meal_picker_preview",
    auth=mobile_bearer,
    response={
        200: PickerPreviewEnvelope,
        401: ErrorEnvelope,
        403: ErrorEnvelope,
        404: ErrorEnvelope,
        422: ErrorEnvelope,
    },
)
def dailyplan_meal_picker_preview(request, dailyplan_id: int, payload: MealPickerInput):
    return success(
        preview_meal_for_dailyplan(
            user=request.auth.user,
            dailyplan_id=dailyplan_id,
            meal_id=payload.meal_id,
            dailyplan_meal_id=payload.dailyplan_meal_id,
            hour=payload.hour,
            note=payload.note,
        )
    )


@router.post(
    "/library/daily-plans/{dailyplan_id}/meal-picker/commit",
    operation_id="mobile_api_api_dailyplan_meal_picker_commit",
    auth=mobile_bearer,
    response={
        200: PickerCommitEnvelope,
        401: ErrorEnvelope,
        403: ErrorEnvelope,
        404: ErrorEnvelope,
        422: ErrorEnvelope,
    },
)
def dailyplan_meal_picker_commit(request, dailyplan_id: int, payload: MealPickerInput):
    require_scope(request.auth, MOBILE_SCOPE_WRITE)
    return success(
        add_meal_from_picker(
            user=request.auth.user,
            dailyplan_id=dailyplan_id,
            meal_id=payload.meal_id,
            dailyplan_meal_id=payload.dailyplan_meal_id,
            hour=payload.hour,
            note=payload.note,
        )
    )


@router.post(
    "/library/programs/{program_id}/daily-plan-picker/preview",
    operation_id="mobile_api_api_program_dailyplan_picker_preview",
    auth=mobile_bearer,
    response={
        200: PickerPreviewEnvelope,
        401: ErrorEnvelope,
        403: ErrorEnvelope,
        404: ErrorEnvelope,
        422: ErrorEnvelope,
    },
)
def program_dailyplan_picker_preview(request, program_id: int, payload: DailyPlanPickerInput):
    return success(
        preview_dailyplan_for_program(
            user=request.auth.user,
            program_id=program_id,
            dailyplan_id=payload.dailyplan_id,
            week_number=payload.week_number,
            day_numbers=payload.day_numbers,
        )
    )


@router.post(
    "/library/programs/{program_id}/daily-plan-picker/commit",
    operation_id="mobile_api_api_program_dailyplan_picker_commit",
    auth=mobile_bearer,
    response={
        200: PickerCommitEnvelope,
        401: ErrorEnvelope,
        403: ErrorEnvelope,
        404: ErrorEnvelope,
        409: ErrorEnvelope,
        422: ErrorEnvelope,
    },
)
def program_dailyplan_picker_commit(request, program_id: int, payload: DailyPlanPickerInput):
    require_scope(request.auth, MOBILE_SCOPE_WRITE)
    return success(
        add_dailyplan_from_picker(
            user=request.auth.user,
            program_id=program_id,
            dailyplan_id=payload.dailyplan_id,
            week_number=payload.week_number,
            day_numbers=payload.day_numbers,
            confirm_replacements=payload.confirm_replacements,
        )
    )


@router.post(
    "/library/programs/{program_id}/week-picker/preview",
    operation_id="mobile_api_api_program_week_picker_preview",
    auth=mobile_bearer,
    response={200: PickerPreviewEnvelope, 401: ErrorEnvelope, 403: ErrorEnvelope, 404: ErrorEnvelope},
)
def program_week_picker_preview(request, program_id: int):
    return success(preview_week_for_program(user=request.auth.user, program_id=program_id))


@router.post(
    "/library/programs/{program_id}/week-picker/commit",
    operation_id="mobile_api_api_program_week_picker_commit",
    auth=mobile_bearer,
    response={200: PickerCommitEnvelope, 401: ErrorEnvelope, 403: ErrorEnvelope, 404: ErrorEnvelope},
)
def program_week_picker_commit(request, program_id: int, expected_week_number: int | None = None):
    require_scope(request.auth, MOBILE_SCOPE_WRITE)
    return success(
        add_week_from_picker(
            user=request.auth.user,
            program_id=program_id,
            expected_week_number=expected_week_number,
        )
    )
