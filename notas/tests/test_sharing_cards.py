from io import BytesIO

from django.test import SimpleTestCase
from PIL import Image

from notas.presentation.sharing_cards import render_share_card_png, snapshot_card_etag


class SharingCardRendererTests(SimpleTestCase):
    def setUp(self):
        self.snapshot = {
            "schema_version": "sharing.snapshot.v1",
            "subject": {"type": "daily_plan", "title": "Plan de fuerza y recuperación"},
            "summary": {"meal_count": 4, "food_count": 12},
            "nutrition": {
                "calories": 2150,
                "protein_grams": 165.4,
                "carbs_grams": 220,
                "fat_grams": 68.2,
            },
            "meals": [],
        }

    def test_renderer_is_deterministic_and_does_not_need_models_or_request(self):
        first = render_share_card_png(self.snapshot)
        second = render_share_card_png(dict(self.snapshot))

        self.assertEqual(first, second)
        self.assertTrue(first.startswith(b"\x89PNG\r\n\x1a\n"))
        with Image.open(BytesIO(first)) as image:
            self.assertEqual(image.size, (1200, 630))

    def test_etag_is_canonical_and_changes_with_snapshot_content(self):
        reordered = dict(reversed(list(self.snapshot.items())))
        self.assertEqual(snapshot_card_etag(self.snapshot), snapshot_card_etag(reordered))

        changed = {**self.snapshot, "summary": {"meal_count": 5, "food_count": 12}}
        self.assertNotEqual(snapshot_card_etag(self.snapshot), snapshot_card_etag(changed))

    def test_untrusted_values_are_bounded_and_invalid_numbers_are_safe(self):
        snapshot = {
            "subject": {"title": "Nombre " * 1000},
            "summary": {"meal_count": "invalid", "food_count": -10},
            "nutrition": {"calories": "invalid"},
        }

        payload = render_share_card_png(snapshot)

        self.assertLess(len(payload), 250_000)
