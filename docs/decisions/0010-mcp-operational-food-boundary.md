# 0010 · MCP solo consume alimentos operativos de `notas.Food`

## Estado

Aceptada.

## Fecha

2026-06-30.

## Contexto

Las decisiones `0007-food-catalog-app-boundary.md` y `0009-food-catalog-hybrid-source-snapshot.md` separan Food Catalog como fuente maestra y `notas.Food` como snapshot operativo.

Al diseñar la integración futura con IA/MCP aparece un riesgo importante: que una herramienta MCP consulte `food_catalog.CatalogFood` directamente y use esos datos para crear Meals, DailyPlans, Programs o Proposals sin materializarlos primero como `notas.Food`.

Eso produciría dos verdades nutricionales operativas:

```text
food_catalog.CatalogFood
notas.Food
```

Esa duplicidad rompería la estabilidad histórica, haría menos auditable el origen de los cálculos y permitiría que la IA se salte los protocolos internos de actualización/curaduría.

## Decisión

El MCP no debe acceder directamente a `food_catalog`.

Para MCP, Solver, Meals, DailyPlans, Programs, Proposals y Comparators, el único universo alimentario disponible es `notas.Food`.

```text
food_catalog.CatalogFood
        ↓ protocolos internos de publicación / snapshot / actualización
notas.Food
        ↓ única fuente operacional visible
MCP / Solver / Meals / DailyPlans / Programs / Proposals / Comparators
```

Por lo tanto:

- MCP no importa `food_catalog`.
- MCP no consulta `CatalogFood`.
- MCP no acepta `catalog_food_id` como alimento operativo.
- MCP no devuelve `catalog_food_id` como identificador usable para crear meals o plans.
- MCP solo acepta y devuelve IDs de `notas.Food` cuando se trate de alimentos operativos.
- Si un alimento existe en Food Catalog pero no existe como `notas.Food`, para MCP ese alimento todavía no está disponible.

## Implicancia sobre `list_food_catalog`

El nombre histórico `list_food_catalog` puede conservarse por compatibilidad de MCP/API, pero su significado operativo queda restringido:

```text
list_food_catalog = lista alimentos operativos disponibles para planificación desde `notas.Food`.
```

No significa:

```text
leer food_catalog.CatalogFood
buscar en el catálogo maestro
exponer IDs del catálogo maestro al MCP
```

A futuro se puede evaluar un rename gradual hacia `list_operational_foods`, pero sin romper contratos existentes mientras MCP ya dependa del nombre actual.

## Protocolos internos permitidos

La conexión entre Food Catalog y `notas.Food` pertenece al backend interno, no al MCP.

Ejemplos de protocolos internos futuros:

```text
publish_catalog_food_to_operational_food
create_operational_food_snapshot
refresh_operational_food_snapshot
link_operational_food_to_catalog_food
mark_operational_food_stale
```

Estos protocolos pueden leer `food_catalog.CatalogFood`, pero su resultado usable por el sistema nutricional debe ser siempre un `notas.Food` con valores nutricionales persistidos como snapshot.

Desde Patch 33, los contratos de payload para candidatos y snapshots se definen en `food_catalog/application/contracts.py`. Desde Patch 34, los modelos maestros se definen en `food_catalog.models`. MCP no consume contratos ni modelos de Food Catalog: solo verá el `notas.Food` ya materializado por protocolos internos futuros.

## Consecuencias

- Se mantiene una sola verdad nutricional operacional.
- Las propuestas IA no pueden usar alimentos maestros sin snapshot operativo.
- Los planes históricos no cambian automáticamente por cambios del catálogo maestro.
- La curaduría del catálogo queda desacoplada de la planificación nutricional.
- Los tests de frontera deben impedir imports directos desde MCP hacia `food_catalog`.

## Relación con decisiones previas

Complementa a:

```text
docs/decisions/0007-food-catalog-app-boundary.md
docs/decisions/0009-food-catalog-hybrid-source-snapshot.md
```

`0007` define Food Catalog como sistema separado.  
`0009` define `notas.Food` como snapshot operativo.  
`0010` define que MCP solo puede usar `notas.Food`, nunca `food_catalog` directamente.
`0011` define contratos internos de Food Catalog sin exponerlos a MCP.

## Estado Patch 35

Patch 35 introduce el primer protocolo backend que puede materializar un alimento publicado del catálogo como `notas.Food`:

```text
notas/application/services/food_catalog_snapshots.py
```

Este protocolo no es una herramienta MCP y no entrega `CatalogFood.id` al MCP. Su salida operacional es siempre un `notas.Food.id`.

Por lo tanto, para MCP la regla no cambia:

```text
MCP -> notas.Food
MCP -X-> food_catalog.CatalogFood
```

## Estado Patch 38

Patch 38 endurece esta decisión en código y tests.

El nombre histórico `list_food_catalog` permanece por compatibilidad, pero su contrato queda restringido:

```text
list_food_catalog -> alimentos operativos de notas.Food
list_food_catalog -X-> food_catalog.CatalogFood
list_food_catalog -X-> catalog_food_id
```

La tool MCP solo reenvía `search` y `limit` hacia el API Adapter. Cualquier argumento de trazabilidad de catálogo maestro se descarta y no se convierte en identificador operativo.

