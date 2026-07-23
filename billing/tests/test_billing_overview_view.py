from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse


User = get_user_model()


class BillingOverviewViewTests(TestCase):
    @override_settings(BILLING_MERCADOPAGO_CHECKOUT_ENABLED=False)
    def test_current_plan_summary_renders_in_its_own_profile_card(self):
        user = User.objects.create_user(
            username="billing_overview_user",
            email="billing-overview@test.com",
            password="12345678",
        )
        self.client.force_login(user)

        response = self.client.get(reverse("billing:overview"))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "home-eyebrow")
        self.assertNotContains(response, "profile-account-subtitle")
        self.assertContains(response, '<section class="profile-section-card">')
        self.assertContains(response, "Plan actual")
        self.assertContains(response, '<div class="profile-account-grid">')
        self.assertNotContains(response, "profile-account-primary-metric")
