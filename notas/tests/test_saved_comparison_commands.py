from types import SimpleNamespace

from django.contrib.auth.models import User
from django.test import TestCase

from notas.application.services.commands.saved_comparison_commands import (
    SavedComparisonCommandError,
    create_saved_comparison,
    rename_saved_comparison,
    update_saved_comparison,
)
from notas.domain.models import SavedComparison


class SavedComparisonCommandTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="felipe",
            password="pass123",
        )

    def _food_selection(self, entity_id, name, quantity):
        return SimpleNamespace(
            id=entity_id,
            name=name,
            quantity=quantity,
        )

    def test_create_saved_comparison_persists_payload_and_snapshot(self):
        selections = [
            self._food_selection(1, "Atún", 120),
            self._food_selection(2, "Pollo", 150),
        ]
        comparable_rows = [
            (selections[0], {"total_kcal": 132, "protein": 28}),
            (selections[1], {"total_kcal": 240, "protein": 46}),
        ]

        result = create_saved_comparison(
            owner=self.user,
            kind=SavedComparison.KIND_FOODS,
            entity_plural_label="Alimentos",
            selections=selections,
            comparable_rows=comparable_rows,
            include_quantities=True,
        )

        comparison = result.comparison

        self.assertEqual(comparison.owner, self.user)
        self.assertEqual(comparison.kind, SavedComparison.KIND_FOODS)
        self.assertEqual(comparison.name, "Atún vs Pollo")
        self.assertEqual(
            comparison.payload,
            [
                {"id": 1, "quantity": 120.0},
                {"id": 2, "quantity": 150.0},
            ],
        )
        self.assertEqual(
            comparison.snapshot_payload,
            [
                {
                    "id": 1,
                    "name": "Atún",
                    "quantity": 120.0,
                    "values": {"total_kcal": 132.0, "protein": 28.0},
                },
                {
                    "id": 2,
                    "name": "Pollo",
                    "quantity": 150.0,
                    "values": {"total_kcal": 240.0, "protein": 46.0},
                },
            ],
        )

    def test_create_saved_comparison_requires_two_complete_items(self):
        selection = self._food_selection(1, "Atún", 120)

        with self.assertRaises(SavedComparisonCommandError):
            create_saved_comparison(
                owner=self.user,
                kind=SavedComparison.KIND_FOODS,
                entity_plural_label="Alimentos",
                selections=[selection],
                comparable_rows=[(selection, {"total_kcal": 132})],
                include_quantities=True,
            )

    def test_update_saved_comparison_replaces_payload_and_snapshot_without_renaming(self):
        comparison = SavedComparison.objects.create(
            owner=self.user,
            kind=SavedComparison.KIND_FOODS,
            name="Mi comparación",
            payload=[{"id": 1, "quantity": 100}],
            snapshot_payload=[],
        )
        selections = [
            self._food_selection(10, "Avena", 90),
            self._food_selection(20, "Yogur", 200),
        ]
        comparable_rows = [
            (selections[0], {"total_kcal": 320}),
            (selections[1], {"total_kcal": 180}),
        ]

        result = update_saved_comparison(
            comparison=comparison,
            selections=selections,
            comparable_rows=comparable_rows,
            include_quantities=True,
        )

        comparison.refresh_from_db()

        self.assertEqual(result.comparison, comparison)
        self.assertEqual(comparison.name, "Mi comparación")
        self.assertEqual(
            comparison.payload,
            [
                {"id": 10, "quantity": 90.0},
                {"id": 20, "quantity": 200.0},
            ],
        )
        self.assertEqual(comparison.snapshot_payload[0]["name"], "Avena")
        self.assertEqual(comparison.snapshot_payload[1]["name"], "Yogur")

    def test_rename_saved_comparison_trims_name(self):
        comparison = SavedComparison.objects.create(
            owner=self.user,
            kind=SavedComparison.KIND_MEALS,
            name="Original",
            payload=[],
            snapshot_payload=[],
        )

        rename_saved_comparison(
            comparison=comparison,
            name="  Nueva comparación  ",
        )

        comparison.refresh_from_db()

        self.assertEqual(comparison.name, "Nueva comparación")

    def test_build_name_counts_extra_items(self):
        from notas.application.services.commands.saved_comparison_commands import build_saved_comparison_name

        selections = [
            self._food_selection(1, "Atún", 100),
            self._food_selection(2, "Pollo", 100),
            self._food_selection(3, "Avena", 100),
            self._food_selection(4, "Arroz", 100),
        ]

        self.assertEqual(
            build_saved_comparison_name(
                entity_plural_label="alimentos",
                selections=selections,
            ),
            "Atún vs Pollo + 2",
        )

    def test_rename_saved_comparison_rejects_blank_name(self):
        comparison = SavedComparison.objects.create(
            owner=self.user,
            kind=SavedComparison.KIND_MEALS,
            name="Original",
            payload=[],
            snapshot_payload=[],
        )

        with self.assertRaises(SavedComparisonCommandError):
            rename_saved_comparison(
                comparison=comparison,
                name="   ",
            )

        comparison.refresh_from_db()
        self.assertEqual(comparison.name, "Original")

    def test_update_saved_comparison_rejects_incomplete_snapshot(self):
        comparison = SavedComparison.objects.create(
            owner=self.user,
            kind=SavedComparison.KIND_FOODS,
            name="Mi comparación",
            payload=[{"id": 1, "quantity": 100}, {"id": 2, "quantity": 100}],
            snapshot_payload=[],
        )
        selections = [
            self._food_selection(10, "Avena", 90),
            self._food_selection(20, "Yogur", 200),
        ]
        comparable_rows = [
            (selections[0], {"total_kcal": 320}),
        ]

        with self.assertRaises(SavedComparisonCommandError):
            update_saved_comparison(
                comparison=comparison,
                selections=selections,
                comparable_rows=comparable_rows,
                include_quantities=True,
            )

        comparison.refresh_from_db()
        self.assertEqual(
            comparison.payload,
            [{"id": 1, "quantity": 100}, {"id": 2, "quantity": 100}],
        )
