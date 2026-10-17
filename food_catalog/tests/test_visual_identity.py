from unittest import TestCase

from core.food_visual_identity import (
    infer_food_visual_identity,
    resolved_food_visual_identity,
)


class FoodVisualIdentityTests(TestCase):
    def test_common_foods_receive_specific_visuals(self):
        cases = {
            "Pechuga de pollo cocida": ("🍗", "chicken_breast"),
            "Manzana Fuji": ("🍎", "apple"),
            "Pera Packham": ("🍐", "pear"),
            "Salmón al horno": ("🐟", "salmon"),
        }

        for name, expected in cases.items():
            with self.subTest(name=name):
                visual = infer_food_visual_identity(name)
                self.assertEqual((visual.emoji, visual.visual_key), expected)

    def test_maca_distinguishes_powder_from_root(self):
        powder = infer_food_visual_identity("Maca andina en polvo")
        root = infer_food_visual_identity("Maca andina")

        self.assertEqual((powder.emoji, powder.visual_key), ("🥣", "maca_powder"))
        self.assertEqual((root.emoji, root.visual_key), ("🌱", "maca_root"))

    def test_group_and_generic_fallbacks_always_return_a_visual(self):
        grouped = infer_food_visual_identity("Producto nuevo", food_group="fruits_and_fruit_juices")
        generic = infer_food_visual_identity("Producto experimental")

        self.assertEqual((grouped.emoji, grouped.visual_key), ("🍎", "fruit_generic"))
        self.assertEqual((generic.emoji, generic.visual_key), ("🍽️", "food_generic"))

    def test_curated_values_take_precedence_over_inference(self):
        visual = resolved_food_visual_identity(
            "Pechuga de pollo",
            emoji="🐔",
            visual_key="curated_chicken_breast",
        )

        self.assertEqual((visual.emoji, visual.visual_key), ("🐔", "curated_chicken_breast"))
