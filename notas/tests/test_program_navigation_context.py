from django.test import SimpleTestCase

from notas.presentation.navigation.program_context import (
    ProgramBreadcrumbParent,
    ProgramNavigationContext,
    compact_program_breadcrumbs,
    context_query_dict,
    contextual_url,
    navigation_context_from_query,
    program_context_query,
    week_url,
)
from notas.presentation.viewmodels.base_vm import UI, BreadcrumbItem


class ProgramNavigationContextTests(SimpleTestCase):
    def test_week_url_returns_to_the_week_inside_program_detail(self):
        program_day = type("ProgramDayStub", (), {"program_id": 8, "week_number": 2})()

        self.assertEqual(week_url(program_day), "/app/programs/8/#week-2")

    def test_program_context_query_serializes_supported_params(self):
        query = program_context_query(program_day=10, dpm=20, mealfood=30)

        self.assertEqual(query, "program_day=10&dpm=20&mealfood=30")

    def test_navigation_context_from_query_ignores_unknown_params(self):
        context = navigation_context_from_query(
            "program_day=10&dpm=20&mealfood=30&next=/unsafe/"
        )

        self.assertEqual(context.program_day_id, "10")
        self.assertEqual(context.dpm_id, "20")
        self.assertEqual(context.mealfood_id, "30")
        self.assertEqual(
            context.as_params(),
            {"program_day": "10", "dpm": "20", "mealfood": "30"},
        )

    def test_context_query_dict_accepts_action_context_payload(self):
        params = context_query_dict({"query": "program_day=10&dpm=20&ignored=1"})

        self.assertEqual(params, {"program_day": "10", "dpm": "20"})

    def test_contextual_url_preserves_existing_query_and_appends_context(self):
        url = contextual_url(
            "/dailyplans/5/?tab=edit",
            "program_day=10&dpm=20&ignored=1",
            select_meal=99,
        )

        self.assertEqual(
            url,
            "/dailyplans/5/?tab=edit&program_day=10&dpm=20&select_meal=99",
        )

    def test_program_navigation_context_can_extend_nested_segments(self):
        context = ProgramNavigationContext(program_day_id=10)

        self.assertEqual(context.with_dpm(20).as_query(), "program_day=10&dpm=20")
        self.assertEqual(
            context.with_dpm(20).with_mealfood(30).as_query(),
            "program_day=10&dpm=20&mealfood=30",
        )


class ProgramBreadcrumbCompactionTests(SimpleTestCase):
    def test_compact_program_breadcrumbs_uses_semantic_kind(self):
        ui = UI(
            viewmode="program:detail:personal",
            entity="program",
            mode="detail",
            breadcrumb=[
                BreadcrumbItem(label="Mis Librerías"),
                BreadcrumbItem(label="Mis Programas"),
                BreadcrumbItem(label="Programa X", url="/programs/1/", kind="program"),
                BreadcrumbItem(label="W1", url="/programs/1/weeks/1/", kind="program_week"),
                BreadcrumbItem(label="Día 1 - Plan", url="/dailyplans/5/", kind="program_day_plan"),
                BreadcrumbItem(label="Meal"),
            ],
        )

        compact_program_breadcrumbs(ui)

        self.assertTrue(ui.breadcrumb[0].is_overflow)
        self.assertEqual(ui.breadcrumb[0].kind, "overflow")
        self.assertEqual([item.label for item in ui.breadcrumb[0].overflow_items], [
            "Mis Librerías",
            "Mis Programas",
            "Programa X",
        ])
        self.assertEqual([item.label for item in ui.breadcrumb[1:]], [
            "W1",
            "Día 1 - Plan",
            "Meal",
        ])

    def test_program_breadcrumb_parent_exposes_kind_for_builders(self):
        parent = ProgramBreadcrumbParent("Semana personalizada", "/week/", kind="program_week")

        self.assertEqual(str(parent), "Semana personalizada")
        self.assertEqual(parent.get_absolute_url(), "/week/")
        self.assertEqual(parent.kind, "program_week")
