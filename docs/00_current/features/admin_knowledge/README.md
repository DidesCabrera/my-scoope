# Knowledge Center: My Scoope

Status: human_reference
Date: 2026-10-28
Audience: usuarios staff humanos de curación, operaciones, soporte y desarrollo
Role: human_reference
Authority: non_authoritative
Update-Policy: explicit_user_request_only

> Esta guía alimenta una interfaz para usuarios humanos. No es una fuente de verdad, no debe usarse
> para interpretar el código y queda fuera de los ciclos normales de desarrollo. Solo se actualiza
> cuando Felipe lo solicita explícitamente.

## Propósito

Este centro ofrece orientación humana sobre My Scoope. Resume la evolución del producto y explica
cómo se relacionan la experiencia móvil, el Calendario, el AI Assistant, Food Catalog, Nutrition
Solver, sharing, comparaciones, billing y la operación beta. Ante cualquier diferencia prevalecen
el código, los tests y la documentación normativa aplicable.

## Guías

| Área | Usar para |
| --- | --- |
| [Evolución del producto](project_evolution.md) | Comprender qué cambió entre julio y octubre de 2026 y obtener un mapa mental actualizado. |
| [Calendario, planificación y progreso](calendar_and_progress.md) | Distinguir plantillas, planes fechados, ejecución, compromisos y métricas. |
| [Recorrido móvil](mobile_journey.md) | Entender el viaje actual desde onboarding hasta planificación y seguimiento cotidiano. |
| [AI Assistant y paridad del sistema](ai_assistant.md) | Entender qué puede asistir, cómo resuelve entidades y qué acciones requieren propuesta, preview o UI confiable. |
| [Food Catalog para el Solver](food_catalog.md) | Curar capacidades, evaluar readiness, publicar snapshots y diagnosticar datos faltantes. |
| [Nutrition Solver](nutrition_solver.md) | Entender optimización V2, restricciones, backends, shadow mode, resultados y rollback. |
| [Compartir y comparar](sharing_and_comparisons.md) | Explicar snapshots compartidos, Inbox, copias propias y comparaciones guardadas. |
| [Pagos y salud de la beta](billing_and_beta.md) | Orientar soporte de suscripciones, compras, restauración, créditos e incidentes beta. |

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
