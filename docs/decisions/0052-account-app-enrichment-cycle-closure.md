# 0052 · Account app enrichment cycle closure

Status: accepted
Date: 2026-07-04

## Context

El ciclo ACC00-ACC07 se abrió para corregir una frontera estratégica del
producto: los planes comerciales, créditos y permisos de uso estaban repartidos
entre `notas.Plan`, `ai_assistant` y la app `accounts`.

Antes del ciclo, My Scoope ya venía separando responsabilidades mayores:

```text
food_catalog
  -> catálogo maestro, curaduría, importación y fuentes alimentarias.

nutrition_solver
  -> motor determinístico de optimización nutricional.

ai_assistant
  -> chat, LLM, tools, proposals revisables, auditoría y observabilidad IA.

accounts
  -> login/onboarding, pero todavía sin ser dueño completo del dominio comercial.
```

La separación de `accounts` era necesaria porque el modelo de negocio depende de
planes, suscripciones, créditos visibles, límites de uso y entitlements. Esas
responsabilidades no pertenecen naturalmente al dominio nutricional de `notas` ni
al dominio operacional de `ai_assistant`.

## Decision

El ciclo ACC queda cerrado con `accounts` como dominio preferente para:

```text
AccountPlan
AccountSubscription
CreditWallet
CreditLedger
commercial entitlements
plan comercial efectivo
créditos disponibles, reservados y consumidos
backfill gradual desde planes legacy
```

`notas.Plan` no se elimina todavía. Queda como compatibilidad transicional para
usuarios y flujos existentes, pero los consumidores nuevos deben resolver permisos
mediante servicios que prefieren `accounts`.

`ai_assistant` conserva la responsabilidad de ejecutar y auditar turnos IA:

```text
AIUsageEvent
provider/model
tokens
estimated_cost_usd
status/error/action_type
latency/tool metadata
```

`accounts` conserva la responsabilidad comercial:

```text
wallet
ledger
reservas
consumos
liberaciones
plan/entitlements
```

La conexión entre ambas capas queda representada por metadata correlacionable en
`AIUsageEvent`, sin exponer tokens ni costos USD como unidad comercial principal
para el usuario.

## Implemented cycle

| Patch | Resultado |
|---:|---|
| ACC00 | Documenta la estrategia Account Plans + Credits. |
| ACC01 | Crea `AccountPlan` y `AccountSubscription`. |
| ACC02 | Crea `CreditWallet` y `CreditLedger` append-only. |
| ACC03 | Agrega seed idempotente de planes comerciales. |
| ACC04 | Corrige planes a `free`, `basic`, `pro` e integra reservas de AI Assistant contra `accounts`. |
| ACC05 | Registra el outcome comercial real en `AIUsageEvent.metadata.account_credit_outcome`. |
| ACC06 | Expone plan/créditos en Profile y mejora inspección en Django Admin. |
| ACC07 | Migra capabilities hacia `accounts.services.entitlements` con fallback legacy a `notas.Plan`. |

## Current operating rules

### Ownership

```text
accounts
  = cuenta, planes comerciales, suscripciones, créditos, ledger y entitlements.

notas
  = experiencia nutricional, entidades operativas y compatibilidad legacy de planes.

ai_assistant
  = ejecución IA, auditoría, eventos de uso, costos/tokens internos y propuestas.
```

### User-facing unit

```text
Usuario ve créditos.
Sistema observa tokens y costos.
```

No se debe convertir tokens en la unidad comercial principal visible para el
usuario. Tokens y USD estimado son métricas internas para margen, routing y
observabilidad.

### Entitlements

Los consumidores nuevos no deben leer `notas.Profile.plan` directamente para
decidir permisos comerciales. Deben usar el servicio de capabilities/entitlements
vigente, que prefiere `accounts` y solo usa `notas.Plan` como fallback.

### Backfill

Los usuarios existentes se migran gradualmente con:

```bash
python manage.py sync_account_subscriptions --dry-run
python manage.py sync_account_subscriptions
python manage.py sync_account_subscriptions --update-existing
```

Los aliases legacy vigentes son:

```text
default -> free
member -> basic
nutritionist -> pro
```

## Strategic dashboard boundary

El dashboard estratégico no debe vivir dentro de `accounts` como app principal.

`accounts` debe entregar datos comerciales de alta calidad:

```text
planes
suscripciones
wallets
ledger
entitlements
estado comercial del usuario
```

Pero el dashboard estratégico debe ser una app transversal, por ejemplo:

```text
admin_analytics / product_intelligence
```

Motivo: el dashboard necesita cruzar señales de muchas apps:

```text
accounts       -> planes, suscripciones, créditos, ledger
ai_assistant   -> tokens, costos, status, quality/guardrails, proposals IA
notas          -> creación y uso de Meals, DailyPlans, Programs, Comparisons, Shares
food_catalog   -> curaduría, imports, calidad de catálogo
nutrition_solver -> previews, propuestas solver-ready, calidad de resultados
```

Si el dashboard viviera en `accounts`, `accounts` empezaría a conocer demasiados
dominios y se convertiría en una app coordinadora global. Eso rompería la frontera
recién ganada.

La regla recomendada es:

```text
accounts produce datos comerciales.
admin_analytics consume datos transversales.
```

## Consequences

- My Scoope tiene una base más escalable para monetización, créditos y límites.
- `accounts` queda enriquecida sin convertirse en dashboard global.
- `notas.Plan` queda explícitamente transicional.
- La IA puede seguir evolucionando sin ser dueña del modelo comercial.
- El futuro ciclo de Product Intelligence/Admin Analytics puede usar `accounts`
  como una de sus fuentes, no como su ubicación arquitectónica.

## Next recommended cycles

1. Ejecutar backfill de `AccountSubscription` en ambientes reales.
2. Crear tests de regresión para consumidores que no deben leer `notas.Profile.plan` directamente.
3. Planificar Billing/Payments solo después de validar planes y créditos internos.
4. Retomar Product Intelligence/Admin Analytics como app transversal.
