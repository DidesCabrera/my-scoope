from pathlib import Path

from django.test import SimpleTestCase


class FoodPickerBadgeStaticAssetsTests(SimpleTestCase):
    def test_food_item_renderer_includes_picker_badges(self):
        path = (
            Path(__file__).resolve().parents[1]
            / "static"
            / "notas"
            / "js"
            / "food_item_list.js"
        )

        content = path.read_text(encoding="utf-8")

        self.assertIn("renderPickerResultBadges", content)
        self.assertIn("renderPickerResultTitle", content)
        self.assertIn("is_user_food", content)
        self.assertIn("is_global_food", content)
        self.assertIn("is_verified", content)
        self.assertIn("visibility === \"core\"", content)

    def test_food_picker_css_includes_badge_styles(self):
        path = (
            Path(__file__).resolve().parents[1]
            / "static"
            / "notas"
            / "css"
            / "components"
            / "food_picker.css"
        )

        content = path.read_text(encoding="utf-8")

        self.assertIn(".picker-item-badges", content)
        self.assertIn(".picker-item-badge", content)
        self.assertIn(".picker-item-badge--user", content)
        self.assertIn(".picker-item-badge--global", content)
        self.assertIn(".picker-item-badge--verified", content)
        self.assertIn(".picker-item-badge--core", content)


    def test_food_picker_js_filters_by_search_text(self):
        food_picker_path = (
            Path(__file__).resolve().parents[1]
            / "static"
            / "notas"
            / "js"
            / "food_picker.js"
        )
        dpm_picker_path = (
            Path(__file__).resolve().parents[1]
            / "static"
            / "notas"
            / "js"
            / "dpm_food_picker.js"
        )

        food_picker_content = food_picker_path.read_text(encoding="utf-8")
        dpm_picker_content = dpm_picker_path.read_text(encoding="utf-8")

        for content in [food_picker_content, dpm_picker_content]:
            self.assertIn("filterFoodsBySearch", content)
            self.assertIn("getFoodSearchText", content)
            self.assertIn("search_text", content)
            self.assertIn("normalize(\"NFD\")", content)
