from types import SimpleNamespace
from unittest import TestCase

from notas.application.services.comparisons.constants import MIN_COMPARATOR_SLOTS
from notas.application.services.comparisons.payloads import (
    normalize_payload,
    payload_has_enough_items,
    selected_payload_from_selections,
    selection_rows_from_params,
)


class ComparatorPayloadTests(TestCase):
    def test_normalize_payload_ignores_invalid_rows(self):
        payload = [
            {"id": "3", "quantity": "120"},
            {"id": "0", "quantity": "90"},
            {"id": "bad"},
            "not-a-row",
        ]

        self.assertEqual(
            normalize_payload(payload, include_quantities=True),
            [{"id": 3, "quantity": 120.0}],
        )

    def test_normalize_payload_uses_quantity_fallback(self):
        self.assertEqual(
            normalize_payload([{"id": 8, "quantity": "-1"}], include_quantities=True),
            [{"id": 8, "quantity": 100.0}],
        )

    def test_selection_rows_from_params_supports_add_action(self):
        rows = selection_rows_from_params(
            {
                "item_1": "10",
                "item_2": "20",
                "comparator_action": "add",
            },
            include_quantities=False,
        )

        self.assertEqual(len(rows), MIN_COMPARATOR_SLOTS + 1)
        self.assertEqual([row["id"] for row in rows], [10, 20, None])

    def test_selection_rows_from_params_removes_middle_and_compacts(self):
        rows = selection_rows_from_params(
            {
                "item_1": "10",
                "item_2": "20",
                "item_3": "30",
                "remove_index": "1",
            },
            include_quantities=False,
        )

        self.assertEqual([row["id"] for row in rows], [10, 30])

    def test_selection_rows_from_params_never_drops_below_two_rows(self):
        rows = selection_rows_from_params(
            {
                "item_1": "10",
                "item_2": "20",
                "remove_index": "0",
            },
            include_quantities=False,
        )

        self.assertEqual(len(rows), MIN_COMPARATOR_SLOTS)
        self.assertEqual([row["id"] for row in rows], [10, 20])

    def test_selection_rows_from_params_preserves_food_quantities_when_removing(self):
        rows = selection_rows_from_params(
            {
                "item_1": "10",
                "qty_1": "90",
                "item_2": "20",
                "qty_2": "100",
                "item_3": "30",
                "qty_3": "150",
                "remove_index": "1",
            },
            include_quantities=True,
        )

        self.assertEqual(rows, [{"id": 10, "quantity": 90.0}, {"id": 30, "quantity": 150.0}])

    def test_selected_payload_from_selections_skips_empty_rows(self):
        selections = [
            SimpleNamespace(id=10, quantity=90),
            SimpleNamespace(id=None, quantity=100),
            SimpleNamespace(id=30, quantity=150),
        ]

        self.assertEqual(
            selected_payload_from_selections(selections, include_quantities=True),
            [{"id": 10, "quantity": 90.0}, {"id": 30, "quantity": 150.0}],
        )

    def test_payload_has_enough_items_matches_save_requirement(self):
        self.assertFalse(payload_has_enough_items([{"id": 10}]))
        self.assertTrue(payload_has_enough_items([{"id": 10}, {"id": 20}]))
