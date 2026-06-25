# Food Import Quality Rules

## Purpose

This document describes the first quality rules used before external foods enter the My Scoope global food catalog.

These rules are defensive. They are not intended to be a complete scientific validation system.

Their purpose is to prevent obviously invalid imported records from entering the database.

## Import flow

External food data must be mapped into ImportedFoodDTO.

Then the data passes through these steps:

1. normalization
2. quality evaluation
3. source import command
4. Food creation
5. FoodSourceMetadata creation

## Architecture location

DTOs live in:

- notas/application/dto/

Food import services live in:

- notas/application/services/food_imports/

Write commands live in:

- notas/application/services/commands/

This follows the current My Scoope architecture where commands centralize write operations and application services contain shared application rules.

## Normalization rules

Imported foods are normalized before being saved.

Current normalization includes:

- trimming text
- collapsing repeated spaces
- lowercasing canonical names
- removing accents from canonical names
- normalizing source keys
- normalizing food group and subgroup keys
- converting numeric values to Decimal

## Required fields

An imported food must have:

- source
- source_food_id
- name
- canonical_name
- protein
- carbs
- fat

## Macro rules

Protein, carbs and fat must be valid grams per 100 g.

Rejected cases:

- negative protein
- negative carbs
- negative fat
- protein greater than 100 g per 100 g
- carbs greater than 100 g per 100 g
- fat greater than 100 g per 100 g
- total macros greater than the configured maximum limit

The initial total macro limit is intentionally defensive and may be refined later.

## Extended nutrient rules

Optional nutrients are allowed to be empty.

When present, they must be valid values.

Rejected cases:

- negative fiber
- negative sugar
- negative saturated fat
- negative sodium
- fiber greater than 100 g per 100 g
- sugar greater than 100 g per 100 g
- saturated fat greater than 100 g per 100 g
- sodium above the configured maximum limit

## Quality score

The first quality score is simple.

A valid food starts with a base score.

The score increases when the record includes useful metadata such as:

- source dataset
- source version
- food group
- food subgroup
- fiber
- sugar
- saturated fat
- sodium

The score is capped at 100.

## Data safety

Invalid imported foods are skipped.

Existing user foods are not modified.

Existing imported foods with the same source and source_food_id are not duplicated.

Current KPI calculations are not changed by this block.