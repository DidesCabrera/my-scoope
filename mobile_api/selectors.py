from __future__ import annotations

from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.utils import timezone

from accounts.services.profile import build_account_credit_display
from notas.application.queries.calendarization_queries import (
    current_calendarization_for_user,
    today_for_calendarization,
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
        }

    local_date = today_for_calendarization(calendarization, now=now)
    day = next((item for item in calendarization.days.all() if item.calendar_date == local_date), None)
    total_days = max(1, (calendarization.end_date - calendarization.start_date).days + 1)
    progress_day = min(max((local_date - calendarization.start_date).days + 1, 0), total_days)
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
