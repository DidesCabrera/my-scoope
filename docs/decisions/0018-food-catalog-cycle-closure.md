# 0018 · Food Catalog cycle closure and boundary guards

Status: accepted  
Date: 2026-06-30

## Context

Ciclo Patch 32-40: se separó Food Catalog como una app Django independiente dentro del monolito, sin convertirla en la fuente operacional directa de Meals, DailyPlans, Programs, Proposals, Solver ni MCP.

Durante el ciclo se tomaron decisiones clave:

- Food Catalog es fuente maestra interna para adquisición, normalización, evidencia, curaduría, publicación y backfill.
- `notas.Food` sigue siendo la única verdad nutricional operacional.
- MCP no accede a food_catalog.
- `list_food_catalog` mantiene su nombre histórico, pero lista alimentos operativos desde `notas.Food`.
- Los IDs de `CatalogFood` no son `food_id` válidos para planificación.
- La conexión `CatalogFood -> notas.Food` ocurre solo mediante protocolos internos de snapshot o backfill explícitos.

## Decision

Patch 40 cierra el ciclo agregando guardas ejecutables y documentación final de frontera.

Las reglas finales del ciclo son:

```text
food_catalog.CatalogFood
    = alimento maestro, curado, trazable, publicable

notas.Food
    = snapshot operacional, única verdad nutricional usada por el producto

MCP
    = consumidor externo de herramientas operativas, solo ve notas.Food
```

La app `food_catalog` no debe importar `notas` ni `mcp_server`.

La capa `food_catalog.application` tampoco debe importar Django. Esa capa contiene contratos y adaptadores puros.

La capa `food_catalog.infrastructure` puede usar Django y modelos propios de `food_catalog`, pero no puede leer `notas.Food` ni registrar herramientas MCP.

Los comandos propios de `food_catalog` son catalog-first. Si un flujo necesita leer `notas.Food`, debe vivir en `notas`, como ocurre con el backfill operacional del Patch 39.

## Consequences

El ciclo deja una frontera suficientemente fuerte para continuar con nuevas etapas sin mezclar responsabilidades.

Permitido:

```text
food_catalog.application -> contratos/adaptadores puros
food_catalog.infrastructure -> persistencia de candidatos maestros
food_catalog.management.commands -> comandos catalog-first
notas.application.services.food_catalog_snapshots -> snapshot interno hacia notas.Food
notas.application.services.commands.food_catalog_backfill -> backfill desde notas.Food hacia candidatos maestros
MCP -> herramientas sobre notas.Food únicamente
```

No permitido:

```text
MCP -> food_catalog
Meals/DailyPlans/Programs -> CatalogFood
Solver -> CatalogFood
Proposals -> CatalogFood
food_catalog -> notas.Food
food_catalog -> mcp_server
food_catalog.application -> django
```

Patch 40 agrega tests para asegurar que estas reglas no se degraden accidentalmente.

## Practical status after Patch 40

El ciclo 32-40 queda cerrado con:

- app física `food_catalog`;
- contratos internos puros;
- modelos maestros iniciales;
- admin y comandos catalog-first;
- adaptadores de importación movidos a Food Catalog;
- protocolo interno de snapshot hacia `notas.Food`;
- frontera MCP endurecida;
- backfill desde alimentos operacionales confiables hacia candidatos maestros;
- export focalizado `foodcatalog` actualizado para incluir tests de frontera.

La siguiente etapa ya no debería centrarse en separar la app, sino en desarrollar capacidades de producto sobre esta frontera, por ejemplo:

- mejorar curaduría y revisión;
- versionado nutricional;
- flujo Brand Verified;
- Natural Verified Seed;
- interfaz administrativa más rica;
- promoción controlada desde `CatalogFood` publicado hacia `notas.Food`.
