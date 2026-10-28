from __future__ import annotations

from datetime import timedelta

from django.db import connection
from django.test import override_settings
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from mobile_api.tests.base import AuthenticatedMobileAPITestCase
from notas.domain.models import (
    CalendarizedDay,
    DailyPlan,
    DailyPlanMeal,
    Food,
    FoodLocalizedName,
    Meal,
    MealFood,
    Program,
    ProgramCalendarization,
)


@override_settings(NUTRITION_ONBOARDING_GATE_ENABLED=False)
class MobileAPIQueryBudgetTests(AuthenticatedMobileAPITestCase):
    """Prevent read-heavy mobile entry points from accumulating hidden N+1 queries."""

    def assert_get_query_budget(self, path: str, maximum: int) -> None:
        with CaptureQueriesContext(connection) as captured:
            response = self.client.get(path)

        self.assertEqual(response.status_code, 200, response.content)
        self.assertLessEqual(
            len(captured),
            maximum,
            f"{path} used {len(captured)} queries; budget is {maximum}\n"
            + "\n".join(query["sql"] for query in captured.captured_queries),
        )

    def query_count(self, method: str, path: str, *, data=None) -> int:
        with CaptureQueriesContext(connection) as captured:
            response = getattr(self.client, method)(path, data=data, content_type="application/json")
        self.assertEqual(response.status_code, 200, response.content)
        return len(captured)

    def test_today_query_budget(self) -> None:
        self.assert_get_query_budget("/api/v1/today", maximum=18)

    def test_home_query_budget(self) -> None:
        self.assert_get_query_budget("/api/v1/home", maximum=24)

    def test_home_summary_query_budget(self) -> None:
        self.assert_get_query_budget("/api/v1/home/summary", maximum=18)

    def test_active_program_query_budget(self) -> None:
        self.assert_get_query_budget("/api/v1/program/active", maximum=18)

    def test_calendar_read_query_budgets(self) -> None:
        self.assert_get_query_budget("/api/v1/calendar?days=42", maximum=10)
        self.assert_get_query_budget("/api/v1/calendar/progress", maximum=10)

    def test_calendar_query_count_does_not_grow_per_planned_day(self) -> None:
        today = timezone.localdate()
        monday = today - timedelta(days=today.weekday())
        empty_overview = self.query_count("get", "/api/v1/calendar?days=42")
        empty_progress = self.query_count("get", "/api/v1/calendar/progress")
        CalendarizedDay.objects.bulk_create([
            CalendarizedDay(
                user=self.user,
                calendar_date=monday + timedelta(days=index),
                source_kind=CalendarizedDay.SOURCE_MANUAL,
                plan_snapshot={"name": f"Plan {index}", "meals": [{"key": f"meal-{index}"}]},
            )
            for index in range(42)
        ])

        self.assertLessEqual(self.query_count("get", "/api/v1/calendar?days=42"), empty_overview + 1)
        self.assertLessEqual(self.query_count("get", "/api/v1/calendar/progress"), empty_progress + 1)

    def test_library_programs_query_budget(self) -> None:
        self.assert_get_query_budget("/api/v1/library/programs", maximum=18)

    def test_library_program_query_budget_does_not_grow_per_item(self) -> None:
        Program.objects.bulk_create(
            [Program(name=f"Programa {index}", created_by=self.user) for index in range(20)]
        )

        self.assert_get_query_budget("/api/v1/library/programs?limit=12", maximum=10)

    def test_food_picker_query_budget_does_not_grow_with_localized_items(self) -> None:
        foods = [
            Food.objects.create(
                name=f"Food {index}",
                protein=10,
                carbs=20,
                fat=5,
                created_by=self.user,
            )
            for index in range(20)
        ]
        FoodLocalizedName.objects.bulk_create(
            [
                FoodLocalizedName(
                    food=food,
                    name=f"Alimento {index}",
                    normalized_name=f"alimento {index}",
                    language="es",
                    country="CL",
                    is_primary=True,
                )
                for index, food in enumerate(foods)
            ]
        )

        self.assert_get_query_budget("/api/v1/foods?limit=20", maximum=8)

    def test_today_query_count_does_not_grow_per_calendarized_day(self) -> None:
        today = timezone.localdate()
        program = Program.objects.create(name="Programa activo", created_by=self.user, duration_weeks=1)
        calendarization = ProgramCalendarization.objects.create(
            user=self.user,
            source_program=program,
            program_name_snapshot=program.name,
            start_date=today - timedelta(days=6),
            end_date=today,
            timezone_name="UTC",
            status=ProgramCalendarization.STATUS_ACTIVE,
        )

        def create_day(offset: int) -> None:
            CalendarizedDay.objects.create(
                calendarization=calendarization,
                calendar_date=today - timedelta(days=offset),
                week_number=1,
                day_number=7 - offset,
                plan_snapshot={"name": f"Día {offset}", "meals": [{"key": f"meal-{offset}"}]},
            )

        create_day(0)
        one_day_queries = self.query_count("get", "/api/v1/today")
        for offset in range(1, 7):
            create_day(offset)
        seven_day_queries = self.query_count("get", "/api/v1/today")

        self.assertLessEqual(seven_day_queries, one_day_queries + 1)

    def test_program_preview_query_count_does_not_grow_per_selected_day(self) -> None:
        program = Program.objects.create(
            name="Programa editable",
            created_by=self.user,
            duration_weeks=1,
            is_draft=False,
        )
        dailyplan = DailyPlan.objects.create(
            name="Plan seleccionable",
            created_by=self.user,
            is_draft=False,
        )
        meal = Meal.objects.create(name="Comida", created_by=self.user, is_draft=False)
        food = Food.objects.create(name="Avena", protein=10, carbs=20, fat=5, created_by=self.user)
        DailyPlanMeal.objects.create(dailyplan=dailyplan, meal=meal)
        MealFood.objects.create(meal=meal, food=food, quantity=100)
        path = f"/api/v1/library/programs/{program.id}/daily-plan-picker/preview"

        one_day_queries = self.query_count(
            "post",
            path,
            data={"dailyplan_id": dailyplan.id, "week_number": 1, "day_numbers": [1]},
        )
        seven_day_queries = self.query_count(
            "post",
            path,
            data={"dailyplan_id": dailyplan.id, "week_number": 1, "day_numbers": list(range(1, 8))},
        )

        self.assertLessEqual(seven_day_queries, one_day_queries)
