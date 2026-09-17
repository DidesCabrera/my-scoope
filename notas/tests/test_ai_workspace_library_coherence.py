from django.contrib.auth.models import User
from django.test import TestCase

from notas.application.ai_tools.workspace_query_tools import query_workspace_tool
from notas.domain.models import DailyPlan, DailyPlanMeal, Food, Meal, Program


class AIWorkspaceLibraryCoherenceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="library-user", password="pass123")

    def test_food_collection_reports_exact_total_and_pages_without_silent_truncation(self):
        for index in range(1, 11):
            Food.objects.create(
                name=f"Papa {index:02d}",
                protein=2,
                carbs=20,
                fat=0,
                created_by=self.user,
            )
        for index in range(1, 4):
            Food.objects.create(
                name=f"Vinagre {index:02d}",
                protein=0,
                carbs=1,
                fat=0,
                created_by=self.user,
            )
        Food.objects.create(
            name="Oculto",
            protein=0,
            carbs=0,
            fat=0,
            created_by=self.user,
            is_active=False,
        )

        first = query_workspace_tool(self.user, resource="foods", limit=8)
        second = query_workspace_tool(self.user, resource="foods", limit=8, offset=8)

        self.assertTrue(first.ok)
        self.assertEqual(first.data["scope"], "library")
        self.assertEqual(first.data["total_count"], 13)
        self.assertEqual(first.data["returned_count"], 8)
        self.assertTrue(first.data["has_more"])
        self.assertEqual(first.data["next_offset"], 8)
        self.assertEqual(second.data["total_count"], 13)
        self.assertEqual(second.data["returned_count"], 5)
        self.assertFalse(second.data["has_more"])
        self.assertTrue(any(item["name"].startswith("Vinagre") for item in second.data["foods"]))

    def test_meal_collection_matches_standalone_non_draft_library(self):
        for index in range(32):
            Meal.objects.create(
                name=f"Comida {index + 1:02d}",
                created_by=self.user,
                is_draft=False,
            )
        Meal.objects.create(name="Borrador", created_by=self.user, is_draft=True)
        embedded = Meal.objects.create(
            name="Snapshot interno",
            created_by=self.user,
            is_draft=False,
        )
        plan = DailyPlan.objects.create(
            name="Plan visible",
            created_by=self.user,
            is_draft=False,
        )
        DailyPlanMeal.objects.create(dailyplan=plan, meal=embedded)

        result = query_workspace_tool(self.user, resource="meals", limit=8)

        self.assertTrue(result.ok)
        self.assertEqual(result.data["total_count"], 32)
        self.assertEqual(result.data["returned_count"], 8)
        self.assertTrue(result.data["has_more"])
        self.assertNotIn("Snapshot interno", {item["name"] for item in result.data["meals"]})

    def test_dailyplan_collection_excludes_drafts_and_program_snapshots(self):
        for index in range(4):
            DailyPlan.objects.create(
                name=f"Plan {index + 1}",
                created_by=self.user,
                is_draft=False,
            )
        DailyPlan.objects.create(
            name="Borrador",
            created_by=self.user,
            is_draft=True,
        )
        DailyPlan.objects.create(
            name="Snapshot de programa",
            created_by=self.user,
            is_draft=False,
            source=DailyPlan.SOURCE_PROGRAM,
        )

        result = query_workspace_tool(self.user, resource="dailyplans")

        self.assertTrue(result.ok)
        self.assertEqual(result.data["total_count"], 4)
        self.assertEqual(result.data["returned_count"], 4)
        self.assertFalse(result.data["has_more"])

    def test_program_collection_uses_visible_library_and_marks_editability(self):
        Program.objects.create(name="Programa 1", created_by=self.user)
        Program.objects.create(name="Programa 2", created_by=self.user)

        result = query_workspace_tool(self.user, resource="programs")

        self.assertTrue(result.ok)
        self.assertEqual(result.data["total_count"], 2)
        self.assertTrue(all(item["editable"] for item in result.data["programs"]))
