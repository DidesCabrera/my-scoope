"""Programs contain every slot of one to eight complete weeks."""

from dataclasses import dataclass

from notas.application.dto.meal_plan_payloads import ProposedDailyPlanDTO, parse_proposed_dailyplan_payload


@dataclass(frozen=True)
class ProposedProgramDay:
    week_number: int
    day_number: int
    dailyplan: ProposedDailyPlanDTO

    def as_dict(self):
        return {"week_number": self.week_number, "day_number": self.day_number, "dailyplan": self.dailyplan.as_dict()}


@dataclass(frozen=True)
class ProposedProgramPayload:
    name: str
    duration_weeks: int
    days: tuple[ProposedProgramDay, ...]
    intent: str = "create_program"

    def as_dict(self):
        return {"intent": self.intent, "program": {"name": self.name, "duration_weeks": self.duration_weeks,
                "days": [day.as_dict() for day in self.days]}}


def parse_program_payload(payload):
    if not isinstance(payload, dict):
        raise ValueError("program_proposal_invalid")
    program = payload.get("program")
    if payload.get("intent") != "create_program" or not isinstance(program, dict):
        raise ValueError("program_proposal_invalid")
    name = program.get("name")
    if not isinstance(name, str) or not name.strip() or len(name.strip()) > 100:
        raise ValueError("program_proposal_name_required")
    duration = program.get("duration_weeks")
    if type(duration) is not int or not 1 <= duration <= 8:
        raise ValueError("program_proposal_duration_must_be_1_to_8")
    days = program.get("days")
    if not isinstance(days, list) or len(days) != 7 * duration:
        raise ValueError("program_proposal_requires_complete_weeks")
    parsed = []
    for day in days:
        if not isinstance(day, dict) or type(day.get("day_number")) is not int or type(day.get("week_number")) is not int:
            raise ValueError("program_proposal_day_invalid")
        plan = parse_proposed_dailyplan_payload({"intent": "create_dailyplan", "dailyplan": day.get("dailyplan")})
        parsed.append(ProposedProgramDay(day["week_number"], day["day_number"], plan.dailyplan))
    if {(day.week_number, day.day_number) for day in parsed} != {(week, day) for week in range(1, duration + 1) for day in range(1, 8)}:
        raise ValueError("program_proposal_days_must_be_unique_and_complete")
    return ProposedProgramPayload(name.strip(), duration, tuple(sorted(parsed, key=lambda day: (day.week_number, day.day_number))))
