# 0007 · Food Catalog App como sistema separado

## Estado

Aceptada.

## Contexto

La base de alimentos de MyScoope dejó de ser una preocupación secundaria de importación.

La experiencia con USDA mostró que una fuente persistente y técnicamente ordenada puede entregar una mala experiencia para usuarios hispanohablantes si los nombres, alimentos y porciones no son naturales para LATAM/España.

La evaluación de FatSecret mostró una cobertura global muy atractiva, pero con riesgos de persistencia, atribución y dependencia estratégica para construir una base canónica propia.

Además, la posibilidad de levantar datos directamente con marcas y curar alimentos naturales desde fuentes públicas convierte el catálogo en un activo estratégico, no solo en infraestructura.

## Decisión

Food Catalog será tratado como una aplicación/sistema independiente dentro de MyScoope.

Separación conceptual:

```text
Food Catalog App
    adquiere, investiga, normaliza, valida, versiona y publica alimentos confiables

Nutrition Management App
    consume alimentos publicados para crear Meals, DailyPlans, Programs, Comparators y Proposals
```

Las entidades de gestión nutricional no deben depender directamente de fuentes externas, APIs, agentes, planillas de marcas o importadores.

## Consecuencias

- Los importadores deben producir candidatos, no crear alimentos canónicos sin revisión.
- El catálogo debe manejar fuentes, licencias, evidencia, aliases, regiones, porciones, deduplicación y estados de confianza.
- FatSecret queda como fuente externa temporal/no canónica salvo acuerdo explícito de persistencia y atribución aceptable.
- USDA queda como fuente técnica secundaria, no como experiencia principal.
- Las marcas pueden alimentar un flujo Brand Verified bajo revisión de MyScoope.
- Los alimentos naturales deben priorizar fuentes públicas/oficiales y curaduría propia.
- Los agentes de IA pueden investigar y normalizar candidatos, pero no publicar alimentos automáticamente.


## Actualización posterior

La decisión `0009-food-catalog-hybrid-source-snapshot.md` precisa la integración inicial entre Food Catalog App y el sistema operativo actual:

```text
Food Catalog App = fuente maestra/canónica, versionada y trazable
notas.Food = snapshot operativo usado por Meals, DailyPlans, Programs y Proposals
```

Por lo tanto, Food Catalog App no reemplaza inicialmente a `notas.Food`. La extracción debe avanzar mediante contratos explícitos que permitan crear, sugerir o refrescar alimentos operativos desde alimentos maestros del catálogo, preservando la estabilidad de planes históricos.

## Actualización Patch 32

La app Django `food_catalog` existe físicamente dentro del monolito y queda registrada como frontera de sistema independiente.

Esta creación es estructural: no mueve `notas.Food`, no crea modelos maestros todavía y no cambia el flujo operativo de Meals, DailyPlans, Programs, Proposals, Comparators, Solver ni MCP.

Regla vigente:

```text
food_catalog = sistema maestro interno de curaduría/publicación
notas.Food = única verdad nutricional operacional
MCP = solo consume notas.Food
```

Food Catalog podrá alimentar a `notas.Food` mediante protocolos internos explícitos, auditables y revisables. No debe ser consultado directamente por MCP ni por entidades operativas de `notas`.

Ver también:

```text
docs/20_decisions/0010-mcp-operational-food-boundary.md
```

## Documento operativo

Ver:

```text
docs/00_current/features/food_catalog/food_catalog_app.md
```
