from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from admin_analytics.services.alerts import build_alerts_vm
from ai_assistant.application.credits import current_period
from ai_assistant.models import AIUsageEvent
from food_catalog.models import CatalogFood
from notas.domain.models import Meal


@override_settings(NUTRITION_ONBOARDING_GATE_ENABLED=False)
class AdminAnalyticsAlertsTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.staff = User.objects.create_user(
            username="staff@example.com",
            email="staff@example.com",
            password="password123",
            is_staff=True,
        )
        self.member = User.objects.create_user(
            username="member@example.com",
            email="member@example.com",
            password="password123",
        )

    def test_alerts_dashboard_is_staff_only_and_renders(self):
        response = self.client.get(reverse("admin_analytics_alerts"))
        self.assertEqual(response.status_code, 302)

        self.client.force_login(self.staff)
        response = self.client.get(reverse("admin_analytics_alerts"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Admin Analytics Alerts")
        self.assertContains(response, "Resumen de alertas")
        self.assertContains(response, "Health signals")

    def test_alert_service_surfaces_ai_errors_and_product_activation(self):
        AIUsageEvent.objects.create(
            user=self.member,
            period=current_period(),
            action_type="assistant.chat",
            provider="openai",
            model_name="gpt-test",
            status=AIUsageEvent.Status.ERROR,
            estimated_cost_usd=Decimal("0.000100"),
        )

        vm = build_alerts_vm()
        titles = {alert.title for alert in vm.alerts}

        self.assertIn("Sin builders activos", titles)
        self.assertIn("Error rate IA alto", titles)

    def test_alert_service_marks_low_food_catalog_quality(self):
        CatalogFood.objects.create(
            canonical_name="Low quality item",
            display_name="Low quality item",
            protein_g_per_100g=10,
            carbs_g_per_100g=10,
            fat_g_per_100g=5,
            data_quality_score=20,
            status=CatalogFood.STATUS_PUBLISHED,
        )
        Meal.objects.create(name="Active meal", created_by=self.member, is_draft=False)

        vm = build_alerts_vm()
        titles = {alert.title for alert in vm.alerts}

        self.assertIn("Quality score bajo", titles)
        self.assertIn("Muchos alimentos sin evidencia", titles)
