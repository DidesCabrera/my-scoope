# Global Food Query Layer

## Purpose

This document describes the first query layer for global foods in My Scoope.

The goal is to expose a safe read contract for global foods before integrating them into the picker or UI.

## Architecture

The query layer lives in:

- notas/application/queries/global_food_queries.py

This layer is read-only.

It does not create, update or delete foods.

## Main rules

The query layer only exposes global foods that are safe for product surfaces.

A visible global food must be:

- is_global true
- is_active true
- visibility core or extended

Hidden and rejected foods are excluded.

User foods are excluded from this query layer.

## Visibility

Core foods are intended to be the first curated catalog.

Extended foods are valid imported foods that may be searchable but should have lower priority.

Hidden foods remain stored for traceability or future curation.

Rejected foods are not exposed.

## Search

Global food search supports:

- name
- canonical_name
- aliases name
- aliases normalized_name

This allows future Spanish aliases to find imported USDA foods.

Example:

A USDA food named Oats, raw may have the Spanish alias Avena.

Searching for Avena should return Oats, raw.

## Ordering

Results are ordered by:

1. core before extended
2. verified before non-verified
3. name
4. id

## Current limitation

This layer does not integrate with the picker yet.

It only prepares a stable read contract for the next block.

## Next block

The next block should integrate global foods into the picker query flow.

The picker should eventually combine:

- user foods
- core global foods
- extended global foods

with this priority:

1. user foods
2. core global foods
3. extended global foods