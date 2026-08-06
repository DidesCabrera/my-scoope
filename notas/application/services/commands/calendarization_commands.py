from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from django.conf import settings
from django.db import IntegrityError, connection, transaction
from django.db.models import Q
from django.utils import timezone

from notas.application.services.calendarization.scheduling import (
    DAILY_NOTIFICATION_GRACE,
    MEAL_NOTIFICATION_GRACE,
    build_scheduled_window,
    local_date_for_timezone,
    validate_timezone_name,
)
from notas.application.services.calendarization.snapshots import (
    build_dailyplan_snapshot,
    program_with_calendarization_content,
)
from notas.application.services.notifications.web_push import (
    build_daily_plan_push_payload,
    endpoint_fingerprint,
    send_web_push,
    validate_push_endpoint,
)
from notas.application.services.notifications.apple_push import (
    apns_is_configured,
    apple_token_fingerprint,
    send_apple_push,
    validate_apple_device_token,
)
from notas.domain.models import (
    ApplePushSubscription,
    CalendarizedDay,
    NotificationDelivery,
    Program,
    ProgramCalendarization,
    ScheduledNotificationEvent,
    WebPushSubscription,
)


@dataclass(frozen=True)
class CalendarizationActivationResult:
    calendarization: ProgramCalendarization
    empty_dates: tuple[date, ...]
    replaced_calendarization_id: int | None = None


@dataclass(frozen=True)
class NotificationDispatchResult:
    claimed: int = 0
    dispatched: int = 0
    skipped: int = 0
    retried: int = 0
    deliveries_sent: int = 0
    deliveries_failed: int = 0


def _initial_status(*, start_date: date, timezone_name: str, now: datetime) -> str:
    today = local_date_for_timezone(timezone_name, now=now)
    if start_date <= today:
        return ProgramCalendarization.STATUS_ACTIVE
    return ProgramCalendarization.STATUS_SCHEDULED


def _event_key(*, calendarization_id: int, calendar_date: date, event_type: str, meal_key: str = "") -> str:
    if event_type == ScheduledNotificationEvent.TYPE_MEAL_REMINDER:
        return f"meal:{calendarization_id}:{calendar_date.isoformat()}:{meal_key}"
    return f"daily:{calendarization_id}:{calendar_date.isoformat()}"


def _upsert_event(
    *,
    calendarization: ProgramCalendarization,
    day: CalendarizedDay,
    event_type: str,
    local_time: time,
    now: datetime,
    meal_key: str = "",
) -> ScheduledNotificationEvent:
    grace = MEAL_NOTIFICATION_GRACE if event_type == ScheduledNotificationEvent.TYPE_MEAL_REMINDER else DAILY_NOTIFICATION_GRACE
    window = build_scheduled_window(
        local_date=day.calendar_date,
        local_time=local_time,
        timezone_name=calendarization.timezone_name,
        grace=grace,
    )
    event_key = _event_key(
        calendarization_id=calendarization.id,
        calendar_date=day.calendar_date,
        event_type=event_type,
        meal_key=meal_key,
    )
    defaults = {
        "calendarization": calendarization,
        "calendarized_day": day,
        "event_type": event_type,
        "meal_snapshot_key": meal_key,
        "local_scheduled_date": day.calendar_date,
        "local_scheduled_time": local_time,
        "timezone_name": calendarization.timezone_name,
        "scheduled_for_utc": window.scheduled_for_utc,
        "available_until_utc": window.available_until_utc,
        "dst_resolution": window.dst_resolution,
        "status": ScheduledNotificationEvent.STATUS_PENDING,
    }
    event, created = ScheduledNotificationEvent.objects.get_or_create(
        event_key=event_key,
        defaults=defaults,
    )
    if created:
        if event.scheduled_for_utc <= now and day.calendar_date == local_date_for_timezone(calendarization.timezone_name, now=now):
            event.status = ScheduledNotificationEvent.STATUS_SKIPPED
            event.skip_reason = "activated_after_due_time"
            event.save(update_fields=["status", "skip_reason", "updated_at"])
        return event

    if event.status in {
        ScheduledNotificationEvent.STATUS_PENDING,
        ScheduledNotificationEvent.STATUS_PROCESSING,
        ScheduledNotificationEvent.STATUS_CANCELLED,
    }:
        for field_name, value in defaults.items():
            setattr(event, field_name, value)
        event.skip_reason = ""
        event.claimed_at = None
        event.dispatched_at = None
        if event.scheduled_for_utc <= now and day.calendar_date == local_date_for_timezone(calendarization.timezone_name, now=now):
            event.status = ScheduledNotificationEvent.STATUS_SKIPPED
            event.skip_reason = "schedule_changed_after_due_time"
        event.save()
    return event


def _sync_day_events(*, calendarization: ProgramCalendarization, day: CalendarizedDay, now: datetime) -> None:
    if not day.plan_snapshot:
        return

    if calendarization.daily_notifications_enabled:
        _upsert_event(
            calendarization=calendarization,
            day=day,
            event_type=ScheduledNotificationEvent.TYPE_DAILY_PLAN,
            local_time=calendarization.daily_notification_time,
            now=now,
        )

    if calendarization.meal_notifications_enabled:
        for meal in day.plan_snapshot.get("meals", []):
            meal_hour = meal.get("hour")
            meal_key = meal.get("key") or ""
            if not meal_hour or not meal_key:
                continue
            try:
                parsed_hour = time.fromisoformat(meal_hour)
            except ValueError:
                continue
            _upsert_event(
                calendarization=calendarization,
                day=day,
                event_type=ScheduledNotificationEvent.TYPE_MEAL_REMINDER,
                local_time=parsed_hour,
                now=now,
                meal_key=meal_key,
            )


def reschedule_calendarized_days(
    *,
    calendarization: ProgramCalendarization,
    days: list[CalendarizedDay],
    now: datetime,
    reason: str,
) -> None:
    day_ids = [day.id for day in days]
    if not day_ids:
        return
    calendarization.notification_events.filter(
        calendarized_day_id__in=day_ids,
        status__in=(
            ScheduledNotificationEvent.STATUS_PENDING,
            ScheduledNotificationEvent.STATUS_PROCESSING,
        ),
    ).update(
        status=ScheduledNotificationEvent.STATUS_CANCELLED,
        skip_reason=reason,
        claimed_at=None,
    )
    for day in days:
        _sync_day_events(calendarization=calendarization, day=day, now=now)


def _cancel_pending_events(calendarization: ProgramCalendarization, *, reason: str) -> None:
    calendarization.notification_events.filter(
        status__in=(
            ScheduledNotificationEvent.STATUS_PENDING,
            ScheduledNotificationEvent.STATUS_PROCESSING,
        )
    ).update(
        status=ScheduledNotificationEvent.STATUS_CANCELLED,
        skip_reason=reason,
        claimed_at=None,
    )


@transaction.atomic
def activate_program_calendarization(
    *,
    user,
    program: Program,
    start_date: date,
    timezone_name: str,
    daily_notification_time: time = time(7, 0),
    daily_notifications_enabled: bool = True,
    meal_notifications_enabled: bool = False,
    confirm_incomplete: bool = False,
    replace_current: bool = False,
    now: datetime | None = None,
) -> CalendarizationActivationResult:
    current_time = now or timezone.now()
    timezone_name = validate_timezone_name(timezone_name)
    if program.created_by_id != user.id:
        raise ValueError("calendarization_program_not_owned")
    if start_date < local_date_for_timezone(timezone_name, now=current_time):
        raise ValueError("calendarization_start_date_past")

    program = program_with_calendarization_content(program.id)
    slots = {
        (program_day.week_number, program_day.day_number): program_day
        for program_day in program.program_dailyplan.all()
    }
    empty_dates = tuple(
        start_date + timedelta(days=offset)
        for offset in range(program.duration_days)
        if ((offset // 7) + 1, (offset % 7) + 1) not in slots
    )
    if empty_dates and not confirm_incomplete:
        raise ValueError("calendarization_incomplete_confirmation_required")

    current = (
        ProgramCalendarization.objects.select_for_update()
        .filter(user=user, status__in=ProgramCalendarization.CURRENT_STATUSES)
        .first()
    )
    replaced_id = None
    if current:
        if not replace_current:
            raise ValueError("calendarization_replacement_confirmation_required")
        replaced_id = current.id
        _cancel_pending_events(current, reason="calendarization_replaced")
        current.status = ProgramCalendarization.STATUS_CANCELLED
        current.cancelled_at = current_time
        current.save(update_fields=["status", "cancelled_at", "updated_at"])

    end_date = start_date + timedelta(days=program.duration_days - 1)
    try:
        calendarization = ProgramCalendarization.objects.create(
            user=user,
            source_program=program,
            program_name_snapshot=program.name,
            start_date=start_date,
            end_date=end_date,
            timezone_name=timezone_name,
            daily_notification_time=daily_notification_time,
            daily_notifications_enabled=daily_notifications_enabled,
            meal_notifications_enabled=meal_notifications_enabled,
            status=_initial_status(start_date=start_date, timezone_name=timezone_name, now=current_time),
            activated_at=current_time,
        )
    except IntegrityError as exc:
        raise ValueError("calendarization_current_conflict") from exc

    for offset in range(program.duration_days):
        week_number = (offset // 7) + 1
        day_number = (offset % 7) + 1
        program_day = slots.get((week_number, day_number))
        snapshot = build_dailyplan_snapshot(program_day) if program_day else None
        day = CalendarizedDay.objects.create(
            calendarization=calendarization,
            calendar_date=start_date + timedelta(days=offset),
            week_number=week_number,
            day_number=day_number,
            source_program_day_id=program_day.id if program_day else None,
            source_dailyplan_id=program_day.dailyplan_id if program_day else None,
            plan_snapshot=snapshot.payload if snapshot else None,
            snapshot_hash=snapshot.content_hash if snapshot else "",
        )
        _sync_day_events(calendarization=calendarization, day=day, now=current_time)

    profile = user.profile
    if profile.timezone_name != timezone_name:
        profile.timezone_name = timezone_name
        profile.save(update_fields=["timezone_name"])

    return CalendarizationActivationResult(
        calendarization=calendarization,
        empty_dates=empty_dates,
        replaced_calendarization_id=replaced_id,
    )


def _owned_current_calendarization(*, user, calendarization_id: int, for_update=False) -> ProgramCalendarization:
    queryset = ProgramCalendarization.objects
    if for_update:
        queryset = queryset.select_for_update()
    try:
        return queryset.get(pk=calendarization_id, user=user)
    except ProgramCalendarization.DoesNotExist as exc:
        raise ValueError("calendarization_not_found") from exc


@transaction.atomic
def pause_calendarization(*, user, calendarization_id: int, now: datetime | None = None) -> ProgramCalendarization:
    calendarization = _owned_current_calendarization(user=user, calendarization_id=calendarization_id, for_update=True)
    if calendarization.status not in {ProgramCalendarization.STATUS_SCHEDULED, ProgramCalendarization.STATUS_ACTIVE}:
        raise ValueError("calendarization_cannot_pause")
    calendarization.status = ProgramCalendarization.STATUS_PAUSED
    calendarization.paused_at = now or timezone.now()
    calendarization.save(update_fields=["status", "paused_at", "updated_at"])
    return calendarization


@transaction.atomic
def resume_calendarization(*, user, calendarization_id: int, now: datetime | None = None) -> ProgramCalendarization:
    current_time = now or timezone.now()
    calendarization = _owned_current_calendarization(user=user, calendarization_id=calendarization_id, for_update=True)
    if calendarization.status != ProgramCalendarization.STATUS_PAUSED:
        raise ValueError("calendarization_cannot_resume")
    today = local_date_for_timezone(calendarization.timezone_name, now=current_time)
    if today > calendarization.end_date:
        calendarization.status = ProgramCalendarization.STATUS_COMPLETED
        calendarization.completed_at = current_time
        _cancel_pending_events(calendarization, reason="calendarization_completed")
    else:
        calendarization.status = (
            ProgramCalendarization.STATUS_SCHEDULED
            if today < calendarization.start_date
            else ProgramCalendarization.STATUS_ACTIVE
        )
    calendarization.paused_at = None
    calendarization.save(update_fields=["status", "paused_at", "completed_at", "updated_at"])
    return calendarization


@transaction.atomic
def cancel_calendarization(*, user, calendarization_id: int, now: datetime | None = None) -> ProgramCalendarization:
    calendarization = _owned_current_calendarization(user=user, calendarization_id=calendarization_id, for_update=True)
    if calendarization.status not in ProgramCalendarization.CURRENT_STATUSES:
        raise ValueError("calendarization_cannot_cancel")
    _cancel_pending_events(calendarization, reason="calendarization_cancelled")
    calendarization.status = ProgramCalendarization.STATUS_CANCELLED
    calendarization.cancelled_at = now or timezone.now()
    calendarization.save(update_fields=["status", "cancelled_at", "updated_at"])
    return calendarization


@transaction.atomic
def update_calendarization_preferences(
    *,
    user,
    calendarization_id: int,
    timezone_name: str,
    daily_notification_time: time,
    daily_notifications_enabled: bool,
    meal_notifications_enabled: bool,
    now: datetime | None = None,
) -> ProgramCalendarization:
    current_time = now or timezone.now()
    timezone_name = validate_timezone_name(timezone_name)
    calendarization = _owned_current_calendarization(user=user, calendarization_id=calendarization_id, for_update=True)
    if calendarization.status not in ProgramCalendarization.CURRENT_STATUSES:
        raise ValueError("calendarization_not_current")

    calendarization.timezone_name = timezone_name
    calendarization.daily_notification_time = daily_notification_time
    calendarization.daily_notifications_enabled = daily_notifications_enabled
    calendarization.meal_notifications_enabled = meal_notifications_enabled
    calendarization.save(
        update_fields=[
            "timezone_name",
            "daily_notification_time",
            "daily_notifications_enabled",
            "meal_notifications_enabled",
            "updated_at",
        ]
    )

    future_events = calendarization.notification_events.filter(
        status__in=(ScheduledNotificationEvent.STATUS_PENDING, ScheduledNotificationEvent.STATUS_PROCESSING),
    )
    future_events.update(status=ScheduledNotificationEvent.STATUS_CANCELLED, skip_reason="preferences_changed", claimed_at=None)
    for day in calendarization.days.filter(calendar_date__gte=local_date_for_timezone(timezone_name, now=current_time)):
        _sync_day_events(calendarization=calendarization, day=day, now=current_time)

    profile = user.profile
    if profile.timezone_name != timezone_name:
        profile.timezone_name = timezone_name
        profile.save(update_fields=["timezone_name"])
    return calendarization


@transaction.atomic
def register_web_push_subscription(
    *,
    user,
    endpoint: str,
    p256dh_key: str,
    auth_key: str,
    user_agent: str = "",
    device_label: str = "",
) -> WebPushSubscription:
    endpoint = validate_push_endpoint(endpoint)
    p256dh_key = (p256dh_key or "").strip()
    auth_key = (auth_key or "").strip()
    if not p256dh_key or not auth_key or len(p256dh_key) > 255 or len(auth_key) > 255:
        raise ValueError("push_subscription_keys_invalid")
    fingerprint = endpoint_fingerprint(endpoint)
    subscription, _ = WebPushSubscription.objects.update_or_create(
        endpoint=endpoint,
        defaults={
            "user": user,
            "endpoint_fingerprint": fingerprint,
            "p256dh_key": p256dh_key,
            "auth_key": auth_key,
            "user_agent": (user_agent or "")[:1000],
            "device_label": (device_label or "")[:120],
            "is_active": True,
            "failure_code": "",
        },
    )
    return subscription


@transaction.atomic
def deactivate_web_push_subscription(*, user, endpoint: str) -> bool:
    endpoint = validate_push_endpoint(endpoint)
    updated = WebPushSubscription.objects.filter(user=user, endpoint=endpoint, is_active=True).update(is_active=False)
    return bool(updated)


@transaction.atomic
def register_apple_push_subscription(
    *,
    user,
    device_session,
    device_token: str,
    environment: str,
) -> ApplePushSubscription:
    if device_session.user_id != user.id or not device_session.is_active or device_session.platform != "ios":
        raise ValueError("apns_device_session_invalid")
    if environment not in dict(ApplePushSubscription.ENVIRONMENT_CHOICES):
        raise ValueError("apns_environment_invalid")
    normalized_token = validate_apple_device_token(device_token)
    fingerprint = apple_token_fingerprint(normalized_token)
    existing = (
        ApplePushSubscription.objects.select_for_update()
        .filter(token_fingerprint=fingerprint)
        .exclude(device_session=device_session)
        .first()
    )
    if existing is not None:
        if existing.user_id != user.id:
            raise ValueError("apns_device_token_conflict")
        existing.delete()
    subscription, _ = ApplePushSubscription.objects.update_or_create(
        device_session=device_session,
        defaults={
            "user": user,
            "device_token": normalized_token,
            "token_fingerprint": fingerprint,
            "environment": environment,
            "is_active": True,
            "failure_code": "",
        },
    )
    return subscription


def _mark_event(event: ScheduledNotificationEvent, *, status: str, reason: str = "", now: datetime) -> None:
    event.status = status
    event.skip_reason = reason
    event.claimed_at = None
    if status == ScheduledNotificationEvent.STATUS_DISPATCHED:
        event.dispatched_at = now
    event.save(update_fields=["status", "skip_reason", "claimed_at", "dispatched_at", "updated_at"])


def _claim_due_events(*, now: datetime, limit: int) -> list[ScheduledNotificationEvent]:
    stale_before = now - timedelta(minutes=15)
    ScheduledNotificationEvent.objects.filter(
        status=ScheduledNotificationEvent.STATUS_PROCESSING,
        claimed_at__lt=stale_before,
    ).update(status=ScheduledNotificationEvent.STATUS_PENDING, claimed_at=None, skip_reason="stale_claim_recovered")

    with transaction.atomic():
        queryset = ScheduledNotificationEvent.objects.filter(
            status=ScheduledNotificationEvent.STATUS_PENDING,
            scheduled_for_utc__lte=now,
        ).order_by("scheduled_for_utc", "id")
        if connection.features.has_select_for_update:
            queryset = queryset.select_for_update(skip_locked=connection.features.has_select_for_update_skip_locked)
        events = list(queryset[:limit])
        event_ids = [event.id for event in events]
        if event_ids:
            ScheduledNotificationEvent.objects.filter(id__in=event_ids, status=ScheduledNotificationEvent.STATUS_PENDING).update(
                status=ScheduledNotificationEvent.STATUS_PROCESSING,
                claimed_at=now,
            )
        for event in events:
            event.status = ScheduledNotificationEvent.STATUS_PROCESSING
            event.claimed_at = now
    return events


def _meal_label(event: ScheduledNotificationEvent) -> str:
    for meal in (event.calendarized_day.plan_snapshot or {}).get("meals", []):
        if meal.get("key") == event.meal_snapshot_key:
            return meal.get("name") or "tu comida"
    return "tu comida"


def _push_payload(event: ScheduledNotificationEvent) -> dict:
    payload = build_daily_plan_push_payload(calendarized_day_id=event.calendarized_day_id)
    if event.event_type == ScheduledNotificationEvent.TYPE_MEAL_REMINDER:
        payload["body"] = f"Es hora de {_meal_label(event)}"
        payload["tag"] = f"myscoope-meal-{event.id}"
    return payload


def dispatch_due_notifications(
    *,
    now: datetime | None = None,
    limit: int = 100,
    send_func=send_web_push,
    apns_send_func=send_apple_push,
) -> NotificationDispatchResult:
    current_time = now or timezone.now()
    reconcile_calendarization_statuses(now=current_time)
    web_push_enabled = bool(getattr(settings, "MYSCOOPE_WEB_PUSH_ENABLED", False))
    native_push_enabled = apns_is_configured()
    if not web_push_enabled and not native_push_enabled:
        return NotificationDispatchResult()

    events = _claim_due_events(now=current_time, limit=max(1, min(limit, 500)))
    dispatched = skipped = retried = deliveries_sent = deliveries_failed = 0

    for event in events:
        event = ScheduledNotificationEvent.objects.select_related(
            "calendarization",
            "calendarization__user",
            "calendarized_day",
        ).get(pk=event.pk)
        calendarization = event.calendarization
        today = local_date_for_timezone(calendarization.timezone_name, now=current_time)

        if calendarization.status == ProgramCalendarization.STATUS_PAUSED:
            _mark_event(event, status=ScheduledNotificationEvent.STATUS_SKIPPED, reason="calendarization_paused", now=current_time)
            skipped += 1
            continue
        if calendarization.status in {ProgramCalendarization.STATUS_CANCELLED, ProgramCalendarization.STATUS_COMPLETED}:
            _mark_event(event, status=ScheduledNotificationEvent.STATUS_CANCELLED, reason="calendarization_not_current", now=current_time)
            skipped += 1
            continue
        if today > calendarization.end_date:
            with transaction.atomic():
                calendarization.status = ProgramCalendarization.STATUS_COMPLETED
                calendarization.completed_at = current_time
                calendarization.save(update_fields=["status", "completed_at", "updated_at"])
                _cancel_pending_events(calendarization, reason="calendarization_completed")
            skipped += 1
            continue
        if calendarization.status == ProgramCalendarization.STATUS_SCHEDULED and today >= calendarization.start_date:
            calendarization.status = ProgramCalendarization.STATUS_ACTIVE
            calendarization.save(update_fields=["status", "updated_at"])
        if current_time > event.available_until_utc:
            _mark_event(event, status=ScheduledNotificationEvent.STATUS_SKIPPED, reason="delivery_window_expired", now=current_time)
            skipped += 1
            continue
        if event.event_type == ScheduledNotificationEvent.TYPE_DAILY_PLAN and not calendarization.daily_notifications_enabled:
            _mark_event(event, status=ScheduledNotificationEvent.STATUS_SKIPPED, reason="daily_notifications_disabled", now=current_time)
            skipped += 1
            continue
        if event.event_type == ScheduledNotificationEvent.TYPE_MEAL_REMINDER and not calendarization.meal_notifications_enabled:
            _mark_event(event, status=ScheduledNotificationEvent.STATUS_SKIPPED, reason="meal_notifications_disabled", now=current_time)
            skipped += 1
            continue

        subscriptions = []
        if web_push_enabled:
            subscriptions.extend(
                (NotificationDelivery.CHANNEL_WEB_PUSH, subscription, send_func)
                for subscription in WebPushSubscription.objects.filter(user=calendarization.user, is_active=True)
            )
        if native_push_enabled:
            subscriptions.extend(
                (NotificationDelivery.CHANNEL_APNS, subscription, apns_send_func)
                for subscription in ApplePushSubscription.objects.filter(
                    user=calendarization.user,
                    is_active=True,
                    device_session__is_active=True,
                )
            )
        if not subscriptions:
            _mark_event(event, status=ScheduledNotificationEvent.STATUS_SKIPPED, reason="no_active_subscription", now=current_time)
            skipped += 1
            continue

        any_sent = False
        transient_failure = False
        payload = _push_payload(event)
        for channel, subscription, sender in subscriptions:
            fingerprint = (
                subscription.endpoint_fingerprint
                if channel == NotificationDelivery.CHANNEL_WEB_PUSH
                else subscription.token_fingerprint
            )
            delivery, _ = NotificationDelivery.objects.get_or_create(
                event=event,
                subscription_fingerprint=fingerprint,
                defaults={
                    "subscription": subscription if channel == NotificationDelivery.CHANNEL_WEB_PUSH else None,
                    "apple_subscription": subscription if channel == NotificationDelivery.CHANNEL_APNS else None,
                    "channel": channel,
                },
            )
            if delivery.status in {NotificationDelivery.STATUS_SENT, NotificationDelivery.STATUS_EXPIRED}:
                any_sent = any_sent or delivery.status == NotificationDelivery.STATUS_SENT
                continue
            if delivery.attempt_count >= 3:
                deliveries_failed += 1
                continue

            result = sender(subscription=subscription, payload=payload)
            delivery.channel = channel
            delivery.subscription = subscription if channel == NotificationDelivery.CHANNEL_WEB_PUSH else None
            delivery.apple_subscription = subscription if channel == NotificationDelivery.CHANNEL_APNS else None
            delivery.attempt_count += 1
            if result.ok:
                delivery.status = NotificationDelivery.STATUS_SENT
                delivery.sent_at = current_time
                delivery.failure_code = ""
                subscription.last_success_at = current_time
                subscription.failure_code = ""
                subscription.save(update_fields=["last_success_at", "failure_code", "updated_at"])
                deliveries_sent += 1
                any_sent = True
            else:
                delivery.failure_code = result.failure_code
                subscription.last_failure_at = current_time
                subscription.failure_code = result.failure_code
                if result.expired:
                    delivery.status = NotificationDelivery.STATUS_EXPIRED
                    subscription.is_active = False
                    subscription.save(update_fields=["is_active", "last_failure_at", "failure_code", "updated_at"])
                else:
                    delivery.status = NotificationDelivery.STATUS_FAILED
                    subscription.save(update_fields=["last_failure_at", "failure_code", "updated_at"])
                    transient_failure = delivery.attempt_count < 3
                deliveries_failed += 1
            delivery.save()

        if transient_failure and current_time < event.available_until_utc:
            _mark_event(event, status=ScheduledNotificationEvent.STATUS_PENDING, reason="retry_pending", now=current_time)
            retried += 1
        elif any_sent:
            _mark_event(event, status=ScheduledNotificationEvent.STATUS_DISPATCHED, now=current_time)
            dispatched += 1
        else:
            _mark_event(event, status=ScheduledNotificationEvent.STATUS_SKIPPED, reason="all_deliveries_failed", now=current_time)
            skipped += 1

    return NotificationDispatchResult(
        claimed=len(events),
        dispatched=dispatched,
        skipped=skipped,
        retried=retried,
        deliveries_sent=deliveries_sent,
        deliveries_failed=deliveries_failed,
    )


def reconcile_calendarization_statuses(*, now: datetime | None = None) -> dict[str, int]:
    current_time = now or timezone.now()
    activated = completed = 0
    for calendarization in ProgramCalendarization.objects.filter(
        status__in=(ProgramCalendarization.STATUS_SCHEDULED, ProgramCalendarization.STATUS_ACTIVE)
    ):
        today = local_date_for_timezone(calendarization.timezone_name, now=current_time)
        if today > calendarization.end_date:
            with transaction.atomic():
                _cancel_pending_events(calendarization, reason="calendarization_completed")
                calendarization.status = ProgramCalendarization.STATUS_COMPLETED
                calendarization.completed_at = current_time
                calendarization.save(update_fields=["status", "completed_at", "updated_at"])
            completed += 1
        elif calendarization.status == ProgramCalendarization.STATUS_SCHEDULED and today >= calendarization.start_date:
            calendarization.status = ProgramCalendarization.STATUS_ACTIVE
            calendarization.save(update_fields=["status", "updated_at"])
            activated += 1
    return {"activated": activated, "completed": completed}


@transaction.atomic
def prune_calendarization_operational_data(
    *,
    now: datetime | None = None,
    event_retention_days: int = 90,
    inactive_subscription_days: int = 30,
) -> dict[str, int]:
    current_time = now or timezone.now()
    event_cutoff = current_time - timedelta(days=max(1, event_retention_days))
    subscription_cutoff = current_time - timedelta(days=max(1, inactive_subscription_days))
    deliveries_deleted, _ = NotificationDelivery.objects.filter(event__created_at__lt=event_cutoff).delete()
    events_deleted, _ = ScheduledNotificationEvent.objects.filter(created_at__lt=event_cutoff).delete()
    subscriptions_deleted, _ = WebPushSubscription.objects.filter(
        is_active=False,
        updated_at__lt=subscription_cutoff,
    ).delete()
    apple_subscriptions_deleted, _ = ApplePushSubscription.objects.filter(
        is_active=False,
        updated_at__lt=subscription_cutoff,
    ).delete()
    return {
        "deliveries_deleted": deliveries_deleted,
        "events_deleted": events_deleted,
        "subscriptions_deleted": subscriptions_deleted,
        "apple_subscriptions_deleted": apple_subscriptions_deleted,
    }
