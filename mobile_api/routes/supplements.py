"""Pro-only supplement library, planning and lived intake endpoints."""

from datetime import time
from decimal import Decimal
from typing import Literal

from django.db import IntegrityError, transaction
from ninja import Field, Router, Schema

from mobile_api.api_support import require_scope, success
from mobile_api.auth import mobile_bearer
from mobile_api.errors import MobileAPIError
from mobile_api.schemas import ErrorEnvelope
from mobile_api.selectors import local_date_for_user
from notas.application.services.commands.supplement_commands import (
    create_calendarized_supplement_intake_from_preset,
    create_supplement_intake,
    create_supplement_intake_from_preset,
    delete_calendarized_supplement_intake,
    delete_supplement,
    delete_supplement_intake,
    delete_supplement_intake_preset,
    reorder_calendarized_supplement_intakes,
    reorder_supplement_intakes,
    require_supplements_pro,
    save_supplement,
    save_supplement_intake_preset,
    update_calendarized_supplement_intake_hour,
    update_supplement_intake,
)
from notas.application.services.oauth_device_sessions import MOBILE_SCOPE_WRITE
from notas.domain.models import (
    CalendarizedDay,
    CalendarizedSupplementIntakeExecution,
    DailyPlan,
    PinnedDailyPlan,
    PinnedSupplementIntakeExecution,
    Supplement,
    SupplementIntake,
    SupplementIntakePreset,
)

router = Router()


class SupplementComponentInput(Schema):
    name: str = Field(min_length=1, max_length=100)
    quantity: Decimal = Field(gt=0)
    unit: Literal["g", "mg", "mcg", "ml", "iu"]


class SupplementNutritionInput(Schema):
    energy_kcal: Decimal | None = Field(default=None, ge=0, le=100_000)
    protein_g: Decimal | None = Field(default=None, ge=0, le=100_000)
    carbs_g: Decimal | None = Field(default=None, ge=0, le=100_000)
    fat_g: Decimal | None = Field(default=None, ge=0, le=100_000)
    saturated_fat_g: Decimal | None = Field(default=None, ge=0, le=100_000)
    sugar_g: Decimal | None = Field(default=None, ge=0, le=100_000)
    fiber_g: Decimal | None = Field(default=None, ge=0, le=100_000)
    sodium_mg: Decimal | None = Field(default=None, ge=0, le=1_000_000)


class SupplementInput(Schema):
    name: str = Field(min_length=1, max_length=100)
    brand: str = Field(default="", max_length=100)
    form: str = ""
    description: str = ""
    user_information: str = ""
    components: list[SupplementComponentInput] = Field(default_factory=list)
    nutrition: SupplementNutritionInput | None = None
    default_quantity: Decimal | None = Field(default=None, gt=0)
    default_unit: str = ""


class IntakeItemInput(Schema):
    supplement_id: int | None = None
    item_id: int | None = None
    quantity: Decimal = Field(gt=0)
    unit: str


class PresetItemInput(Schema):
    supplement_id: int
    quantity: Decimal = Field(gt=0)
    unit: str


class SupplementIntakePresetInput(Schema):
    name: str = Field(min_length=1, max_length=100)
    items: list[PresetItemInput] = Field(min_length=1, max_length=30)


class PresetApplyInput(Schema):
    preset_id: int
    hour: time


class IntakeInput(Schema):
    hour: time | None = None
    items: list[IntakeItemInput] = Field(min_length=1, max_length=30)


class IntakeOrderInput(Schema):
    ordered_ids: list[int]


class CalendarizedIntakeOrderInput(Schema):
    ordered_keys: list[str]


class IntakeHourInput(Schema):
    hour: time


class IntakeCheckInInput(Schema):
    action: Literal["completed", "skipped", "reset"]
    idempotency_key: str = Field(min_length=1, max_length=120)


def _pro(user):
    try:
        require_supplements_pro(user)
    except PermissionError as exc:
        raise MobileAPIError("supplements_pro_required", "Los suplementos requieren Pro.", 403) from exc


def _error(exc):
    code = str(exc)
    return MobileAPIError(code, "No pudimos actualizar los suplementos.", 404 if code.endswith("_not_found") else 422)


def _supplement_payload(row):
    return {
        "id": row.id, "name": row.name, "brand": row.brand, "form": row.form,
        "description": row.description, "user_information": row.user_information,
        "components": row.components,
        "nutrition": row.nutrition,
        "default_quantity": str(row.default_quantity) if row.default_quantity is not None else None,
        "default_unit": row.default_unit,
    }


def _intake_payload(intake, number):
    return {
        "id": intake.id, "key": f"supplement_intake:{intake.id}",
        "label": f"Ingesta {number}", "order": number,
        "hour": intake.hour.strftime("%H:%M") if intake.hour else None,
        "items": [
            {
                "id": item.id, "supplement_id": item.supplement_id,
                "supplement": item.supplement_snapshot,
                "quantity": str(item.quantity), "unit": item.unit,
            }
            for item in intake.items.all()
        ],
    }


def _preset_payload(preset):
    return {
        "id": preset.id,
        "name": preset.name,
        "items": [
            {
                "id": item.id,
                "supplement_id": item.supplement_id,
                "supplement": item.supplement_snapshot,
                "quantity": str(item.quantity),
                "unit": item.unit,
            }
            for item in preset.items.all()
        ],
    }


def _owned_plan(user, dailyplan_id):
    plan = DailyPlan.objects.filter(pk=dailyplan_id, created_by=user).first()
    if plan is None:
        raise MobileAPIError("dailyplan_not_found", "La minuta no está disponible.", 404)
    return plan


def _plan_intakes(plan):
    rows = SupplementIntake.objects.filter(dailyplan=plan).prefetch_related("items")
    return [_intake_payload(row, number) for number, row in enumerate(rows, 1)]


@router.get("/library/supplements", operation_id="list_supplements", auth=mobile_bearer, response={200: dict, 403: ErrorEnvelope})
def list_supplements(request, search: str = ""):
    _pro(request.auth.user)
    rows = Supplement.objects.filter(created_by=request.auth.user)
    if search.strip():
        rows = rows.filter(name__icontains=search.strip())
    return success({"items": [_supplement_payload(row) for row in rows]})


@router.get("/library/supplement-intake-presets", operation_id="list_supplement_intake_presets", auth=mobile_bearer, response={200: dict, 403: ErrorEnvelope})
def list_supplement_intake_presets(request, search: str = ""):
    _pro(request.auth.user)
    rows = SupplementIntakePreset.objects.filter(created_by=request.auth.user).prefetch_related("items")
    if search.strip():
        rows = rows.filter(name__icontains=search.strip())
    return success({"items": [_preset_payload(row) for row in rows]})


@router.post("/library/supplement-intake-presets", operation_id="create_supplement_intake_preset", auth=mobile_bearer, response={200: dict, 403: ErrorEnvelope, 422: ErrorEnvelope})
def create_supplement_intake_preset(request, payload: SupplementIntakePresetInput):
    require_scope(request.auth, MOBILE_SCOPE_WRITE)
    try:
        row = save_supplement_intake_preset(user=request.auth.user, **payload.dict())
    except PermissionError:
        _pro(request.auth.user)
    except ValueError as exc:
        raise _error(exc) from exc
    return success(_preset_payload(row))


@router.get("/library/supplement-intake-presets/{preset_id}", operation_id="supplement_intake_preset_detail", auth=mobile_bearer, response={200: dict, 403: ErrorEnvelope, 404: ErrorEnvelope})
def supplement_intake_preset_detail(request, preset_id: int):
    _pro(request.auth.user)
    row = SupplementIntakePreset.objects.filter(pk=preset_id, created_by=request.auth.user).prefetch_related("items").first()
    if row is None:
        raise _error(ValueError("supplement_intake_preset_not_found"))
    return success(_preset_payload(row))


@router.put("/library/supplement-intake-presets/{preset_id}", operation_id="update_supplement_intake_preset", auth=mobile_bearer, response={200: dict, 403: ErrorEnvelope, 404: ErrorEnvelope, 422: ErrorEnvelope})
def update_supplement_intake_preset(request, preset_id: int, payload: SupplementIntakePresetInput):
    require_scope(request.auth, MOBILE_SCOPE_WRITE)
    try:
        row = save_supplement_intake_preset(user=request.auth.user, preset_id=preset_id, **payload.dict())
    except PermissionError:
        _pro(request.auth.user)
    except ValueError as exc:
        raise _error(exc) from exc
    return success(_preset_payload(row))


@router.delete("/library/supplement-intake-presets/{preset_id}", operation_id="remove_supplement_intake_preset", auth=mobile_bearer, response={200: dict, 403: ErrorEnvelope, 404: ErrorEnvelope})
def remove_supplement_intake_preset(request, preset_id: int):
    require_scope(request.auth, MOBILE_SCOPE_WRITE)
    try:
        delete_supplement_intake_preset(user=request.auth.user, preset_id=preset_id)
    except PermissionError:
        _pro(request.auth.user)
    except ValueError as exc:
        raise _error(exc) from exc
    return success({"deleted_id": preset_id})


@router.post("/library/supplements", operation_id="create_supplement", auth=mobile_bearer, response={200: dict, 403: ErrorEnvelope, 422: ErrorEnvelope})
def create_supplement(request, payload: SupplementInput):
    require_scope(request.auth, MOBILE_SCOPE_WRITE)
    try:
        row = save_supplement(user=request.auth.user, **payload.dict())
    except PermissionError:
        _pro(request.auth.user)
    except ValueError as exc:
        raise _error(exc) from exc
    return success(_supplement_payload(row))


@router.get("/library/supplements/{supplement_id}", operation_id="supplement_detail", auth=mobile_bearer, response={200: dict, 403: ErrorEnvelope, 404: ErrorEnvelope})
def supplement_detail(request, supplement_id: int):
    _pro(request.auth.user)
    row = Supplement.objects.filter(pk=supplement_id, created_by=request.auth.user).first()
    if row is None:
        raise _error(ValueError("supplement_not_found"))
    return success(_supplement_payload(row))


@router.put("/library/supplements/{supplement_id}", operation_id="update_supplement", auth=mobile_bearer, response={200: dict, 403: ErrorEnvelope, 404: ErrorEnvelope, 422: ErrorEnvelope})
def update_supplement(request, supplement_id: int, payload: SupplementInput):
    require_scope(request.auth, MOBILE_SCOPE_WRITE)
    _pro(request.auth.user)
    try:
        row = save_supplement(user=request.auth.user, supplement_id=supplement_id, **payload.dict())
    except ValueError as exc:
        raise _error(exc) from exc
    return success(_supplement_payload(row))


@router.delete("/library/supplements/{supplement_id}", operation_id="remove_supplement", auth=mobile_bearer, response={200: dict, 403: ErrorEnvelope, 404: ErrorEnvelope})
def remove_supplement(request, supplement_id: int):
    require_scope(request.auth, MOBILE_SCOPE_WRITE)
    _pro(request.auth.user)
    try:
        delete_supplement(user=request.auth.user, supplement_id=supplement_id)
    except ValueError as exc:
        raise _error(exc) from exc
    return success({"deleted_id": supplement_id})


@router.get("/library/daily-plans/{dailyplan_id}/supplement-intakes", operation_id="list_plan_intakes", auth=mobile_bearer, response={200: dict, 403: ErrorEnvelope, 404: ErrorEnvelope})
def list_plan_intakes(request, dailyplan_id: int):
    _pro(request.auth.user)
    return success({"items": _plan_intakes(_owned_plan(request.auth.user, dailyplan_id))})


@router.post("/library/daily-plans/{dailyplan_id}/supplement-intakes", operation_id="add_plan_intake", auth=mobile_bearer, response={200: dict, 403: ErrorEnvelope, 404: ErrorEnvelope, 422: ErrorEnvelope})
def add_plan_intake(request, dailyplan_id: int, payload: IntakeInput):
    require_scope(request.auth, MOBILE_SCOPE_WRITE)
    _pro(request.auth.user)
    try:
        create_supplement_intake(user=request.auth.user, dailyplan_id=dailyplan_id, items=[item.dict() for item in payload.items], hour=payload.hour)
    except ValueError as exc:
        raise _error(exc) from exc
    return success({"items": _plan_intakes(_owned_plan(request.auth.user, dailyplan_id))})


@router.post("/library/daily-plans/{dailyplan_id}/supplement-intakes/from-preset", operation_id="add_plan_intake_from_preset", auth=mobile_bearer, response={200: dict, 403: ErrorEnvelope, 404: ErrorEnvelope, 422: ErrorEnvelope})
def add_plan_intake_from_preset(request, dailyplan_id: int, payload: PresetApplyInput):
    require_scope(request.auth, MOBILE_SCOPE_WRITE)
    try:
        create_supplement_intake_from_preset(
            user=request.auth.user,
            dailyplan_id=dailyplan_id,
            preset_id=payload.preset_id,
            hour=payload.hour,
        )
    except PermissionError:
        _pro(request.auth.user)
    except ValueError as exc:
        raise _error(exc) from exc
    return success({"items": _plan_intakes(_owned_plan(request.auth.user, dailyplan_id))})


@router.put("/library/daily-plans/{dailyplan_id}/supplement-intakes/order", operation_id="order_plan_intakes", auth=mobile_bearer, response={200: dict, 403: ErrorEnvelope, 422: ErrorEnvelope})
def order_plan_intakes(request, dailyplan_id: int, payload: IntakeOrderInput):
    require_scope(request.auth, MOBILE_SCOPE_WRITE)
    _pro(request.auth.user)
    try:
        reorder_supplement_intakes(user=request.auth.user, dailyplan_id=dailyplan_id, intake_ids=payload.ordered_ids)
    except ValueError as exc:
        raise _error(exc) from exc
    return success({"items": _plan_intakes(_owned_plan(request.auth.user, dailyplan_id))})


@router.put("/library/daily-plans/{dailyplan_id}/supplement-intakes/{intake_id}", operation_id="change_plan_intake", auth=mobile_bearer, response={200: dict, 403: ErrorEnvelope, 404: ErrorEnvelope, 422: ErrorEnvelope})
def change_plan_intake(request, dailyplan_id: int, intake_id: int, payload: IntakeInput):
    require_scope(request.auth, MOBILE_SCOPE_WRITE)
    _pro(request.auth.user)
    try:
        update_supplement_intake(user=request.auth.user, dailyplan_id=dailyplan_id, intake_id=intake_id, items=[item.dict() for item in payload.items], hour=payload.hour)
    except ValueError as exc:
        raise _error(exc) from exc
    return success({"items": _plan_intakes(_owned_plan(request.auth.user, dailyplan_id))})


@router.delete("/library/daily-plans/{dailyplan_id}/supplement-intakes/{intake_id}", operation_id="remove_plan_intake", auth=mobile_bearer, response={200: dict, 403: ErrorEnvelope, 404: ErrorEnvelope})
def remove_plan_intake(request, dailyplan_id: int, intake_id: int):
    require_scope(request.auth, MOBILE_SCOPE_WRITE)
    _pro(request.auth.user)
    try:
        delete_supplement_intake(user=request.auth.user, dailyplan_id=dailyplan_id, intake_id=intake_id)
    except ValueError as exc:
        raise _error(exc) from exc
    return success({"items": _plan_intakes(_owned_plan(request.auth.user, dailyplan_id))})


def _execution_state(events, intake_keys):
    statuses = dict.fromkeys(intake_keys, "planned")
    for event in events:
        if event.intake_key in statuses:
            statuses[event.intake_key] = "planned" if event.action == "reset" else event.action
    return statuses


@router.get("/today/pinned-plan/supplement-intakes", operation_id="pinned_intakes", auth=mobile_bearer, response={200: dict, 403: ErrorEnvelope, 404: ErrorEnvelope})
def pinned_intakes(request):
    _pro(request.auth.user)
    pinned = PinnedDailyPlan.objects.filter(user=request.auth.user, is_active=True).select_related("dailyplan").first()
    if pinned is None:
        raise _error(ValueError("pinned_dailyplan_not_found"))
    items = _plan_intakes(pinned.dailyplan)
    events = PinnedSupplementIntakeExecution.objects.filter(pinned_dailyplan=pinned, local_date=local_date_for_user(request.auth.user))
    states = _execution_state(events, {item["key"] for item in items})
    return success({"items": [{**item, "status": states[item["key"]]} for item in items]})


@router.post("/today/pinned-plan/supplement-intakes/{intake_id}/check-ins", operation_id="pinned_intake_check_in", auth=mobile_bearer, response={200: dict, 403: ErrorEnvelope, 404: ErrorEnvelope, 409: ErrorEnvelope})
def pinned_intake_check_in(request, intake_id: int, payload: IntakeCheckInInput):
    require_scope(request.auth, MOBILE_SCOPE_WRITE)
    _pro(request.auth.user)
    pinned = PinnedDailyPlan.objects.filter(user=request.auth.user, is_active=True).first()
    if pinned is None or not SupplementIntake.objects.filter(pk=intake_id, dailyplan_id=pinned.dailyplan_id).exists():
        raise _error(ValueError("supplement_intake_not_found"))
    try:
        with transaction.atomic():
            PinnedSupplementIntakeExecution.objects.create(
                pinned_dailyplan=pinned, local_date=local_date_for_user(request.auth.user),
                intake_key=f"supplement_intake:{intake_id}", action=payload.action,
                idempotency_key=payload.idempotency_key,
            )
    except IntegrityError as exc:
        raise MobileAPIError("supplement_intake_idempotency_conflict", "La acción ya fue registrada.", 409) from exc
    return pinned_intakes(request)


@router.get("/days/{day_id}/supplement-intakes", operation_id="calendarized_intakes", auth=mobile_bearer, response={200: dict, 403: ErrorEnvelope, 404: ErrorEnvelope})
def calendarized_intakes(request, day_id: int):
    _pro(request.auth.user)
    day = CalendarizedDay.objects.filter(pk=day_id, user=request.auth.user, assignment_state=CalendarizedDay.STATE_CURRENT).first()
    if day is None:
        raise _error(ValueError("calendarized_day_not_found"))
    rows = (day.plan_snapshot or {}).get("supplement_intakes") or []
    states = _execution_state(day.supplement_execution_events.all(), {row["key"] for row in rows})
    return success({"items": [{**row, "status": states[row["key"]]} for row in rows]})


@router.post("/days/{day_id}/supplement-intakes/from-preset", operation_id="add_calendarized_intake_from_preset", auth=mobile_bearer, response={200: dict, 403: ErrorEnvelope, 404: ErrorEnvelope, 422: ErrorEnvelope})
def add_calendarized_intake_from_preset(request, day_id: int, payload: PresetApplyInput):
    require_scope(request.auth, MOBILE_SCOPE_WRITE)
    try:
        create_calendarized_supplement_intake_from_preset(
            user=request.auth.user,
            day_id=day_id,
            preset_id=payload.preset_id,
            hour=payload.hour,
        )
    except PermissionError:
        _pro(request.auth.user)
    except ValueError as exc:
        raise _error(exc) from exc
    return calendarized_intakes(request, day_id)


@router.put("/days/{day_id}/supplement-intakes/order", operation_id="order_calendarized_intakes", auth=mobile_bearer, response={200: dict, 403: ErrorEnvelope, 404: ErrorEnvelope, 422: ErrorEnvelope})
def order_calendarized_intakes(request, day_id: int, payload: CalendarizedIntakeOrderInput):
    require_scope(request.auth, MOBILE_SCOPE_WRITE)
    try:
        reorder_calendarized_supplement_intakes(user=request.auth.user, day_id=day_id, intake_keys=payload.ordered_keys)
    except PermissionError:
        _pro(request.auth.user)
    except ValueError as exc:
        raise _error(exc) from exc
    return calendarized_intakes(request, day_id)


@router.patch("/days/{day_id}/supplement-intakes/{intake_id}/hour", operation_id="change_calendarized_intake_hour", auth=mobile_bearer, response={200: dict, 403: ErrorEnvelope, 404: ErrorEnvelope, 422: ErrorEnvelope})
def change_calendarized_intake_hour(request, day_id: int, intake_id: int, payload: IntakeHourInput):
    require_scope(request.auth, MOBILE_SCOPE_WRITE)
    try:
        update_calendarized_supplement_intake_hour(user=request.auth.user, day_id=day_id, intake_key=f"supplement_intake:{intake_id}", hour=payload.hour)
    except PermissionError:
        _pro(request.auth.user)
    except ValueError as exc:
        raise _error(exc) from exc
    return calendarized_intakes(request, day_id)


@router.delete("/days/{day_id}/supplement-intakes/{intake_id}", operation_id="remove_calendarized_intake", auth=mobile_bearer, response={200: dict, 403: ErrorEnvelope, 404: ErrorEnvelope, 422: ErrorEnvelope})
def remove_calendarized_intake(request, day_id: int, intake_id: int):
    require_scope(request.auth, MOBILE_SCOPE_WRITE)
    try:
        delete_calendarized_supplement_intake(user=request.auth.user, day_id=day_id, intake_key=f"supplement_intake:{intake_id}")
    except PermissionError:
        _pro(request.auth.user)
    except ValueError as exc:
        raise _error(exc) from exc
    return calendarized_intakes(request, day_id)


@router.post("/days/{day_id}/supplement-intakes/{intake_id}/check-ins", operation_id="calendarized_intake_check_in", auth=mobile_bearer, response={200: dict, 403: ErrorEnvelope, 404: ErrorEnvelope, 409: ErrorEnvelope})
def calendarized_intake_check_in(request, day_id: int, intake_id: int, payload: IntakeCheckInInput):
    require_scope(request.auth, MOBILE_SCOPE_WRITE)
    _pro(request.auth.user)
    day = CalendarizedDay.objects.filter(pk=day_id, user=request.auth.user, assignment_state=CalendarizedDay.STATE_CURRENT).first()
    key = f"supplement_intake:{intake_id}"
    if day is None or key not in {row["key"] for row in (day.plan_snapshot or {}).get("supplement_intakes") or []}:
        raise _error(ValueError("supplement_intake_not_found"))
    try:
        with transaction.atomic():
            CalendarizedSupplementIntakeExecution.objects.create(
                calendarized_day=day, intake_key=key, action=payload.action,
                idempotency_key=payload.idempotency_key,
            )
    except IntegrityError as exc:
        raise MobileAPIError("supplement_intake_idempotency_conflict", "La acción ya fue registrada.", 409) from exc
    return calendarized_intakes(request, day_id)
