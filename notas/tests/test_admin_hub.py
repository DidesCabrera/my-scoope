from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse


@override_settings(NUTRITION_ONBOARDING_GATE_ENABLED=False)
class AdminHubTests(TestCase):
    def test_admin_workspace_connects_analytics_operations_and_knowledge(self):
        User = get_user_model()
        user = User.objects.create_superuser(
            username="admin-hub@example.com",
            email="admin-hub@example.com",
            password="password123",
        )
        self.client.force_login(user)

        response = self.client.get(reverse("admin_home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Admin Workspace")
        self.assertContains(response, "Admin Analytics")
        self.assertContains(response, "Admin Operations")
        self.assertContains(response, "Knowledge Center")
        self.assertContains(response, reverse("admin_analytics_overview"))
        self.assertContains(response, reverse("admin_operations_overview"))
        self.assertContains(response, reverse("admin_knowledge_overview"))
