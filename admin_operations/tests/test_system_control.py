from django.contrib.auth import get_user_model
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.test import TestCase, override_settings
from django.urls import reverse

from admin_operations.system_control import build_system_control_vm


@override_settings(NUTRITION_ONBOARDING_GATE_ENABLED=False, AI_ASSISTANT_OPENAI_API_KEY="never-render-this-key")
class SystemControlAccessTests(TestCase):
    def setUp(self):
        self.url = reverse("admin_operations_system_control")

    def test_requires_staff_access(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)

        user = get_user_model().objects.create_user(
            username="pcf-member", password="password", is_staff=False
        )
        self.client.force_login(user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)

    def test_staff_can_read_sanitized_project_control(self):
        user = get_user_model().objects.create_user(
            username="pcf-staff", password="password", is_staff=True
        )
        self.client.force_login(user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Project Control")
        self.assertContains(response, "Control plane de sólo lectura")
        self.assertContains(response, "database.migrations")
        self.assertNotContains(response, "never-render-this-key")
        self.assertNotContains(response, "<form")

    def test_control_plane_rejects_post(self):
        user = get_user_model().objects.create_user(
            username="pcf-post-staff", password="password", is_staff=True
        )
        self.client.force_login(user)

        response = self.client.post(self.url)

        self.assertEqual(response.status_code, 405)

    def test_control_plane_uses_bounded_aggregate_queries(self):
        with CaptureQueriesContext(connection) as queries:
            content = build_system_control_vm()

        self.assertTrue(content.probes)
        self.assertLessEqual(len(queries), 20)
