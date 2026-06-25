# Food Localized Name Services

## Purpose

This document describes the service layer for localized food display names.

The goal is to create and retrieve localized display names without modifying the original Food record.

## Main service

The main service is:

- ensure_food_localized_names

It lives in:

- notas/application/services/food_imports/localized_names.py

## Input contract

Localized names are represented by FoodLocalizedNameInput.

Fields:

- name
- language
- country
- is_primary

## Idempotency

The service is idempotent.

Calling it multiple times with the same localized name does not create duplicates.

Existing localized names may be updated if the primary flag changes.

## Display lookup

The helper get_primary_food_localized_name returns the primary localized name.

Fallback order:

1. exact language and country
2. language-only
3. empty string

## Example

Food original name:

Chicken breast, cooked

Localized name:

Pechuga de pollo cocida

Food.name is not changed.

The localized name is used as display metadata.