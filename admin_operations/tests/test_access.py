from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse


@override_settings(NUTRITION_ONBOARDING_GATE_ENABLED=False)
class AdminOperationsAccessTests(TestCase):
    def test_overview_requires_login(self):
        response = self.client.get(reverse("admin_operations_overview"))

        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response["Location"])

    def test_overview_rejects_non_staff_user(self):
        User = get_user_model()
        user = User.objects.create_user(
            username="member-ops@example.com",
            email="member-ops@example.com",
            password="password123",
            is_staff=False,
        )
        self.client.force_login(user)

        response = self.client.get(reverse("admin_operations_overview"))

        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response["Location"])

    def test_overview_allows_staff_user(self):
        User = get_user_model()
        user = User.objects.create_user(
            username="staff-ops@example.com",
            email="staff-ops@example.com",
            password="password123",
            is_staff=True,
        )
        self.client.force_login(user)

        response = self.client.get(reverse("admin_operations_overview"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Admin Operations")
        self.assertContains(response, "Operational Console")
        self.assertContains(response, "Colas accionables para operar My Scoope")
        self.assertNotContains(response, "admin-operations-hero")

    def test_overview_uses_independent_operations_shell(self):
        User = get_user_model()
        user = User.objects.create_user(
            username="staff-ops-shell@example.com",
            email="staff-ops-shell@example.com",
            password="password123",
            is_staff=True,
        )
        self.client.force_login(user)

        response = self.client.get(reverse("admin_operations_overview"))

        self.assertEqual(response.status_code, 200)
        html = response.content.decode("utf-8")
        self.assertIn('class="admin-analytics-shell admin-operations-shell"', html)
        self.assertIn('class="admin-analytics-app admin-operations-app"', html)
        self.assertIn("Ir a Analytics", html)
        self.assertIn("Django Admin legacy", html)
        self.assertNotIn('class="app-body"', html)
        self.assertNotIn('components/sidebar.html', html)

    def test_overview_renders_operational_placeholders(self):
        User = get_user_model()
        user = User.objects.create_user(
            username="staff-ops-placeholders@example.com",
            email="staff-ops-placeholders@example.com",
            password="password123",
            is_staff=True,
        )
        self.client.force_login(user)

        response = self.client.get(reverse("admin_operations_overview"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'aria-current="page"')
        self.assertContains(response, "Food Catalog")
        self.assertContains(response, "Accounts &amp; Credits")
        self.assertContains(response, "Audit-first")
        self.assertContains(response, "OPS03 workflow activo")
