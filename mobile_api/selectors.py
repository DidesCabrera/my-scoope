from __future__ import annotations

from datetime import timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.utils import timezone

from accounts.services.profile import build_account_credit_display
from billing.application.services.apple_app_store import get_or_create_apple_app_account_token
from billing.models import BillingProduct, PaymentProvider, ProviderSubscription
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
        "review_disclosure_required": (
            profile.mobile_disclosure_version != profile.MOBILE_DISCLOSURE_VERSION
            or profile.mobile_disclosure_accepted_at is None
        ),
        "review_disclosure_version": profile.MOBILE_DISCLOSURE_VERSION,
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


def subscription_payload(user, *, purchases_enabled: bool) -> dict:
    profile = getattr(user, "profile", None)
    eligible = str(getattr(profile, "role", "member") or "member").lower() == "member"
    subscription = getattr(user, "account_subscription", None)
    token = get_or_create_apple_app_account_token(user) if eligible else None
    products = []
    if eligible and purchases_enabled:
        products = [
            {
                "product_id": product.external_product_id,
                "plan_name": product.account_plan.name,
                "interval": product.interval,
            }
            for product in BillingProduct.objects.select_related("account_plan").filter(
                provider=PaymentProvider.APPLE_APP_STORE,
                active=True,
                account_plan__status="active",
            )
        ]
    evidence = list(
        ProviderSubscription.objects.filter(user=user)
        .exclude(status=ProviderSubscription.Status.PENDING)
        .order_by("provider", "-updated_at")
        .values("provider", "status", "current_period_end")
    )
    metadata = dict(getattr(subscription, "metadata", {}) or {})
    return {
        "eligible": eligible,
        "purchases_enabled": bool(eligible and purchases_enabled and products),
        "app_account_token": str(token.token) if token is not None else "",
        "plan_name": subscription.plan.name if subscription is not None else "Sin plan",
        "status": subscription.status if subscription is not None else "none",
        "products": products,
        "evidence": [
            {
                "provider": item["provider"],
                "status": item["status"],
                "period_end": item["current_period_end"],
            }
            for item in evidence
        ],
        "duplicate_active_providers": bool(metadata.get("billing_duplicate_active_providers")),
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
            "event_key": event.event_key,
            "event_type": event.event_type,
            "meal_key": event.meal_snapshot_key,
            "local_date": event.local_scheduled_date,
            "local_time": event.local_scheduled_time,
            "scheduled_for_utc": event.scheduled_for_utc,
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


def food_label_capture_payload(result) -> dict:
    food = result.food
    receipt = result.receipt
    return {
        "id": food.id,
        "name": food.name,
        "protein_g": food.protein,
        "carbs_g": food.carbs,
        "fat_g": food.fat,
        "saturated_fat_g": float(food.saturated_fat_g_per_100g) if food.saturated_fat_g_per_100g is not None else None,
        "sugar_g": float(food.sugar_g_per_100g) if food.sugar_g_per_100g is not None else None,
        "fiber_g": float(food.fiber_g_per_100g) if food.fiber_g_per_100g is not None else None,
        "sodium_mg": float(food.sodium_mg_per_100g) if food.sodium_mg_per_100g is not None else None,
        "total_kcal": food.total_kcal,
        "is_user_food": food.created_by_id is not None and not food.is_global,
        "is_verified": food.is_verified,
        "capture_receipt_id": receipt.id,
        "detected_basis": receipt.detected_basis,
        "serving_size_g": float(receipt.serving_size_g) if receipt.serving_size_g is not None else None,
        "ocr_engine": receipt.ocr_engine,
        "created_at": receipt.created_at,
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
