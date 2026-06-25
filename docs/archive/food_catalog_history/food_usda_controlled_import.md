# USDA Controlled Food Import

## Purpose

This document describes the first controlled USDA import flow in My Scoope.

The goal is not to import the full USDA database yet.

The goal is to prove that a small list of USDA-like payloads can move through the complete import pipeline safely.

## Architecture

The command lives in:

- notas/application/services/commands/import_usda_food_payloads.py

The USDA mapper lives in:

- notas/application/services/food_imports/usda/mapper.py

The generic batch command lives in:

- notas/application/services/commands/import_food_batch.py

The generic single food import command lives in:

- notas/application/services/commands/import_food_from_source.py

## Flow

USDA-like payload list

USDA mapper

ImportedFoodDTO list

generic food batch import

generic source food import

normalization

quality evaluation

Food

FoodSourceMetadata

FoodImportBatch

## Data safety

This block does not import the full USDA database.

This block does not modify user foods.

This block does not modify historical meals.

This block does not modify daily plans.

This block does not change current KPI calculations.

The import remains additive.

## Deduplication

Deduplication is based on:

- source
- source_food_id

For USDA records, source is:

- usda

The source_food_id is the USDA fdcId.

## Batch tracking

Each controlled import creates a FoodImportBatch record.

The batch stores:

- source
- source_version
- total_rows
- imported_rows
- skipped_rows
- failed_rows
- status
- notes

## Fixture policy

Small controlled fixtures may live in:

- notas/tests/fixtures/food_imports/usda/

Fixtures are used to validate the import flow without relying on external downloads or network access.

## Current limitation

This block does not parse the official USDA CSV or ZIP files.

A future block may add:

- USDA file reader
- source dataset loader
- import dry-run
- admin action
- management command
- selected subset imports