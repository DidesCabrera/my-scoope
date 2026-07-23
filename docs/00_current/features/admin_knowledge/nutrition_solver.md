# Nutrition Solver: optimización V2 y operación

Status: human_reference
Date: 2026-07-17
Audience: usuarios staff humanos de producto, operaciones, soporte y desarrollo
Role: human_reference
Authority: non_authoritative
Update-Policy: explicit_user_request_only

> Orientación exclusiva para personas. No define contratos del Nutrition Solver, no forma parte del
> contexto normativo de Codex y no se sincroniza automáticamente con ciclos o features.

## Qué optimiza actualmente

Optimization V2 ya no recibe una única combinación fijada para ajustar gramos. El problema incluye:

- perfiles de alimentos con capacidades, procedencia y confianza;
- slots de comida y gramáticas funcionales;
- rangos nutricionales por comida y por día;
- límites y pasos discretos de porción;
- exclusiones, preferencias y restricciones de repetición;
- tiempo máximo y semilla determinista.

Antes de optimizar porciones, el portfolio acotado conserva varias combinaciones completas. CP-SAT
puede decidir selección y cantidades en un único modelo, corregir el día globalmente y devolver
alternativas con composiciones distintas.

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

Ver [Food Catalog para Nutrition Solver](food_catalog.md) para el checklist completo de curación,
snapshot y diagnóstico.

## Gramáticas actuales

| Arquetipo | Uso | Cobertura mínima |
| --- | --- | --- |
| `main_plate` | main, dinner | proteína principal/de apoyo + carbohidrato/mixed food. |
| `breakfast_composition` | breakfast | proteína/mixed food + carbohidrato/fruta/mixed food. |
| `snack_pair` | snack | proteína/mixed food + carbohidrato/fruta/mixed food/grasa densa. |

Las categorías son grupos de capacidades, no slots exclusivos. Un mismo alimento puede ser elegible
en más de un grupo, pero no puede ocupar dos componentes requeridos él solo dentro de una comida.

## Restricciones y resultado imposible

Las restricciones duras incluyen rangos mínimos/máximos, bounds de porción, componente mínimo y
máximo, grupos funcionales requeridos y exclusiones explícitas. CP-SAT también puede aplicar límites
globales de repetición.

Si no existe solución, el resultado es `impossible` con un reason code. El runtime no debe:

- ampliar rangos silenciosamente;
- ignorar una exclusión;
- inventar un rol faltante;
- cambiar automáticamente de backend;
- persistir un plan parcial como si fuera válido.

Las preferencias y costos de simplicidad ordenan soluciones factibles, pero no reemplazan reglas
duras.

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

| Configuración | Resultado visible |
| --- | --- |
| heuristic + shadow off | Generador legacy visible; rollback estable. |
| heuristic + shadow CP-SAT | Payload legacy visible y comparación registrada. |
| CP-SAT activo | Payload DailyPlan generado por Optimization V2. |

En todos los casos, el resultado persiste como `NutritionProposal(status=pending_review)`; aplicar la
propuesta sigue siendo una acción humana separada.

## Calidad y telemetría

La calidad se informa en dos ejes:

- **nutricional:** proximidad a valores preferidos dentro de rangos permitidos;
- **funcional:** cobertura de grupos de roles y conteo válido de componentes.

Shadow mode también registra backend, estados, delta de ambos scores y solapamiento de selección.
No confundir baja coincidencia de alimentos con regresión: una alternativa puede ser distinta y
mejor. La decisión usa factibilidad y calidad, no identidad exacta de la composición.

## Gate de calidad

No avanzar rollout si el shadow pasa de factible a imposible, pierde más de 15 puntos de calidad
nutricional, pierde más de 20 puntos de coherencia funcional o CI presenta una regresión dura. Las
propuestas continúan en `pending_review` hasta revisión explícita.

## Diagnóstico rápido

| Síntoma | Revisar |
| --- | --- |
| `required_role_group_empty` | Cobertura de roles en perfiles elegibles y snapshots. |
| `candidate_portfolio_empty` | Exclusiones, forma incompatible, top-K y cobertura completa. |
| `cp_sat_infeasible` | Rangos, bounds, step, componentes y restricciones globales. |
| `required_food_unavailable` | ID operacional, visibilidad, estado activo y elegibilidad. |
| Calidad funcional baja | Roles derivados, confianza, afinidades y gramática aplicada. |
| Calidad nutricional baja pero factible | Preferred values, pesos y amplitud de rangos. |
| Shadow regresiona | Comparar reason codes y scores antes de activar el backend. |

## Referencias

- [Knowledge Center](README.md)
- [Food Catalog para Nutrition Solver](food_catalog.md)
- [Mapa de arquitectura](../../architecture/nutrition_solver_extraction_map.md)
- [ADR 0146: backend CP-SAT](../../../20_decisions/0146-cp-sat-optimization-backend.md)
- [ADR 0148: shadow y quality gates](../../../20_decisions/0148-shadow-quality-and-regression-gates.md)
