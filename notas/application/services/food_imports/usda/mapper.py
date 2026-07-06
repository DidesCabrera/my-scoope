"""Compatibility wrapper for Food Catalog USDA import mapper."""

from food_catalog.application.imports.usda.mapper import (
    USDA_NUTRIENT_CARBS,
    USDA_NUTRIENT_FAT,
    USDA_NUTRIENT_FIBER,
    USDA_NUTRIENT_PROTEIN,
    USDA_NUTRIENT_SATURATED_FAT,
    USDA_NUTRIENT_SODIUM,
    USDA_NUTRIENT_SUGARS,
    USDA_SOURCE_DATASET_DEFAULT,
    map_usda_food_to_imported_food_dto,
)

__all__ = [
    "USDA_NUTRIENT_CARBS",
    "USDA_NUTRIENT_FAT",
    "USDA_NUTRIENT_FIBER",
    "USDA_NUTRIENT_PROTEIN",
    "USDA_NUTRIENT_SATURATED_FAT",
    "USDA_NUTRIENT_SODIUM",
    "USDA_NUTRIENT_SUGARS",
    "USDA_SOURCE_DATASET_DEFAULT",
    "map_usda_food_to_imported_food_dto",
]
