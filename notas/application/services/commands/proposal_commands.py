from dataclasses import dataclass
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
from notas.application.proposals.operations import (
    OPERATION_UPDATE_MEAL_FOOD_QUANTITY,
)
from notas.application.services.commands.proposal_apply_helpers import (
    build_applied_create_dailyplan_metadata,
    build_applied_create_meal_metadata,
    create_dailyplan_from_apply_plan,
    create_meal_from_apply_plan,
)
from notas.application.queries.proposal_simulation_queries import (
    simulate_proposal_payload,
)
from notas.application.queries.validation_queries import (
    compare_dailyplan_to_targets,
)
from notas.application.validation.proposal_payload_validators import (
    validate_proposal_payload_or_raise,
)
from notas.domain.models import (
    DailyPlan,
    Meal,
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
    is_creator = proposal.created_by_id == user.id
    is_dailyplan_owner = (
        proposal.dailyplan_id
        and proposal.dailyplan
        and proposal.dailyplan.created_by_id == user.id
    )

    if not is_creator and not is_dailyplan_owner:
        raise ValueError("proposal_review_not_allowed")


def _ensure_can_cancel_proposal(
    *,
    user,
    proposal: NutritionProposal,
) -> None:
    is_creator = proposal.created_by_id == user.id
    is_dailyplan_owner = (
        proposal.dailyplan_id
        and proposal.dailyplan
        and proposal.dailyplan.created_by_id == user.id
    )

    if not is_creator and not is_dailyplan_owner:
        raise ValueError("proposal_cancel_not_allowed")


def _ensure_can_delete_proposal(
    *,
    user,
    proposal: NutritionProposal,
) -> None:
    is_creator = proposal.created_by_id == user.id
    is_dailyplan_owner = (
        proposal.dailyplan_id
        and proposal.dailyplan
        and proposal.dailyplan.created_by_id == user.id
    )

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
    if proposal.status != NutritionProposal.STATUS_APPROVED:
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
def create_proportional_dailyplan_calorie_proposal(
    *,
    user,
    dailyplan_id: int,
    calorie_delta: float,
    title: str = "",
    summary: str = "",
    source: str = NutritionProposal.SOURCE_AI,
) -> NutritionProposalCreateResult:
    """Prepare a reviewable same-food calorie adjustment for an owned plan.

    Every Meal attached to a DailyPlan is an independent snapshot. Scaling its
    MealFood quantities therefore changes only this plan when the approved
    proposal is later applied; reusable Meals in the library stay untouched.
    """

    dailyplan = (
        DailyPlan.objects
        .filter(pk=dailyplan_id, created_by=user)
        .prefetch_related("dailyplan_meals__meal__meal_food_set__food")
        .first()
    )
    if dailyplan is None:
        raise ValueError("dailyplan_not_available_for_proposal")

    try:
        delta = float(calorie_delta)
    except (TypeError, ValueError) as exc:
        raise ValueError("calorie_delta_invalid") from exc
    if abs(delta) < 0.0001:
        raise ValueError("calorie_delta_must_not_be_zero")

    current_total = float(dailyplan.total_kcal or 0)
    target_total = current_total + delta
    if current_total <= 0:
        raise ValueError("dailyplan_has_no_scalable_calories")
    if target_total <= 0:
        raise ValueError("dailyplan_target_calories_must_be_positive")

    scale_factor = target_total / current_total
    meal_foods_by_id = {}
    for dailyplan_meal in dailyplan.dailyplan_meals.all():
        for meal_food in dailyplan_meal.meal.meal_food_set.all():
            meal_foods_by_id[meal_food.id] = meal_food
    if not meal_foods_by_id:
        raise ValueError("dailyplan_has_no_scalable_foods")

    suggested_changes = []
    for meal_food in meal_foods_by_id.values():
        from_quantity = float(meal_food.quantity)
        to_quantity = round(from_quantity * scale_factor, 4)
        if to_quantity <= 0 or abs(to_quantity - from_quantity) < 0.0001:
            continue
        suggested_changes.append(
            {
                "type": OPERATION_UPDATE_MEAL_FOOD_QUANTITY,
                "mealfood_id": meal_food.id,
                "from_quantity": from_quantity,
                "to_quantity": to_quantity,
            }
        )
    if not suggested_changes:
        raise ValueError("dailyplan_calorie_adjustment_has_no_changes")

    payload = {
        "intent": "adjust_dailyplan_to_targets",
        "strategy": "proportional_quantity_scaling",
        "preserve_foods": True,
        "preserve_meal_structure": True,
        "calorie_delta": delta,
        "scale_factor": scale_factor,
        "current_total_kcal": current_total,
        "target_total_kcal": target_total,
        "suggested_changes": suggested_changes,
    }
    return create_validated_dailyplan_proposal(
        user=user,
        dailyplan_id=dailyplan.id,
        title=title.strip() or f"Ajustar {dailyplan.name} en {delta:+g} kcal",
        summary=summary.strip() or (
            "Mantiene los mismos alimentos y comidas; solo escala sus cantidades "
            f"proporcionalmente para pasar de {current_total:.1f} a {target_total:.1f} kcal."
        ),
        source=source,
        targets={"total_kcal": target_total},
        tolerances={"total_kcal": 1.0},
        proposed_payload=payload,
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
    Aplica una propuesta aprobada create_meal creando una Meal real independiente.

    Reglas:
    - Solo el dueño del DailyPlan contexto puede aplicar.
    - La propuesta debe estar aprobada.
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

    meal = create_meal_from_apply_plan(
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
        metadata=build_applied_create_meal_metadata(
            meal=meal,
            intent=CREATE_MEAL_INTENT,
        ),
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
    Aplica una propuesta aprobada create_dailyplan creando un DailyPlan real.

    Reglas:
    - Solo el dueño del DailyPlan contexto puede aplicar.
    - La propuesta debe estar aprobada.
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

    dailyplan = create_dailyplan_from_apply_plan(
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
        metadata=build_applied_create_dailyplan_metadata(
            dailyplan=dailyplan,
            intent=CREATE_DAILYPLAN_INTENT,
        ),
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
