from __future__ import annotations

from dataclasses import dataclass

from django.db import transaction
from django.db.models import F

from notas.application.services.commands.dailyplan_commands import clone_dailyplan_meals
from notas.domain.models import DailyPlan, Program, ProgramDay


@dataclass(frozen=True)
class ProgramCreateResult:
    program: Program


@dataclass(frozen=True)
class ProgramDayAssignResult:
    program: Program
    program_day: ProgramDay
    dailyplan: DailyPlan
    replaced_dailyplan_id: int | None = None


@dataclass(frozen=True)
class ProgramDayRemoveResult:
    program: Program
    program_day_id: int
    dailyplan_id: int | None = None


@dataclass(frozen=True)
class ProgramWeekRemoveResult:
    program: Program
    removed_week_number: int
    removed_dailyplan_ids: tuple[int, ...] = ()


def normalize_duration_weeks(raw_value) -> int:
    try:
        value = int(raw_value)
    except (TypeError, ValueError):
        raise ValueError("program_duration_weeks_invalid")

    if value < Program.MIN_DURATION_WEEKS:
        raise ValueError("program_duration_weeks_invalid")

    return value


def validate_program_slot(*, program: Program, week_number, day_number) -> tuple[int, int]:
    try:
        week = int(week_number)
        day = int(day_number)
    except (TypeError, ValueError):
        raise ValueError("program_slot_invalid")

    if week < 1 or week > program.normalized_duration_weeks:
        raise ValueError("program_week_out_of_range")

    if day < 1 or day > 7:
        raise ValueError("program_day_out_of_range")

    return week, day


def get_program_origin(program: Program) -> Program:
    return program.forked_from or program


def _safe_delete_program_dailyplan_snapshot(dailyplan: DailyPlan | None) -> None:
    if not dailyplan:
        return

    if dailyplan.source != DailyPlan.SOURCE_PROGRAM:
        return

    if dailyplan.program_slots.exists():
        return

    dailyplan.delete()


def clone_dailyplan_for_program(source: DailyPlan, user) -> DailyPlan:
    """
    Crea un snapshot completo del DailyPlan para usarlo dentro de un programa.
    No queda como elemento normal de la librería porque source='program'.
    """
    origin = source.forked_from or source

    clone = DailyPlan.objects.create(
        name=source.name,
        source=DailyPlan.SOURCE_PROGRAM,
        created_by=user,
        forked_from=origin,
        original_author=origin.created_by,
        is_public=False,
        is_forkable=True,
        is_copiable=False,
        is_draft=False,
    )

    clone_dailyplan_meals(source, clone)

    return clone


@transaction.atomic
def create_weekly_program(*, user, name: str, duration_weeks=None) -> ProgramCreateResult:
    clean_name = (name or "").strip()
    weeks = normalize_duration_weeks(duration_weeks or Program.DEFAULT_DURATION_WEEKS)

    if not clean_name:
        raise ValueError("program_name_required")

    program = Program.objects.create(
        name=clean_name,
        created_by=user,
        duration_weeks=weeks,
        is_draft=True,
    )

    return ProgramCreateResult(program=program)


@transaction.atomic
def add_week_to_program(*, program: Program) -> Program:
    program.duration_weeks = program.normalized_duration_weeks + 1

    if program.is_draft and program.program_dailyplan.exists():
        program.is_draft = False

    program.save(update_fields=["duration_weeks", "is_draft"])
    return program


@transaction.atomic
def remove_week_from_program(*, program: Program, week_number) -> ProgramWeekRemoveResult:
    week, _ = validate_program_slot(
        program=program,
        week_number=week_number,
        day_number=1,
    )

    if program.normalized_duration_weeks <= Program.MIN_DURATION_WEEKS:
        raise ValueError("program_cannot_remove_last_week")

    week_slots = list(
        ProgramDay.objects
        .select_related("dailyplan")
        .filter(program=program, week_number=week)
    )
    dailyplan_snapshots = [slot.dailyplan for slot in week_slots if slot.dailyplan_id]
    removed_dailyplan_ids = tuple(dailyplan.id for dailyplan in dailyplan_snapshots)

    ProgramDay.objects.filter(program=program, week_number=week).delete()

    shifted_slots = ProgramDay.objects.filter(program=program, week_number__gt=week)
    shifted_slots.update(week_number=F("week_number") + 1000)
    ProgramDay.objects.filter(program=program, week_number__gt=1000).update(
        week_number=F("week_number") - 1001
    )

    program.duration_weeks = max(
        program.normalized_duration_weeks - 1,
        Program.MIN_DURATION_WEEKS,
    )

    if program.is_draft and program.program_dailyplan.exists():
        program.is_draft = False

    program.save(update_fields=["duration_weeks", "is_draft"])

    for dailyplan in dailyplan_snapshots:
        _safe_delete_program_dailyplan_snapshot(dailyplan)

    return ProgramWeekRemoveResult(
        program=program,
        removed_week_number=week,
        removed_dailyplan_ids=removed_dailyplan_ids,
    )


@transaction.atomic
def assign_dailyplan_to_program_slot(
    *,
    program: Program,
    source_dailyplan: DailyPlan,
    user,
    week_number,
    day_number,
) -> ProgramDayAssignResult:
    week, day = validate_program_slot(
        program=program,
        week_number=week_number,
        day_number=day_number,
    )

    existing = (
        ProgramDay.objects
        .select_related("dailyplan")
        .filter(program=program, week_number=week, day_number=day)
        .first()
    )

    cloned_dailyplan = clone_dailyplan_for_program(source_dailyplan, user)
    replaced_dailyplan = None

    if existing:
        replaced_dailyplan = existing.dailyplan
        existing.dailyplan = cloned_dailyplan
        existing.save(update_fields=["dailyplan"])
        program_day = existing
    else:
        program_day = ProgramDay.objects.create(
            program=program,
            dailyplan=cloned_dailyplan,
            week_number=week,
            day_number=day,
        )

    if replaced_dailyplan:
        _safe_delete_program_dailyplan_snapshot(replaced_dailyplan)

    return ProgramDayAssignResult(
        program=program,
        program_day=program_day,
        dailyplan=cloned_dailyplan,
        replaced_dailyplan_id=replaced_dailyplan.id if replaced_dailyplan else None,
    )


@transaction.atomic
def remove_program_day(*, program_day: ProgramDay) -> ProgramDayRemoveResult:
    program = program_day.program
    dailyplan = program_day.dailyplan
    program_day_id = program_day.id
    dailyplan_id = dailyplan.id if dailyplan else None

    program_day.delete()
    _safe_delete_program_dailyplan_snapshot(dailyplan)

    return ProgramDayRemoveResult(
        program=program,
        program_day_id=program_day_id,
        dailyplan_id=dailyplan_id,
    )


@transaction.atomic
def delete_program(*, program: Program) -> int:
    program_id = program.id
    program_days = list(program.program_dailyplan.select_related("dailyplan"))
    dailyplan_snapshots = [program_day.dailyplan for program_day in program_days]

    program.delete()

    for dailyplan in dailyplan_snapshots:
        _safe_delete_program_dailyplan_snapshot(dailyplan)

    return program_id


@transaction.atomic
def fork_program(original: Program, user) -> Program:
    origin = get_program_origin(original)

    forked = Program.objects.create(
        name=f"{original.name}",
        created_by=user,
        original_author=origin.created_by,
        forked_from=origin,
        duration_weeks=original.normalized_duration_weeks,
        is_public=False,
        is_forkable=True,
        is_copiable=False,
        is_draft=False,
    )

    for program_day in original.program_dailyplan.select_related("dailyplan"):
        cloned_dailyplan = clone_dailyplan_for_program(program_day.dailyplan, user)
        ProgramDay.objects.create(
            program=forked,
            dailyplan=cloned_dailyplan,
            week_number=program_day.week_number,
            day_number=program_day.day_number,
        )

    return forked


@transaction.atomic
def copy_program(original: Program, user) -> Program:
    copied = Program.objects.create(
        name=f"{original.name} (copy)",
        created_by=user,
        duration_weeks=original.normalized_duration_weeks,
        is_public=False,
        is_forkable=True,
        is_copiable=False,
        is_draft=False,
    )

    for program_day in original.program_dailyplan.select_related("dailyplan"):
        cloned_dailyplan = clone_dailyplan_for_program(program_day.dailyplan, user)
        ProgramDay.objects.create(
            program=copied,
            dailyplan=cloned_dailyplan,
            week_number=program_day.week_number,
            day_number=program_day.day_number,
        )

    return copied
