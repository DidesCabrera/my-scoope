# 0011 · Contratos internos de Food Catalog antes de modelos maestros

## Estado

Aceptada.

## Fecha

2026-06-30.

## Contexto

Después de crear la app física `food_catalog`, el siguiente riesgo es avanzar
rápido hacia modelos o herramientas sin definir primero el contrato entre el
catálogo maestro y el alimento operacional.

Las decisiones vigentes establecen que:

```text
food_catalog = fuente maestra interna de curaduría
notas.Food = única verdad nutricional operacional
MCP = solo consume notas.Food
```

Por lo tanto, Food Catalog necesita contratos de entrada/salida propios, pero
esos contratos no deben convertirse en herramientas MCP ni en accesos directos
desde Meals, DailyPlans, Programs, Proposals, Comparators o Solver.

## Decisión

Food Catalog define contratos internos de aplicación antes de crear modelos
maestros.

El punto ejecutable inicial queda en:

```text
food_catalog/application/contracts.py
```

Estos contratos describen:

- candidatos estructurados para revisión;
- perfiles nutricionales normalizados por 100 g;
- evidencia y trazabilidad de fuente;
- opciones de porción normalizadas a gramos;
- snapshots publicados por Food Catalog;
- payloads preparados para que un protocolo interno futuro pueda crear o
  refrescar `notas.Food`.

Los contratos son deliberadamente puros:

```text
no importan django
no importan notas
no importan mcp_server
no crean registros en base de datos
no consultan modelos operativos
```

## Regla central

```text
Food Catalog puede producir contratos y snapshots internos.
Solo un protocolo backend explícito puede materializar esos snapshots en notas.Food.
MCP y los flujos operativos nunca consumen esos contratos directamente.
```

## Relación con `notas.Food`

El contrato puede usar nombres de campos compatibles con `notas.Food` para que
el futuro protocolo de snapshot sea simple, por ejemplo:

```text
name
protein
carbs
fat
canonical_name
food_group
food_subgroup
fiber_g_per_100g
sugar_g_per_100g
saturated_fat_g_per_100g
sodium_mg_per_100g
data_quality_score
visibility
```

Pero esa compatibilidad es un contrato de payload, no una dependencia ORM.

## No decidido todavía

Esta decisión no introduce aún:

- `CatalogFood`;
- `CatalogFoodPortion`;
- `CatalogFoodAlias`;
- migraciones de base de datos;
- campos nuevos en `notas.Food`;
- protocolo real de publicación hacia `notas.Food`;
- herramientas MCP para Food Catalog.

## Consecuencias positivas

- Se puede diseñar Food Catalog sin acoplarlo prematuramente a `notas`.
- Los futuros modelos maestros tendrán un contrato claro que cumplir.
- El futuro protocolo `CatalogFood → notas.Food` podrá implementarse de forma
  auditable y testeable.
- Se protege la regla de una sola verdad nutricional operacional.

## Riesgos y controles

Riesgo: que los contratos sean usados como si fueran alimentos operativos.

Control:

```text
Los contratos viven en food_catalog/application y no son expuestos al MCP.
Las herramientas operativas deben seguir validando y usando solo notas.Food.id.
```

Riesgo: que Food Catalog empiece a importar `notas` para facilitar el snapshot.

Control:

```text
Tests de contratos impiden imports de django, notas y mcp_server desde food_catalog/application.
```

## Relación con decisiones previas

Complementa a:

```text
docs/20_decisions/0007-food-catalog-app-boundary.md
docs/20_decisions/0009-food-catalog-hybrid-source-snapshot.md
docs/20_decisions/0010-mcp-operational-food-boundary.md
```

`0007` define Food Catalog como sistema separado.  
`0009` define `notas.Food` como snapshot operativo.  
`0010` define que MCP no accede a `food_catalog`.  
`0011` define el primer contrato interno ejecutable antes de crear modelos maestros.

## Nota posterior Patch 34

Patch 34 implementa los modelos maestros iniciales (`CatalogFood`, porciones, aliases, fuentes e import batches) usando estos contratos como referencia conceptual. La regla se mantiene: esos modelos no son operacionales, no escriben `notas.Food` y no se exponen a MCP.
