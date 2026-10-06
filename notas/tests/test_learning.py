from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

User = get_user_model()


@override_settings(NUTRITION_ONBOARDING_GATE_ENABLED=False)
class LearningViewsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="learner", password="secret")
        self.client.force_login(self.user)

    def test_learning_home_exposes_two_catalogs(self):
        response = self.client.get(reverse("learning_home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Fundamentos Sistema")
        self.assertContains(response, "Fundamentos Nutricionales")
        self.assertContains(response, "Manuales de uso")

    def test_nutrition_catalog_links_to_article_detail(self):
        response = self.client.get(reverse("learning_catalog", args=["nutrition"]))

        self.assertContains(response, "Qué significa comer saludable")
        self.assertContains(response, reverse("learning_article", args=["nutrition", "alimentacion-saludable"]))

        detail = self.client.get(reverse("learning_article", args=["nutrition", "alimentacion-saludable"]))
        self.assertContains(detail, "Cuatro ideas guía")
        self.assertContains(detail, "Contenido educativo general")
        self.assertContains(detail, "OMS · Alimentación saludable")

    def test_manual_catalog_has_product_modules_and_detail(self):
        response = self.client.get(reverse("learning_catalog", args=["manuals"]))

        for title in ("Fichas personales", "Bibliotecas y jerarquía", "Inicio y programa activo", "Comparaciones", "Compartidos", "Asistente y propuestas"):
            self.assertContains(response, title)
        detail = self.client.get(reverse("learning_article", args=["manuals", "bibliotecas"]))
        self.assertContains(detail, "De menor a mayor")

    def test_learning_requires_authentication(self):
        self.client.logout()
        response = self.client.get(reverse("learning_home"))
        self.assertEqual(response.status_code, 302)
