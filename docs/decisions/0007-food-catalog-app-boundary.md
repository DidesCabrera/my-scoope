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

## Documento operativo

Ver:

```text
docs/current/features/food_catalog/food_catalog_app.md
```
