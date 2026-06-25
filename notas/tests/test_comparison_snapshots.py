from types import SimpleNamespace
from unittest import TestCase

from notas.application.services.comparisons.snapshots import (
    comparable_rows_from_snapshot,
    normalize_snapshot_payload,
    selection_rows_from_snapshot,
    snapshot_payload_from_comparable_rows,
)


class ComparatorSnapshotTests(TestCase):
    def test_snapshot_payload_preserves_names_quantities_and_values(self):
        selection = SimpleNamespace(id=7, name="Atún", quantity=120)
        values = {"total_kcal": 132, "protein": 28, "unknown": 99}

        self.assertEqual(
            snapshot_payload_from_comparable_rows([(selection, values)], include_quantities=True),
            [
                {
                    "id": 7,
                    "name": "Atún",
                    "quantity": 120.0,
                    "values": {"total_kcal": 132.0, "protein": 28.0},
                }
            ],
        )

    def test_snapshot_payload_skips_incomplete_rows(self):
        rows = [
            (SimpleNamespace(id=None, name="Atún", quantity=120), {"total_kcal": 132}),
            (SimpleNamespace(id=8, name="", quantity=120), {"total_kcal": 132}),
            (SimpleNamespace(id=9, name="Pollo", quantity=100), {"total_kcal": 165}),
        ]

        self.assertEqual(
            snapshot_payload_from_comparable_rows(rows, include_quantities=True),
            [
                {
                    "id": 9,
                    "name": "Pollo",
                    "quantity": 100.0,
                    "values": {"total_kcal": 165.0},
                }
            ],
        )

    def test_normalize_snapshot_payload_uses_safe_defaults(self):
        payload = [
            {"id": "3", "name": "Avena", "quantity": "bad", "values": {"protein": "10.5"}},
            {"id": "bad", "name": "Invalid"},
        ]

        self.assertEqual(
            normalize_snapshot_payload(payload, include_quantities=True),
            [
                {
                    "id": 3,
                    "name": "Avena",
                    "quantity": 100.0,
                    "values": {"protein": 10.5},
                }
            ],
        )

    def test_selection_rows_from_snapshot_can_hydrate_labels_without_source_entities(self):
        payload = [{"id": 3, "name": "Avena", "quantity": 90, "values": {"total_kcal": 320}}]

        self.assertEqual(
            selection_rows_from_snapshot(payload, include_quantities=True),
            [{"id": 3, "name": "Avena", "quantity": 90.0}],
        )

    def test_comparable_rows_from_snapshot_rebuilds_metric_inputs(self):
        payload = [{"id": 3, "name": "Avena", "quantity": 90, "values": {"total_kcal": 320}}]

        rows = comparable_rows_from_snapshot(payload, include_quantities=True)

        self.assertEqual(len(rows), 1)
        selection, values = rows[0]
        self.assertEqual(selection.id, 3)
        self.assertEqual(selection.name, "Avena")
        self.assertEqual(selection.quantity, 90.0)
        self.assertEqual(values, {"total_kcal": 320.0})
