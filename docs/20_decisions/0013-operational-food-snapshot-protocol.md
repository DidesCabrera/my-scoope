# 0013 - Protocolo interno de snapshot operacional de alimentos

Status: accepted  
Date: 2026-06-30

## Context

Patch 34 introdujo modelos maestros persistentes en `food_catalog`:

```text
CatalogFood
CatalogFoodPortion
CatalogFoodAlias
CatalogFoodSource
CatalogImportBatch
```

Las decisiones vigentes siguen siendo:

```text
food_catalog.CatalogFood = fuente maestra/canónica, versionada y trazable
notas.Food = única verdad nutricional operacional
MCP = solo consume notas.Food
```

El siguiente paso es permitir que un alimento maestro publicado pueda quedar
disponible en el sistema operativo sin abrir acceso directo desde Meals, Solver,
MCP, Programs, Proposals o Comparators hacia `food_catalog`.

## Decision

Introducir un protocolo backend interno que materializa un `CatalogFood`
publicado como snapshot explícito en `notas.Food`.

El protocolo vive en:

```text
notas/application/services/food_catalog_snapshots.py
```

Esta ubicación es intencional: quien materializa la verdad operacional es
`notas.Food`, no `food_catalog`. La app `food_catalog` sigue sin importar
`notas` ni MCP.

El protocolo inicial permite:

```text
build_operational_food_snapshot_payload(catalog_food)
create_operational_food_snapshot_from_catalog(catalog_food)
refresh_operational_food_snapshot_from_catalog(food)
mark_operational_food_catalog_snapshot_stale(food)
```

Solo los `CatalogFood` con estado `published` pueden materializarse como
`notas.Food`.

## Trace fields on `notas.Food`

`notas.Food` agrega campos opcionales de trazabilidad:

```text
catalog_food_id
catalog_food_ref
catalog_snapshot_version
catalog_snapshot_payload
catalog_snapshot_created_at
catalog_sync_status
```

Estos campos no convierten a `CatalogFood` en modelo operacional. En particular:

```text
catalog_food_id != food_id operacional
catalog_food_ref != food_id operacional
```

Son referencias de auditoría para saber desde qué alimento maestro se creó o
refrescó el snapshot.

## Boundary rule

El único import permitido desde `notas.application` hacia `food_catalog` es el
servicio interno de snapshot:

```text
notas/application/services/food_catalog_snapshots.py
```

Ese servicio puede leer `food_catalog.models` y contratos internos para copiar
valores hacia `notas.Food`.

Ninguna herramienta MCP debe importar `food_catalog` ni resolver
`CatalogFood.id` como alimento operativo.

## Operational truth

Luego de materializar un snapshot, todo el sistema operativo sigue leyendo solo:

```text
notas.Food.protein
notas.Food.carbs
notas.Food.fat
notas.Food.fiber_g_per_100g
notas.Food.sugar_g_per_100g
notas.Food.saturated_fat_g_per_100g
notas.Food.sodium_mg_per_100g
notas.Food.default_portion_g
```

Por lo tanto, si `CatalogFood` cambia en el futuro, no cambia automáticamente el
resultado nutricional de Meals, DailyPlans, Programs o Proposals. Para actualizar
la verdad operacional se requiere un refresh explícito del snapshot.

## Consequences

- Food Catalog ya puede alimentar `notas.Food` mediante un canal controlado.
- `notas.Food` mantiene valores copiados y auditables.
- MCP sigue sin acceso directo a `food_catalog`.
- Meals, DailyPlans, Programs, Proposals, Comparators y Solver siguen usando
  exclusivamente `notas.Food`.
- El vínculo con catálogo no es `ForeignKey`; es trazabilidad opcional para
  reducir acoplamiento entre apps.
- Los snapshots pueden marcarse como `stale` sin cambiar macros ni planes ya
  creados.

## Follow-ups

1. agregar comandos/admin actions para publicar o refrescar snapshots desde el
   admin de Food Catalog;
2. migrar importadores y curaduría hacia `food_catalog`;
3. endurecer MCP para renombrar gradualmente `list_food_catalog` hacia una noción
   más explícita de alimentos operativos;
4. agregar auditoría de refresh si se necesita historial de cambios por snapshot.

## References

- `0007-food-catalog-app-boundary.md`
- `0009-food-catalog-hybrid-source-snapshot.md`
- `0010-mcp-operational-food-boundary.md`
- `0011-food-catalog-internal-contracts.md`
- `0012-food-catalog-master-models.md`
- `docs/00_current/features/food_catalog/food_catalog_app.md`
