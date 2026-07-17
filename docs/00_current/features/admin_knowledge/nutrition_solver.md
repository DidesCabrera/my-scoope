# Nutrition Solver: operación y calidad de catálogo

Status: current
Date: 2026-07-16

## Qué decide cada app

| App | Responsabilidad |
| --- | --- |
| Food Catalog | Curar hechos, capacidades, procedencia, versión y confianza. |
| `notas` | Conservar el snapshot operativo estable y persistir propuestas revisables. |
| Nutrition Solver | Declarar requisitos, construir restricciones, optimizar y explicar calidad. |
| AI Assistant | Orquestar y presentar la propuesta; no inventar porciones finales. |

## Datos que elevan la calidad

Los nutrientes y límites de porción son requeridos. Roles funcionales y afinidades de comida tienen
alto impacto en coherencia. Forma, estado de preparación, porción natural, etiquetas dietarias,
alérgenos, esfuerzo y costo amplían restricciones y preferencias. Cada valor puede llevar confianza
y fuente. Un valor ausente debe permanecer ausente; una regla derivada se identifica como tal.

Un alimento sólo entra al optimizador activo si el snapshot operativo está activo, visible y tiene
`solver_enabled=True`. Publicar de nuevo desde Food Catalog actualiza el snapshot; no existe lectura
viva desde el solver al catálogo maestro.

## Activación y rollback

```text
NUTRITION_SOLVER_BACKEND=heuristic_v2   # default y rollback
NUTRITION_SOLVER_SHADOW_ENABLED=false
NUTRITION_SOLVER_SHADOW_BACKEND=cp_sat_v1
NUTRITION_SOLVER_TIME_LIMIT_MS=1500
```

Para observar CP-SAT sin alterar propuestas, mantener el backend heurístico y activar shadow. Para
activación controlada, usar `cp_sat_v1`. Si el problema es imposible, se detiene la generación con
un motivo estructurado: no se relajan restricciones duras ni se cambia silenciosamente de backend.

## Gate de calidad

No avanzar rollout si el shadow pasa de factible a imposible, pierde más de 15 puntos de calidad
nutricional, pierde más de 20 puntos de coherencia funcional o CI presenta una regresión dura. Las
propuestas continúan en `pending_review` hasta revisión explícita.
