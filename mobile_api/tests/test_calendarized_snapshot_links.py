from zoneinfo import ZoneInfo

from django.utils import timezone

from mobile_api.tests.base import AuthenticatedMobileAPITestCase
from notas.domain.models import CalendarizedDay, Food, Meal, MealFood, ProgramCalendarization


class CalendarizedSnapshotLinkTests(AuthenticatedMobileAPITestCase):
    def test_day_detail_resolves_food_from_legacy_meal_food_key(self):
        today = timezone.localdate(timezone=ZoneInfo("UTC"))
        meal = Meal.objects.create(name="Comida enlazada", created_by=self.user, is_draft=False)
        food = Food.objects.create(name="Avena enlazada", protein=10, carbs=50, fat=6, created_by=self.user)
        meal_food = MealFood.objects.create(meal=meal, food=food, quantity=80)
        calendarization = ProgramCalendarization.objects.create(
            user=self.user,
            program_name_snapshot="Programa activo",
            start_date=today,
            end_date=today,
            timezone_name="UTC",
            status=ProgramCalendarization.STATUS_ACTIVE,
        )
        day = CalendarizedDay.objects.create(
            calendarization=calendarization,
            calendar_date=today,
            week_number=1,
            day_number=1,
            plan_snapshot={
                "name": "Plan con snapshot legado",
                "totals": {},
                "meals": [
                    {
                        "key": "meal-1",
                        "name": meal.name,
                        "foods": [{"key": f"meal_food:{meal_food.id}", "name": food.name, "quantity_g": 80}],
                        "totals": {},
                    }
                ],
            },
        )

        response = self.client.get(f"/api/v1/program/days/{day.id}")

        self.assertEqual(response.status_code, 200)
        food_payload = response.json()["data"]["plan_snapshot"]["meals"][0]["foods"][0]
        self.assertEqual(food_payload["detail_id"], food.id)
