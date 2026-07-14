# 0014 — Food Catalog import adapters

Status: accepted  
Date: 2026-06-30

## Context

Food Catalog now exists as an independent Django app with internal contracts and
master models. The previous USDA/import pipeline lived under `notas` because the
initial implementation imported rows directly into the operational `Food` model.

After the hybrid source/snapshot decision, source adapters, normalization and
quality checks belong to Food Catalog. They are part of the acquisition and
curation system, not part of Meals, DailyPlans, Programs, Solver or MCP.

At the same time, `notas.Food` remains the only operational nutrition truth.
Existing commands still materialize operational foods and must keep working
while the import system is migrated gradually.

## Decision

Move pure import-adapter code to Food Catalog:

```text
food_catalog/application/imports/
```

This includes:

```text
contracts.py
normalization.py
quality.py
sources.py
usda/foundation_foods_reader.py
usda/mapper.py
```

Keep historical `notas` import paths as compatibility wrappers during the
transition:

```text
notas/application/dto/imported_food_dto.py
notas/application/services/food_imports/normalization.py
notas/application/services/food_imports/quality.py
notas/application/services/food_imports/usda/foundation_foods_reader.py
notas/application/services/food_imports/usda/mapper.py
```

These wrappers may import Food Catalog because they are explicit migration
bridges. They do not grant MCP access to Food Catalog and they do not make
`CatalogFood` operational.

Operational persistence still belongs to `notas` for now:

```text
notas/application/services/commands/import_food_from_source.py
notas/application/services/commands/import_food_batch.py
notas/application/services/commands/import_usda_food_payloads.py
```

Those commands write `notas.Food` and remain part of the operational update
protocol until a later patch introduces catalog-first import/backfill flows.

## Consequences

- Food Catalog owns source adapters and pure import contracts.
- `food_catalog/application/imports` must not import `notas`, Django models or MCP.
- `notas` keeps compatibility wrappers so existing commands/tests do not break.
- MCP still sees only `notas.Food`.
- Meals, DailyPlans, Programs, Proposals, Comparators and Solver still consume
  only `notas.Food`.
- Future patches can move curation/import commands from wrappers to catalog-first
  commands without changing the pure adapter contracts again.
