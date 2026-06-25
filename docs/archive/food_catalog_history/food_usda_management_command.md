# USDA JSON Import Management Command

## Purpose

This document describes the controlled USDA JSON import management command.

The command allows My Scoope to import a small JSON file containing USDA-like payloads through the existing food import pipeline.

This is still not a full USDA dataset import.

## Command

The command lives in:

- notas/management/commands/import_usda_foods_json.py

## Example usage

python manage.py import_usda_foods_json notas/tests/fixtures/food_imports/usda/sample_foundation_foods.json --source-version 2026-04 --source-dataset foundation_foods

## Required arguments

path:

Path to a JSON file containing a list of USDA-like food payloads.

--source-version:

Source dataset version.

Example:

2026-04

## Optional arguments

--source-dataset:

Source dataset name.

Default:

foundation_foods

--notes:

Optional notes stored in FoodImportBatch.

## Import flow

JSON file

USDA-like payload list

import_usda_food_payloads

USDA mapper

ImportedFoodDTO list

generic food batch import

Food

FoodSourceMetadata

FoodImportBatch

## Data safety

This command does not modify user foods.

This command does not modify historical plans.

This command does not modify meal snapshots.

This command does not change KPI calculations.

The import is additive.

## Deduplication

Deduplication remains based on:

- source
- source_food_id

For USDA, source_food_id corresponds to fdcId.

## Current limitation

The command expects a JSON list already shaped like the supported USDA-like payload.

It does not yet read the official USDA ZIP or CSV dataset directly.

That can be implemented later as a separate loader.