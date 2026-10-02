from pathlib import Path

from django.test import SimpleTestCase

TEMPLATES = Path(__file__).resolve().parents[1] / "templates" / "components"
STATIC = Path(__file__).resolve().parents[1] / "static" / "notas"


class ProgramDetailWebParityTests(SimpleTestCase):
    def test_program_chart_uses_thin_curves_and_compact_day_markers(self):
        styles = (STATIC / "css" / "components" / "programs_charts.css").read_text()
        script = (STATIC / "js" / "program_metric_chart.js").read_text()

        self.assertIn(".program-chart-outline-path", styles)
        self.assertIn("stroke-width: 1px", styles)
        self.assertNotIn("program-chart-outline-path { stroke-width: 2.65px; }", styles)
        self.assertIn('circle.setAttribute("r", "1.5")', script)
        self.assertIn(".program-chart-outline-area", styles)
        self.assertIn(".program-chart-outline-gradient-stop", styles)
        self.assertIn('[["0", "0.2"], ["1", "0"]]', script)
        self.assertIn("makeOutlineArea(areaCommands.join", script)

    def test_week_detail_orders_plans_foods_and_comparison_insights(self):
        source = (TEMPLATES / "program_week_child_card.html").read_text()

        plans = source.index("Planes diarios esta semana")
        foods = source.index('program_week_foods_section.html')
        chart = source.index('program_metric_chart_base.html')
        comparison = source.index("Tabla de comparación entre planes diarios")

        self.assertLess(plans, foods)
        self.assertLess(foods, chart)
        self.assertLess(chart, comparison)
        self.assertIn('program_week_foods_section.html" with week=week %}\n\n  <hr>', source)

    def test_week_comparison_matches_mobile_labels_and_values(self):
        calories = (TEMPLATES / "program_week_table_calories.html").read_text()
        macros = (TEMPLATES / "program_week_table_macros.html").read_text()
        combined = (TEMPLATES / "program_week_table_combined.html").read_text()

        for source in (calories, combined):
            self.assertIn("CAL prom", source)
            self.assertIn("% var", source)
            self.assertIn("program-week-table__variation-chip", source)
            self.assertNotIn('data-grid-col--program-plans', source)

        for source in (macros, combined):
            self.assertIn('role="columnheader">Pg</div>', source)
            self.assertIn('role="columnheader">Cg</div>', source)
            self.assertIn('role="columnheader">Fg</div>', source)
            self.assertIn("average_protein_per_assigned_day", source)
            self.assertIn("average_carbs_per_assigned_day", source)
            self.assertIn("average_fat_per_assigned_day", source)

        for source in (calories, macros, combined):
            self.assertIn('data-lucide="calendar"', source)
            self.assertIn("Semana {{ week.week_number }}", source)
