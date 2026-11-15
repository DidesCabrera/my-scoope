import json
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

from django.test import SimpleTestCase

from food_catalog.application.editorial_descriptions import description_for_food


class FoodDescriptionDatasetTests(SimpleTestCase):
    def test_production_baseline_has_exact_reviewed_identity_coverage(self):
        path = Path(__file__).resolve().parent.parent / "data" / "food_descriptions_v1.json"
        records = json.loads(path.read_text(encoding="utf-8"))["records"]
        catalog = [row for row in records if "catalog_ref" in row]
        legacy = [row for row in records if "operational_food_id" in row]
        self.assertEqual((len(catalog), len(legacy)), (222, 49))
        self.assertEqual(len({row["catalog_ref"] for row in catalog}), 222)
        self.assertEqual(len({row["operational_food_id"] for row in legacy}), 49)
        portions_path = path.with_name("myscoope_food_portions_v1.json")
        original_foods = json.loads(portions_path.read_text(encoding="utf-8"))["foods"]
        self.assertEqual(
            {(row["catalog_ref"], row["name"]) for row in original_foods},
            {(row["catalog_ref"], row["name"]) for row in catalog if row["name"] not in {"Pan de completo", "Vienesa tradicional PF", "Mayonesa regular"}},
        )
        for row in records:
            self.assertTrue(row["review_state"].startswith("approved"))
            self.assertTrue(row["name"] and row["description"] and row["guidance_source"])
            self.assertLessEqual(len(row["description"]), 220)

    def test_description_requires_exact_identity_and_active_global_status(self):
        food = SimpleNamespace(
            id=123, name="Aceite de oliva", is_global=True, is_active=True,
            is_verified=True, catalog_food_ref=UUID("b806c80e-0ea2-4b9f-aa41-4607fec28269"),
        )
        self.assertIn("Aceite vegetal", description_for_food(food))
        self.assertEqual(description_for_food(SimpleNamespace(**{**vars(food), "name": "Otro aceite"})), "")
        self.assertEqual(description_for_food(SimpleNamespace(**{**vars(food), "is_global": False})), "")
        self.assertEqual(description_for_food(SimpleNamespace(**{**vars(food), "is_active": False})), "")
        legacy = SimpleNamespace(id=63, name="Alimento", is_global=True, is_active=True, is_verified=False, catalog_food_ref=None)
        self.assertIn("no identifica", description_for_food(legacy))
        self.assertEqual(description_for_food(SimpleNamespace(**{**vars(legacy), "name": "Otro"})), "")
        self.assertEqual(description_for_food(SimpleNamespace(**{**vars(legacy), "is_verified": True})), "")
