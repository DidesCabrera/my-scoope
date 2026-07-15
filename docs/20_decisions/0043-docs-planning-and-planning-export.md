# 0043 · Docs planning area and planning export mode

Status: accepted
Date: 2026-07-02

## Context

My Scoope acumula ciclos grandes que no siempre deben implementarse inmediatamente. En particular, el ciclo de Product Intelligence & Admin Analytics es estratégico, pero probablemente debe coordinarse con Food Catalog y con mejoras de integración de IA interna.

Hasta ahora `docs/00_current/` contenía documentación vigente y `docs/20_decisions/` registraba decisiones aceptadas. Faltaba un lugar oficial para planes futuros que una IA pudiera leer sin confundirlos con contratos ya implementados.

También existía la necesidad de exportar un ZIP pequeño centrado en documentación y planificación para conversaciones donde el objetivo no sea modificar código productivo, sino afinar roadmap, prioridades y ciclos de patches.

## Decision

Se crea:

```text
docs/10_active_cycles/
```

Esta carpeta contiene planes de ciclos futuros con estado explícito. No reemplaza `docs/00_current/` ni `docs/20_decisions/`.

Se agrega un modo nuevo al script de exportación:

```bash
./scripts/export_for_chatgpt.sh planning
```

Este modo genera:

```text
../proyecto_django_export_planning.zip
```

El modo `planning` incluye documentación, decisiones, archivo de exportación y contexto mínimo de configuración/proyecto. No incluye tests, datasets pesados, imágenes, base local ni código productivo amplio.

## Consequences

- La planificación futura queda dentro de la documentación oficial del proyecto.
- Una IA puede revisar planes próximos sin depender de notas personales en `manual_docs/`.
- Los planes futuros no se mezclan con contratos vigentes de implementación.
- Las decisiones estables que nazcan desde un plan deben seguir registrándose en `docs/20_decisions/`.
- Para ciclos de planificación, el export recomendado pasa a ser `planning`.
- Para implementación, siguen vigentes `ai`, `full`, `usda` y `foodcatalog` según el tipo de trabajo.
