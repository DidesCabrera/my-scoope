"""Bounded inspection of persisted program evidence, without exposing other clients."""

from notas.application.ai_tools.runtime import run_ai_tool
from notas.domain.models import NutritionProposal


def revise_culinary_program_tool(user, *, proposal_id, week_numbers, meal_numbers, avoid_food_ids=()):
    def execute():
        from notas.application.ai_intake.culinary_program import revise_culinary_program
        from notas.application.ai_intake.program_generator import program_proposal_tool_summary
        proposal = revise_culinary_program(user=user, proposal_id=proposal_id, week_numbers=week_numbers,
                                          meal_numbers=meal_numbers, avoid_food_ids=avoid_food_ids)
        return {"proposal": program_proposal_tool_summary(proposal), "revision": proposal.current_snapshot["revision"]}
    return run_ai_tool(execute, user=user)


def inspect_program_proposal(user, proposal_id, *, week_number=None, day_number=None):
    proposal = NutritionProposal.objects.filter(pk=proposal_id, created_by=user).first()
    if proposal is None:
        raise ValueError("proposal_not_allowed")
    program = proposal.proposed_payload.get("program")
    if not isinstance(program, dict):
        raise ValueError("program_proposal_required")
    for key, value, maximum in (("week", week_number, program["duration_weeks"]), ("day", day_number, 7)):
        if value is not None and (type(value) is not int or not 1 <= value <= maximum):
            raise ValueError(f"program_inspection_{key}_invalid")
    if day_number is not None and week_number is None:
        raise ValueError("program_inspection_week_required")
    from notas.application.ai_intake.program_generator import program_proposal_tool_summary
    result = program_proposal_tool_summary(proposal)
    if week_number is not None:
        simulation = proposal.validation_summary.get("simulation", {}).get("program", {})
        result["days"] = [day for day in simulation.get("days", []) if day["week_number"] == week_number
                          and (day_number is None or day["day_number"] == day_number)]
        result["requirement_evidence"] = [day for day in proposal.validation_summary.get("requirements", {}).get("days", [])
            if day["week"] == week_number and (day_number is None or day["day"] == day_number)]
    else:
        result["inspection_hint"] = "Request week_number (and optional day_number) for food quantities and requirement evidence."
    return {"proposal": result}
