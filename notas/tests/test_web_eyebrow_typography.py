from pathlib import Path

from django.test import SimpleTestCase

STATIC = Path(__file__).resolve().parents[1] / "static" / "notas" / "css"


class WebEyebrowTypographyTests(SimpleTestCase):
    def test_web_eyebrows_use_the_shared_medium_weight(self):
        generated = (STATIC / "ui-contract.generated.css").read_text()
        self.assertIn("--font-weight-eyebrow: 500;", generated)

        sources = [
            STATIC / "sharing_preview.css",
            STATIC / "components" / "calendarization.css",
            STATIC / "components" / "card_title.css",
            STATIC / "components" / "home.css",
            STATIC / "components" / "profile.css",
            STATIC / "components" / "program_active_kpis.css",
            STATIC / "components" / "programs.css",
            STATIC / "components" / "proposals.css",
            STATIC / "components" / "ui_system_gallery.css",
        ]
        for source in sources:
            with self.subTest(source=source.name):
                self.assertIn("font-weight: var(--font-weight-eyebrow)", source.read_text())
