# 0012 - Food Catalog master models

Status: accepted  
Date: 2026-06-30

## Context

Patch 32 created the physical Django app boundary for `food_catalog`. Patch 33
added pure internal contracts, but Food Catalog still had no persistent master
records.

The next step is to persist catalog curation data without changing the existing
operational food model.

The recent architectural decisions remain in force:

```text
food_catalog = master catalog / curation / evidence / publication
notas.Food = only operational nutrition truth
MCP = only consumes notas.Food
```

## Decision

Introduce initial master models inside the independent `food_catalog` app:

```text
CatalogFood
CatalogFoodPortion
CatalogFoodAlias
CatalogFoodSource
CatalogImportBatch
```

These models own Food Catalog curation state, evidence, import batches, aliases,
serving options and normalized nutrients per 100 g.

They do **not** replace `notas.Food`.

They do **not** create Meals, DailyPlans, Programs, Proposals or Comparators.

They do **not** expose anything to MCP.

They do **not** define the operational snapshot protocol yet.

## Model roles

### CatalogFood

Master catalog record. It stores the canonical/display identity, review status,
source category, quality score and normalized nutrition per 100 g.

Its primary key and `catalog_ref` are catalog identifiers only. They are not
valid `food_id` values for operational planning.

### CatalogFoodPortion

Curated serving option attached to a `CatalogFood`.

### CatalogFoodAlias

Search alias or localized name attached to a `CatalogFood`.

### CatalogFoodSource

Traceable evidence/source metadata for a `CatalogFood`, including source IDs,
license status, hashes and attribution.

### CatalogImportBatch

Batch-level record for future imports, dry runs and curation jobs.

## Boundary rule

`food_catalog.models` may import Django model primitives and auth settings, but
must not import:

```text
notas
mcp_server
```

Operational systems must not import these master models to perform nutrition
calculations. Patch 35 later introduces the internal backend protocol that may
materialize a published catalog snapshot into `notas.Food`; this does not change
the Patch 34 rule that `CatalogFood` is not an operational food.

## Consequences

- Food Catalog now has its own database tables and admin registrations.
- `notas.Food` remains unchanged and remains the only valid food source for
  Meals, DailyPlans, Programs, Proposals, Comparators, Solver and MCP.
- MCP still cannot access `food_catalog` directly.
- Future patches can build internal snapshot/update protocols on top of these
  master records.
- Tests now enforce that `food_catalog` does not import `notas` or MCP.

## Follow-ups

Suggested next steps:

1. migrate import/curation commands into `food_catalog`;
2. add admin actions/commands for snapshot creation and refresh;
3. harden MCP naming so food tools are explicitly operational-food tools;
4. add audit history if snapshot refreshes need a historical log.

## References

- `0007-food-catalog-app-boundary.md`
- `0009-food-catalog-hybrid-source-snapshot.md`
- `0010-mcp-operational-food-boundary.md`
- `0011-food-catalog-internal-contracts.md`
- `0013-operational-food-snapshot-protocol.md`
- `docs/current/features/food_catalog/food_catalog_app.md`
