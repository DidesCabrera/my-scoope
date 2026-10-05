from __future__ import annotations

from mobile_api.read_cache import (
    cache_home,
    get_cached_home,
    mobile_read_generation,
    payload_version,
)
from mobile_api.selectors import active_program_payload, today_payload
from notas.application.queries.calendarization_queries import current_calendarization_for_user
from notas.application.queries.proposal_queries import get_available_proposal_queryset
from notas.application.services.nutrition.weight import get_current_weight, get_current_weight_log
from notas.domain.models import DailyPlan, Food, Meal, Program


def _library_counts(user) -> dict[str, int]:
    return {
        "food": Food.objects.filter(created_by=user, is_active=True).count(),
        "meal": Meal.objects.filter(created_by=user, dailyplanmeal__isnull=True).distinct().count(),
        "daily_plan": DailyPlan.objects.filter(created_by=user).exclude(source=DailyPlan.SOURCE_PROGRAM).count(),
        "program": Program.objects.filter(created_by=user).count(),
    }


def _latest_weight(user) -> dict | None:
    item = get_current_weight_log(user)
    if item is None:
        return None
    return {
        "id": item.id,
        "measured_on": item.date,
        "weight_kg": item.weight_kg,
        "source": item.source,
        "created_at": item.created_at,
        "calendarization_id": None,
    }


def home_payload(user) -> dict:
    generation = mobile_read_generation(user.id)
    cached = get_cached_home(user.id)
    if cached is not None:
        return cached

    calendarization = current_calendarization_for_user(user)
    current_weight = get_current_weight(user)
    payload = {
        "today": today_payload(user, calendarization=calendarization),
        "active_program": active_program_payload(
            user,
            calendarization=calendarization,
            current_weight=current_weight,
        ),
        "latest_weight": _latest_weight(user),
        "library_counts": _library_counts(user),
        "pending_proposal_count": get_available_proposal_queryset(user).filter(status="pending_review").count(),
    }
    payload["version"] = payload_version(payload)
    cache_home(user.id, payload, generation=generation)
    return payload
