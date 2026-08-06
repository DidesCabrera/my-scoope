from __future__ import annotations

from datetime import timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.utils import timezone

from accounts.services.profile import build_account_credit_display
from notas.application.queries.calendarization_queries import (
    current_calendarization_for_user,
    today_for_calendarization,
)
from notas.application.queries.calendarization_execution_queries import (
    calendarization_measurement_summary,
    calendarization_progress_summary,
    meal_execution_state_for_day,
    pending_revision_for_calendarization,
)
from notas.application.services.nutrition.body_metrics import get_basic_body_profile


def session_payload(auth) -> dict:
    user = auth.user
    display_name = user.get_full_name().strip() or user.username
    return {
        "user_id": user.id,
        "username": user.username,
        "email": user.email,
        "display_name": display_name,
        "scopes": list(auth.token.scopes),
        "device_session_id": (
            str(auth.token.device_session.public_id)
            if auth.token.device_session_id
            else None
        ),
    }


def profile_payload(user) -> dict:
    body = get_basic_body_profile(user)
    profile = user.profile
    return {
        "birth_date": body.birth_date,
        "sex": body.sex,
        "height_cm": body.height_cm,
        "timezone_name": profile.timezone_name,
        "onboarding_completed": profile.onboarding_completed_at is not None,
        "onboarding_version": profile.onboarding_version,
        "current_weight_kg": body.current_weight_kg,
    }


def entitlements_payload(user) -> dict:
    account = build_account_credit_display(user)
    return {
        "plan_name": account.plan_name,
        "plan_slug": account.plan_slug,
        "subscription_status": account.subscription_status,
        "period": account.period,
        "available_credits": account.available_credits,
        "reserved_credits": account.reserved_credits,
        "monthly_credit_limit": account.monthly_credit_limit,
        "daily_credit_limit": account.daily_credit_limit,
    }


def today_payload(user, *, now=None) -> dict:
    calendarization = current_calendarization_for_user(user)
    if calendarization is None:
        timezone_name = getattr(user.profile, "timezone_name", "UTC") or "UTC"
        try:
            user_timezone = ZoneInfo(timezone_name)
        except ZoneInfoNotFoundError:
            user_timezone = ZoneInfo("UTC")
        local_date = timezone.localdate(now or timezone.now(), timezone=user_timezone)
        return {
            "local_date": local_date,
            "calendarization": None,
            "day_id": None,
            "has_plan": False,
            "plan_snapshot": None,
            "meal_execution": [],
            "adherence": None,
            "measurements": None,
            "reminders": None,
            "pending_revision": None,
        }

    local_date = today_for_calendarization(calendarization, now=now)
    day = next((item for item in calendarization.days.all() if item.calendar_date == local_date), None)
    total_days = max(1, (calendarization.end_date - calendarization.start_date).days + 1)
    progress_day = min(max((local_date - calendarization.start_date).days + 1, 0), total_days)
    elapsed_end = min(local_date, calendarization.end_date)
    period_start = max(calendarization.start_date, elapsed_end - timedelta(days=6))
    return {
        "local_date": local_date,
        "calendarization": {
            "id": calendarization.id,
            "program_name": calendarization.program_name_snapshot,
            "status": calendarization.status,
            "start_date": calendarization.start_date,
            "end_date": calendarization.end_date,
            "timezone_name": calendarization.timezone_name,
            "progress_day": progress_day,
            "progress_total_days": total_days,
            "progress_percent": round((progress_day / total_days) * 100),
        },
        "day_id": day.id if day else None,
        "has_plan": bool(day and day.has_plan),
        "plan_snapshot": day.plan_snapshot if day and day.has_plan else None,
        "meal_execution": meal_execution_state_for_day(day) if day and day.has_plan else [],
        "adherence": (
            calendarization_progress_summary(
                calendarization,
                period_start=period_start,
                period_end=elapsed_end,
            )
            if elapsed_end >= calendarization.start_date
            else None
        ),
        "measurements": calendarization_measurement_summary(calendarization),
        "reminders": reminder_settings_payload(calendarization),
        "pending_revision": revision_payload(pending_revision_for_calendarization(calendarization)),
    }


def reminder_settings_payload(calendarization) -> dict:
    upcoming = [
        {
            "event_type": event.event_type,
            "meal_key": event.meal_snapshot_key,
            "local_date": event.local_scheduled_date,
            "local_time": event.local_scheduled_time,
            "status": event.status,
        }
        for event in calendarization.notification_events.filter(status="pending").order_by(
            "scheduled_for_utc", "id"
        )[:20]
    ]
    return {
        "timezone_name": calendarization.timezone_name,
        "daily_notification_time": calendarization.daily_notification_time,
        "daily_notifications_enabled": calendarization.daily_notifications_enabled,
        "meal_notifications_enabled": calendarization.meal_notifications_enabled,
        "upcoming": upcoming,
    }


def revision_payload(revision) -> dict | None:
    if revision is None:
        return None
    before_by_date = {
        item.get("calendar_date"): item
        for item in revision.before_snapshot.get("days", [])
    }
    days = []
    for after in revision.after_snapshot.get("days", []):
        calendar_date = after.get("calendar_date")
        before = before_by_date.get(calendar_date, {})
        before_plan = before.get("plan_snapshot") or {}
        after_plan = after.get("plan_snapshot") or {}
        days.append(
            {
                "calendar_date": calendar_date,
                "before_name": before_plan.get("name", ""),
                "after_name": after_plan.get("name", ""),
                "before_totals": before_plan.get("totals", {}),
                "after_totals": after_plan.get("totals", {}),
            }
        )
    return {
        "id": revision.id,
        "effective_from": revision.effective_from,
        "status": revision.status,
        "rationale": revision.rationale,
        "days": days,
        "created_at": revision.created_at,
    }


def review_payload(review) -> dict:
    return {
        "id": review.id,
        "period_start": review.period_start,
        "period_end": review.period_end,
        "energy_score": review.energy_score,
        "hunger_score": review.hunger_score,
        "training_performance_score": review.training_performance_score,
        "note": review.note,
        "summary_snapshot": review.summary_snapshot,
        "created_at": review.created_at,
    }


def active_program_payload(user) -> dict:
    calendarization = current_calendarization_for_user(user)
    if calendarization is None:
        return {"calendarization": None, "days": []}

    local_date = today_for_calendarization(calendarization)
    total_days = max(1, (calendarization.end_date - calendarization.start_date).days + 1)
    progress_day = min(max((local_date - calendarization.start_date).days + 1, 0), total_days)
    days = [
        {
            "id": day.id,
            "calendar_date": day.calendar_date,
            "week_number": day.week_number,
            "day_number": day.day_number,
            "has_plan": day.has_plan,
            "plan_name": (day.plan_snapshot or {}).get("name", ""),
        }
        for day in calendarization.days.all()
    ]
    return {
        "calendarization": {
            "id": calendarization.id,
            "program_name": calendarization.program_name_snapshot,
            "status": calendarization.status,
            "start_date": calendarization.start_date,
            "end_date": calendarization.end_date,
            "timezone_name": calendarization.timezone_name,
            "progress_day": progress_day,
            "progress_total_days": total_days,
            "progress_percent": round((progress_day / total_days) * 100),
        },
        "days": days,
    }
