from django.contrib.auth import get_user_model
from django.test import TestCase

from notas.domain.models import DailyPlan
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
