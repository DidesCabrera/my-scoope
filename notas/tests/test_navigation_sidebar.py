from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from notas.presentation.composition.viewmodel.ui_builder import build_ui_vm
from notas.presentation.config.viewmodel_config import (
    DAILYPLAN_MEAL_VIEWMODE_DETAIL,
    FOOD_VIEWMODE_PERSONAL_LIST,
    PROFILE_VIEWMODE,
)
from notas.presentation.navigation.nav_builders import (
    build_sidebar_vm,
    resolve_navigation_root,
)

User = get_user_model()


class SidebarBuilderTests(TestCase):

    def test_resolve_navigation_root_returns_same_entity_for_primary_entities(self):
        self.assertEqual(resolve_navigation_root("dailyplan"), "dailyplan")
        self.assertEqual(resolve_navigation_root("meal"), "meal")
        self.assertEqual(resolve_navigation_root("food"), "food")

    def test_resolve_navigation_root_maps_secondary_entity_to_primary_root(self):
        self.assertEqual(resolve_navigation_root("dailyplan_meal"), "dailyplan")

    def test_build_sidebar_vm_marks_food_personal_as_active(self):
        sidebar = build_sidebar_vm(FOOD_VIEWMODE_PERSONAL_LIST)

        active_items = []

        for section in sidebar:
            for group in section["groups"]:
                if group["is_active"]:
                    active_items.append(group)
                for item in group["items"]:
                    if item["is_active"]:
                        active_items.append(item)

        self.assertEqual(len(active_items), 1)
        self.assertEqual(active_items[0]["key"], "food")
        self.assertEqual(active_items[0]["nav_root"], "food")
        self.assertEqual(active_items[0]["scope"], "personal")

    def test_build_sidebar_vm_marks_dailyplan_personal_as_active_for_dailyplan_meal(self):
        sidebar = build_sidebar_vm(DAILYPLAN_MEAL_VIEWMODE_DETAIL)

        active_items = []

        for section in sidebar:
            for group in section["groups"]:
                if group["is_active"]:
                    active_items.append(group)
                for item in group["items"]:
                    if item["is_active"]:
                        active_items.append(item)

        self.assertEqual(len(active_items), 1)
        self.assertEqual(active_items[0]["key"], "dailyplan")
        self.assertEqual(active_items[0]["nav_root"], "dailyplan")
        self.assertEqual(active_items[0]["scope"], "personal")


  

    def test_build_sidebar_vm_contains_account_section(self):
        sidebar = build_sidebar_vm(PROFILE_VIEWMODE)

        section_keys = [section["key"] for section in sidebar]

        self.assertIn("account", section_keys)

    def test_build_sidebar_vm_uses_reorganized_section_order(self):
        sidebar = build_sidebar_vm(PROFILE_VIEWMODE)

        self.assertEqual([section["key"] for section in sidebar[:2]], ["account", "workspace"])
        self.assertEqual(sidebar[0]["label"], "Tools")
        self.assertEqual(sidebar[1]["label"], "Mis librerias")
        self.assertEqual(
            [group["label"] for group in sidebar[0]["groups"][:6]],
            [
                "Asistente",
                "Propuestas",
                "Calendarizar",
                "Comparar",
                "Explorar",
                "Inbox",
            ],
        )
        self.assertEqual(
            [group["label"] for group in sidebar[1]["groups"]],
            [
                "Mis Programas Semanales",
                "Mis Planes Diarios",
                "Mis Comidas",
                "Mis Alimentos",
            ],
        )
        explore_group = sidebar[0]["groups"][4]
        self.assertEqual(explore_group["key"], "explore")
        self.assertEqual(explore_group["nav_root"], "explore")

        tool_groups = {group["key"]: group for group in sidebar[0]["groups"]}
        self.assertNotIn("chat_new", tool_groups)
        self.assertEqual(tool_groups["chat"]["label"], "Asistente")
        self.assertEqual(tool_groups["chat"]["url_name"], "ai_nutrition_chat_list")
        self.assertEqual(tool_groups["chat"]["icon"], "sparkles")
        self.assertEqual(tool_groups["proposal"]["icon"], "clipboard-check")
        self.assertEqual(tool_groups["comparators"]["icon"], "scale")

 
    def test_build_ui_vm_for_profile_populates_navigation_metadata(self):
        ui = build_ui_vm(PROFILE_VIEWMODE)

        self.assertEqual(ui.nav_root, "profile")
        self.assertEqual(ui.icon, "circle-user-round")
        self.assertEqual(ui.section_label, "Tools")
        self.assertEqual(ui.page_icon, "circle-user-round")


    def test_build_sidebar_vm_does_not_include_profile_group(self):
        sidebar = build_sidebar_vm(PROFILE_VIEWMODE)

        group_keys = []

        for section in sidebar:
            for group in section["groups"]:
                group_keys.append(group["key"])

        self.assertNotIn("profile", group_keys)
    
    def test_build_ui_vm_for_profile_populates_navigation_metadata(self):
        ui = build_ui_vm(PROFILE_VIEWMODE)

        self.assertEqual(ui.nav_root, "profile")
        self.assertEqual(ui.icon, "circle-user-round")
        self.assertEqual(ui.section_label, "Tools")
        self.assertEqual(ui.page_icon, "circle-user-round")



@override_settings(NUTRITION_ONBOARDING_GATE_ENABLED=False)
class SidebarIntegrationTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="felipe",
            email="felipe@test.com",
            password="12345678",
        )

        self.client = Client()
        self.client.login(
            username="felipe",
            password="12345678",
        )

    def test_food_list_exposes_sidebar_sections_in_vm_ui(self):
        response = self.client.get(reverse("food_list"))

        self.assertEqual(response.status_code, 200)
        self.assertIn("vm", response.context)
        self.assertIn("ui", response.context["vm"])
        self.assertIn("sidebar_sections", response.context["vm"]["ui"])

        sidebar_sections = response.context["vm"]["ui"]["sidebar_sections"]

        self.assertTrue(len(sidebar_sections) > 0)

    def test_profile_detail_exposes_sidebar_sections_in_vm_ui(self):
        response = self.client.get(reverse("profile_detail"))

        self.assertEqual(response.status_code, 200)
        self.assertIn("vm", response.context)
        self.assertIn("ui", response.context["vm"])
        self.assertIn("sidebar_sections", response.context["vm"]["ui"])

        sidebar_sections = response.context["vm"]["ui"]["sidebar_sections"]

        self.assertTrue(len(sidebar_sections) > 0)
