# Apply Core Food Seed Command

## Purpose

This document describes the management command used to apply the initial core food seed catalog.

The command promotes known useful global foods into the curated core catalog.

## Command

The command is:

python manage.py apply_core_food_seed

## Architecture

The command lives in:

- notas/management/commands/apply_core_food_seed.py

The service lives in:

- notas/application/services/food_imports/core_food_seed_service.py

The seed catalog lives in:

- notas/application/services/food_imports/core_food_seed_catalog.py

## What the command does

For matching global foods, the command:

- marks the food as core
- marks the food as verified
- marks the food as active
- creates Spanish aliases
- creates Spanish localized display names

## Matching rule

Foods are matched by canonical_name.

Only global foods are affected.

User foods are not modified.

## Current initial foods

The current seed may include:

- oats raw
- chicken breast cooked
- rice white cooked
- bananas raw

## Safety rules

The command does not create missing Food records.

The command does not modify nutrition values.

The command does not modify user foods.

The command does not modify historical meals or daily plans.

The command is idempotent.

Running it multiple times should not duplicate aliases or localized names.