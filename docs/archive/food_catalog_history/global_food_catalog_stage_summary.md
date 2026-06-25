# Global Food Catalog UX and Curation Stage Summary

## Purpose

This document summarizes the Global Food Catalog UX and Curation stage.

The goal of this stage was to make imported/global foods usable in picker flows without exposing unsafe or uncurated data.

## Completed capabilities

This stage added:

- global food query layer
- picker query for user foods plus visible global foods
- enriched picker payload contract
- picker visual badges
- admin curation actions
- Spanish aliases for USDA/global foods
- initial core catalog curation service
- management command to promote initial core foods

## Picker behavior

The picker can now expose:

- current user foods
- active global core foods
- active global extended foods

The picker excludes:

- private foods from other users
- inactive foods
- hidden global foods
- rejected global foods

## Picker metadata

Picker payload items include:

- picker_source
- picker_label
- is_user_food
- is_global_food
- is_verified
- visibility
- data_quality_score
- source

## Visual labels

Food picker items can visually show labels such as:

- Tu alimento
- Global
- Verificado
- USDA
- Core

## Spanish aliases

USDA/global foods can be found through Spanish aliases.

Example:

Oats, raw

Can be found by searching:

- Avena
- Avena cruda
- Avena integral

## Admin curation

Admins can mark foods as:

- core
- extended
- hidden
- rejected
- verified
- unverified
- active
- inactive

## Initial core catalog

The initial core catalog is explicit and conservative.

It promotes known useful global foods by canonical_name.

Current initial core foods may include:

- oats raw
- chicken breast cooked
- rice white cooked
- bananas raw

## What this stage does not do yet

This stage does not import a full USDA dataset.

This stage does not automatically translate all foods.

This stage does not generate standard portions at scale.

This stage does not create a custom curation dashboard.

This stage does not expose thousands of global foods by default.

## Recommended next stage

The next stage should focus on real dataset expansion.

Suggested next stage:

USDA Foundation Foods controlled import and curation

Recommended blocks:

1. Download or prepare Foundation Foods JSON or CSV.
2. Build a real USDA dataset reader.
3. Dry-run import with row counts.
4. Import Foundation Foods as extended or hidden.
5. Apply Spanish aliases where available.
6. Promote selected foods to core.
7. Add standard portions for core foods.
8. Review picker UX with larger result sets.