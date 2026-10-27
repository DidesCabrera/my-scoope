"""Read the current calendar assignments for the two onboarding proposals."""

from accounts.services.onboarding import onboarding_applied_dailyplan_ids
from mobile_api.selectors import _aggregated_food_panel_items
from notas.application.queries.calendarization_projection_queries import (
    snapshot_food_aggregation_rows,
    snapshot_nutrition_totals,
)
from notas.domain.models import CalendarizedDay


def _foods_for_snapshots(snapshots: list[dict], *, id_prefix: str) -> list[dict]:
    totals = dict.fromkeys(("total_kcal", "kcal_protein", "kcal_carbs", "kcal_fat"), 0.0)
    for snapshot in snapshots:
        nutrition = snapshot_nutrition_totals(snapshot)
        for key in totals:
            totals[key] += nutrition[key]
    return _aggregated_food_panel_items(snapshot_food_aggregation_rows(snapshots, totals), id_prefix=id_prefix)


def onboarding_calendarization_payload(user, proposal_ids: list[int]) -> dict:
    plan_ids = onboarding_applied_dailyplan_ids(user=user, proposal_ids=proposal_ids)
    days = list(CalendarizedDay.objects.filter(
        user=user, source_dailyplan_id__in=plan_ids.values(), source_kind=CalendarizedDay.SOURCE_MANUAL,
        assignment_state=CalendarizedDay.STATE_CURRENT,
    ).order_by("calendar_date", "id")) if plan_ids else []
    by_plan = {}
    for day in days:
        if isinstance(day.plan_snapshot, dict) and day.plan_snapshot:
            by_plan.setdefault(day.source_dailyplan_id, []).append(day)
    plans = []
    for proposal_id in proposal_ids:
        dailyplan_id = plan_ids.get(proposal_id)
        assigned = by_plan.get(dailyplan_id, []) if dailyplan_id else []
        plans.append({
            "proposal_id": proposal_id,
            "dailyplan_id": dailyplan_id,
            "dates": [day.calendar_date for day in assigned],
            "foods": _foods_for_snapshots([day.plan_snapshot for day in assigned], id_prefix=f"onboarding-{proposal_id}"),
        })
    snapshots = [day.plan_snapshot for day in days if isinstance(day.plan_snapshot, dict) and day.plan_snapshot]
    return {"plans": plans, "days_count": len(snapshots),
            "foods": _foods_for_snapshots(snapshots, id_prefix="onboarding-all")}
