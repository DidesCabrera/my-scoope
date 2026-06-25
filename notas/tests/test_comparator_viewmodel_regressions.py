from unittest import TestCase

from notas.presentation.viewmodels.comparators import (
    ComparatorSelection,
    build_metrics,
    format_selection_name,
)


class ComparatorViewmodelRegressionTests(TestCase):
    def test_food_selection_name_formats_quantity_as_suffix(self):
        self.assertEqual(format_selection_name("Atún", 120), "Atún (120g)")
        self.assertEqual(format_selection_name("Atún", None), "Atún")

    def test_metric_order_includes_ppk_second_when_enabled(self):
        selection = ComparatorSelection(id=1, name="Plan A", position=1)
        metrics = build_metrics(
            [(selection, {"total_kcal": 2000, "ppk": 1.8, "protein": 140})],
            include_ppk=True,
        )

        self.assertEqual([metric.key for metric in metrics[:3]], ["total_kcal", "ppk", "protein"])

    def test_metric_order_excludes_ppk_for_foods(self):
        selection = ComparatorSelection(id=1, name="Atún", quantity=120, position=1)
        metrics = build_metrics(
            [(selection, {"total_kcal": 132, "protein": 28})],
            include_ppk=False,
        )

        self.assertEqual([metric.key for metric in metrics[:2]], ["total_kcal", "protein"])

    def test_food_metric_bar_uses_quantity_as_label_suffix_not_value(self):
        selection = ComparatorSelection(id=1, name="Atún", quantity=120, position=1)
        metrics = build_metrics(
            [(selection, {"total_kcal": 132})],
            include_ppk=False,
        )

        bar = metrics[0].bars[0]

        self.assertEqual(bar.label, "Atún")
        self.assertEqual(bar.label_suffix, "(120g)")
        self.assertEqual(bar.formatted_value, "132 kcal")
