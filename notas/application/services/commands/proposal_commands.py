from dataclasses import dataclass
from datetime import time

from django.db import transaction
from django.utils import timezone

from notas.application.dto.proposal_apply import (
    build_create_dailyplan_apply_plan,
    build_create_meal_apply_plan,
)
from notas.application.dto.proposal_payloads import (
    CREATE_DAILYPLAN_INTENT,
    CREATE_MEAL_INTENT,
)
from notas.application.proposals.applicators import (
    ProposalOperationsApplyResult,
    validate_and_apply_proposal_operations,
)
from notas.application.queries.proposal_simulation_queries import (
    simulate_proposal_payload,
)
from notas.application.queries.read_boundaries import (
    get_readable_food_queryset,
)
from notas.application.queries.validation_queries import (
    compare_dailyplan_to_targets,
)
from notas.application.validation.proposal_payload_validators import (
    validate_proposal_payload_or_raise,
)
from notas.domain.models import (
    DailyPlan,
    DailyPlanMeal,
    Food,
    Meal,
    MealFood,
    NutritionProposal,
    NutritionProposalAuditEvent,
)


@dataclass(frozen=True)
class NutritionProposalCreateResult:
    proposal: NutritionProposal


@dataclass(frozen=True)
class NutritionProposalStatusResult:
    proposal: NutritionProposal


@dataclass(frozen=True)
class NutritionProposalApplyResult:
    proposal: NutritionProposal
    operations_result: ProposalOperationsApplyResult


@dataclass(frozen=True)
class NutritionProposalApplyCreateMealResult:
    proposal: NutritionProposal
    meal: Meal

    def as_dict(self) -> dict:
        return {
            "proposal_id": self.proposal.id,
            "meal_id": self.meal.id,
            "meal_name": self.meal.name,
        }


@dataclass(frozen=True)
class NutritionProposalApplyCreateDailyPlanResult:
    proposal: NutritionProposal
    dailyplan: DailyPlan

    def as_dict(self) -> dict:
        return {
            "proposal_id": self.proposal.id,
            "dailyplan_id": self.dailyplan.id,
            "dailyplan_name": self.dailyplan.name,
        }


def _get_owned_dailyplan_for_proposal(
    *,
    user,
    dailyplan_id: int,
) -> DailyPlan:
    dailyplan = (
        DailyPlan.objects
        .filter(
            pk=dailyplan_id,
            created_by=user,
        )
        .first()
    )

    if not dailyplan:
        raise ValueError("dailyplan_not_available_for_proposal")

    return dailyplan


def _validate_initial_status(status: str) -> None:
    allowed_statuses = {
        NutritionProposal.STATUS_DRAFT,
        NutritionProposal.STATUS_PENDING_REVIEW,
    }

    if status not in allowed_statuses:
        raise ValueError("invalid_proposal_initial_status")


def _validate_source(source: str) -> None:
    allowed_sources = {
        NutritionProposal.SOURCE_MANUAL,
        NutritionProposal.SOURCE_AI,
        NutritionProposal.SOURCE_SYSTEM,
        NutritionProposal.SOURCE_MCP,
    }

    if source not in allowed_sources:
        raise ValueError("invalid_proposal_source")


def _ensure_can_review_proposal(
    *,
    user,
    proposal: NutritionProposal,
) -> None:
    if proposal.dailyplan.created_by_id != user.id:
        raise ValueError("proposal_review_not_allowed")


def _ensure_can_cancel_proposal(
    *,
    user,
    proposal: NutritionProposal,
) -> None:
    is_creator = proposal.created_by_id == user.id
    is_dailyplan_owner = proposal.dailyplan.created_by_id == user.id

    if not is_creator and not is_dailyplan_owner:
        raise ValueError("proposal_cancel_not_allowed")


def _ensure_can_delete_proposal(
    *,
    user,
    proposal: NutritionProposal,
) -> None:
    is_creator = proposal.created_by_id == user.id
    is_dailyplan_owner = proposal.dailyplan.created_by_id == user.id

    if not is_creator and not is_dailyplan_owner:
        raise ValueError("proposal_delete_not_allowed")


def _ensure_pending_review(
    proposal: NutritionProposal,
) -> None:
    if proposal.status != NutritionProposal.STATUS_PENDING_REVIEW:
        raise ValueError("proposal_is_not_pending_review")


def _ensure_not_final(
    proposal: NutritionProposal,
) -> None:
    if proposal.is_final:
        raise ValueError("proposal_is_final")


def _ensure_applicable_status(
    proposal: NutritionProposal,
) -> None:
    if proposal.status not in {
        NutritionProposal.STATUS_PENDING_REVIEW,
        NutritionProposal.STATUS_APPROVED,
    }:
        raise ValueError("proposal_is_not_applicable")


def _ensure_not_applied(
    proposal: NutritionProposal,
) -> None:
    if proposal.applied_at or proposal.applied_by_id:
        raise ValueError("proposal_already_applied")

    if proposal.status == NutritionProposal.STATUS_APPLIED:
        raise ValueError("proposal_already_applied")


def _build_current_snapshot_from_validation(
    validation_data: dict,
) -> dict:
    return {
        "dailyplan_id": validation_data["dailyplan_id"],
        "dailyplan_name": validation_data["dailyplan_name"],
        "actual": validation_data["actual"],
    }


def _create_proposal_audit_event(
    *,
    proposal: NutritionProposal,
    actor,
    action: str,
    status_before: str = "",
    status_after: str = "",
    message: str = "",
    metadata: dict | None = None,
) -> NutritionProposalAuditEvent:
    return NutritionProposalAuditEvent.objects.create(
        proposal=proposal,
        actor=actor,
        action=action,
        status_before=status_before or "",
        status_after=status_after or "",
        message=message,
        metadata=metadata or {},
    )


def _get_readable_food_for_apply(
    *,
    user,
    food_id: int,
) -> Food:
    food = (
        get_readable_food_queryset(user)
        .filter(pk=food_id)
        .first()
    )

    if not food:
        raise ValueError("proposal_apply_food_not_available")

    return food


def _create_meal_from_apply_plan(
    *,
    user,
    apply_plan,
) -> Meal:
    meal = Meal.objects.create(
        name=apply_plan.meal.name,
        created_by=user,
        is_public=False,
        is_forkable=True,
        is_copiable=False,
        is_draft=False,
        pending_dailyplan=None,
        forked_from=None,
        original_author=None,
    )

    for index, food_item in enumerate(apply_plan.meal.foods, start=1):
        food = _get_readable_food_for_apply(
            user=user,
            food_id=food_item.food_id,
        )

        MealFood.objects.create(
            meal=meal,
            food=food,
            quantity=food_item.quantity,
            order=index,
        )

    meal.refresh_from_db()

    return meal


def _parse_apply_hour(hour: str | None):
    if not hour:
        return None

    hour_part, minute_part = hour.split(":")

    return time(
        hour=int(hour_part),
        minute=int(minute_part),
    )


def _create_snapshot_meal_from_apply_meal(
    *,
    user,
    apply_meal,
) -> Meal:
    meal = Meal.objects.create(
        name=apply_meal.name,
        created_by=user,
        is_public=False,
        is_forkable=True,
        is_copiable=False,
        is_draft=False,
        pending_dailyplan=None,
        forked_from=None,
        original_author=None,
    )

    for index, food_item in enumerate(apply_meal.foods, start=1):
        food = _get_readable_food_for_apply(
            user=user,
            food_id=food_item.food_id,
        )

        MealFood.objects.create(
            meal=meal,
            food=food,
            quantity=food_item.quantity,
            order=index,
        )

    meal.refresh_from_db()

    return meal


def _normalize_dailyplan_source_from_proposal(
    proposal: NutritionProposal,
) -> str:
    source = proposal.source

    allowed_sources = {
        DailyPlan.SOURCE_MANUAL,
        DailyPlan.SOURCE_AI,
        DailyPlan.SOURCE_SYSTEM,
        DailyPlan.SOURCE_MCP,
    }

    if source in allowed_sources:
        return source

    return DailyPlan.SOURCE_AI


def _create_dailyplan_from_apply_plan(
    *,
    user,
    proposal: NutritionProposal,
    apply_plan,
) -> DailyPlan:
    dailyplan = DailyPlan.objects.create(
        name=apply_plan.dailyplan.name,
        created_by=user,
        source=_normalize_dailyplan_source_from_proposal(proposal),
        is_public=False,
        is_forkable=True,
        is_copiable=False,
        is_draft=False,
        forked_from=None,
        original_author=None,
    )

    for index, dailyplan_meal in enumerate(
        apply_plan.dailyplan.meals,
        start=1,
    ):
        snapshot_meal = _create_snapshot_meal_from_apply_meal(
            user=user,
            apply_meal=dailyplan_meal.meal,
        )

        DailyPlanMeal.objects.create(
            dailyplan=dailyplan,
            meal=snapshot_meal,
            hour=_parse_apply_hour(dailyplan_meal.hour),
            note=(dailyplan_meal.note or "").strip() or None,
            order=index,
        )

    dailyplan.refresh_from_db()

    return dailyplan


@transaction.atomic
def create_dailyplan_proposal(
    *,
    user,
    dailyplan_id: int,
    title: str,
    summary: str = "",
    source: str = NutritionProposal.SOURCE_MANUAL,
    status: str = NutritionProposal.STATUS_PENDING_REVIEW,
    targets: dict | None = None,
    current_snapshot: dict | None = None,
    proposed_payload: dict | None = None,
    validation_summary: dict | None = None,
) -> NutritionProposalCreateResult:
    clean_title = (title or "").strip()
    clean_summary = (summary or "").strip()

    if not clean_title:
        raise ValueError("proposal_title_required")

    _validate_source(source)
    _validate_initial_status(status)

    dailyplan = _get_owned_dailyplan_for_proposal(
        user=user,
        dailyplan_id=dailyplan_id,
    )

    proposal = NutritionProposal.objects.create(
        dailyplan=dailyplan,
        created_by=user,
        status=status,
        source=source,
        title=clean_title,
        summary=clean_summary,
        targets=targets or {},
        current_snapshot=current_snapshot or {},
        proposed_payload=proposed_payload or {},
        validation_summary=validation_summary or {},
    )

    _create_proposal_audit_event(
        proposal=proposal,
        actor=user,
        action=NutritionProposalAuditEvent.ACTION_CREATED,
        status_before="",
        status_after=proposal.status,
        message="Nutrition proposal created.",
        metadata={
            "source": proposal.source,
            "dailyplan_id": proposal.dailyplan_id,
        },
    )

    return NutritionProposalCreateResult(
        proposal=proposal,
    )


@transaction.atomic
def submit_proposal_for_review(
    *,
    user,
    proposal: NutritionProposal,
) -> NutritionProposalStatusResult:
    if proposal.created_by_id != user.id:
        raise ValueError("proposal_submit_not_allowed")

    if proposal.status != NutritionProposal.STATUS_DRAFT:
        raise ValueError("proposal_is_not_draft")

    status_before = proposal.status

    proposal.status = NutritionProposal.STATUS_PENDING_REVIEW
    proposal.save(
        update_fields=[
            "status",
        ]
    )

    _create_proposal_audit_event(
        proposal=proposal,
        actor=user,
        action=NutritionProposalAuditEvent.ACTION_SUBMITTED_FOR_REVIEW,
        status_before=status_before,
        status_after=proposal.status,
        message="Nutrition proposal submitted for review.",
    )

    return NutritionProposalStatusResult(
        proposal=proposal,
    )


@transaction.atomic
def cancel_proposal(
    *,
    user,
    proposal: NutritionProposal,
) -> NutritionProposalStatusResult:
    _ensure_can_cancel_proposal(
        user=user,
        proposal=proposal,
    )
    _ensure_not_final(proposal)

    status_before = proposal.status

    proposal.status = NutritionProposal.STATUS_CANCELLED
    proposal.reviewed_by = user
    proposal.reviewed_at = timezone.now()

    proposal.save(
        update_fields=[
            "status",
            "reviewed_by",
            "reviewed_at",
        ]
    )

    _create_proposal_audit_event(
        proposal=proposal,
        actor=user,
        action=NutritionProposalAuditEvent.ACTION_CANCELLED,
        status_before=status_before,
        status_after=proposal.status,
        message="Nutrition proposal cancelled.",
    )

    return NutritionProposalStatusResult(
        proposal=proposal,
    )


@transaction.atomic
def reject_proposal(
    *,
    user,
    proposal: NutritionProposal,
) -> NutritionProposalStatusResult:
    _ensure_can_review_proposal(
        user=user,
        proposal=proposal,
    )
    _ensure_pending_review(proposal)

    status_before = proposal.status

    proposal.status = NutritionProposal.STATUS_REJECTED
    proposal.reviewed_by = user
    proposal.reviewed_at = timezone.now()

    proposal.save(
        update_fields=[
            "status",
            "reviewed_by",
            "reviewed_at",
        ]
    )

    _create_proposal_audit_event(
        proposal=proposal,
        actor=user,
        action=NutritionProposalAuditEvent.ACTION_REJECTED,
        status_before=status_before,
        status_after=proposal.status,
        message="Nutrition proposal rejected.",
    )

    return NutritionProposalStatusResult(
        proposal=proposal,
    )


@transaction.atomic
def approve_proposal(
    *,
    user,
    proposal: NutritionProposal,
) -> NutritionProposalStatusResult:
    """
    Aprueba la propuesta como estado revisado.

    Importante:
    este comando todavía NO aplica cambios al DailyPlan final.
    La aplicación del proposed_payload ocurre en comandos apply explícitos.
    """
    _ensure_can_review_proposal(
        user=user,
        proposal=proposal,
    )
    _ensure_pending_review(proposal)

    status_before = proposal.status

    proposal.status = NutritionProposal.STATUS_APPROVED
    proposal.reviewed_by = user
    proposal.reviewed_at = timezone.now()

    proposal.save(
        update_fields=[
            "status",
            "reviewed_by",
            "reviewed_at",
        ]
    )

    _create_proposal_audit_event(
        proposal=proposal,
        actor=user,
        action=NutritionProposalAuditEvent.ACTION_APPROVED,
        status_before=status_before,
        status_after=proposal.status,
        message="Nutrition proposal approved.",
        metadata={
            "applies_payload": False,
        },
    )

    return NutritionProposalStatusResult(
        proposal=proposal,
    )


@transaction.atomic
def create_validated_dailyplan_proposal(
    *,
    user,
    dailyplan_id: int,
    title: str,
    summary: str = "",
    source: str = NutritionProposal.SOURCE_AI,
    status: str = NutritionProposal.STATUS_PENDING_REVIEW,
    targets: dict,
    tolerances: dict | None = None,
    proposed_payload: dict | None = None,
) -> NutritionProposalCreateResult:
    """
    Crea una propuesta nutricional con validación calculada automáticamente.

    Importante:
    este comando NO aplica cambios al DailyPlan final.
    Solo persiste una propuesta revisable con snapshot y validation_summary.
    """
    targets = targets or {}

    if not targets:
        raise ValueError("proposal_targets_required")

    validation_summary = compare_dailyplan_to_targets(
        user=user,
        dailyplan_id=dailyplan_id,
        targets=targets,
        tolerances=tolerances,
    ).as_dict()

    current_snapshot = _build_current_snapshot_from_validation(
        validation_summary,
    )

    payload = proposed_payload or {
        "intent": "adjust_dailyplan_to_targets",
        "suggested_changes": [],
    }

    return create_dailyplan_proposal(
        user=user,
        dailyplan_id=dailyplan_id,
        title=title,
        summary=summary,
        source=source,
        status=status,
        targets=targets,
        current_snapshot=current_snapshot,
        proposed_payload=payload,
        validation_summary=validation_summary,
    )


@transaction.atomic
def create_validated_meal_proposal(
    *,
    user,
    dailyplan_id: int,
    title: str,
    proposed_payload: dict,
    summary: str = "",
    source: str = NutritionProposal.SOURCE_AI,
    status: str = NutritionProposal.STATUS_PENDING_REVIEW,
    targets: dict | None = None,
) -> NutritionProposalCreateResult:
    """
    Crea una propuesta revisable para crear una Meal.

    Importante:
    - NO crea Meal real.
    - NO crea MealFood real.
    - NO modifica DailyPlan.
    - Solo persiste una NutritionProposal validada.
    """
    if not isinstance(proposed_payload, dict):
        raise ValueError("proposal_payload_must_be_object")

    parsed_payload = validate_proposal_payload_or_raise(
        proposed_payload,
    )

    if parsed_payload.intent != CREATE_MEAL_INTENT:
        raise ValueError("proposal_payload_must_be_create_meal")

    normalized_payload = parsed_payload.as_dict()

    simulation = simulate_proposal_payload(
        user=user,
        payload=normalized_payload,
    )

    current_snapshot = {
        "dailyplan_id": dailyplan_id,
        "context": "meal_proposal",
    }

    validation_summary = {
        "payload_validation": {
            "is_valid": True,
            "intent": CREATE_MEAL_INTENT,
        },
        "simulation": simulation.as_dict(),
    }

    return create_dailyplan_proposal(
        user=user,
        dailyplan_id=dailyplan_id,
        title=title,
        summary=summary,
        source=source,
        status=status,
        targets=targets or {},
        current_snapshot=current_snapshot,
        proposed_payload=normalized_payload,
        validation_summary=validation_summary,
    )


@transaction.atomic
def create_validated_dailyplan_build_proposal(
    *,
    user,
    dailyplan_id: int,
    title: str,
    proposed_payload: dict,
    summary: str = "",
    source: str = NutritionProposal.SOURCE_AI,
    status: str = NutritionProposal.STATUS_PENDING_REVIEW,
    targets: dict | None = None,
) -> NutritionProposalCreateResult:
    """
    Crea una propuesta revisable para construir un DailyPlan nuevo.

    Importante:
    - NO crea DailyPlan real.
    - NO crea Meal real.
    - NO crea MealFood real.
    - NO modifica el DailyPlan de contexto.
    - Solo persiste una NutritionProposal validada y simulada.
    """
    if not isinstance(proposed_payload, dict):
        raise ValueError("proposal_payload_must_be_object")

    parsed_payload = validate_proposal_payload_or_raise(
        proposed_payload,
    )

    if parsed_payload.intent != CREATE_DAILYPLAN_INTENT:
        raise ValueError("proposal_payload_must_be_create_dailyplan")

    normalized_payload = parsed_payload.as_dict()

    simulation = simulate_proposal_payload(
        user=user,
        payload=normalized_payload,
    )

    current_snapshot = {
        "dailyplan_id": dailyplan_id,
        "context": "dailyplan_build_proposal",
    }

    validation_summary = {
        "payload_validation": {
            "is_valid": True,
            "intent": CREATE_DAILYPLAN_INTENT,
        },
        "simulation": simulation.as_dict(),
    }

    return create_dailyplan_proposal(
        user=user,
        dailyplan_id=dailyplan_id,
        title=title,
        summary=summary,
        source=source,
        status=status,
        targets=targets or {},
        current_snapshot=current_snapshot,
        proposed_payload=normalized_payload,
        validation_summary=validation_summary,
    )


@transaction.atomic
def apply_approved_proposal(
    *,
    user,
    proposal: NutritionProposal,
) -> NutritionProposalApplyResult:
    """
    Aplica una propuesta pendiente usando applicators seguros.

    Este comando corresponde al flujo legacy de operaciones:
    adjust_dailyplan_to_targets / suggested_changes.

    Para proposals ricas nuevas se usan comandos explícitos:
    - apply_approved_create_meal_proposal
    - apply_approved_create_dailyplan_proposal
    """
    _ensure_can_review_proposal(
        user=user,
        proposal=proposal,
    )
    _ensure_applicable_status(proposal)
    _ensure_not_applied(proposal)

    status_before = proposal.status

    operations_result = validate_and_apply_proposal_operations(
        proposal,
    )

    now = timezone.now()
    proposal.status = NutritionProposal.STATUS_APPLIED
    proposal.reviewed_by = user
    proposal.reviewed_at = now
    proposal.applied_by = user
    proposal.applied_at = now

    proposal.save(
        update_fields=[
            "status",
            "reviewed_by",
            "reviewed_at",
            "applied_by",
            "applied_at",
        ]
    )

    _create_proposal_audit_event(
        proposal=proposal,
        actor=user,
        action=NutritionProposalAuditEvent.ACTION_APPLIED,
        status_before=status_before,
        status_after=proposal.status,
        message="Nutrition proposal applied.",
        metadata=operations_result.as_dict(),
    )

    return NutritionProposalApplyResult(
        proposal=proposal,
        operations_result=operations_result,
    )


@transaction.atomic
def apply_approved_create_meal_proposal(
    *,
    user,
    proposal: NutritionProposal,
) -> NutritionProposalApplyCreateMealResult:
    """
    Aplica una propuesta pendiente create_meal creando una Meal real independiente.

    Reglas:
    - Solo el dueño del DailyPlan contexto puede aplicar.
    - La propuesta debe estar pendiente o en estado legacy approved.
    - No puede aplicarse dos veces.
    - El intent debe ser create_meal.
    - Los foods deben ser legibles por el usuario.
    - NO se asocia la Meal creada a ningún DailyPlan.
    """
    _ensure_can_review_proposal(
        user=user,
        proposal=proposal,
    )
    _ensure_applicable_status(proposal)
    _ensure_not_applied(proposal)

    status_before = proposal.status

    apply_plan = build_create_meal_apply_plan(
        proposal=proposal,
    )

    meal = _create_meal_from_apply_plan(
        user=user,
        apply_plan=apply_plan,
    )

    now = timezone.now()
    proposal.status = NutritionProposal.STATUS_APPLIED
    proposal.reviewed_by = user
    proposal.reviewed_at = now
    proposal.applied_by = user
    proposal.applied_at = now

    proposal.save(
        update_fields=[
            "status",
            "reviewed_by",
            "reviewed_at",
            "applied_by",
            "applied_at",
        ]
    )

    _create_proposal_audit_event(
        proposal=proposal,
        actor=user,
        action=NutritionProposalAuditEvent.ACTION_APPLIED,
        status_before=status_before,
        status_after=proposal.status,
        message="Create meal proposal applied.",
        metadata={
            "intent": CREATE_MEAL_INTENT,
            "meal_id": meal.id,
            "meal_name": meal.name,
            "foods": [
                {
                    "food_id": meal_food.food_id,
                    "food_name": meal_food.food.name,
                    "quantity": float(meal_food.quantity),
                    "unit": "g",
                    "order": meal_food.order,
                }
                for meal_food in (
                    meal.meal_food_set
                    .select_related("food")
                    .all()
                )
            ],
        },
    )

    return NutritionProposalApplyCreateMealResult(
        proposal=proposal,
        meal=meal,
    )


@transaction.atomic
def apply_approved_create_dailyplan_proposal(
    *,
    user,
    proposal: NutritionProposal,
) -> NutritionProposalApplyCreateDailyPlanResult:
    """
    Aplica una propuesta pendiente create_dailyplan creando un DailyPlan real.

    Reglas:
    - Solo el dueño del DailyPlan contexto puede aplicar.
    - La propuesta debe estar pendiente o en estado legacy approved.
    - No puede aplicarse dos veces.
    - El intent debe ser create_dailyplan.
    - Los foods deben ser legibles por el usuario.
    - Se crea un DailyPlan final independiente.
    - Se crean Meals snapshot para las DailyPlanMeal.
    - NO se crean Meals reutilizables de librería.
    - NO se modifica el DailyPlan contexto.
    """
    _ensure_can_review_proposal(
        user=user,
        proposal=proposal,
    )
    _ensure_applicable_status(proposal)
    _ensure_not_applied(proposal)

    status_before = proposal.status

    apply_plan = build_create_dailyplan_apply_plan(
        proposal=proposal,
    )

    dailyplan = _create_dailyplan_from_apply_plan(
        user=user,
        proposal=proposal,
        apply_plan=apply_plan,
    )

    now = timezone.now()
    proposal.status = NutritionProposal.STATUS_APPLIED
    proposal.reviewed_by = user
    proposal.reviewed_at = now
    proposal.applied_by = user
    proposal.applied_at = now

    proposal.save(
        update_fields=[
            "status",
            "reviewed_by",
            "reviewed_at",
            "applied_by",
            "applied_at",
        ]
    )

    _create_proposal_audit_event(
        proposal=proposal,
        actor=user,
        action=NutritionProposalAuditEvent.ACTION_APPLIED,
        status_before=status_before,
        status_after=proposal.status,
        message="Create dailyplan proposal applied.",
        metadata={
            "intent": CREATE_DAILYPLAN_INTENT,
            "dailyplan_id": dailyplan.id,
            "dailyplan_name": dailyplan.name,
            "source": dailyplan.source,
            "meals": [
                {
                    "dailyplan_meal_id": dailyplan_meal.id,
                    "meal_id": dailyplan_meal.meal_id,
                    "meal_name": dailyplan_meal.meal.name,
                    "hour": (
                        dailyplan_meal.hour.strftime("%H:%M")
                        if dailyplan_meal.hour
                        else None
                    ),
                    "note": dailyplan_meal.note or "",
                    "order": dailyplan_meal.order,
                }
                for dailyplan_meal in (
                    dailyplan.dailyplan_meals
                    .select_related("meal")
                    .all()
                )
            ],
        },
    )

    return NutritionProposalApplyCreateDailyPlanResult(
        proposal=proposal,
        dailyplan=dailyplan,
    )

@transaction.atomic
def delete_proposal(
    *,
    user,
    proposal: NutritionProposal,
) -> None:
    _ensure_can_delete_proposal(
        user=user,
        proposal=proposal,
    )

    proposal.delete()
