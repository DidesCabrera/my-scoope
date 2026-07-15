from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse


class AIUsageDashboardAdminTests(TestCase):
    def test_staff_admin_can_open_usage_dashboard(self):
        admin_user = User.objects.create_superuser(
            username="admin-user",
            email="admin@test.local",
            password="pw12345",
        )
        self.client.force_login(admin_user)

        response = self.client.get(reverse("admin:ai_assistant_aiusageevent_usage_dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "AI Assistant usage dashboard")
        self.assertContains(response, "Estimated cost USD")
