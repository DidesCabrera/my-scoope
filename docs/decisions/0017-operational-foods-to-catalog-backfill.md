# 0017 · Backfill interno desde `notas.Food` hacia Food Catalog

## Estado

Aceptada.

## Fecha

2026-06-30.

## Contexto

Las decisiones previas definieron una separación híbrida:

```text
food_catalog.CatalogFood = fuente maestra/canónica interna
notas.Food = única verdad nutricional operacional
MCP = solo consume notas.Food
```

Después de crear modelos maestros, importadores catalog-first, admin y el protocolo de snapshot `CatalogFood -> notas.Food`, falta una vía segura para poblar el catálogo maestro inicial desde alimentos operativos ya confiables.

My Scoope ya puede tener alimentos globales y verificados en `notas.Food`. Esos alimentos pueden servir como semilla de curaduría del catálogo maestro, siempre que el proceso no invierta la regla operacional ni convierta `CatalogFood` en fuente directa de Meals, Plans, Solver o MCP.

## Decisión

El Patch 39 agrega un backfill interno conservador desde `notas.Food` hacia `food_catalog.CatalogFood`.

El comando vive en `notas`, no en `food_catalog`, porque lee modelos operativos de `notas`:

```text
python manage.py backfill_catalog_from_operational_foods --dry-run
python manage.py backfill_catalog_from_operational_foods
```

El servicio asociado vive en:

```text
notas/application/services/commands/food_catalog_backfill.py
```

Esta ubicación mantiene la frontera:

```text
notas puede ejecutar un bridge interno explícito hacia food_catalog
food_catalog no importa notas
MCP no importa food_catalog
```

## Criterios de elegibilidad

El backfill solo considera alimentos operativos confiables:

```text
notas.Food.is_global = True
notas.Food.is_verified = True
notas.Food.is_active = True
```

Además, omite alimentos que ya tengan traza hacia Food Catalog:

```text
catalog_food_id
catalog_food_ref
```

Esto evita reingresar como candidatos alimentos que ya provienen de un snapshot del catálogo maestro.

## Qué crea

El backfill crea registros maestros no publicados:

```text
CatalogFood
CatalogFoodSource
CatalogFoodPortion
CatalogFoodAlias
CatalogImportBatch
```

El estado por defecto es:

```text
reviewed
```

No se usa `published` por defecto, porque el backfill es una semilla de curaduría. La publicación sigue siendo una decisión posterior explícita.

## Qué NO cambia

El backfill no modifica `notas.Food`.

En particular, no asigna automáticamente:

```text
catalog_food_id
catalog_food_ref
catalog_sync_status
```

La razón es semántica: en este flujo el catálogo maestro se deriva desde el alimento operativo, no al revés. Marcar el alimento como snapshot del catálogo sería engañoso.

Tampoco cambia:

```text
MealFood
Meal
DailyPlan
Program
Proposal
Solver
MCP
```

## Frontera MCP

El comando no afecta lo que MCP puede ver.

MCP sigue leyendo exclusivamente alimentos operativos desde `notas.Food`. Crear un `CatalogFood` por backfill no hace que ese registro maestro sea consultable por MCP ni lo transforma en `food_id` operacional.

## Consecuencias

- Food Catalog puede iniciar su base maestra desde alimentos ya confiables del sistema.
- `food_catalog` mantiene independencia y no importa `notas`.
- `notas.Food` mantiene su rol de verdad operacional.
- El backfill queda auditable mediante `CatalogImportBatch` y `CatalogFoodSource`.
- La publicación y el snapshot hacia `notas.Food` siguen siendo pasos separados.
