from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse


@override_settings(NUTRITION_ONBOARDING_GATE_ENABLED=False)
class AdminOperationsV1ClosureTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.staff = User.objects.create_user(
            username="ops08-staff@example.com",
            email="ops08-staff@example.com",
            password="password123",
            is_staff=True,
        )
        self.client.force_login(self.staff)

    def test_overview_renders_ops08_closure_card(self):
        response = self.client.get(reverse("admin_operations_overview"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "OPS08 · V1 closure")
        self.assertContains(response, "Consola operacional V1 cerrada")
        self.assertContains(response, "Confirmación antes de mutar")
        self.assertContains(response, "Audit log activo")

    def test_operations_shell_contains_shared_confirmation_script(self):
        response = self.client.get(reverse("admin_operations_overview"))

        self.assertEqual(response.status_code, 200)
        html = response.content.decode("utf-8")
        self.assertIn("data-admin-operations-confirm", html)
        self.assertIn("Confirmar acción operacional", html)
        self.assertIn("window.confirm", html)

    def test_ai_mutation_forms_opt_into_confirmation_contract(self):
        response = self.client.get(reverse("admin_operations_ai_assistant"))

        self.assertEqual(response.status_code, 200)
        html = response.content.decode("utf-8")
        # The page can be empty, but the shared shell still carries the confirmation contract.
        self.assertIn("data-admin-operations-confirm", html)
        self.assertIn("Confirmar acción operacional", html)
