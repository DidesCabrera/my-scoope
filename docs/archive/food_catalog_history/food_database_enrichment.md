# Food Database Enrichment

## Purpose

The food database enrichment process prepares My Scoope to support a robust, traceable and extensible food catalog.

The goal is not to replace existing user foods. The goal is to complement the current Food model with metadata, aliases, portions, source traceability and future import capabilities.

## Current rule

Existing food data must not be overwritten or destructively migrated.

Current nutrition calculations must continue to use the existing Food fields:

- protein
- carbs
- fat

These values are interpreted as grams per 100 g.

Current kcal values are derived from domain constants:

- protein kcal = protein * 4
- carbs kcal = carbs * 4
- fat kcal = fat * 9

## Existing category contract

The Food.category property is already used by queries, DTOs and presentation builders.

It returns one of these logical values:

- system
- user

Because of this, food classification fields must not use the name category.

The enrichment layer uses these fields instead:

- food_group
- food_subgroup

## Enrichment models

The enrichment layer adds the following models:

- FoodSourceMetadata
- FoodPortion
- FoodAlias
- FoodImportBatch

## Model map

Food is still the main entity used by meals, daily plans and nutrition calculations.

Food relationships:

- Food has one FoodSourceMetadata
- Food has many FoodPortions
- Food has many FoodAliases
- Food is used by MealFood
- Food participates indirectly in DailyPlan nutrition through Meal and DailyPlanMeal

## Data safety rule

The enrichment process must be additive and backward-compatible.

It must not change:

- MealFood calculations
- Meal nutrition calculations
- DailyPlan nutrition calculations
- historical snapshots
- current picker behavior
- current food ownership rules

## Food ownership model

Foods may be user-created or global.

User food:

- created_by is set
- is_global is false
- category returns user

System or global food:

- created_by may be null
- is_global may be true
- category returns system

## Why food_group and food_subgroup exist

The app already uses Food.category for ownership/UI logic.

The fields food_group and food_subgroup are used for nutritional classification.

Examples:

- food_group: legumes
- food_subgroup: cooked legumes

- food_group: meats
- food_subgroup: poultry

- food_group: cereals
- food_subgroup: oats

## Roadmap

1. Add enrichment fields and supporting models.
2. Add admin visibility for curation.
3. Add documentation for traceability.
4. Add USDA import staging.
5. Normalize and validate imported foods.
6. Add global foods to the food picker.
7. Add a curation workflow.
8. Add Chile and LatAm localization.
9. Add source versioning and update strategy.

## Current block

Block 1 focuses on:

- model enrichment
- admin visibility
- source traceability
- aliases
- portions
- import batch structure
- documentation

This block must not change current KPI calculations.

## Implementation principle

The existing Food model remains the main food entity.

The enrichment layer adds information around Food instead of replacing Food.

This keeps the current app stable while preparing it for external food databases.