from datetime import date, datetime, time, timedelta
from datetime import timezone as dt_timezone

from django.contrib.auth.models import User
from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from notas.application.services.calendarization.scheduling import local_datetime_to_utc
from notas.application.services.commands.calendarization_commands import (
    activate_program_calendarization,
    cancel_calendarization,
    dispatch_due_notifications,
    pause_calendarization,
    register_apple_push_subscription,
    register_web_push_subscription,
    resume_calendarization,
    update_calendarization_preferences,
    update_calendarized_meal_hour,
)
from notas.application.services.notifications.apple_push import ApplePushSendResult
from notas.application.services.notifications.web_push import (
    WebPushSendResult,
    send_web_push,
    validate_push_endpoint,
)
from notas.domain.models import (
    ApplePushSubscription,
    CalendarizedDay,
    CalendarizedMealExecution,
    DailyPlan,
    DailyPlanMeal,
    Food,
    Meal,
    MealFood,
    NotificationDelivery,
    OAuthClient,
    OAuthDeviceSession,
    Program,
    ProgramCalendarization,
    ProgramDay,
    ScheduledNotificationEvent,
    WebPushSubscription,
)

UTC = dt_timezone.utc


class CalendarizationFixtureMixin:
    def setUp(self):
        self.user = User.objects.create_user(username="calendar-owner", password="pw")
        self.other = User.objects.create_user(username="calendar-other", password="pw")
        for user in (self.user, self.other):
            user.profile.onboarding_completed_at = timezone.now()
            user.profile.onboarding_version = 1
            user.profile.save(update_fields=["onboarding_completed_at", "onboarding_version"])
        self.program = Program.objects.create(name="Semana base", created_by=self.user, duration_weeks=1)
        self.dailyplan = DailyPlan.objects.create(name="Día original", created_by=self.user)
        ProgramDay.objects.create(program=self.program, dailyplan=self.dailyplan, week_number=1, day_number=1)

    def activate(self, **overrides):
        values = {
            "user": self.user,
            "program": self.program,
            "start_date": date(2026, 7, 20),
            "timezone_name": "America/Santiago",
            "daily_notification_time": time(7),
            "confirm_incomplete": True,
            "now": datetime(2026, 7, 19, 12, tzinfo=UTC),
        }
        values.update(overrides)
        return activate_program_calendarization(**values)


class CalendarizationCommandTests(CalendarizationFixtureMixin, TestCase):
    def test_activation_materializes_all_days_and_keeps_snapshot_immutable(self):
        result = self.activate()
        self.assertEqual(result.calendarization.days.count(), 7)
        self.assertEqual(len(result.empty_dates), 6)
        first = result.calendarization.days.get(day_number=1)
        self.assertEqual(first.plan_snapshot["name"], "Día original")
        self.dailyplan.name = "Día editado"
        self.dailyplan.save(update_fields=["name"])
        first.refresh_from_db()
        self.assertEqual(first.plan_snapshot["name"], "Día original")

    def test_snapshot_survives_source_program_deletion(self):
        result = self.activate()
        day_id = result.calendarization.days.get(day_number=1).id
        self.program.delete()
        day = CalendarizedDay.objects.select_related("calendarization").get(id=day_id)
        self.assertIsNone(day.calendarization.source_program)
        self.assertEqual(day.plan_snapshot["name"], "Día original")

    def test_changing_active_meal_hour_updates_snapshot_hash_and_reschedules_reminder(self):
        meal = Meal.objects.create(name="Desayuno activo", created_by=self.user)
        slot = DailyPlanMeal.objects.create(
            dailyplan=self.dailyplan,
            meal=meal,
            hour=time(8),
            order=1,
        )
        result = self.activate(
            start_date=date(2026, 7, 20),
            timezone_name="UTC",
            meal_notifications_enabled=True,
            now=datetime(2026, 7, 19, 12, tzinfo=UTC),
        )
        day = result.calendarization.days.get(day_number=1)
        meal_key = f"dailyplan_meal:{slot.id}"
        original_hash = day.snapshot_hash

        update_calendarized_meal_hour(
            user=self.user,
            day_id=day.id,
            meal_snapshot_key=meal_key,
            hour=time(9, 25),
            now=datetime(2026, 7, 19, 12, tzinfo=UTC),
        )

        day.refresh_from_db()
        event = ScheduledNotificationEvent.objects.get(
            calendarized_day=day,
            event_type=ScheduledNotificationEvent.TYPE_MEAL_REMINDER,
            meal_snapshot_key=meal_key,
        )
        self.assertEqual(day.plan_snapshot["meals"][0]["hour"], "09:25")
        self.assertNotEqual(day.snapshot_hash, original_hash)
        self.assertEqual(event.local_scheduled_time, time(9, 25))
        self.assertEqual(event.status, ScheduledNotificationEvent.STATUS_PENDING)

    def test_incomplete_program_requires_explicit_confirmation(self):
        with self.assertRaisesMessage(ValueError, "calendarization_incomplete_confirmation_required"):
            self.activate(confirm_incomplete=False)

    def test_only_owned_program_can_be_calendarized(self):
        with self.assertRaisesMessage(ValueError, "calendarization_program_not_owned"):
            self.activate(user=self.other)

    def test_replacement_cancels_existing_calendarization(self):
        first = self.activate().calendarization
        second = self.activate(start_date=date(2026, 7, 27), replace_current=True).calendarization
        first.refresh_from_db()
        self.assertEqual(first.status, ProgramCalendarization.STATUS_CANCELLED)
        self.assertTrue(second.is_current)

    def test_database_enforces_one_current_calendarization_per_user(self):
        self.activate()
        with self.assertRaises(IntegrityError), transaction.atomic():
            ProgramCalendarization.objects.create(
                user=self.user,
                program_name_snapshot="Conflict",
                start_date=date(2026, 8, 1),
                end_date=date(2026, 8, 7),
            )

    def test_pause_resume_cancel_state_machine(self):
        calendarization = self.activate().calendarization
        pause_calendarization(user=self.user, calendarization_id=calendarization.id)
        calendarization.refresh_from_db()
        self.assertEqual(calendarization.status, ProgramCalendarization.STATUS_PAUSED)
        resume_calendarization(
            user=self.user,
            calendarization_id=calendarization.id,
            now=datetime(2026, 7, 20, 12, tzinfo=UTC),
        )
        calendarization.refresh_from_db()
        self.assertEqual(calendarization.status, ProgramCalendarization.STATUS_ACTIVE)
        cancel_calendarization(user=self.user, calendarization_id=calendarization.id)
        calendarization.refresh_from_db()
        self.assertEqual(calendarization.status, ProgramCalendarization.STATUS_CANCELLED)

    def test_timezone_changes_utc_schedule_and_is_saved_to_profile(self):
        calendarization = self.activate().calendarization
        event = calendarization.notification_events.get(event_type=ScheduledNotificationEvent.TYPE_DAILY_PLAN)
        self.assertEqual(event.scheduled_for_utc, datetime(2026, 7, 20, 11, tzinfo=UTC))
        self.assertEqual(event.dst_resolution, "exact")
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.timezone_name, "America/Santiago")
        update_calendarization_preferences(
            user=self.user,
            calendarization_id=calendarization.id,
            timezone_name="America/Los_Angeles",
            daily_notification_time=time(8, 30),
            daily_notifications_enabled=True,
            meal_notifications_enabled=False,
            now=datetime(2026, 7, 19, 12, tzinfo=UTC),
        )
        event.refresh_from_db()
        self.assertEqual(event.scheduled_for_utc, datetime(2026, 7, 20, 15, 30, tzinfo=UTC))

    def test_activation_after_notification_time_marks_today_skipped(self):
        result = self.activate(
            start_date=date(2026, 7, 19),
            timezone_name="UTC",
            now=datetime(2026, 7, 19, 9, tzinfo=UTC),
        )
        event = result.calendarization.notification_events.get(event_type=ScheduledNotificationEvent.TYPE_DAILY_PLAN)
        self.assertEqual(event.status, ScheduledNotificationEvent.STATUS_SKIPPED)
        self.assertEqual(event.skip_reason, "activated_after_due_time")

    def test_meal_reminders_are_created_only_for_meals_with_an_hour(self):
        breakfast = Meal.objects.create(name="Desayuno", created_by=self.user)
        dinner = Meal.objects.create(name="Cena", created_by=self.user)
        DailyPlanMeal.objects.create(dailyplan=self.dailyplan, meal=breakfast, hour=time(9), order=1)
        DailyPlanMeal.objects.create(dailyplan=self.dailyplan, meal=dinner, hour=None, order=2)
        calendarization = self.activate(meal_notifications_enabled=True).calendarization
        meal_events = calendarization.notification_events.filter(
            event_type=ScheduledNotificationEvent.TYPE_MEAL_REMINDER
        )
        self.assertEqual(meal_events.count(), 1)
        self.assertEqual(meal_events.get().local_scheduled_time, time(9))


@override_settings(MYSCOOPE_WEB_PUSH_ENABLED=True)
class CalendarizationDispatchTests(CalendarizationFixtureMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.calendarization = self.activate(timezone_name="UTC").calendarization
        self.subscription = register_web_push_subscription(
            user=self.user,
            endpoint="https://push.example.com/device-token",
            p256dh_key="public-key",
            auth_key="auth-key",
        )

    def test_dispatch_is_idempotent_per_event_and_device(self):
        event = self.calendarization.notification_events.get(event_type=ScheduledNotificationEvent.TYPE_DAILY_PLAN)
        now = event.scheduled_for_utc + timedelta(minutes=1)
        calls = []

        def send_func(**kwargs):
            calls.append(kwargs)
            return WebPushSendResult(ok=True)

        first = dispatch_due_notifications(now=now, send_func=send_func)
        second = dispatch_due_notifications(now=now, send_func=send_func)
        self.assertEqual(first.deliveries_sent, 1)
        self.assertEqual(second.claimed, 0)
        self.assertEqual(len(calls), 1)
        self.assertEqual(NotificationDelivery.objects.count(), 1)

    def test_transient_failure_is_retried(self):
        event = self.calendarization.notification_events.get(event_type=ScheduledNotificationEvent.TYPE_DAILY_PLAN)
        now = event.scheduled_for_utc + timedelta(minutes=1)
        outcomes = iter((WebPushSendResult(ok=False, failure_code="temporary"), WebPushSendResult(ok=True)))

        def send_func(**kwargs):
            return next(outcomes)

        first = dispatch_due_notifications(now=now, send_func=send_func)
        second = dispatch_due_notifications(now=now + timedelta(minutes=1), send_func=send_func)
        self.assertEqual(first.retried, 1)
        self.assertEqual(second.deliveries_sent, 1)
        self.assertEqual(NotificationDelivery.objects.get().attempt_count, 2)

    def test_expired_subscription_is_deactivated(self):
        event = self.calendarization.notification_events.get(event_type=ScheduledNotificationEvent.TYPE_DAILY_PLAN)
        dispatch_due_notifications(
            now=event.scheduled_for_utc + timedelta(minutes=1),
            send_func=lambda **kwargs: WebPushSendResult(ok=False, expired=True, failure_code="http_410"),
        )
        self.subscription.refresh_from_db()
        self.assertFalse(self.subscription.is_active)


@override_settings(
    MYSCOOPE_WEB_PUSH_ENABLED=False,
    MYSCOOPE_APNS_ENABLED=True,
    MYSCOOPE_APNS_KEY_ID="KEY123",
    MYSCOOPE_APNS_TEAM_ID="TEAM123",
    MYSCOOPE_APNS_PRIVATE_KEY="private-key",
    MYSCOOPE_APNS_BUNDLE_ID="com.myscoope.app",
)
class ApplePushDispatchTests(CalendarizationFixtureMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.calendarization = self.activate(timezone_name="UTC").calendarization
        client = OAuthClient.objects.create(
            client_id="calendar-apns-tests",
            client_name="Calendar APNs tests",
            redirect_uris=["myscoope://oauth/callback"],
            allowed_scopes=["mobile:read"],
        )
        session = OAuthDeviceSession.objects.create(
            client=client,
            user=self.user,
            device_id_hash="a" * 64,
            device_name="Test iPhone",
            platform=OAuthDeviceSession.PLATFORM_IOS,
        )
        self.subscription = register_apple_push_subscription(
            user=self.user,
            device_session=session,
            device_token="ab" * 32,
            environment=ApplePushSubscription.ENVIRONMENT_SANDBOX,
        )

    def test_dispatch_uses_apns_once_for_native_device(self):
        event = self.calendarization.notification_events.get(event_type=ScheduledNotificationEvent.TYPE_DAILY_PLAN)
        calls = []

        def apns_send_func(**kwargs):
            calls.append(kwargs)
            return ApplePushSendResult(ok=True)

        result = dispatch_due_notifications(
            now=event.scheduled_for_utc + timedelta(minutes=1),
            apns_send_func=apns_send_func,
        )

        self.assertEqual(result.deliveries_sent, 1)
        self.assertEqual(len(calls), 1)
        delivery = NotificationDelivery.objects.get()
        self.assertEqual(delivery.channel, NotificationDelivery.CHANNEL_APNS)
        self.assertEqual(delivery.apple_subscription, self.subscription)


class WebPushSecurityTests(TestCase):
    def test_rejects_non_https_private_and_authenticated_endpoints(self):
        invalid = (
            "http://push.example.com/x",
            "https://127.0.0.1/x",
            "https://localhost/x",
            "https://user:password@push.example.com/x",
            "https://push.example.com:8443/x",
        )
        for endpoint in invalid:
            with self.subTest(endpoint=endpoint), self.assertRaises(ValueError):
                validate_push_endpoint(endpoint)

    @override_settings(MYSCOOPE_WEB_PUSH_ENABLED=True)
    def test_send_rejects_private_endpoint_without_transport_request(self):
        user = User.objects.create_user(username="private-endpoint")
        subscription = WebPushSubscription.objects.create(
            user=user,
            endpoint="https://127.0.0.1/push",
            endpoint_fingerprint="x" * 64,
            p256dh_key="p",
            auth_key="a",
        )
        result = send_web_push(subscription=subscription, payload={"title": "x"})
        self.assertFalse(result.ok)
        self.assertEqual(result.failure_code, "push_endpoint_rejected")


class CalendarizationTimezoneTests(TestCase):
    def test_nonexistent_dst_time_uses_first_valid_instant(self):
        instant, resolution = local_datetime_to_utc(
            date(2026, 3, 8),
            time(2, 30),
            "America/New_York",
        )
        self.assertEqual(instant, datetime(2026, 3, 8, 7, tzinfo=UTC))
        self.assertEqual(resolution, "first_valid_after_gap")

    def test_repeated_dst_time_uses_first_occurrence(self):
        instant, resolution = local_datetime_to_utc(
            date(2026, 11, 1),
            time(1, 30),
            "America/New_York",
        )
        self.assertEqual(instant, datetime(2026, 11, 1, 5, 30, tzinfo=UTC))
        self.assertEqual(resolution, "first_occurrence")


class CalendarizationViewTests(CalendarizationFixtureMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.user)

    def test_dashboard_lists_only_owned_programs(self):
        foreign = Program.objects.create(name="Programa ajeno", created_by=self.other)
        response = self.client.get(reverse("calendarization_dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.program.name)
        self.assertNotContains(response, foreign.name)
        self.assertContains(response, 'data-empty-days="6"')
        self.assertContains(response, "Calendarizador")
        self.assertContains(response, "Historial")
        self.assertNotContains(response, ">Zona horaria<")
        self.assertContains(response, '<input type="date" name="start_date" required data-start-date>')
        self.assertContains(response, '<div class="calendarization-warning" data-incomplete-warning hidden>')

    def test_history_has_its_own_view(self):
        result = self.activate()
        cancel_calendarization(user=self.user, calendarization_id=result.calendarization.id)
        response = self.client.get(reverse("calendarization_history"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.program.name)
        self.assertContains(response, "Historial")
        self.assertContains(response, "Calendarizador")

    def test_dashboard_with_current_uses_home_calendar_layout_without_replacement_card(self):
        self.activate()
        response = self.client.get(
            reverse("calendarization_dashboard"),
            {"calendar_week": "2026-07-20", "calendar_date": "2026-07-20"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'class="home-calendar calendarization-current"')
        self.assertContains(response, 'class="calendarization-current__overview"')
        self.assertContains(response, 'class="program-active-kpis program-active-kpis--standalone"')
        self.assertContains(response, "Ir a detalle de programa")
        self.assertContains(response, reverse("program_detail", args=[self.program.id]))
        self.assertContains(response, "calendarization-current__section-divider")
        self.assertContains(response, "Planificación semanal")
        self.assertContains(response, "calendarization-current__week-foods-divider")
        self.assertContains(response, "Alimentos en esta Semana")
        self.assertContains(
            response,
            'class="program-board-shell calendarization-current__planning"',
        )
        self.assertContains(response, 'class="calendarization-actions"')
        self.assertContains(response, 'class="card "')
        self.assertContains(response, "card-kpi")
        self.assertContains(response, "Programa en curso")
        self.assertNotContains(response, "Reemplazar calendarización")
        self.assertNotContains(response, "Nueva calendarización")
        self.assertContains(response, "Notificaciones")
        self.assertContains(response, "Guardar preferencias")
        self.assertContains(response, "Cancelar")
        self.assertContains(
            response,
            'class="home-calendar__week-slider home-calendar__week-slider--single"',
            count=1,
        )
        self.assertContains(response, "program-week-days-layout")
        self.assertContains(response, "data-calendarization-day", count=7)
        self.assertNotContains(response, "data-home-calendar-week-nav")
        self.assertNotContains(response, "data-home-calendar-day-link")
        self.assertNotContains(response, "home_calendarization.js")
        self.assertContains(response, "calendarization_days.js")
        self.assertNotContains(response, "Pausar")
        self.assertNotContains(response, "Reanudar")

    def test_dashboard_week_tabs_render_only_the_selected_weeks_days(self):
        ProgramCalendarization.objects.create(
            user=self.user,
            program_name_snapshot="Programa de tres semanas",
            start_date=date(2026, 7, 13),
            end_date=date(2026, 8, 2),
            timezone_name="UTC",
            status=ProgramCalendarization.STATUS_ACTIVE,
        )

        response = self.client.get(
            reverse("calendarization_dashboard"),
            {"calendar_week": "2026-07-20", "calendar_date": "2026-07-20"},
        )

        self.assertContains(response, "Semana 1")
        self.assertContains(response, "Semana 2")
        self.assertContains(response, "Semana 3")
        self.assertContains(response, 'class="home-calendar__day ', count=7)
        self.assertContains(response, "data-calendarization-day", count=7)
        self.assertNotContains(response, "data-home-calendar-day-link")
        self.assertNotContains(response, "data-home-calendar-week-nav")

    def test_activation_endpoint_creates_calendarization(self):
        response = self.client.post(
            reverse("calendarization_activate"),
            {
                "program_id": self.program.id,
                "start_date": (timezone.localdate() + timedelta(days=1)).isoformat(),
                "notification_time": "07:00",
                "timezone_name": "UTC",
                "daily_notifications_enabled": "on",
                "confirm_incomplete": "on",
            },
        )
        self.assertRedirects(response, reverse("calendarization_dashboard"))
        self.assertEqual(ProgramCalendarization.objects.filter(user=self.user).count(), 1)

    def test_day_detail_does_not_leak_another_users_snapshot(self):
        result = self.activate()
        day = result.calendarization.days.first()
        self.client.force_login(self.other)
        response = self.client.get(reverse("calendarization_day_detail", args=[day.id]))
        self.assertEqual(response.status_code, 404)

    def test_dashboard_exposes_todays_snapshot(self):
        self.activate(
            start_date=date(2026, 7, 19),
            timezone_name="UTC",
            now=datetime(2026, 7, 19, 6, tzinfo=UTC),
        )
        with self.settings(TIME_ZONE="UTC"):
            response = self.client.get(
                reverse("calendarization_dashboard"),
                {"calendar_week": "2026-07-13", "calendar_date": "2026-07-19"},
            )
        self.assertContains(response, "Día original")
        self.assertContains(response, "card-kpi")

    def test_todays_plan_detail_uses_official_dailyplan_ui_and_embeds_meal_check_in(self):
        meal = Meal.objects.create(name="Almuerzo snapshot", created_by=self.user)
        food = Food.objects.create(
            name="Arroz integral",
            protein=3,
            carbs=23,
            fat=1,
            created_by=self.user,
        )
        MealFood.objects.create(meal=meal, food=food, quantity=150, order=1)
        slot = DailyPlanMeal.objects.create(
            dailyplan=self.dailyplan,
            meal=meal,
            hour=time(13, 15),
            order=1,
        )
        today = timezone.localdate(timezone=UTC)
        day = self.activate(
            start_date=today,
            timezone_name="UTC",
            now=datetime.combine(today, time(6), tzinfo=UTC),
        ).calendarization.days.get(day_number=1)
        day_url = reverse("calendarization_day_detail", args=[day.id])
        meal_key = f"dailyplan_meal:{slot.id}"
        check_in_url = reverse(
            "calendarization_meal_check_in",
            args=[day.id, meal_key],
        )

        response = self.client.get(day_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-page="dailyplan-detail"')
        self.assertContains(response, 'class="card-title-comp js-header-meta-sentinel"')
        self.assertContains(response, 'class="dash-kpi-comp"', count=2)
        self.assertContains(response, "Tabla de comparación entre comidas")
        self.assertContains(response, "Detalle de cada Comida")
        self.assertContains(response, "Información de Alimentos")
        self.assertContains(response, "data-grid--calendarized-menu")
        self.assertContains(response, "Almuerzo snapshot")
        self.assertContains(response, "Arroz integral")
        self.assertContains(response, "13:15")
        self.assertContains(response, 'data-lucide="clock"')
        self.assertContains(response, 'class="structural-item structural-item--time"', count=1)
        self.assertContains(response, 'aria-label="Ver detalle"', count=2)
        self.assertContains(response, 'data-lucide="chevron-right"')
        self.assertContains(response, "Cumplimiento de esta comida", count=1)
        self.assertContains(response, "data-meal-checkin-status", count=1)
        self.assertContains(response, f'name="return_to" value="{day_url}"', count=2)
        self.assertNotContains(response, "calendarization-hero")
        self.assertNotContains(response, "calendarization-macros")

        completed = self.client.post(
            check_in_url,
            {
                "action": "completed",
                "idempotency_key": "web-day-status-0001",
                "return_to": day_url,
            },
        )
        self.assertRedirects(completed, day_url)
        noted = self.client.post(
            check_in_url,
            {
                "action": "note",
                "note": "Todo según lo planificado.",
                "idempotency_key": "web-day-note-0001",
                "return_to": day_url,
            },
        )
        self.assertRedirects(noted, day_url)

        updated = self.client.get(day_url)
        self.assertContains(updated, "Todo según lo planificado.")
        self.assertTrue(updated.context["vm"]["content"]["meal_entries"][0]["checkin"]["completed"])
        self.assertEqual(
            CalendarizedMealExecution.objects.filter(calendarized_day=day).count(),
            2,
        )

    def test_plan_detail_hides_check_in_outside_today_and_external_return_is_rejected(self):
        meal = Meal.objects.create(name="Cena futura", created_by=self.user)
        slot = DailyPlanMeal.objects.create(
            dailyplan=self.dailyplan,
            meal=meal,
            hour=time(20),
            order=1,
        )
        tomorrow = timezone.localdate(timezone=UTC) + timedelta(days=1)
        day = self.activate(
            start_date=tomorrow,
            timezone_name="UTC",
            now=datetime.combine(tomorrow - timedelta(days=1), time(6), tzinfo=UTC),
        ).calendarization.days.get(day_number=1)
        meal_key = f"dailyplan_meal:{slot.id}"
        day_url = reverse("calendarization_day_detail", args=[day.id])
        meal_url = reverse("calendarization_meal_detail", args=[day.id, meal_key])
        check_in_url = reverse(
            "calendarization_meal_check_in",
            args=[day.id, meal_key],
        )

        response = self.client.get(day_url)
        self.assertNotContains(response, "Cumplimiento de esta comida")

        posted = self.client.post(
            check_in_url,
            {
                "action": "completed",
                "idempotency_key": "web-external-return-0001",
                "return_to": "https://attacker.example/steal",
            },
        )
        self.assertRedirects(posted, meal_url)
        self.assertFalse(CalendarizedMealExecution.objects.exists())

    def test_web_meal_check_in_uses_persisted_execution_and_updates_indicators(self):
        meal = Meal.objects.create(name="Desayuno de hoy", created_by=self.user)
        slot = DailyPlanMeal.objects.create(
            dailyplan=self.dailyplan,
            meal=meal,
            hour=time(8),
            order=1,
        )
        today = timezone.localdate(timezone=UTC)
        calendarization = self.activate(
            start_date=today,
            timezone_name="UTC",
            now=datetime.combine(today, time(6), tzinfo=UTC),
        ).calendarization
        day = calendarization.days.get(day_number=1)
        meal_key = f"dailyplan_meal:{slot.id}"
        detail_url = reverse(
            "calendarization_meal_detail",
            args=[day.id, meal_key],
        )
        check_in_url = reverse(
            "calendarization_meal_check_in",
            args=[day.id, meal_key],
        )

        dashboard = self.client.get(
            reverse("calendarization_dashboard"),
            {
                "calendar_week": (today - timedelta(days=today.weekday())).isoformat(),
                "calendar_date": today.isoformat(),
            },
        )
        self.assertContains(dashboard, detail_url)
        self.assertContains(dashboard, 'data-lucide="chevron-right"')

        completed_payload = {
            "action": "completed",
            "idempotency_key": "web-status-test-0001",
        }
        completed = self.client.post(check_in_url, completed_payload)
        self.assertRedirects(completed, detail_url)
        retried = self.client.post(check_in_url, completed_payload)
        self.assertRedirects(retried, detail_url)
        note = self.client.post(
            check_in_url,
            {
                "action": "note",
                "idempotency_key": "web-note-test-0001",
                "note": "Cumplida sin reemplazos.",
            },
        )
        self.assertRedirects(note, detail_url)

        events = CalendarizedMealExecution.objects.filter(calendarized_day=day)
        self.assertEqual(events.count(), 2)
        self.assertEqual(events.filter(action="completed").count(), 1)
        self.assertEqual(events.filter(action="note").get().note, "Cumplida sin reemplazos.")

        detail = self.client.get(detail_url)
        self.assertContains(detail, "Cumplimiento de esta comida")
        self.assertContains(detail, "Comida cumplida")
        self.assertContains(detail, "Guardar nota")
        self.assertContains(detail, 'class="structural-item structural-item--time"')
        self.assertContains(detail, 'data-lucide="clock"')
        self.assertNotContains(detail, "calendarization-meal-detail__time")
        self.assertContains(detail, "Cumplida sin reemplazos.")
        self.assertContains(detail, 'data-lucide="check"')
        self.assertContains(detail, 'data-lucide="notebook-pen"')

        dashboard = self.client.get(
            reverse("calendarization_dashboard"),
            {
                "calendar_week": (today - timedelta(days=today.weekday())).isoformat(),
                "calendar_date": today.isoformat(),
            },
        )
        self.assertContains(dashboard, 'data-lucide="check-check"')
        self.assertContains(dashboard, 'data-lucide="notebook-pen"')
        self.assertContains(dashboard, "1/1")
        self.assertContains(dashboard, "100%")

    def test_scheduled_program_exposes_todays_meal_check_in_and_activates_on_submit(self):
        meal = Meal.objects.create(name="Desayuno programado", created_by=self.user)
        slot = DailyPlanMeal.objects.create(
            dailyplan=self.dailyplan,
            meal=meal,
            hour=time(8),
            order=1,
        )
        today = timezone.localdate(timezone=UTC)
        calendarization = self.activate(
            start_date=today,
            timezone_name="UTC",
            now=datetime.combine(today - timedelta(days=1), time(6), tzinfo=UTC),
        ).calendarization
        day = calendarization.days.get(day_number=1)
        meal_key = f"dailyplan_meal:{slot.id}"
        detail_url = reverse("calendarization_meal_detail", args=[day.id, meal_key])

        detail = self.client.get(detail_url)
        self.assertContains(detail, "Cumplimiento de esta comida")
        response = self.client.post(
            reverse("calendarization_meal_check_in", args=[day.id, meal_key]),
            {
                "action": "completed",
                "idempotency_key": "scheduled-status-test-0001",
            },
        )

        self.assertRedirects(response, detail_url)
        calendarization.refresh_from_db()
        self.assertEqual(calendarization.status, ProgramCalendarization.STATUS_ACTIVE)
        self.assertTrue(CalendarizedMealExecution.objects.filter(calendarized_day=day).exists())

    def test_web_meal_check_in_rejects_another_users_day(self):
        meal = Meal.objects.create(name="Comida privada", created_by=self.user)
        slot = DailyPlanMeal.objects.create(
            dailyplan=self.dailyplan,
            meal=meal,
            hour=time(8),
            order=1,
        )
        today = timezone.localdate()
        day = self.activate(
            start_date=today,
            timezone_name="UTC",
            now=datetime.combine(today, time(6), tzinfo=UTC),
        ).calendarization.days.get(day_number=1)
        self.client.force_login(self.other)

        response = self.client.post(
            reverse(
                "calendarization_meal_check_in",
                args=[day.id, f"dailyplan_meal:{slot.id}"],
            ),
            {"action": "completed"},
        )

        self.assertEqual(response.status_code, 404)
        self.assertFalse(CalendarizedMealExecution.objects.exists())

    def test_active_meal_header_exposes_change_time_and_web_form_updates_snapshot(self):
        meal = Meal.objects.create(name="Almuerzo activo", created_by=self.user)
        slot = DailyPlanMeal.objects.create(
            dailyplan=self.dailyplan,
            meal=meal,
            hour=time(13),
            order=1,
        )
        day = self.activate(
            start_date=date(2026, 7, 20),
            timezone_name="UTC",
            now=datetime(2026, 7, 19, 12, tzinfo=UTC),
        ).calendarization.days.get(day_number=1)
        meal_key = f"dailyplan_meal:{slot.id}"
        detail_url = reverse("calendarization_meal_detail", args=[day.id, meal_key])
        change_url = reverse("calendarization_meal_change_time", args=[day.id, meal_key])
        rename_url = reverse("calendarization_meal_rename", args=[day.id, meal_key])

        detail = self.client.get(detail_url)
        form = self.client.get(change_url)
        updated = self.client.post(
            change_url,
            {"hour": "14:10", "note": "Este campo legacy debe ignorarse"},
        )

        self.assertContains(detail, "Cambiar hora")
        self.assertContains(detail, change_url)
        self.assertContains(detail, "Renombrar")
        self.assertContains(detail, rename_url)
        self.assertContains(detail, "13:00")
        action_keys = [action["key"] for action in detail.context["vm"]["content"]["header"]["actions"]]
        self.assertEqual(
            action_keys,
            ["calendarization_history", "rename", "change_time"],
        )
        self.assertContains(form, "plan activo")
        self.assertNotContains(form, 'name="note"')
        self.assertEqual(list(form.context["form"].fields), ["hour"])
        self.assertRedirects(updated, detail_url)
        day.refresh_from_db()
        self.assertEqual(day.plan_snapshot["meals"][0]["hour"], "14:10")
        self.assertEqual(day.plan_snapshot["meals"][0].get("note", ""), "")

    def test_active_plan_and_meal_headers_rename_only_the_day_snapshot(self):
        meal = Meal.objects.create(name="Cena original", created_by=self.user)
        slot = DailyPlanMeal.objects.create(
            dailyplan=self.dailyplan,
            meal=meal,
            hour=time(20),
            order=1,
        )
        day = self.activate(
            start_date=date(2026, 7, 20),
            timezone_name="UTC",
            now=datetime(2026, 7, 19, 12, tzinfo=UTC),
        ).calendarization.days.get(day_number=1)
        meal_key = f"dailyplan_meal:{slot.id}"
        day_detail_url = reverse("calendarization_day_detail", args=[day.id])
        day_rename_url = reverse("calendarization_day_rename", args=[day.id])
        meal_detail_url = reverse(
            "calendarization_meal_detail",
            args=[day.id, meal_key],
        )
        meal_rename_url = reverse(
            "calendarization_meal_rename",
            args=[day.id, meal_key],
        )

        day_detail = self.client.get(day_detail_url)
        day_form = self.client.get(day_rename_url)
        renamed_day = self.client.post(
            day_rename_url,
            {"name": "Plan activo personalizado"},
        )
        meal_form = self.client.get(meal_rename_url)
        renamed_meal = self.client.post(
            meal_rename_url,
            {"name": "Cena activa personalizada"},
        )

        self.assertContains(day_detail, "Renombrar")
        self.assertContains(day_detail, day_rename_url)
        day_action_keys = [action["key"] for action in day_detail.context["vm"]["content"]["header"]["actions"]]
        self.assertEqual(day_action_keys, ["calendarization_history", "rename"])
        self.assertContains(day_form, "Renombrar plan activo")
        self.assertContains(meal_form, "Renombrar comida activa")
        self.assertRedirects(renamed_day, day_detail_url)
        self.assertRedirects(renamed_meal, meal_detail_url)

        day.refresh_from_db()
        self.dailyplan.refresh_from_db()
        meal.refresh_from_db()
        self.assertEqual(day.plan_snapshot["name"], "Plan activo personalizado")
        self.assertEqual(
            day.plan_snapshot["meals"][0]["name"],
            "Cena activa personalizada",
        )
        self.assertEqual(self.dailyplan.name, "Día original")
        self.assertEqual(meal.name, "Cena original")

    def test_push_subscription_rejects_malformed_json_shape(self):
        response = self.client.post(
            reverse("calendarization_push_subscribe"),
            data="[]",
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_push_subscription_requires_csrf(self):
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.user)
        response = csrf_client.post(
            reverse("calendarization_push_subscribe"),
            data='{"endpoint":"https://push.example.com/x","keys":{"p256dh":"p","auth":"a"}}',
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)

    def test_service_worker_contains_push_handlers(self):
        response = self.client.get(reverse("pwa_service_worker"))
        self.assertContains(response, 'addEventListener("push"')
        self.assertContains(response, 'addEventListener("notificationclick"')


class CalendarizationManagementCommandTests(TestCase):
    @override_settings(MYSCOOPE_WEB_PUSH_ENABLED=False)
    def test_dispatch_command_is_safe_when_push_is_disabled(self):
        call_command("dispatch_calendar_notifications", limit=5)

    @override_settings(MYSCOOPE_WEB_PUSH_ENABLED=False)
    def test_background_worker_supports_one_shot_health_run(self):
        call_command("run_calendar_notification_worker", once=True, interval=30, limit=5)
