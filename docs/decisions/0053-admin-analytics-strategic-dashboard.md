# 0053 · Admin Analytics strategic dashboard

Status: accepted
Date: 2026-07-04

## Context

Después de separar y enriquecer las apps `food_catalog`, `nutrition_solver`,
`ai_assistant` y `accounts`, My Scoope tiene fronteras más claras para escalar:

```text
accounts       -> cuenta, planes comerciales, suscripciones, créditos y entitlements
ai_assistant   -> LLM, chat, tools, proposals, usage events y costos internos
food_catalog   -> catálogo maestro, curaduría y calidad de datos alimentarios
nutrition_solver -> motor determinístico de optimización nutricional
notas          -> experiencia nutricional operativa del usuario
```

El siguiente problema estratégico es de operación interna: el administrador de
producto necesita visualizar activación, uso, costos, créditos, calidad de datos,
calidad del solver y riesgo operacional sin revisar manualmente modelos, admin o
base de datos.

## Decision

Crear un ciclo de trabajo para una app transversal:

```text
admin_analytics
```

Esta app será responsable del dashboard estratégico interno de My Scoope.

No debe vivir dentro de `accounts`.

`accounts` es una fuente de datos comerciales, pero el dashboard necesita cruzar
señales de múltiples dominios:

```text
accounts       -> planes, suscripciones, wallets, ledger y entitlements
ai_assistant   -> AIUsageEvent, provider/model, tokens, costos, tools y outcomes
notas          -> Meals, DailyPlans, Programs, comparaciones, shares y propuestas
food_catalog   -> cobertura, curaduría, fuentes, completitud y duplicados
nutrition_solver -> calidad de solución, constraints, desviaciones y aceptación
```

La regla aceptada es:

```text
accounts produce datos comerciales.
admin_analytics consume datos transversales.
```

## Scope

El dashboard debe comenzar como una app staff-only y read-first:

```text
selectors
services agregadores
viewmodels
templates internos
permisos staff
```

No debe modificar dominio ni ejecutar procesos de negocio.

No reemplaza Django Admin. Django Admin sigue siendo para inspección técnica;
`admin_analytics` será para inteligencia de producto, negocio y operación.

## Initial modules

El ciclo debe cubrir progresivamente:

```text
overview ejecutivo
funnel de activación
actividad nutricional
AI Assistant / LLM operations
créditos, planes y economía
Food Catalog quality
Nutrition Solver quality
alertas internas / health signals
```

## North Star Metric

La métrica norte inicial será:

```text
Weekly Active Nutrition Builders
```

Cuenta usuarios que en los últimos 7 días realizaron al menos una acción
nutricional significativa, como crear/editar Meals, DailyPlans o Programs,
aplicar propuestas IA, guardar comparaciones o enviar shares nutricionales.

## Planned cycle

```text
ADM00 — Docs: Strategic Dashboard / Admin Analytics strategy
ADM01 — App base admin_analytics
ADM02 — Overview ejecutivo con métricas agregadas
ADM03 — Account metrics: planes, créditos, wallets y ledger
ADM04 — AI Assistant metrics: usage, tools, costos y outcomes
ADM05 — Product activity metrics: notas
ADM06 — Food Catalog quality metrics
ADM07 — Nutrition Solver quality metrics
ADM08 — Filtros temporales y segmentación
ADM09 — Alertas internas / health signals
ADM10 — UI polish + cierre de ciclo
```

## Consequences

- My Scoope gana una consola interna para operar producto, IA y economía.
- `accounts` mantiene una frontera limpia: produce datos comerciales, no coordina
  analítica transversal.
- `admin_analytics` puede cruzar señales de múltiples apps sin contaminar sus
  responsabilidades.
- El dashboard podrá evolucionar desde queries read-only hacia snapshots o eventos
  agregados solo si el volumen lo justifica.
- El ciclo ADM se convierte en el siguiente proyecto natural después del cierre de
  Account.
