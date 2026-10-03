from django.template.loader import render_to_string
from django.test import SimpleTestCase


class CardTitleLinkTests(SimpleTestCase):
    def test_entity_child_card_links_the_complete_title_section(self):
        html = render_to_string(
            "components/card_child_title.html",
            {
                "titulo": {
                    "icon": "carrot",
                    "label": "Food",
                    "name": "Manzana",
                    "structural_indicators": {"foods_count": 2},
                    "url": "/foods/7/",
                }
            },
        )

        self.assertIn(
            'href="/foods/7/" class="card-title-section-link"', html
        )
        self.assertLess(html.index("card-title-section-link"), html.index("card-title-eyebrow"))
        self.assertLess(html.index("card-title-section-link"), html.index("<h3>Manzana</h3>"))
        self.assertEqual(html.count('aria-label="Ver detalle de Manzana"'), 1)

    def test_program_child_card_links_the_complete_title_section(self):
        html = render_to_string(
            "components/card_child_program.html",
            {
                "child_card": {
                    "actions": [],
                    "chart": {},
                    "child_id": 9,
                    "filled_days_count": 5,
                    "foods_count": 12,
                    "metadata": {},
                    "title": "Programa base",
                    "url": "/programs/9/",
                    "weeks_count": 2,
                }
            },
        )

        self.assertIn(
            'href="/programs/9/" class="card-title-section-link"', html
        )
        self.assertLess(html.index("card-title-section-link"), html.index("card-title-eyebrow"))
        self.assertLess(
            html.index("card-title-section-link"), html.index("<h3>Programa base</h3>")
        )
        self.assertEqual(html.count('aria-label="Ver detalle de Programa base"'), 1)
