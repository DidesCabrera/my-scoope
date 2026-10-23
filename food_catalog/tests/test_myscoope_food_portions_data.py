import json
from decimal import Decimal
from pathlib import Path

from django.test import SimpleTestCase

from shared_kernel.food_portions import HouseholdMeasure, MyScoopeFoodGroup

DATA_PATH = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "myscoope_food_portions_v1.json"
)


class MyScoopeFoodPortionsDataTests(SimpleTestCase):
    def test_sheet_snapshot_contains_the_219_assigned_foods(self):
        payload = json.loads(DATA_PATH.read_text(encoding="utf-8"))
        foods = payload["foods"]

        self.assertEqual(payload["schema_version"], "myscoope.food_portions.v1")
        self.assertEqual(len(foods), 219)
        self.assertEqual(len({food["catalog_ref"] for food in foods}), 219)

    def test_every_row_uses_the_controlled_contract_values(self):
        foods = json.loads(DATA_PATH.read_text(encoding="utf-8"))["foods"]
        allowed_groups = {group.value for group in MyScoopeFoodGroup}
        allowed_measures = {measure.value for measure in HouseholdMeasure}

        for food in foods:
            with self.subTest(food=food["name"]):
                self.assertIn(food["myscoope_group"], allowed_groups)
                self.assertIn(food["household_measure"], allowed_measures)
                self.assertGreater(Decimal(food["household_amount"]), 0)
                self.assertGreater(Decimal(food["metric_amount"]), 0)
                self.assertIn(food["metric_unit"], {"g", "ml"})

    def test_every_sheet_group_is_represented_by_the_taxonomy(self):
        foods = json.loads(DATA_PATH.read_text(encoding="utf-8"))["foods"]

        self.assertEqual(
            {food["myscoope_group"] for food in foods},
            {group.value for group in MyScoopeFoodGroup},
        )
