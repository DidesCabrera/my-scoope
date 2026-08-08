from types import SimpleNamespace

from django.template.loader import render_to_string
from django.test import SimpleTestCase
from django.utils import translation


class AllocTemplateLocalizationTests(SimpleTestCase):
    def assert_css_alloc_is_unlocalized(self, template_name, context):
        with translation.override("es"):
            rendered = render_to_string(template_name, context)

        self.assertIn("--alloc: 25.5;", rendered)
        self.assertNotIn("--alloc: 25,5;", rendered)

    def test_shared_alloc_templates_emit_valid_css_numbers_in_spanish(self):
        for template_name in (
            "components/alloc_bar.html",
            "components/alloc_bar_mini.html",
            "components/grid_alloc_item.html",
            "components/alloc_cell_protein.html",
            "components/alloc_cell_carbs.html",
            "components/alloc_cell_fat.html",
            "components/kpi_alloc_cell_protein.html",
            "components/kpi_alloc_cell_carbs.html",
            "components/kpi_alloc_cell_fat.html",
        ):
            with self.subTest(template_name=template_name):
                self.assert_css_alloc_is_unlocalized(
                    template_name,
                    {"value": 25.5, "kind": "protein"},
                )

    def test_range_alloc_template_emits_valid_css_numbers_in_spanish(self):
        metric = SimpleNamespace(label="25,5%", bar_value=25.5)
        self.assert_css_alloc_is_unlocalized(
            "components/dash_kpi_range.html",
            {
                "ranges": SimpleNamespace(
                    alloc_protein=metric,
                    alloc_carbs=metric,
                    alloc_fat=metric,
                )
            },
        )
