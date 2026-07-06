from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from admin_analytics.filters import AdminAnalyticsFilters
from admin_analytics.selectors.overview import get_overview_metrics
from notas.domain.models import Meal


@override_settings(NUTRITION_ONBOARDING_GATE_ENABLED=False)
class AdminAnalyticsFiltersTests(TestCase):
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
            is_staff=False,
        )

    def test_filters_sanitize_unknown_values(self):
        filters = AdminAnalyticsFilters.from_querydict({"period": "999d", "user_segment": "robots"})

        self.assertEqual(filters.period, "7d")
        self.assertEqual(filters.user_segment, "all")
        self.assertEqual(filters.period_label, "Últimos 7 días")

    def test_overview_period_filter_changes_activity_window(self):
        now = timezone.now()
        recent = Meal.objects.create(name="Recent meal", created_by=self.member, is_draft=False)
        old = Meal.objects.create(name="Old meal", created_by=self.member, is_draft=False)
        Meal.objects.filter(pk=recent.pk).update(created_at=now - timedelta(days=10))
        Meal.objects.filter(pk=old.pk).update(created_at=now - timedelta(days=40))

        metrics_7d = get_overview_metrics(now=now, analytics_filters=AdminAnalyticsFilters(period="7d"))
        metrics_30d = get_overview_metrics(now=now, analytics_filters=AdminAnalyticsFilters(period="30d"))

        self.assertEqual(metrics_7d["product_activity"]["meals_7d"], 0)
        self.assertEqual(metrics_30d["product_activity"]["meals_7d"], 1)
        self.assertEqual(metrics_30d["period_label"], "Últimos 30 días")

    def test_overview_user_segment_filters_user_owned_activity(self):
        now = timezone.now()
        Meal.objects.create(name="Staff meal", created_by=self.staff, is_draft=False)
        Meal.objects.create(name="Member meal", created_by=self.member, is_draft=False)

        staff_metrics = get_overview_metrics(now=now, analytics_filters=AdminAnalyticsFilters(user_segment="staff"))
        member_metrics = get_overview_metrics(now=now, analytics_filters=AdminAnalyticsFilters(user_segment="members"))

        self.assertEqual(staff_metrics["users"]["total"], 1)
        self.assertEqual(member_metrics["users"]["total"], 1)
        self.assertEqual(staff_metrics["product_activity"]["meals_7d"], 1)
        self.assertEqual(member_metrics["product_activity"]["meals_7d"], 1)

    def test_filters_render_for_staff(self):
        self.client.force_login(self.staff)

        response = self.client.get(reverse("admin_analytics_overview"), {"period": "30d", "user_segment": "members"})

        self.assertEqual(response.status_code, 200)
        html = response.content.decode("utf-8")
        self.assertContains(response, 'class="admin-analytics-subheader"', html=False)
        self.assertContains(response, 'class="admin-analytics-filterbar"', html=False)
        self.assertContains(response, "Últimos 30 días")
        self.assertContains(response, "Miembros")
        self.assertContains(response, 'option value="30d" selected', html=False)
        self.assertContains(response, 'option value="members" selected', html=False)
        self.assertEqual(html.count('class="admin-analytics-filterbar"'), 1)
        self.assertNotIn("admin-analytics-filters", html)
        self.assertNotIn("Período y segmento", html)
