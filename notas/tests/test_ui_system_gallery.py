from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse


@override_settings(DEBUG=True)
class UISystemGalleryTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="ui-system-reviewer",
            email="ui-system@example.com",
            password="safe-test-password",
            is_staff=True,
        )
        self.url = reverse("ui_system_gallery")

    def test_gallery_is_available_without_product_data_in_debug(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Solo desarrollo")

    def test_gallery_renders_real_product_components(self):
        self.client.force_login(self.user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "UI System Web")
        self.assertContains(response, 'class="dash-kpi-comp"')
        self.assertContains(response, "list-page-header--program")
        self.assertContains(response, "card card--program program-card")
        self.assertContains(response, "?embed=1#components")
        self.assertEqual(response["X-Frame-Options"], "SAMEORIGIN")

    def test_embed_uses_the_same_gallery_without_recursive_frame(self):
        self.client.force_login(self.user)

        response = self.client.get(f"{self.url}?embed=1")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "ui-system-gallery-page--embed")
        self.assertNotContains(response, "ui-system-gallery__mobile-frame")

    @override_settings(DEBUG=False)
    def test_gallery_is_not_exposed_outside_debug(self):
        self.client.force_login(self.user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 404)
