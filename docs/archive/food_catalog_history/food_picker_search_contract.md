# Food Picker Search Contract

## Purpose

This document describes the enriched food picker search contract.

The goal is to prepare the picker for global food badges and source-aware display without changing the visual UI yet.

## Query

The picker query lives in:

- notas/application/queries/food_picker_queries.py

The main functions are:

- get_food_picker_queryset(user)
- list_food_picker_items(user, search, limit)
- search_food_picker_items(user, search, limit)

## Payload compatibility

The enriched picker payload keeps the original fields:

- id
- name
- protein
- carbs
- fat
- total_kcal
- alloc

It adds metadata fields:

- picker_source
- picker_label
- is_user_food
- is_global_food
- is_verified
- visibility
- data_quality_score
- source

## Picker source values

Current picker source values are:

- user
- global
- system

## Picker labels

Current picker labels are:

- Tu alimento
- Global
- Sistema

These labels are data-level labels.

Visual badges will be added in a later block.

## Search

Picker search supports:

- name
- canonical_name
- alias name
- alias normalized_name

## Ordering

Picker ordering is:

1. user foods
2. core global/system foods
3. extended global/system foods
4. verified foods before non-verified foods
5. higher data quality score first
6. name
7. id

## Data safety

The query excludes:

- private foods from other users
- hidden global foods
- rejected global foods
- inactive global foods

## Current scope

This block only enriches the data contract.

It does not modify CSS.

It does not modify templates.

It does not modify JavaScript rendering.

The next block can use these fields to render badges visually.