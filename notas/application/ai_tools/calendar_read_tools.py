"""Calendar reads use dated assignments, never a Program template as the agenda."""

from datetime import date, timedelta

from notas.application.ai_tools.runtime import run_ai_tool
from notas.application.services.calendarization.scheduling import local_date_for_timezone
from notas.domain.models import CalendarCommitment, CalendarizedDay


def query_calendar_tool(user, *, resource, date_from=None, date_to=None, kind=None, limit=20, offset=0):
    return run_ai_tool(
        _query_calendar, user, resource=resource, date_from=date_from,
        date_to=date_to, kind=kind, limit=limit, offset=offset, user=user,
    )


def _date(value, default):
    try:
        return date.fromisoformat(value) if value else default
    except (TypeError, ValueError) as exc:
        raise ValueError("calendar_date_invalid") from exc


def _query_calendar(user, *, resource, date_from, date_to, kind, limit, offset):
    today = local_date_for_timezone(user.profile.timezone_name or "UTC")
    first = _date(date_from, today)
    last = _date(date_to, first if resource == "calendar_day" else first + timedelta(days=27))
    if last < first or (last - first).days > 41 or (resource == "calendar_day" and last != first):
        raise ValueError("calendar_range_invalid")
    if kind and kind not in {choice for choice, _ in CalendarCommitment.KIND_CHOICES}:
        raise ValueError("calendar_commitment_kind_invalid")
    commitments = CalendarCommitment.objects.filter(user=user, calendar_date__range=(first, last))
    if kind:
        commitments = commitments.filter(kind=kind)
    by_date = {}
    for row in commitments.order_by("calendar_date", "kind", "id"):
        by_date.setdefault(row.calendar_date, []).append({
            "id": row.id, "kind": row.kind, "date": row.calendar_date.isoformat(),
            "hour": row.hour.isoformat() if row.hour else None, "note": row.note,
            "food_period_start": row.food_period_start.isoformat() if row.food_period_start else None,
            "food_period_end": row.food_period_end.isoformat() if row.food_period_end else None,
            "food_plans_count": row.food_plans_count,
            "foods_snapshot": row.foods_snapshot if resource == "calendar_day" else None,
        })
    if resource == "calendar_commitments":
        items = [item for values in by_date.values() for item in values]
    else:
        days = {
            row.calendar_date: row
            for row in CalendarizedDay.objects.filter(
                user=user, calendar_date__range=(first, last),
                assignment_state=CalendarizedDay.STATE_CURRENT,
            ).select_related("calendarization", "origin_calendarization")
        }
        items = []
        for index in range((last - first).days + 1):
            day_date = first + timedelta(days=index)
            row = days.get(day_date)
            origin = (row.origin_calendarization or row.calendarization) if row else None
            items.append({
                "date": day_date.isoformat(), "day_id": row.id if row else None,
                "has_plan": bool(row and row.has_plan),
                "plan_name": (row.plan_snapshot or {}).get("name", "") if row else "",
                "source_kind": row.source_kind if row else None,
                "source_program_name": origin.program_name_snapshot if origin else None,
                "snapshot_hash": row.snapshot_hash if row else None,
                "commitments": by_date.get(day_date, []),
                **({"plan_snapshot": row.plan_snapshot if row else None} if resource == "calendar_day" else {}),
            })
    if resource == "calendar_day":
        return {"resource": resource, "item": items[0], "timezone_name": user.profile.timezone_name}
    limit, offset = max(1, min(int(limit), 50)), max(0, int(offset))
    total = len(items)
    page = items[offset:offset + limit]
    return {
        "resource": resource, "items": page, "date_from": first.isoformat(),
        "date_to": last.isoformat(), "timezone_name": user.profile.timezone_name,
        "total_count": total, "count_for_user_questions": total,
        "returned_count": len(page), "offset": offset,
        "has_more": offset + len(page) < total,
        "next_offset": offset + len(page) if offset + len(page) < total else None,
    }
