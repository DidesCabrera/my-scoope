# Food Spanish Aliases

## Purpose

This document describes the first Spanish alias layer for imported/global foods.

The goal is to let users search imported USDA foods using Spanish names without renaming the original food record yet.

## Current approach

The original Food name remains unchanged.

Spanish names are stored as FoodAlias records.

Example:

Oats, raw

Aliases:

- Avena
- Avena cruda
- Avena integral

## Architecture

Alias services live in:

- notas/application/services/food_imports/aliases.py

USDA Spanish alias catalog lives in:

- notas/application/services/food_imports/usda/spanish_alias_catalog.py

USDA alias application service lives in:

- notas/application/services/food_imports/usda/spanish_aliases.py

The management command lives in:

- notas/management/commands/apply_usda_spanish_aliases.py

## Search behavior

The picker query searches by:

- Food.name
- Food.canonical_name
- FoodAlias.name
- FoodAlias.normalized_name

This allows a user to search for:

Avena

and find:

Oats, raw

## Data safety

Aliases do not change nutrition values.

Aliases do not rename the original food.

Aliases do not affect historical meals or daily plans.

Aliases only improve search and future display possibilities.

## Current limitation

This block only includes a small controlled Spanish alias catalog.

It is not a full automatic translation system.

More aliases can be added progressively as the core catalog grows.