# Food Catalog

Django app boundary for the master food catalog subsystem.

## Patch 40 status

This app exists physically, is protected by boundary tests and is registered in `INSTALLED_APPS`, defines internal
application contracts, owns initial master catalog models, owns pure
source/import adapters, and has initial catalog-first import commands:

```text
food_catalog/application/contracts.py
food_catalog/application/imports/
food_catalog/models.py
food_catalog/infrastructure/imports/
food_catalog/management/commands/dry_run_catalog_usda_foods_json.py
food_catalog/management/commands/import_catalog_usda_foods_json.py
notas/application/services/commands/food_catalog_backfill.py
notas/management/commands/backfill_catalog_from_operational_foods.py
```

Initial master models:

```text
CatalogFood
CatalogFoodPortion
CatalogFoodAlias
CatalogFoodSource
CatalogImportBatch
```

Pure import modules:

```text
food_catalog/application/imports/contracts.py
food_catalog/application/imports/normalization.py
food_catalog/application/imports/quality.py
food_catalog/application/imports/sources.py
food_catalog/application/imports/usda/foundation_foods_reader.py
food_catalog/application/imports/usda/mapper.py
```

The current operational nutrition source remains:

```text
notas.Food
```

Patch 35 added the first internal snapshot bridge in `notas`, not in this app:

```text
notas/application/services/food_catalog_snapshots.py
```

That bridge may materialize a published `CatalogFood` into `notas.Food` by
copying nutrients and trace metadata. The resulting `notas.Food.id` is the only
operational food identifier for Meals, DailyPlans, Programs, Proposals,
Comparators, Solver and MCP.

Patch 36 keeps historical `notas` import paths as compatibility wrappers while
moving source-adapter ownership to this app. Those wrappers are temporary
migration bridges and do not mean MCP or operational features can read
`food_catalog` directly.

## Boundary rule

Food Catalog contracts, import adapters and master models can describe
candidates, evidence, curation state and publication-ready master foods, but
they are not MCP tools and they do not write operational foods by themselves.

The internal backend snapshot protocol may materialize a published catalog
snapshot into `notas.Food`. Until that materialization happens, the food is not
available for Meals, DailyPlans, Programs, Proposals, Solver or MCP.


## Catalog-first commands

Patch 37 adds Food Catalog-owned commands:

```text
python manage.py dry_run_catalog_usda_foods_json <path> --source-version <version>
python manage.py import_catalog_usda_foods_json <path> --source-version <version>
```

They persist or simulate master catalog candidates only. They write
`CatalogFood`, `CatalogFoodSource` and `CatalogImportBatch`; they do not create
or update `notas.Food`. Operational availability still depends on the explicit
snapshot protocol in `notas/application/services/food_catalog_snapshots.py`.

## Patch 38 · MCP no consume Food Catalog

`food_catalog` sigue siendo una app interna de curaduría, importación y publicación. MCP no debe importar esta app ni leer `CatalogFood`. Las herramientas MCP solo pueden ver alimentos que ya existen como `notas.Food`; el nombre histórico `list_food_catalog` lista esos alimentos operativos, no el catálogo maestro.

## Patch 39 · Backfill operacional hacia candidatos maestros

Existe un comando interno para sembrar Food Catalog desde alimentos operativos confiables:

```text
python manage.py backfill_catalog_from_operational_foods --dry-run
python manage.py backfill_catalog_from_operational_foods
```

El comando vive en `notas` porque lee `notas.Food`. Crea candidatos maestros, fuentes, porciones y aliases en `food_catalog`, pero no modifica el alimento operativo de origen, no publica automáticamente el catálogo y no cambia lo que MCP puede ver.

## Patch 40 · cycle closure

Patch 40 closes the separation cycle with executable boundary guards and final
cycle documentation.

Current invariant:

```text
food_catalog.CatalogFood = master catalog food
notas.Food = only operational nutrition truth
MCP = operational tools over notas.Food only
```

Food Catalog modules must not define MCP tools. The pure application layer must
not import Django, `notas` or `mcp_server`. Infrastructure and Food Catalog
management commands may use Django and `food_catalog.models`, but they must not
read `notas.Food`; operational bridges that read `notas.Food` stay in `notas`.

The cycle Patch 32-40 is now considered closed. Next work should build product
capabilities on top of this boundary rather than reopening the ownership split.
