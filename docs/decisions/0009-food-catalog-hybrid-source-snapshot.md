# 0009 · Food Catalog híbrido: fuente maestra y snapshot operativo

## Estado

Aceptada.

## Contexto

La decisión `0007-food-catalog-app-boundary.md` definió que Food Catalog debe evolucionar como una aplicación/sistema independiente dentro de MyScoope.

Al mismo tiempo, el modelo actual `notas.Food` está estrechamente acoplado al flujo operativo de gestión nutricional:

```text
MealFood → Food
Meal → MealFood
DailyPlan → DailyPlanMeal → Meal
Programs, Comparators, Proposals y Sharing consumen esas entidades operativas
```

Mover `Food`, `FoodPortion` y entidades relacionadas directamente a una nueva app Django podría introducir demasiada fricción en migraciones, imports, admin, tests, pickers, cálculos nutricionales y planes históricos.

También existe una diferencia conceptual importante entre:

```text
Food Catalog
    fuente maestra, curada, versionada y trazable de datos alimentarios

notas.Food
    alimento operativo usado dentro de Meals, DailyPlans, Programs y Proposals
```

## Decisión

MyScoope adoptará una arquitectura híbrida:

```text
Food Catalog App
    mantiene alimentos maestros/candidatos publicados, versionados y trazables
    por ejemplo: CatalogFood, CatalogFoodPortion, CatalogFoodAlias, CatalogImportBatch

Nutrition Management / notas
    mantiene Food como snapshot operativo usable por Meals, DailyPlans, Programs y Proposals
```

Food Catalog no reemplaza inicialmente a `notas.Food`.

Food Catalog debe alimentar, sugerir, crear o refrescar alimentos operativos mediante protocolos internos explícitos. `notas.Food` conserva los valores nutricionales necesarios para que los planes históricos sean estables aunque el catálogo maestro evolucione.

La relación recomendada es opcional y trazable:

```text
food_catalog.CatalogFood
        ↓ publica / sugiere / crea snapshot
notas.Food
        ↓ uso operativo estable
MealFood / Meal / DailyPlan / Program / Proposal
```

## Regla central

```text
Food Catalog es fuente maestra interna.
notas.Food es la única verdad nutricional operacional.
Meals, DailyPlans, Programs, Proposals, Comparators, Solver y MCP no dependen directamente del catálogo maestro.
```

## Implicancias

- `notas.Food` puede seguir existiendo como entidad operativa aunque exista una app `food_catalog`.
- `Food` puede tener en el futuro una referencia opcional al alimento maestro publicado, por ejemplo `catalog_food_id`, sin convertir esa referencia en dependencia obligatoria para Meals.
- Los datos nutricionales usados por Meals/DailyPlans deben permanecer estables para preservar históricos y auditoría.
- Cambios posteriores en `CatalogFood` no deben modificar automáticamente cálculos históricos.
- La actualización desde catálogo hacia `notas.Food` debe ser explícita, auditable y revisable.
- MCP no debe leer `food_catalog` ni recibir `catalog_food_id`; solo puede operar con IDs de `notas.Food`.
- Alimentos creados por usuarios pueden permanecer solo en `notas.Food`; solo se convierten en candidatos globales si pasan por Food Catalog.
- Food Catalog puede manejar fuentes, licencias, evidencia, versionado, deduplicación, aliases y estados de confianza sin contaminar el core operativo.

## Protocolos internos futuros sugeridos

La conexión entre Food Catalog y `notas.Food` debe implementarse mediante casos de uso internos, no como acceso libre desde entidades operativas ni como herramientas MCP.

Ejemplos:

```python
publish_catalog_food_to_operational_food(catalog_food_id, user=None)
create_operational_food_snapshot(catalog_food_id, user=None)
refresh_operational_food_snapshot(food_id, catalog_food_id, user=None)
propose_catalog_match_for_operational_food(food_id)
mark_operational_food_stale(food_id, catalog_food_id)
```

Estos protocolos pueden leer `food_catalog.CatalogFood`, pero su salida operacional debe ser siempre `notas.Food`.

Desde Patch 33, los payloads iniciales para esos protocolos viven en `food_catalog/application/contracts.py`. Son contratos puros, sin imports de Django, `notas` ni MCP, y todavía no crean ni actualizan registros.

Desde Patch 34, los modelos maestros iniciales viven en `food_catalog.models`. Persisten alimentos canónicos, porciones, aliases, fuentes e import batches, pero siguen sin escribir ni reemplazar `notas.Food`.

Desde Patch 35, el protocolo interno de snapshot vive en `notas/application/services/food_catalog_snapshots.py`. Solo ese puente puede leer `food_catalog` para materializar un `CatalogFood` publicado como `notas.Food`; el resto del sistema operativo sigue consumiendo únicamente el snapshot.

## Naming recomendado

Para evitar confusión entre dos alimentos con responsabilidades distintas:

```text
food_catalog.CatalogFood
notas.Food
```

Evitar introducir otro modelo llamado simplemente `Food` en una app separada si eso hace ambiguos los imports y el lenguaje del dominio.

## Consecuencias positivas

- Reduce el riesgo de migraciones grandes sobre el flujo actual.
- Mantiene estable la creación de Meals y DailyPlans.
- Permite que Food Catalog crezca como sistema propio.
- Prepara una extracción futura sin forzar microservicios ahora.
- Conserva trazabilidad entre dato maestro y snapshot operativo.
- Permite versionar y revisar datos maestros sin alterar planes ya creados.

## Riesgos y controles

Riesgo: duplicidad entre `CatalogFood` y `notas.Food`.

Control:

```text
CatalogFood = fuente maestra/versionada
notas.Food = snapshot operativo usado por planes
```

Riesgo: `notas.Food` se desactualiza respecto al catálogo.

Control:

```text
refresh explícito, con auditoría y sin mutar históricos automáticamente
```

Riesgo: el resto del sistema empieza a depender directamente de `food_catalog`.

Control:

```text
protocolos internos + tests de frontera que impidan consumo directo desde `notas` operativo y desde MCP
```

## Relación con decisiones previas

Esta decisión complementa, no reemplaza, a:

```text
docs/decisions/0007-food-catalog-app-boundary.md
```

`0007` define que Food Catalog es un sistema separado.  
`0009` define cómo se integra con el `Food` operativo actual sin romper Meals/DailyPlans.
`0010` define que MCP solo consume `notas.Food` y no accede directamente a `food_catalog`.
`0011` define contratos internos puros para candidatos, publicaciones y snapshots antes de crear modelos maestros.

`0012` introduce los modelos maestros iniciales de `food_catalog` sin cambiar la regla de `notas.Food` como verdad operacional.
`0013` introduce el protocolo interno de snapshot que copia datos publicados hacia `notas.Food` sin abrir acceso directo desde MCP ni desde las entidades operativas.
