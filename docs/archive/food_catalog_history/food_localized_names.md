# Food Localized Names

## Purpose

This document describes localized display names for global foods.

The goal is to keep the original food name for traceability while allowing the product to show a localized name to users.

## Example

Original food:

Chicken breast, cooked

Localized display name:

Pechuga de pollo cocida

Spanish aliases:

- Pollo
- Pechuga de pollo
- Pollo cocido

## Why not rename Food.name

Food.name may come from an external source such as USDA.

Renaming it directly would weaken traceability.

Instead, localized names provide a display layer on top of the original food.

## Model

FoodLocalizedName stores display names by language and country.

Important fields:

- food
- name
- normalized_name
- language
- country
- is_primary

## Relationship with FoodAlias

FoodAlias is mainly for search.

FoodLocalizedName is mainly for display.

A food may have many aliases but one primary localized name per language/country.

## Data safety

Localized names do not change nutrition values.

Localized names do not modify historical meals.

Localized names do not change source metadata.

Localized names are presentation-friendly metadata around Food.