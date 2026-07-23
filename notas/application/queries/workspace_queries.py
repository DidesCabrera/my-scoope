from __future__ import annotations

from notas.application.queries.calendarization_queries import (
    calendarization_history_for_user,
    current_calendarization_for_user,
)
from notas.domain.models import (
    DailyPlanMealShare,
    DailyPlanShare,
    FoodShare,
    MealShare,
    Program,
)


def list_owned_program_summaries(user, *, search: str = "", limit: int = 20) -> list[dict]:
    queryset = Program.objects.filter(created_by=user)
    clean_search = str(search or "").strip()
    if clean_search:
        queryset = queryset.filter(name__icontains=clean_search)
    programs = queryset.prefetch_related("program_dailyplan")[:limit]
    return [
        {
            "id": program.id,
            "name": program.name,
            "created_by_id": program.created_by_id,
            "duration_weeks": program.normalized_duration_weeks,
            "filled_days_count": program.filled_days_count,
            "empty_days_count": program.empty_days_count,
            "is_draft": program.is_draft,
            "is_public": program.is_public,
        }
        for program in programs
    ]


def get_owned_program_detail(user, *, program_id: int) -> dict:
    program = (
        Program.objects
        .filter(pk=program_id, created_by=user)
        .prefetch_related("program_dailyplan__dailyplan")
        .first()
    )
    if program is None:
        raise ValueError("program_not_available")
    slots = [
        {
            "program_day_id": slot.id,
            "week_number": slot.week_number,
            "day_number": slot.day_number,
            "dailyplan_id": slot.dailyplan_id,
            "dailyplan_name": slot.dailyplan.name,
            "total_kcal": float(slot.dailyplan.total_kcal),
        }
        for slot in program.program_dailyplan.all()
    ]
    return {
        "id": program.id,
        "name": program.name,
        "created_by_id": program.created_by_id,
        "duration_weeks": program.normalized_duration_weeks,
        "filled_days_count": len(slots),
        "empty_days_count": max(program.duration_days - len(slots), 0),
        "is_draft": program.is_draft,
        "is_public": program.is_public,
        "slots": slots,
    }


def get_user_calendarization_context(user, *, history_limit: int = 5) -> dict:
    current = current_calendarization_for_user(user)
    history = calendarization_history_for_user(user, limit=history_limit)
    return {
        "current": _serialize_calendarization(current, include_days=True) if current else None,
        "history": [
            _serialize_calendarization(item, include_days=False)
            for item in history
        ],
    }


def list_user_inbox_summaries(
    user,
    *,
    scope: str = "received",
    favorites_only: bool = False,
    limit: int = 20,
) -> list[dict]:
    scope = str(scope or "received").strip().lower()
    if scope not in {"received", "sent"}:
        raise ValueError("inbox_scope_invalid")

    model_specs = (
        (DailyPlanShare, "dailyplan", "dailyplan"),
        (MealShare, "meal", "meal"),
        (FoodShare, "food", "food"),
        (DailyPlanMealShare, "dailyplan_meal", "dailyplan_meal"),
    )
    items = []
    for model, kind, related_name in model_specs:
        if scope == "sent":
            queryset = model.objects.filter(sender=user, removed=False)
        else:
            queryset = model.objects.filter(
                accepted_by=user,
                dismissed=False,
                removed=False,
            )
            if favorites_only:
                queryset = queryset.filter(is_favorite=True)
        queryset = queryset.select_related("sender", related_name)
        for share in queryset[:limit]:
            entity = getattr(share, related_name)
            items.append(
                {
                    "share_id": share.id,
                    "kind": kind,
                    "direction": scope,
                    "entity_id": entity.id,
                    "entity_name": _shared_entity_name(entity),
                    "sender": share.sender.get_username(),
                    "recipient_email": share.recipient_email,
                    "subject": share.subject,
                    "message": share.message,
                    "is_favorite": share.is_favorite,
                    "is_read": share.is_read,
                    "created_at": share.created_at.isoformat(),
                }
            )
    items.sort(key=lambda item: item["created_at"], reverse=True)
    return items[:limit]


def _serialize_calendarization(calendarization, *, include_days: bool) -> dict:
    payload = {
        "id": calendarization.id,
        "program_id": calendarization.source_program_id,
        "program_name": calendarization.program_name_snapshot,
        "status": calendarization.status,
        "start_date": calendarization.start_date.isoformat(),
        "end_date": calendarization.end_date.isoformat(),
        "timezone_name": calendarization.timezone_name,
        "daily_notifications_enabled": calendarization.daily_notifications_enabled,
        "meal_notifications_enabled": calendarization.meal_notifications_enabled,
    }
    if include_days:
        payload["days"] = [
            {
                "id": day.id,
                "date": day.calendar_date.isoformat(),
                "week_number": day.week_number,
                "day_number": day.day_number,
                "dailyplan_id": day.source_dailyplan_id,
                "has_plan": day.has_plan,
            }
            for day in calendarization.days.all()
        ]
    return payload


def _shared_entity_name(entity) -> str:
    meal = getattr(entity, "meal", None)
    if meal is not None:
        return str(meal.name)
    return str(getattr(entity, "name", entity))
