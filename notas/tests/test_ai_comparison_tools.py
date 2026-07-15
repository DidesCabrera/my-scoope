from django.contrib.auth.models import User
from django.test import TestCase

from notas.application.ai_tools.comparison_tools import (
    list_saved_comparisons_tool,
    read_saved_comparison_tool,
)
from notas.domain.models import SavedComparison


class AIComparisonToolsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="felipe", password="secret")
        self.other_user = User.objects.create_user(username="other", password="secret")
        self.comparison = SavedComparison.objects.create(
            owner=self.user,
            kind=SavedComparison.KIND_DAILYPLANS,
            name="Plan actual vs propuesta",
            payload=[{"id": 1}, {"id": 2}],
            snapshot_payload=[
                {"id": 1, "name": "Plan actual", "values": {"total_kcal": 2100, "protein": 130}},
                {"id": 2, "name": "Propuesta", "values": {"total_kcal": 2300, "protein": 150}},
            ],
        )
        SavedComparison.objects.create(
            owner=self.other_user,
            kind=SavedComparison.KIND_DAILYPLANS,
            name="Privada",
            payload=[{"id": 9}, {"id": 10}],
        )

    def test_list_saved_comparisons_is_owner_scoped_and_read_only(self):
        result = list_saved_comparisons_tool(self.user, kind="dailyplans")

        self.assertTrue(result.ok)
        comparisons = result.data["saved_comparisons"]
        self.assertEqual(len(comparisons), 1)
        self.assertEqual(comparisons[0]["id"], self.comparison.id)
        self.assertEqual(comparisons[0]["name"], "Plan actual vs propuesta")
        self.assertEqual(comparisons[0]["item_count"], 2)
        self.assertFalse(result.data["source_boundary"]["writes_allowed"])
        self.assertTrue(result.data["source_boundary"]["owner_scoped"])

    def test_read_saved_comparison_returns_snapshot_and_card(self):
        result = read_saved_comparison_tool(self.user, comparison_id=self.comparison.id)

        self.assertTrue(result.ok)
        saved_comparison = result.data["saved_comparison"]
        self.assertEqual(saved_comparison["id"], self.comparison.id)
        self.assertEqual(saved_comparison["snapshot_payload"][0]["name"], "Plan actual")
        card = result.data["comparison_card"]
        self.assertEqual(card["type"], "saved_comparison_card")
        self.assertEqual(card["status"], "snapshot")
        self.assertEqual(card["items"][1]["values"]["protein"], 150.0)
        self.assertFalse(card["source_boundary"]["writes_allowed"])

    def test_read_saved_comparison_blocks_other_users_comparison(self):
        result = read_saved_comparison_tool(self.other_user, comparison_id=self.comparison.id)

        self.assertFalse(result.ok)
        self.assertEqual(result.error.code, "not_found")
