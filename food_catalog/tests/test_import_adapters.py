from decimal import Decimal

from django.test import SimpleTestCase

from food_catalog.application.imports.contracts import ImportedFoodDTO
from food_catalog.application.imports.normalization import (
    normalize_food_name,
    normalize_imported_food,
)
from food_catalog.application.imports.quality import evaluate_imported_food_quality
from food_catalog.application.imports.sources import SOURCE_USDA
from food_catalog.application.imports.usda.foundation_foods_reader import (
    extract_foundation_food_payloads,
)
from food_catalog.application.imports.usda.mapper import (
    USDA_NUTRIENT_CARBS,
    USDA_NUTRIENT_ENERGY,
    USDA_NUTRIENT_FAT,
    USDA_NUTRIENT_PROTEIN,
    map_usda_food_to_imported_food_dto,
)


class FoodCatalogImportAdapterTests(SimpleTestCase):
    def test_import_dto_normalization_lives_in_food_catalog(self):
        dto = ImportedFoodDTO(
            source=" USDA ",
            source_food_id=" 12345 ",
            source_dataset=" Foundation Foods ",
            source_version=" 2026-04 ",
            name="  Avena   Integral Ácida  ",
            canonical_name="",
            protein=Decimal("16.9"),
            carbs=Decimal("66.3"),
            fat=Decimal("6.9"),
        )

        result = normalize_imported_food(dto)

        self.assertEqual(result.source, SOURCE_USDA)
        self.assertEqual(result.source_food_id, "12345")
        self.assertEqual(result.source_dataset, "foundation_foods")
        self.assertEqual(result.name, "Avena Integral Ácida")
        self.assertEqual(result.canonical_name, "avena integral acida")
        self.assertEqual(normalize_food_name("  Pechúga   de Pollo  "), "pechuga de pollo")

    def test_usda_mapper_preserves_source_identity_and_spanish_curated_name(self):
        payload = {
            "fdcId": 168421,
            "dataType": "SR Legacy",
            "description": "Kale, raw",
            "foodCategory": {"description": "Vegetables and Vegetable Products"},
            "foodNutrients": [
                {"nutrient": {"number": USDA_NUTRIENT_PROTEIN}, "amount": 2.92},
                {"nutrient": {"number": USDA_NUTRIENT_CARBS}, "amount": 4.42},
                {"nutrient": {"number": USDA_NUTRIENT_FAT}, "amount": 1.49},
                {"nutrient": {"number": USDA_NUTRIENT_ENERGY}, "amount": 35},
            ],
            "foodPortions": [{"amount": 1, "gramWeight": 67, "modifier": "cup"}],
        }

        result = map_usda_food_to_imported_food_dto(
            payload,
            source_version="2018-04",
            source_dataset="sr_legacy",
            preferred_name="Kale crudo",
            food_subgroup="leafy",
            preparation_state="raw",
        )

        self.assertEqual(result.name, "Kale crudo")
        self.assertEqual(result.source_description, "Kale, raw")
        self.assertEqual(result.source_data_type, "SR Legacy")
        self.assertEqual(result.calories_kcal_per_100g, Decimal("35"))
        self.assertEqual(result.preparation_state, "raw")
        self.assertEqual(len(result.raw_payload_hash), 64)
        self.assertIn("168421", result.source_url)
        self.assertEqual(result.source_portions[0]["grams"], "67")

    def test_quality_validation_is_source_agnostic(self):
        dto = ImportedFoodDTO(
            source=SOURCE_USDA,
            source_food_id="12345",
            source_dataset="foundation_foods",
            source_version="2026-04",
            name="Oats",
            canonical_name="oats",
            protein=Decimal("16.9"),
            carbs=Decimal("66.3"),
            fat=Decimal("6.9"),
        )

        result = evaluate_imported_food_quality(dto)

        self.assertTrue(result.is_valid)
        self.assertEqual(result.reason, "valid")

    def test_usda_mapper_returns_food_catalog_import_dto(self):
        payload = {
            "fdcId": 12345,
            "description": "Oats, raw",
            "foodNutrients": [
                {"nutrient": {"number": USDA_NUTRIENT_PROTEIN}, "amount": 16.9},
                {"nutrient": {"number": USDA_NUTRIENT_CARBS}, "amount": 66.3},
                {"nutrient": {"number": USDA_NUTRIENT_FAT}, "amount": 6.9},
            ],
        }

        result = map_usda_food_to_imported_food_dto(
            payload,
            source_version="2026-04",
        )

        self.assertIsInstance(result, ImportedFoodDTO)
        self.assertEqual(result.source, SOURCE_USDA)
        self.assertEqual(result.source_food_id, "12345")
        self.assertEqual(result.name, "Oats, raw")
        self.assertEqual(result.protein, Decimal("16.9"))

    def test_foundation_reader_extracts_supported_root_shape(self):
        payloads = [
            {"fdcId": 1001, "description": "Oats, raw"},
        ]

        result = extract_foundation_food_payloads({"FoundationFoods": payloads})

        self.assertEqual(result, payloads)
