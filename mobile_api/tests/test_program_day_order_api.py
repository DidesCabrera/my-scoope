from mobile_api.tests.base import AuthenticatedMobileAPITestCase
from notas.domain.models import DailyPlan, Program, ProgramDay


class ProgramDayOrderAPITests(AuthenticatedMobileAPITestCase):
    def test_reorders_days_and_rejects_incomplete_order(self):
        program = Program.objects.create(name="Programa editable", created_by=self.user, duration_weeks=1)
        first_plan = DailyPlan.objects.create(
            name="Primer día", created_by=self.user, is_draft=False, source=DailyPlan.SOURCE_PROGRAM
        )
        third_plan = DailyPlan.objects.create(
            name="Tercer día", created_by=self.user, is_draft=False, source=DailyPlan.SOURCE_PROGRAM
        )
        first_day = ProgramDay.objects.create(program=program, dailyplan=first_plan, week_number=1, day_number=1)
        third_day = ProgramDay.objects.create(program=program, dailyplan=third_plan, week_number=1, day_number=3)
        endpoint = f"/api/v1/library/programs/{program.id}/weeks/1/days/order"

        invalid_response = self.client.put(
            endpoint,
            data={"ordered_ids": [1, 2]},
            content_type="application/json",
        )
        valid_response = self.client.put(
            endpoint,
            data={"ordered_ids": [3, 2, 1, 4, 5, 6, 7]},
            content_type="application/json",
        )

        self.assertEqual(invalid_response.status_code, 422)
        self.assertEqual(valid_response.status_code, 200)
        first_day.refresh_from_db()
        third_day.refresh_from_db()
        self.assertEqual(first_day.day_number, 3)
        self.assertEqual(third_day.day_number, 1)
