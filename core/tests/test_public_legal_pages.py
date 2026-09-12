from django.test import SimpleTestCase
from django.urls import reverse


class PublicLegalPagesTests(SimpleTestCase):
    def test_required_legal_and_support_pages_are_public(self):
        expected = {
            "terms": "Términos de Uso",
            "privacy": "Política de Privacidad",
            "refund_policy": "Política de Cancelaciones y Reembolsos",
            "support": "Centro de Soporte",
        }

        for route_name, heading in expected.items():
            with self.subTest(route_name=route_name):
                response = self.client.get(reverse(route_name))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, heading)
                self.assertContains(response, "My Scoope SpA")
                self.assertContains(response, "felipe@myscoope.com")

    def test_every_legal_page_links_to_all_public_policies(self):
        links = ("/privacy/", "/terms/", "/refund-policy/", "/support/")

        for route_name in ("terms", "privacy", "refund_policy", "support"):
            response = self.client.get(reverse(route_name))
            for link in links:
                with self.subTest(route_name=route_name, link=link):
                    self.assertContains(response, f'href="{link}"')

    def test_refund_policy_separates_web_and_store_channels(self):
        response = self.client.get(reverse("refund_policy"))

        self.assertContains(response, "Garantía de devolución de 30 días")
        self.assertContains(response, "No ofrecemos devoluciones proporcionales")
        self.assertContains(response, "Paddle Buyer Support")
        self.assertContains(response, "Apple App Store")
        self.assertContains(response, "Google Play")
        self.assertContains(response, "derechos irrenunciables")

    def test_landing_discloses_currency_billing_and_legal_navigation(self):
        response = self.client.get(reverse("landing"))

        self.assertContains(response, "CLP 7.990")
        self.assertContains(response, "CLP 79.900 facturados anualmente")
        self.assertContains(response, "150 créditos de asistencia IA al mes")
        self.assertContains(response, "1.000 créditos de asistencia IA al mes")
        self.assertContains(response, 'href="/refund-policy/"')
        self.assertNotContains(response, "Funciones premium futuras")

    def test_public_commercial_pages_do_not_present_retired_payment_channels(self):
        for route_name in ("landing", "terms", "privacy", "refund_policy", "support"):
            response = self.client.get(reverse(route_name))
            content = response.content.decode().lower()
            with self.subTest(route_name=route_name):
                self.assertNotIn("mercado pago", content)
                self.assertNotIn("openfactura", content)
