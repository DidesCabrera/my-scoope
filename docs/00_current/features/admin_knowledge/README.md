# Knowledge Center: Food Catalog y Nutrition Solver

Status: current
Date: 2026-07-17
Audience: curadores, operaciones, soporte, desarrollo y asistentes de IA

## Propósito

Este centro explica cómo la calidad del Food Catalog condiciona la calidad del Nutrition Solver y
qué revisar cuando una propuesta no es viable o no resulta funcionalmente coherente. Es una guía
operativa; los ADR bajo `docs/20_decisions/` conservan el razonamiento arquitectónico completo.

## Guías

| Área | Usar para |
| --- | --- |
| [Food Catalog para el Solver](food_catalog.md) | Curar capacidades, evaluar readiness, publicar snapshots y diagnosticar datos faltantes. |
| [Nutrition Solver](nutrition_solver.md) | Entender optimización V2, restricciones, backends, shadow mode, resultados y rollback. |

## Contrato entre aplicaciones

```text
CatalogFood curado
  -> publicación y snapshot explícito
  -> notas.Food operativo y versionado
  -> SolverFoodProfile puro
  -> OptimizationProblemV2
  -> propuesta pending_review
```

| Aplicación | Es dueña de | No debe hacer |
| --- | --- | --- |
| Food Catalog | Hechos curados, evidencia, capacidades, confianza y versión. | Generar propuestas o convertirse en dependencia runtime del solver. |
| `notas` | Snapshot operativo, permisos y persistencia de propuestas. | Inventar silenciosamente hechos maestros ausentes. |
| Nutrition Solver | Requisitos, gramática, restricciones, optimización, alternativas y diagnóstico. | Leer `CatalogFood`, persistir planes o relajar restricciones duras. |
| AI Assistant | Orquestar y presentar resultados revisables. | Inventar alimentos, porciones o afirmar que una propuesta fue aplicada. |

## Regla de diagnóstico

Primero clasificar el problema:

1. **Dato maestro:** capacidad incorrecta o ausente en Food Catalog.
2. **Snapshot:** dato curado que todavía no llegó a `notas.Food`.
3. **Elegibilidad:** alimento inactivo, oculto o con `solver_enabled=False`.
4. **Modelo:** problema imposible por rangos, gramática, exclusiones o límites de porción.
5. **Presentación:** resultado correcto que la propuesta o explicación no comunica con claridad.

No corregir un problema de datos ampliando tolerancias del solver. No corregir una restricción real
inventando capacidades en el adaptador operacional.
