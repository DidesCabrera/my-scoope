# 0015 — Food Catalog admin and import commands

Status: accepted
Date: 2026-06-30

## Context

Patch 36 moved pure import adapters into Food Catalog:

```text
food_catalog/application/imports/
```

Those adapters normalize and validate external rows, but they intentionally do
not write database rows. Food Catalog now needs a first catalog-first operational
surface for curators and maintainers:

- admin actions for curation state changes;
- commands that import source payloads into `food_catalog` master candidate
  tables;
- dry-run commands that estimate import impact without writing rows.

The existing `notas` commands still write operational `notas.Food` and must keep
working during the transition.

## Decision

Introduce Food Catalog-owned import orchestration outside the pure application
contracts:

```text
food_catalog/infrastructure/imports/
```

This layer may import Django and `food_catalog.models`, but it must not import
`notas` or MCP. It persists source rows as catalog master candidates:

```text
ImportedFoodDTO
    ↓ normalize + validate
CatalogFood(status=external_candidate)
CatalogFoodSource
CatalogImportBatch
```

Add Food Catalog management commands:

```text
python manage.py dry_run_catalog_usda_foods_json <path> --source-version <version>
python manage.py import_catalog_usda_foods_json <path> --source-version <version>
```

These commands write only `food_catalog` models. They do not create or update
`notas.Food`. Operational availability still requires the explicit snapshot
protocol introduced in Patch 35.

Add first admin curation actions for `CatalogFood`:

```text
mark_as_pending_review
mark_as_published
mark_as_deprecated
```

Publishing a `CatalogFood` means the master record is eligible for the internal
snapshot protocol. It does not by itself make the food available to MCP, Meals,
DailyPlans or Programs.

## Consequences

- Food Catalog can now ingest external USDA JSON into master candidate tables.
- Dry-run imports can be reviewed before writing catalog data.
- Curators can promote catalog foods through basic admin state actions.
- Existing `notas` import commands remain available and unchanged.
- MCP still sees only `notas.Food`.
- `CatalogFood.id` is still not a valid operational `food_id`.
- The new persistence layer lives outside `food_catalog/application` so pure
  contracts and adapters remain framework-independent.

## Follow-ups

1. add richer curation workflows for aliases, portions and evidence review;
2. add snapshot refresh commands/actions from published catalog foods into
   selected `notas.Food` rows;
3. gradually deprecate legacy operational import commands once catalog-first
   flows and snapshot protocols cover the required cases;
4. harden MCP food naming so historical `list_food_catalog` clearly means
   operational foods from `notas.Food`.

## References

- `0009-food-catalog-hybrid-source-snapshot.md`
- `0010-mcp-operational-food-boundary.md`
- `0013-operational-food-snapshot-protocol.md`
- `0014-food-catalog-import-adapters.md`
- `docs/current/features/food_catalog/food_catalog_app.md`
