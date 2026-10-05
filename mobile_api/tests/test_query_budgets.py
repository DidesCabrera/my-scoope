from __future__ import annotations

from django.db import connection
from django.test import override_settings
from django.test.utils import CaptureQueriesContext

from mobile_api.tests.base import AuthenticatedMobileAPITestCase
from notas.domain.models import Program


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

    def test_today_query_budget(self) -> None:
        self.assert_get_query_budget("/api/v1/today", maximum=18)

    def test_home_query_budget(self) -> None:
        self.assert_get_query_budget("/api/v1/home", maximum=24)

    def test_active_program_query_budget(self) -> None:
        self.assert_get_query_budget("/api/v1/program/active", maximum=18)

    def test_library_programs_query_budget(self) -> None:
        self.assert_get_query_budget("/api/v1/library/programs", maximum=18)

    def test_library_program_query_budget_does_not_grow_per_item(self) -> None:
        Program.objects.bulk_create(
            [Program(name=f"Programa {index}", created_by=self.user) for index in range(20)]
        )

        self.assert_get_query_budget("/api/v1/library/programs?limit=12", maximum=10)
