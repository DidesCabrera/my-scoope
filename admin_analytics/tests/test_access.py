from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse


@override_settings(NUTRITION_ONBOARDING_GATE_ENABLED=False)
class AdminAnalyticsAccessTests(TestCase):
    def test_overview_requires_login(self):
        response = self.client.get(reverse("admin_analytics_overview"))

        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response["Location"])

    def test_overview_rejects_non_staff_user(self):
        User = get_user_model()
        user = User.objects.create_user(
            username="member@example.com",
            email="member@example.com",
            password="password123",
            is_staff=False,
        )
        self.client.force_login(user)

        response = self.client.get(reverse("admin_analytics_overview"))

        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response["Location"])

    def test_overview_allows_staff_user(self):
        User = get_user_model()
        user = User.objects.create_user(
            username="staff@example.com",
            email="staff@example.com",
            password="password123",
            is_staff=True,
        )
        self.client.force_login(user)

        response = self.client.get(reverse("admin_analytics_overview"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Admin Analytics")
        self.assertContains(response, "Strategic Console")
        self.assertContains(response, "Weekly Active Nutrition Builders")

    def test_overview_uses_independent_admin_shell(self):
        User = get_user_model()
        user = User.objects.create_user(
            username="staff-shell@example.com",
            email="staff-shell@example.com",
            password="password123",
            is_staff=True,
        )
        self.client.force_login(user)

        response = self.client.get(reverse("admin_analytics_overview"))

        self.assertEqual(response.status_code, 200)
        html = response.content.decode("utf-8")
        self.assertIn('class="admin-analytics-shell"', html)
        self.assertIn('class="admin-analytics-app"', html)
        self.assertIn("Django admin legacy", html)
        self.assertNotIn('class="app-body"', html)
        self.assertNotIn('components/sidebar.html', html)

    def test_nav_marks_current_section_and_renders_cycle_modules(self):
        User = get_user_model()
        user = User.objects.create_user(
            username="staff-nav@example.com",
            email="staff-nav@example.com",
            password="password123",
            is_staff=True,
        )
        self.client.force_login(user)

        response = self.client.get(reverse("admin_analytics_overview"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'aria-current="page"')
        self.assertContains(response, "Mapa de módulos implementados")
        self.assertContains(response, "ADM09 implementado")

    def test_page_title_lives_in_topbar_not_first_content_card(self):
        User = get_user_model()
        user = User.objects.create_user(
            username="staff-title@example.com",
            email="staff-title@example.com",
            password="password123",
            is_staff=True,
        )
        self.client.force_login(user)

        response = self.client.get(reverse("admin_analytics_accounts"))

        self.assertEqual(response.status_code, 200)
        html = response.content.decode("utf-8")
        self.assertIn('class="admin-analytics-page-heading"', html)
        self.assertIn("Accounts Analytics", html)
        self.assertIn("Planes, suscripciones, wallets y ledger de créditos.", html)
        self.assertNotIn("<h2>Accounts Analytics</h2>", html)
        self.assertNotIn("Staff-only · Read-first · {{ vm.content.period_label }}", html)

    def test_mobile_shell_controls_are_available(self):
        User = get_user_model()
        user = User.objects.create_user(
            username="staff-mobile@example.com",
            email="staff-mobile@example.com",
            password="password123",
            is_staff=True,
        )
        self.client.force_login(user)

        response = self.client.get(reverse("admin_analytics_overview"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="admin-analytics-menu-toggle"')
        self.assertContains(response, 'id="admin-analytics-filter-toggle"')
        self.assertContains(response, 'aria-label="Abrir navegación"')
        self.assertContains(response, 'aria-label="Mostrar filtros"')
        self.assertContains(response, 'admin-analytics-mobile-scrim--menu')
