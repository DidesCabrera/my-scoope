# USDA Food Usage Policy

## Purpose

This document defines how USDA FoodData Central foods should be used inside My Scoope.

The goal is to use USDA as a reliable external source without flooding the product with too many technical or duplicated foods.

## Current import capability

My Scoope can import controlled USDA-like JSON payloads through:

- notas/management/commands/import_usda_foods_json.py

The import flow is:

1. JSON file
2. USDA payload list
3. USDA mapper
4. ImportedFoodDTO
5. normalization
6. quality evaluation
7. Food creation
8. FoodSourceMetadata creation
9. FoodImportBatch tracking

## Data safety

USDA imports must be additive.

They must not:

- modify user foods
- modify historical meals
- modify daily plans
- change KPI calculations
- overwrite existing foods silently

## Deduplication

USDA foods are deduplicated by:

- source
- source_food_id

For USDA, source_food_id corresponds to fdcId.

## Recommended rollout

The recommended rollout is:

1. Import a small controlled sample.
2. Validate the imported foods in admin.
3. Import Foundation Foods.
4. Keep imported foods as extended or hidden by default.
5. Manually promote high-value foods to core.
6. Add aliases and Spanish names.
7. Add standard portions.
8. Expose global foods in the picker.
9. Expand to SR Legacy only after the picker and curation workflow are ready.

## Visibility policy

Imported foods should not become core automatically.

Initial visibility is based on quality score:

- quality score 70 or higher: extended
- quality score below 70: hidden

The core visibility level is reserved for curated foods.

The rejected visibility level is reserved for explicit admin or curation decisions.

## Practical USDA strategy

Foundation Foods should be the first real USDA dataset considered for import.

It is smaller and better suited for a first global catalog.

SR Legacy may be added later as a larger generic food base.

Branded Foods should not be imported into the normal picker without stronger filtering, search, deduplication and product-specific UX.

## Product recommendation

For the first real product version, My Scoope should expose a curated global catalog.

Recommended initial catalog:

- 100 to 300 manually reviewed core foods
- 300 to 1,000 extended global foods
- additional imported foods hidden until curated

## Historical data rule

Historical nutrition snapshots must remain stable.

If a USDA source changes later, My Scoope should compare metadata and hashes before deciding whether to update, version or mark the food for review.


## Initial core catalog policy

Core foods should be explicit.

Imported foods should not become core only because they come from USDA.

A food may become core when:

- it is common enough for normal users
- nutrition values are complete enough
- it has a useful Spanish alias
- it is active
- it is verified
- it is useful in picker search

The initial core catalog is maintained by canonical_name.