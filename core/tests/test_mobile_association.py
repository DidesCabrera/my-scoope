from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from notas.domain.models import Meal


class MobileAssociationTests(SimpleTestCase):
    def test_association_endpoints_fail_closed_without_signing_identity(self):
        self.assertEqual(self.client.get(reverse("apple_app_site_association")).status_code, 503)
        self.assertEqual(self.client.get(reverse("android_asset_links")).status_code, 503)

    @override_settings(MYSCOOPE_APPLE_TEAM_ID="AB12CD34EF")
    def test_apple_association_contains_meal_detail_app_link(self):
        response = self.client.get(reverse("apple_app_site_association"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/json")
        details = response.json()["applinks"]["details"][0]
        self.assertEqual(details["appID"], "AB12CD34EF.com.myscoope.app")
        self.assertEqual(details["paths"], ["/s/*", "/mobile/confirm-email/*", "/libraries/meals/*"])

    def test_meal_app_link_has_a_private_web_fallback(self):
        response = self.client.get(reverse("meal_app_link", args=[23]))
        self.assertRedirects(response, "/app/meals/23/", fetch_redirect_response=False)
        self.assertEqual(self.client.post(reverse("meal_app_link", args=[23])).status_code, 405)

    @override_settings(
        MYSCOOPE_ANDROID_SHA256_CERT_FINGERPRINTS=[
            ":".join(["AA"] * 32),
        ]
    )
    def test_android_association_contains_package_and_valid_fingerprint(self):
        response = self.client.get(reverse("android_asset_links"))

        self.assertEqual(response.status_code, 200)
        target = response.json()[0]["target"]
        self.assertEqual(target["package_name"], "com.myscoope.app")
        self.assertEqual(target["sha256_cert_fingerprints"], [":".join(["AA"] * 32)])


@override_settings(NUTRITION_ONBOARDING_GATE_ENABLED=False)
class MealAppLinkAccountTests(TestCase):
    def test_other_account_sees_helpful_page_without_meal_details(self):
        user_model = get_user_model()
        owner = user_model.objects.create_user(username="meal_owner", password="testpass123")
        visitor = user_model.objects.create_user(username="other_account", password="testpass123")
        meal = Meal.objects.create(name="Private meal", created_by=owner, is_draft=False)
        self.client.force_login(visitor)

        response = self.client.get(reverse("meal_app_link", args=[meal.pk]))

        self.assertEqual(response.status_code, 404)
        self.assertContains(response, "misma cuenta que conectaste a ChatGPT", status_code=404)
        self.assertNotContains(response, meal.name, status_code=404)
