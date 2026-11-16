"""Reviewable, owner-scoped calendar commands for dated plans and commitments."""

from datetime import date, time, timedelta
from uuid import uuid4

from notas.application.services.calendarization.scheduling import local_date_for_timezone
from notas.application.services.commands.calendar_commitment_commands import (
    delete_calendar_commitment,
    register_calendar_commitments,
    update_calendar_commitment,
)
from notas.application.services.commands.calendar_day_commands import (
    assign_dailyplan_to_calendar_date,
    move_calendar_date_plan,
    remove_calendar_date_plan,
)
from notas.domain.models import CalendarCommitment, CalendarizedDay, DailyPlan, Program, ProgramCalendarization


def _date(value):
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("calendar_date_invalid") from exc


def _hour(value):
    try:
        return time.fromisoformat(value) if value else None
    except (TypeError, ValueError) as exc:
        raise ValueError("calendar_hour_invalid") from exc


def validate_calendar_patch(user, key, arguments):
    today = local_date_for_timezone(user.profile.timezone_name or "UTC")
    if key == "program_projection.project":
        from notas.application.services.calendarization.scheduling import validate_timezone_name
        timezone_name = validate_timezone_name(arguments["timezone_name"])
        if _date(arguments["start_date"]) < local_date_for_timezone(timezone_name):
            raise ValueError("calendarization_start_date_past")
        if not Program.objects.filter(pk=arguments["program_id"], created_by=user).exists():
            raise ValueError("calendarization_program_not_owned")
    if key == "calendar_day.assign_plan":
        if not DailyPlan.objects.exclude(source=DailyPlan.SOURCE_PROGRAM).filter(
            pk=arguments["dailyplan_id"], created_by=user,
        ).exists():
            raise ValueError("calendar_dailyplan_not_owned")
    if key == "calendar_commitment.create":
        if arguments["kind"] not in {kind for kind, _ in CalendarCommitment.KIND_CHOICES}:
            raise ValueError("calendar_commitment_kind_invalid")
        dates = arguments["dates"]
        if not isinstance(dates, list) or not 1 <= len(dates) <= 62 or len(set(dates)) != len(dates):
            raise ValueError("calendar_commitment_dates_invalid")
        for value in dates:
            if _date(value) < today:
                raise ValueError("calendar_commitment_date_in_past")
    if key in {"calendar_day.assign_plan", "calendar_day.move_plan", "calendar_commitment.update"}:
        value = arguments.get("date")
        if value and _date(value) < today:
            raise ValueError("calendar_date_in_past")
    if "hour" in arguments:
        _hour(arguments["hour"])
    if key.startswith("calendar_day.") and key != "calendar_day.remove_plan":
        arguments.setdefault("assignment_key", f"ai-calendar-{uuid4().hex}")


def preview_calendar_patch(user, key, arguments, target, before, after):
    if key == "program_projection.project":
        from notas.application.services.commands.calendarization_commands import calendarization_empty_dates
        program = Program.objects.get(pk=arguments["program_id"], created_by=user)
        first = _date(arguments["start_date"])
        last = first + timedelta(days=program.duration_days - 1)
        after["program_name"] = program.name
        after["end_date"] = last.isoformat()
        after["empty_dates"] = [x.isoformat() for x in calendarization_empty_dates(program=program, start_date=first)]
        after["occupied_dates"] = [x.isoformat() for x in CalendarizedDay.objects.filter(
            user=user, calendar_date__range=(first, last), assignment_state=CalendarizedDay.STATE_CURRENT,
        ).values_list("calendar_date", flat=True)]
        current = ProgramCalendarization.objects.filter(
            user=user, status__in=ProgramCalendarization.CURRENT_STATUSES,
        ).first()
        after["current_projection_id"] = current.id if current else None
        after["will_replace_current"] = bool(current and arguments.get("replace_current"))
        after["timezone_name"] = arguments["timezone_name"]
        after["notification_defaults"] = {"daily_enabled": True, "daily_hour": "07:00", "meal_enabled": False}
    elif key == "calendar_day.assign_plan":
        current = CalendarizedDay.objects.filter(
            user=user, calendar_date=_date(arguments["date"]),
            assignment_state=CalendarizedDay.STATE_CURRENT,
        ).first()
        after["existing_day"] = {
            "id": current.id, "source_kind": current.source_kind,
            "plan_name": (current.plan_snapshot or {}).get("name", ""),
            "has_execution": current.meal_execution_events.exists(),
        } if current else None
        after["source_plan_name"] = DailyPlan.objects.get(pk=arguments["dailyplan_id"]).name
        after["will_replace_existing"] = bool(current and arguments.get("replace_existing"))
    elif key == "calendar_commitment.create":
        after["existing_dates"] = list(CalendarCommitment.objects.filter(
            user=user, kind=arguments["kind"], calendar_date__in=[_date(x) for x in arguments["dates"]],
        ).values_list("calendar_date", flat=True))
        after["existing_dates"] = [x.isoformat() for x in after["existing_dates"]]
        after["food_snapshot_recalculated_at_commit"] = bool(arguments.get("food_period_start"))
    elif key == "calendar_day.move_plan":
        after["source_date"] = target.calendar_date.isoformat()
        after["target_date"] = arguments["date"]
        occupant = CalendarizedDay.objects.filter(
            user=user, calendar_date=_date(arguments["date"]),
            assignment_state=CalendarizedDay.STATE_CURRENT,
        ).first()
        after["target_existing_day_id"] = occupant.id if occupant else None
        after["will_replace_existing"] = bool(occupant and arguments.get("replace_existing"))
    elif key == "calendar_commitment.update":
        after.update({field: arguments[field] for field in ("date", "note", "hour", "food_period_start", "food_period_end") if field in arguments})
        after["food_snapshot_recalculated_at_commit"] = "food_period_start" in arguments or "food_period_end" in arguments
    return after


def calendar_target_snapshot(target):
    if isinstance(target, CalendarizedDay):
        return {
            "id": target.id, "date": target.calendar_date.isoformat(),
            "source_kind": target.source_kind, "snapshot_hash": target.snapshot_hash,
            "has_execution": target.meal_execution_events.exists(),
        }
    return {
        "id": target.id, "date": target.calendar_date.isoformat(),
        "kind": target.kind, "hour": target.hour.isoformat() if target.hour else None,
        "note": target.note, "food_period_start": str(target.food_period_start) if target.food_period_start else None,
        "food_period_end": str(target.food_period_end) if target.food_period_end else None,
    }


def commit_calendar_patch(user, key, target, arguments):
    validate_calendar_patch(user, key, arguments)
    if key == "program_projection.project":
        from notas.application.services.commands.calendarization_commands import activate_program_calendarization
        result = activate_program_calendarization(
            user=user, program=Program.objects.get(pk=arguments["program_id"], created_by=user),
            start_date=_date(arguments["start_date"]), timezone_name=arguments["timezone_name"],
            confirm_incomplete=bool(arguments.get("confirm_incomplete")),
            replace_current=bool(arguments.get("replace_current")),
        )
        return {"program_projection_id": result.calendarization.id, "start_date": arguments["start_date"]}
    if key == "calendar_day.assign_plan":
        day = assign_dailyplan_to_calendar_date(
            user=user, dailyplan_id=int(arguments["dailyplan_id"]), local_date=_date(arguments["date"]),
            assignment_key=arguments["assignment_key"], replace_existing=bool(arguments.get("replace_existing")),
        )
        return {"calendar_day_id": day.id, "date": day.calendar_date.isoformat()}
    if key == "calendar_day.remove_plan":
        day = remove_calendar_date_plan(user=user, local_date=target.calendar_date)
        return {"calendar_day_id": day.id, "date": day.calendar_date.isoformat()}
    if key == "calendar_day.move_plan":
        day = move_calendar_date_plan(
            user=user, source_date=target.calendar_date, target_date=_date(arguments["date"]),
            assignment_key=arguments["assignment_key"], replace_existing=bool(arguments.get("replace_existing")),
        )
        return {"calendar_day_id": day.id, "date": day.calendar_date.isoformat()}
    if key == "calendar_commitment.create":
        rows = register_calendar_commitments(
            user=user, kind=arguments["kind"], dates=[_date(x) for x in arguments["dates"]],
            note=arguments.get("note", ""),
            food_period_start=_date(arguments["food_period_start"]) if arguments.get("food_period_start") else None,
            food_period_end=_date(arguments["food_period_end"]) if arguments.get("food_period_end") else None,
        )
        return {"calendar_commitment_ids": [x.id for x in rows]}
    if key == "calendar_commitment.update":
        row = update_calendar_commitment(
            user=user, commitment_id=target.id, note=arguments.get("note"),
            hour=_hour(arguments.get("hour")),
            calendar_date=_date(arguments["date"]) if arguments.get("date") else None,
            update_food_period="food_period_start" in arguments or "food_period_end" in arguments,
            food_period_start=_date(arguments["food_period_start"]) if arguments.get("food_period_start") else None,
            food_period_end=_date(arguments["food_period_end"]) if arguments.get("food_period_end") else None,
        )
        return {"calendar_commitment_id": row.id}
    deleted_id = delete_calendar_commitment(user=user, commitment_id=target.id)
    return {"calendar_commitment_id": deleted_id}
