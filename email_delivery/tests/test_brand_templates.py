from types import SimpleNamespace

from django.test import RequestFactory, SimpleTestCase

from notas.application.services.notifications.share_emails import (
    build_normalized_share_invitation_email,
)


class ShareEmailBrandTests(SimpleTestCase):
    def setUp(self):
        self.request = RequestFactory().get("/share/", HTTP_HOST="testserver")

    def _render(self, subject_type, *, variant=""):
        invitation = SimpleNamespace(
            public_id="12345678-1234-1234-1234-123456789abc",
            subject="Plan compartido",
            message="<b>Mensaje personal</b>",
            resource=SimpleNamespace(
                subject_type=subject_type,
                snapshot={
                    "subject": {
                        "title": "Contenido de prueba",
                        "variant": variant,
                    }
                },
                sender=SimpleNamespace(username="Felipe"),
            ),
        )
        return build_normalized_share_invitation_email(
            request=self.request,
            invitation=invitation,
        )

    def test_every_entity_uses_approved_color_and_single_preview_action(self):
        cases = (
            ("daily_plan", "", "#6229CE"),
            ("meal", "", "#CF34B0"),
            ("meal", "daily_plan_meal", "#CF34B0"),
            ("food", "", "#FF8800"),
            ("program", "", "#1B6491"),
        )
        for kind, variant, color in cases:
            with self.subTest(kind=kind, variant=variant):
                subject, text, html = self._render(kind, variant=variant)
                self.assertEqual(subject, "Plan compartido")
                self.assertIn("/i/", text)
                self.assertIn("Revisar invitación", html)
                self.assertIn(color, html)
                self.assertEqual(html.count('style="display:inline-block;padding:14px'), 1)
                self.assertIn("myscoope-email-logo.png", html)
                self.assertIn("&lt;b&gt;Mensaje personal&lt;/b&gt;", html)
                self.assertNotIn("<b>Mensaje personal</b>", html)
