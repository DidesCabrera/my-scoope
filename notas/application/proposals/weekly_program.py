"""Transactional application of reviewed programs; independent of chat/AI."""

from dataclasses import dataclass

from django.db import transaction
from django.utils import timezone

from notas.application.dto.program_proposal import parse_program_payload
from notas.application.dto.proposal_apply import build_create_dailyplan_apply_plan
from notas.application.queries.proposal_simulation_queries import simulate_proposal_payload
from notas.application.services.cache.program_summary import refresh_program_summary_cache
from notas.application.services.commands.program_commands import create_weekly_program
from notas.application.services.commands.proposal_apply_helpers import create_dailyplan_from_apply_plan
from notas.domain.models import DailyPlan, Food, NutritionProposal, NutritionProposalAuditEvent, ProgramDay


@dataclass(frozen=True)
class AppliedProgramResult:
    proposal: NutritionProposal
    program: object

    def as_dict(self):
        return {"proposal_id": self.proposal.pk, "program_id": self.program.pk, "status": self.proposal.status}


@transaction.atomic
def apply_approved_program_proposal(*, user, proposal):
    stored = NutritionProposal.objects.select_for_update().filter(pk=proposal.pk, created_by=user).first()
    if stored is None:
        raise ValueError("proposal_not_allowed")
    if stored.status != NutritionProposal.STATUS_APPROVED or stored.applied_at:
        raise ValueError("proposal_apply_requires_applicable_status")
    parsed = parse_program_payload(stored.proposed_payload)
    food_ids = {food.food_id for day in parsed.days for meal in day.dailyplan.meals for food in meal.meal.foods}
    # Lock ingredients until commit, then recheck the exact evidence the user approved.
    foods = list(Food.objects.select_for_update().filter(pk__in=food_ids).order_by("pk"))
    if len(foods) != len(food_ids) or any(not food.is_active for food in foods):
        raise ValueError("proposal_apply_food_not_available")
    current = simulate_proposal_payload(user, stored.proposed_payload).as_dict()
    if current != stored.validation_summary.get("simulation"):
        raise ValueError("program_proposal_changed_since_review")
    if "program_specification" in stored.targets:
        from notas.application.services.nutrition.culinary_validation import revalidate_culinary_proposal
        revalidate_culinary_proposal(user=user, proposal=stored)
    program = create_weekly_program(user=user, name=parsed.name, duration_weeks=parsed.duration_weeks).program
    if "program_specification" in stored.targets:
        program.nutrition_specification = stored.targets["program_specification"]
        program.culinary_provenance = {"catalog": stored.current_snapshot["culinary_catalog"],
                                      "weeks": stored.current_snapshot["culinary_weeks"]}
        program.save(update_fields=["nutrition_specification", "culinary_provenance"])
    for day in parsed.days:
        adapter = NutritionProposal(pk=stored.pk, status=NutritionProposal.STATUS_APPROVED,
            proposed_payload={"intent": "create_dailyplan", "dailyplan": day.dailyplan.as_dict()})
        plan = create_dailyplan_from_apply_plan(user=user, proposal=stored,
            apply_plan=build_create_dailyplan_apply_plan(proposal=adapter))
        plan.source = DailyPlan.SOURCE_PROGRAM
        plan.save(update_fields=["source"])
        ProgramDay.objects.create(program=program, dailyplan=plan, week_number=day.week_number, day_number=day.day_number)
    program.is_draft = False
    program.save(update_fields=["is_draft"])
    refresh_program_summary_cache(program)
    stored.status = NutritionProposal.STATUS_APPLIED
    stored.applied_by = user
    stored.applied_at = timezone.now()
    stored.save(update_fields=["status", "applied_by", "applied_at"])
    NutritionProposalAuditEvent.objects.create(proposal=stored, actor=user,
        action=NutritionProposalAuditEvent.ACTION_APPLIED, status_before=NutritionProposal.STATUS_APPROVED,
        status_after=stored.status, message="Programa aplicado con planes diarios independientes.",
        metadata={"intent": "create_program", "program_id": program.pk, "program_name": program.name})
    return AppliedProgramResult(stored, program)
