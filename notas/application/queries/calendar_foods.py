from __future__ import annotations

from datetime import date

from django.db.models import Q

from notas.application.queries.calendarization_projection_queries import (
    snapshot_food_aggregation_rows,
    snapshot_nutrition_totals,
)
from notas.domain.models import CalendarizedDay

MAX_PERIOD_DAYS = 366


def calendar_foods_for_period(user, *, start_date: date, end_date: date) -> dict:
    """Aggregate foods from current, immutable calendar plan snapshots, inclusive of both dates."""
    if end_date < start_date or (end_date - start_date).days >= MAX_PERIOD_DAYS:
        raise ValueError("calendar_food_period_invalid")

    days = CalendarizedDay.objects.filter(
        Q(user=user) | Q(user__isnull=True, calendarization__user=user),
        assignment_state=CalendarizedDay.STATE_CURRENT,
        calendar_date__range=(start_date, end_date),
    ).order_by("calendar_date", "id")
    snapshots = [day.plan_snapshot for day in days if isinstance(day.plan_snapshot, dict) and day.plan_snapshot]
    totals = dict.fromkeys(("total_kcal", "kcal_protein", "kcal_carbs", "kcal_fat"), 0.0)
    meals_count = 0
    for snapshot in snapshots:
        nutrition = snapshot_nutrition_totals(snapshot)
        for key in totals:
            totals[key] += nutrition[key]
        meals = snapshot.get("meals")
        if isinstance(meals, list):
            meals_count += sum(1 for meal in meals if isinstance(meal, dict))
    return {
        "start_date": start_date,
        "end_date": end_date,
        "plans_count": len(snapshots),
        "meals_count": meals_count,
        "foods_aggregation_table": snapshot_food_aggregation_rows(snapshots, totals),
    }
