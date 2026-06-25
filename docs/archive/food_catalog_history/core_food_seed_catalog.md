# Core Food Seed Catalog

## Purpose

This document describes the initial core food seed catalog.

The goal is to define a small, controlled set of global foods that should become usable in the picker with Spanish display names and aliases.

## Why a seed catalog exists

Imported foods should not automatically become core.

A seed catalog makes curation explicit.

The catalog maps known canonical names to:

- localized display names
- Spanish aliases
- core visibility
- verified status
- active status

## Architecture

The seed catalog lives in:

- notas/application/services/food_imports/core_food_seed_catalog.py

The service that applies the seed lives in:

- notas/application/services/food_imports/core_food_seed_service.py

## Current initial foods

The initial catalog includes:

- oats raw
- chicken breast cooked
- rice white cooked
- bananas raw

## Applied changes

When a matching global food exists, the seed service:

- marks it as core
- marks it as verified
- marks it as active
- creates Spanish aliases
- creates Spanish localized display names

## Safety rules

The seed service does not create missing foods.

The seed service does not modify user foods.

The seed service does not modify nutrition values.

The seed service only matches global foods by canonical_name.

## Future expansion

The catalog can grow progressively toward 100 to 300 core foods.

Recommended categories:

- proteins
- eggs and dairy
- grains and cereals
- legumes
- fruits
- vegetables
- fats and oils
- nuts and seeds
- Chile and LatAm common foods