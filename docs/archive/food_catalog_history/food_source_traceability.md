# Food Source Traceability

## Purpose

Food source traceability allows My Scoope to identify where each food came from, when it was imported, under which dataset version, and how it was normalized.

This is required for:

- public food database imports
- food quality control
- future synchronization
- debugging nutrition values
- licensing and attribution
- AI-safe food recommendations

## Core model

FoodSourceMetadata stores source-level information for a Food.

Each Food may have one FoodSourceMetadata record.

## Supported sources

Initial supported sources:

- manual
- usda
- open_food_facts
- latinfoods
- inta_chile
- admin_import

## Important fields

### source

Origin of the food data.

Examples:

- manual
- usda
- open_food_facts
- latinfoods
- inta_chile
- admin_import

### source_food_id

External identifier from the original source.

For example, this may be the USDA FoodData Central ID in a future USDA import.

Manual foods may have an empty source_food_id.

### source_dataset

Dataset name or subset.

Examples:

- foundation_foods
- sr_legacy
- branded_foods
- manual

### source_version

Version of the external dataset.

This is useful when public food databases publish new releases.

### source_url

Public reference URL for the source.

### raw_payload_hash

Hash of the original imported payload.

This helps detect whether the external source changed.

### normalized_payload_hash

Hash of the normalized internal payload used by My Scoope.

This helps detect whether the internal normalized representation changed.

### license_name

License associated with the source.

Examples:

- CC0
- Open Database License
- Manual entry

### attribution

Required attribution text when applicable.

### imported_at

Date when the food was imported.

### last_synced_at

Date when the food was last compared with its source.

## Uniqueness rule

For external foods, this pair must be unique:

- source
- source_food_id

This prevents duplicate imports from the same external source.

Manual foods may have an empty source_food_id.

## Data safety rule

External updates must not silently overwrite historical nutrition values.

When source data changes, the system should eventually compare payload hashes and decide whether to:

- keep the current food unchanged
- update the global food
- create a new version
- mark the food for review

## Historical data policy

Daily plan and meal snapshots must remain stable.

A food update should not unexpectedly change old nutrition history.

This is especially important because meals, daily plans and proposal workflows may depend on values that were valid at the time they were created.

## Future synchronization policy

A future synchronization process should:

1. Import a new source batch.
2. Match foods by source and source_food_id.
3. Compare raw_payload_hash.
4. Compare normalized_payload_hash.
5. Detect nutrition changes.
6. Decide whether the change can be applied automatically or requires review.
7. Keep a traceable record of the import.

## Relationship with FoodImportBatch

FoodImportBatch tracks import-level information.

FoodSourceMetadata tracks food-level source information.

FoodImportBatch answers:

- Which source was imported?
- Which version was imported?
- How many rows were processed?
- How many rows succeeded?
- How many rows failed?

FoodSourceMetadata answers:

- Where did this specific food come from?
- What was its external ID?
- What source version was used?
- When was it imported?
- Has it been synchronized?

## Current block

In Block 1, traceability is only structural.

This block does not yet import USDA, Open Food Facts or LATINFOODS.

It only prepares the model and admin surface so future imports can be implemented safely.