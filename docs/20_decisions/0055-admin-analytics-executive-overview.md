# 0055 · Admin Analytics executive overview

Status: accepted
Date: 2026-07-04

## Context

ADM01 creó el shell staff-only de `admin_analytics`, pero la pantalla todavía no
entregaba señales operativas reales. El siguiente paso del ciclo es convertir el
overview en una primera vista útil para operación interna sin crear todavía un
warehouse, snapshots analíticos ni procesos de escritura.

## Decision

Implementar ADM02 como un overview ejecutivo read-first construido desde datos
operacionales existentes.

La app `admin_analytics` agrega:

```text
admin_analytics/selectors/overview.py
admin_analytics/services/overview.py
```

El selector concentra consultas agregadas sobre:

```text
Django User / Profile
Meal / DailyPlan / Program
SavedComparison / Shares
NutritionProposal
AIUsageEvent
AccountSubscription / CreditWallet / CreditLedger
```

El service transforma esas métricas en viewmodels de lectura para la UI.

## Metrics included

ADM02 expone señales iniciales de:

```text
usuarios totales
usuarios nuevos 7/30 días
onboarding completado
Weekly Active Nutrition Builders
Meals/DailyPlans/Programs creados en 7 días
total histórico de Meals/DailyPlans/Programs
shares recientes
turnos IA, completados, errores y bloqueos
input/output/total tokens
costo IA estimado USD
créditos cargados/consumidos/reservados
suscripciones activas
wallets y balances
propuestas IA creadas/aplicadas
comparaciones guardadas
```

## Consequences

- `admin_analytics` sigue siendo read-only.
- No se agregan modelos ni migraciones.
- Las métricas son suficientes para que `/staff/analytics/` deje de ser un
  placeholder y pase a ser una primera pantalla operativa.
- Las métricas son deliberadamente simples; filtros temporales, segmentación,
  drill-downs y alertas avanzadas quedan para ADM08/ADM09.
- ADM03 y ADM04 podrán especializar las secciones de cuentas e IA sin rehacer el
  shell del overview.
