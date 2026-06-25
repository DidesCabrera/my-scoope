# Food Picker Global Food Integration

## Purpose

This document describes the first integration between the food picker and the global food catalog.

The goal of this block is to make picker payloads use a controlled query instead of reading all Food records directly.

## Query

The picker query lives in:

- notas/application/queries/food_picker_queries.py

The main function is:

- get_food_picker_queryset(user)

## Included foods

The picker query includes:

- foods created by the current user
- active global foods with visibility core
- active global foods with visibility extended
- active legacy system foods created without user when visibility is core or extended

## Excluded foods

The picker query excludes:

- private foods from other users
- inactive global foods
- hidden global foods
- rejected global foods

## Ordering

The picker query orders foods by:

1. user foods
2. core global foods
3. extended global foods
4. verified foods before non-verified foods
5. name
6. id

## Current scope

This block does not change the frontend visual design.

It does not add badges yet.

It does not show labels such as Global, Verified or User food.

It only changes the source of picker data.

## Updated surfaces

The query is used by:

- meal detail food picker payload
- daily plan meal detail food picker payload
- foods_json endpoint

## Data safety

The integration is additive.

It does not modify foods.

It does not modify meals.

It does not modify daily plans.

It only changes which foods are exposed to picker payloads.