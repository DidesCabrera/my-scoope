from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse


User = get_user_model()


@override_settings(NUTRITION_ONBOARDING_GATE_ENABLED=False)
class ComparatorEntryFlowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="comparador", password="test-password")
        self.client.force_login(self.user)

    def test_sidebar_entry_redirects_to_saved_food_comparisons(self):
        response = self.client.get(reverse("comparator_index"))

        self.assertRedirects(
            response,
            reverse("saved_comparisons_list", kwargs={"kind": "foods"}),
            fetch_redirect_response=False,
        )

    def test_saved_comparison_page_exposes_tabs_empty_action_and_creation_menu(self):
        response = self.client.get(reverse("saved_comparisons_list", kwargs={"kind": "foods"}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Comparador")
        self.assertContains(response, "Alimentos")
        self.assertContains(response, "Comidas")
        self.assertContains(response, "Planes")
        self.assertContains(response, "Crear nueva comparación")
        self.assertContains(response, "Crear nueva comparación")
        self.assertContains(response, 'data-lucide="plus"')
        self.assertContains(response, reverse("food_comparator"))
        header = response.context["vm"]["content"]["header"]
        self.assertEqual(len(header["desktop_inline_actions"]), 1)
        self.assertEqual(header["desktop_inline_actions"][0]["url"], reverse("food_comparator"))
        self.assertEqual(header["desktop_menu_actions"], [])
