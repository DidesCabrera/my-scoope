from pathlib import Path

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.template.loader import render_to_string
from django.urls import reverse

from notas.domain.models import DailyPlan, Program, ProgramDay
from notas.presentation.config.viewmodel_config import DAILYPLAN_VIEWMODE_PERSONAL_DETAIL
from notas.presentation.pages.dailyplan_contexts import (
    build_dailyplan_create_context,
    build_dailyplan_detail_context,
    build_dailyplan_list_context,
)
from notas.presentation.pages.dailyplan_pages import (
    get_dailyplan_detail_page_data,
    get_dailyplan_list_page_data,
)

User = get_user_model()


class DailyPlanPresentationContextTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="felipe",
            password="pass123",
        )
        self.dailyplan = DailyPlan.objects.create(
            name="Training Day",
            created_by=self.user,
            is_draft=False,
        )

    def test_build_dailyplan_create_context_returns_base_vm_context(self):
        context = build_dailyplan_create_context()

        self.assertIn("vm", context)
        self.assertEqual(context["vm"]["ui"]["entity"], "dailyplan")
        self.assertEqual(context["vm"]["ui"]["scope"], "create")
        self.assertIsNone(context["vm"]["content"])

    def test_build_dailyplan_list_context_preserves_list_mode(self):
        page = get_dailyplan_list_page_data(
            user=self.user,
            request_get={"mode": "delete"},
        )

        context = build_dailyplan_list_context(page)

        self.assertEqual(context["vm"]["content"]["list_mode"], "delete")
        self.assertEqual(context["vm"]["ui"]["entity"], "dailyplan")

    def test_build_dailyplan_detail_context_can_include_picker_payload(self):
        page = get_dailyplan_detail_page_data(
            user=self.user,
            dailyplan_id=self.dailyplan.id,
            viewmode=DAILYPLAN_VIEWMODE_PERSONAL_DETAIL,
            request_get={},
        )

        context = build_dailyplan_detail_context(
            page=page,
            user=self.user,
            include_picker=True,
        )

        self.assertIn("vm", context)
        self.assertEqual(context["vm"]["content"]["main_card"]["titulo"]["name"], "Training Day")
        self.assertIn("meal_picker_data_json", context)
        self.assertIn("meal_picker_context", context)
        self.assertIn("selected_meal_id", context)
        self.assertIn("editing_dailyplanmeal_id", context)

    def test_dailyplan_back_returns_to_its_program_week_context(self):
        program = Program.objects.create(
            name="Programa contextual",
            created_by=self.user,
            duration_weeks=2,
        )
        program_day = ProgramDay.objects.create(
            program=program,
            dailyplan=self.dailyplan,
            week_number=2,
            day_number=1,
        )
        page = get_dailyplan_detail_page_data(
            user=self.user,
            dailyplan_id=self.dailyplan.id,
            viewmode=DAILYPLAN_VIEWMODE_PERSONAL_DETAIL,
            request_get={"program_day": str(program_day.id)},
        )

        context = build_dailyplan_detail_context(
            page=page,
            user=self.user,
            program_day_id=program_day.id,
        )

        self.assertEqual(
            context["vm"]["ui"]["back_url"],
            f"{reverse('program_detail', args=[program.id])}#week-2",
        )
        self.assertEqual(
            [item["label"] for item in context["vm"]["ui"]["breadcrumb"]],
            ["...", "Semana 2", "Día 1 - Training Day"],
        )

    def test_dailyplan_back_returns_to_library_without_program_context(self):
        page = get_dailyplan_detail_page_data(
            user=self.user,
            dailyplan_id=self.dailyplan.id,
            viewmode=DAILYPLAN_VIEWMODE_PERSONAL_DETAIL,
            request_get={},
        )

        context = build_dailyplan_detail_context(page=page, user=self.user)

        self.assertEqual(context["vm"]["ui"]["back_url"], reverse("dailyplan_list"))

    def test_dailyplan_meal_sequence_is_rendered_in_card_eyebrows(self):
        eyebrow = render_to_string(
            "components/card_child_title.html",
            {
                "meal_number": 2,
                "titulo": {
                    "icon": "utensils",
                    "label": "Meal",
                    "name": "Almuerzo",
                    "structural_indicators": {},
                },
            },
        )
        detail_template = Path("notas/templates/notas/dailyplans/detail.html").read_text()

        self.assertIn("Comida 2", eyebrow)
        self.assertIn("meal_number=forloop.counter", detail_template)
        self.assertNotIn("dailyplan-detail__meal-step-marker", detail_template)
        self.assertNotIn("dailyplan-detail__meal-step-number", detail_template)
