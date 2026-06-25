# USDA Food Import Mapper

## Purpose

This document describes the first USDA FoodData Central mapper used by My Scoope.

The mapper converts a USDA-like food payload into the internal ImportedFoodDTO contract.

This block does not download or import the full USDA dataset.

It only prepares the mapping layer required before real imports.

## Architecture

The mapper lives in:

- notas/application/services/food_imports/usda/mapper.py

The mapper returns:

- ImportedFoodDTO

The mapper does not write to the database.

Database writes remain centralized in:

- notas/application/services/commands/import_food_from_source.py
- notas/application/services/commands/import_food_batch.py

## Import flow

USDA payload

ImportedFoodDTO

normalize_imported_food

evaluate_imported_food_quality

import_food_from_source

Food and FoodSourceMetadata

## Supported USDA fields

The first mapper supports a minimal FoodData Central-like payload.

Required fields:

- fdcId
- description
- foodNutrients

Optional fields:

- foodCategory

## Nutrient mapping

The initial mapper extracts these USDA nutrient numbers:

- 203: protein
- 204: total fat
- 205: carbohydrate by difference
- 291: dietary fiber
- 269: total sugars
- 606: saturated fat
- 307: sodium

## Data safety

The USDA mapper does not change existing foods.

The USDA mapper does not update user foods.

The USDA mapper does not update historical meals or daily plans.

The mapper only prepares ImportedFoodDTO records.

Validation, deduplication and persistence remain in the existing import pipeline.

## Current limitation

This block intentionally does not parse full USDA CSV files.

A later block may add:

- CSV reader
- ZIP dataset reader
- source batch command
- import subset selector
- dry-run mode
- admin import action

## Source attribution

USDA FoodData Central data should be attributed as:

U.S. Department of Agriculture, Agricultural Research Service, Beltsville Human Nutrition Research Center. FoodData Central.

USDA FoodData Central data are published under CC0 1.0.