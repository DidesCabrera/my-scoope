from datetime import timedelta
from zoneinfo import ZoneInfo

from django.contrib.auth.models import User
from django.test import Client, override_settings
from django.utils import timezone

from mobile_api.tests.base import AuthenticatedMobileAPITestCase
from notas.application.services.mcp_user_tokens import create_mcp_user_token
from notas.application.services.oauth_device_sessions import MOBILE_SCOPE_READ, MOBILE_SCOPE_WRITE
from notas.domain.models import (
    CalendarizationRevision,
    CalendarizedDay,
    DailyPlan,
    DailyPlanMeal,
    Meal,
    Program,
    ProgramCalendarization,
)


@override_settings(NUTRITION_ONBOARDING_GATE_ENABLED=False)
class MobileAPICalendarizationEditTests(AuthenticatedMobileAPITestCase):
    def test_future_day_picker_assigns_snapshot_and_records_applied_revision_without_mutating_template(self):
        today = timezone.localdate(timezone=ZoneInfo("UTC"))
        template = Program.objects.create(
            name="Plantilla original",
            created_by=self.user,
            duration_weeks=1,
            is_draft=False,
        )
        dailyplan = DailyPlan.objects.create(
            name="Plan futuro de biblioteca",
            created_by=self.user,
            is_draft=False,
        )
        calendarization = ProgramCalendarization.objects.create(
            user=self.user,
            source_program=template,
            program_name_snapshot=template.name,
            start_date=today,
            end_date=today + timedelta(days=6),
            timezone_name="UTC",
            status=ProgramCalendarization.STATUS_ACTIVE,
        )
        day = CalendarizedDay.objects.create(
            calendarization=calendarization,
            calendar_date=today + timedelta(days=1),
            week_number=1,
            day_number=1,
        )

        preview = self.client.post(
            f"/api/v1/program/days/{day.id}/daily-plan-picker/preview",
            data={"dailyplan_id": dailyplan.id},
            content_type="application/json",
        )
        commit = self.client.post(
            f"/api/v1/program/days/{day.id}/daily-plan-picker/commit",
            data={"dailyplan_id": dailyplan.id, "idempotency_key": "active-day-assignment-01"},
            content_type="application/json",
        )

        self.assertEqual(preview.status_code, 200)
        self.assertFalse(preview.json()["data"]["confirmation_required"])
        self.assertEqual(preview.json()["data"]["result"]["name"], dailyplan.name)
        self.assertEqual(commit.status_code, 200)
        day.refresh_from_db()
        template.refresh_from_db()
        self.assertEqual(day.plan_snapshot["name"], dailyplan.name)
        self.assertEqual(day.plan_snapshot["source"]["dailyplan_id"], dailyplan.id)
        self.assertEqual(day.source_dailyplan_id, dailyplan.id)
        self.assertIsNone(day.source_program_day_id)
        self.assertEqual(template.name, "Plantilla original")
        revision = CalendarizationRevision.objects.get(pk=commit.json()["data"]["created_id"])
        self.assertEqual(revision.status, CalendarizationRevision.STATUS_APPLIED)
        self.assertIsNone(revision.before_snapshot["days"][0]["plan_snapshot"])
        self.assertEqual(revision.after_snapshot["days"][0]["plan_snapshot"]["name"], dailyplan.name)

        retry = self.client.post(
            f"/api/v1/program/days/{day.id}/daily-plan-picker/commit",
            data={"dailyplan_id": dailyplan.id, "idempotency_key": "active-day-assignment-01", "confirm_replacement": True},
            content_type="application/json",
        )
        self.assertEqual(retry.status_code, 200)
        self.assertEqual(retry.json()["data"]["created_id"], revision.id)
        self.assertEqual(CalendarizationRevision.objects.count(), 1)

    def test_active_day_replacement_requires_confirmation_and_today_is_not_editable(self):
        today = timezone.localdate(timezone=ZoneInfo("UTC"))
        original = DailyPlan.objects.create(name="Plan anterior", created_by=self.user, is_draft=False)
        replacement = DailyPlan.objects.create(name="Plan reemplazo", created_by=self.user, is_draft=False)
        calendarization = ProgramCalendarization.objects.create(
            user=self.user,
            program_name_snapshot="Programa activo",
            start_date=today,
            end_date=today + timedelta(days=6),
            timezone_name="UTC",
            status=ProgramCalendarization.STATUS_ACTIVE,
        )
        future_day = CalendarizedDay.objects.create(
            calendarization=calendarization,
            calendar_date=today + timedelta(days=1),
            week_number=1,
            day_number=1,
            plan_snapshot={"schema_version": "calendarized_dailyplan.v1", "source": {"dailyplan_id": original.id}, "name": original.name, "meals": [], "totals": {}},
        )
        today_day = CalendarizedDay.objects.create(
            calendarization=calendarization,
            calendar_date=today,
            week_number=1,
            day_number=2,
        )

        preview = self.client.post(
            f"/api/v1/program/days/{future_day.id}/daily-plan-picker/preview",
            data={"dailyplan_id": replacement.id},
            content_type="application/json",
        )
        unconfirmed = self.client.post(
            f"/api/v1/program/days/{future_day.id}/daily-plan-picker/commit",
            data={"dailyplan_id": replacement.id, "idempotency_key": "active-day-replace-01"},
            content_type="application/json",
        )
        past_or_present = self.client.post(
            f"/api/v1/program/days/{today_day.id}/daily-plan-picker/preview",
            data={"dailyplan_id": replacement.id},
            content_type="application/json",
        )

        self.assertEqual(preview.status_code, 200)
        self.assertTrue(preview.json()["data"]["confirmation_required"])
        self.assertEqual(unconfirmed.status_code, 409)
        self.assertEqual(unconfirmed.json()["error"]["code"], "calendarized_day_plan_replacement_confirmation_required")
        self.assertEqual(past_or_present.status_code, 422)

    def test_calendarized_day_exposes_owned_meal_detail_links_without_mutating_snapshot(self):
        today = timezone.localdate(timezone=ZoneInfo("UTC"))
        dailyplan = DailyPlan.objects.create(name="Plan activo", created_by=self.user, is_draft=False)
        owned_meal = Meal.objects.create(name="Comida navegable", created_by=self.user, is_draft=False)
        owned_slot = DailyPlanMeal.objects.create(dailyplan=dailyplan, meal=owned_meal)
        other = User.objects.create_user(username="calendar-meal-owner")
        foreign_meal = Meal.objects.create(name="Comida ajena", created_by=other, is_draft=False)
        foreign_slot = DailyPlanMeal.objects.create(dailyplan=dailyplan, meal=foreign_meal)
        calendarization = ProgramCalendarization.objects.create(
            user=self.user,
            program_name_snapshot="Programa activo",
            start_date=today,
            end_date=today,
            timezone_name="UTC",
            status=ProgramCalendarization.STATUS_ACTIVE,
        )
        stored_snapshot = {
            "name": "Plan activo",
            "totals": {"protein_g": 150, "carbs_g": 200, "fat_g": 60},
            "meals": [
                {"key": f"dailyplan_meal:{owned_slot.id}", "name": owned_meal.name, "totals": {"protein_g": 30}},
                {"key": f"dailyplan_meal:{foreign_slot.id}", "name": foreign_meal.name, "totals": {"protein_g": 15}},
            ],
        }
        day = CalendarizedDay.objects.create(
            calendarization=calendarization,
            calendar_date=today,
            week_number=1,
            day_number=1,
            plan_snapshot=stored_snapshot,
        )

        response = self.client.get(f"/api/v1/program/days/{day.id}")

        self.assertEqual(response.status_code, 200)
        meals = response.json()["data"]["plan_snapshot"]["meals"]
        self.assertEqual(response.json()["data"]["plan_snapshot"]["totals"]["protein_per_kilogram"], 2.0)
        self.assertEqual(meals[0]["totals"]["protein_per_kilogram"], 0.4)
        self.assertEqual(meals[0]["detail_id"], owned_meal.id)
        self.assertNotIn("detail_id", meals[1])
        day.refresh_from_db()
        self.assertEqual(day.plan_snapshot, stored_snapshot)

    def test_active_meal_hour_endpoint_updates_only_the_owned_calendarized_day(self):
        today = timezone.localdate(timezone=ZoneInfo("UTC"))
        calendarization = ProgramCalendarization.objects.create(
            user=self.user,
            program_name_snapshot="Programa activo",
            start_date=today,
            end_date=today + timedelta(days=6),
            timezone_name="UTC",
            status=ProgramCalendarization.STATUS_ACTIVE,
        )
        day = CalendarizedDay.objects.create(
            calendarization=calendarization,
            calendar_date=today,
            week_number=1,
            day_number=1,
            plan_snapshot={
                "name": "Plan activo",
                "meals": [{"key": "dailyplan_meal:77", "name": "Cena", "hour": "20:00", "foods": []}],
                "totals": {},
            },
        )

        response = self.client.patch(
            f"/api/v1/program/days/{day.id}/meals/dailyplan_meal:77",
            data={"hour": "21:15"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["plan_snapshot"]["meals"][0]["hour"], "21:15")
        day.refresh_from_db()
        self.assertEqual(day.plan_snapshot["meals"][0]["hour"], "21:15")

        other_user = User.objects.create_user(username="other-hour-user")
        other_client = Client()
        other_token = create_mcp_user_token(
            user=other_user,
            name="Other hour token",
            scopes=[MOBILE_SCOPE_READ, MOBILE_SCOPE_WRITE],
            expires_at=timezone.now() + timedelta(minutes=15),
        )
        other_client.defaults["HTTP_AUTHORIZATION"] = f"Bearer {other_token.raw_token}"
        hidden = other_client.patch(
            f"/api/v1/program/days/{day.id}/meals/dailyplan_meal:77",
            data={"hour": "22:00"},
            content_type="application/json",
        )
        self.assertEqual(hidden.status_code, 404)

    def test_active_plan_and_meal_rename_endpoints_update_only_the_day_snapshot(self):
        today = timezone.localdate(timezone=ZoneInfo("UTC"))
        source_plan = DailyPlan.objects.create(
            name="Plan de biblioteca",
            created_by=self.user,
            is_draft=False,
        )
        source_meal = Meal.objects.create(
            name="Cena de biblioteca",
            created_by=self.user,
            is_draft=False,
        )
        source_slot = DailyPlanMeal.objects.create(
            dailyplan=source_plan,
            meal=source_meal,
        )
        calendarization = ProgramCalendarization.objects.create(
            user=self.user,
            program_name_snapshot="Programa activo",
            start_date=today,
            end_date=today + timedelta(days=6),
            timezone_name="UTC",
            status=ProgramCalendarization.STATUS_ACTIVE,
        )
        day = CalendarizedDay.objects.create(
            calendarization=calendarization,
            calendar_date=today,
            week_number=1,
            day_number=1,
            plan_snapshot={
                "source": {"dailyplan_id": source_plan.id},
                "name": source_plan.name,
                "meals": [
                    {
                        "key": f"dailyplan_meal:{source_slot.id}",
                        "name": source_meal.name,
                        "hour": "20:00",
                        "foods": [],
                    }
                ],
                "totals": {},
            },
        )
        meal_key = f"dailyplan_meal:{source_slot.id}"

        renamed_plan = self.client.patch(
            f"/api/v1/program/days/{day.id}",
            data={"name": "Plan activo personalizado"},
            content_type="application/json",
        )
        renamed_meal = self.client.patch(
            f"/api/v1/program/days/{day.id}/meals/{meal_key}/name",
            data={"name": "Cena activa personalizada"},
            content_type="application/json",
        )

        self.assertEqual(renamed_plan.status_code, 200)
        self.assertEqual(
            renamed_plan.json()["data"]["plan_snapshot"]["name"],
            "Plan activo personalizado",
        )
        self.assertEqual(renamed_meal.status_code, 200)
        self.assertEqual(
            renamed_meal.json()["data"]["plan_snapshot"]["meals"][0]["name"],
            "Cena activa personalizada",
        )
        day.refresh_from_db()
        source_plan.refresh_from_db()
        source_meal.refresh_from_db()
        self.assertEqual(day.plan_snapshot["name"], "Plan activo personalizado")
        self.assertEqual(
            day.plan_snapshot["meals"][0]["name"],
            "Cena activa personalizada",
        )
        self.assertEqual(source_plan.name, "Plan de biblioteca")
        self.assertEqual(source_meal.name, "Cena de biblioteca")

        invalid = self.client.patch(
            f"/api/v1/program/days/{day.id}",
            data={"name": "   "},
            content_type="application/json",
        )
        self.assertEqual(invalid.status_code, 422)

        other_user = User.objects.create_user(username="other-rename-user")
        other_client = Client()
        other_token = create_mcp_user_token(
            user=other_user,
            name="Other rename token",
            scopes=[MOBILE_SCOPE_READ, MOBILE_SCOPE_WRITE],
            expires_at=timezone.now() + timedelta(minutes=15),
        )
        other_client.defaults["HTTP_AUTHORIZATION"] = f"Bearer {other_token.raw_token}"
        hidden_plan = other_client.patch(
            f"/api/v1/program/days/{day.id}",
            data={"name": "No permitido"},
            content_type="application/json",
        )
        hidden_meal = other_client.patch(
            f"/api/v1/program/days/{day.id}/meals/{meal_key}/name",
            data={"name": "No permitido"},
            content_type="application/json",
        )
        self.assertEqual(hidden_plan.status_code, 404)
        self.assertEqual(hidden_meal.status_code, 404)
