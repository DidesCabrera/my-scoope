# Admin Analytics / Strategic Dashboard Cycle

Status: completed
Date: 2026-07-04

## Contexto

My Scoope cerró ciclos importantes de separación de responsabilidades:

```text
accounts
  -> cuenta, planes comerciales, suscripciones, créditos, wallet, ledger y entitlements.

ai_assistant
  -> chat, LLM externo, tools, proposals revisables, usage events, costos/tokens internos y guardrails.

food_catalog
  -> catálogo maestro, curaduría, importadores y calidad de datos alimentarios.

nutrition_solver
  -> motor determinístico de optimización nutricional, contratos puros y adapters operacionales.

notas
  -> experiencia nutricional principal: Foods operativos, Meals, DailyPlans, Programs, Comparisons y Shares.
```

Este avance da claridad arquitectónica: las piezas críticas del sistema ya tienen
un lugar natural. El próximo problema de producto no es mover responsabilidades,
sino **observar el producto internamente para operarlo mejor**.

Como administrador de producto, se necesita un dashboard estratégico que permita
entender crecimiento, activación, uso real, costos de IA, consumo de créditos,
calidad de datos, salud del solver y señales de riesgo operacional.

## Decisión de ubicación

Crear una app transversal:

```text
admin_analytics
```

El dashboard estratégico no debe vivir en `accounts`, aunque `accounts` sea una
de sus fuentes más importantes.

Regla:

```text
accounts produce datos comerciales.
admin_analytics consume datos transversales.
```

Motivo: el dashboard cruza datos de muchas apps. Si viviera dentro de `accounts`,
`accounts` empezaría a conocer demasiado sobre `ai_assistant`, `notas`,
`food_catalog` y `nutrition_solver`, debilitando la separación recién lograda.

## Objetivo del ciclo

Construir un dashboard interno staff-only que permita responder:

```text
¿Está creciendo el producto?
¿Los usuarios se activan?
¿Dónde se atascan?
¿Qué partes del producto generan más valor?
¿Cuánto cuesta operar la IA?
¿Qué usuarios consumen más créditos?
¿Qué tools usa más el LLM?
¿Qué tan bien funciona el solver?
¿Qué tan buena es la calidad del food catalog?
¿Qué planes comerciales tienen sentido?
¿Qué riesgo operativo o económico existe?
```

El dashboard no debe ser solo una colección de gráficos. Debe funcionar como un
**centro de control interno del producto**.

## Principios arquitectónicos

### Read-first

La primera versión debe ser principalmente read-only:

```text
consultas agregadas
selectors
services de reporte
viewmodels
templates staff-only
```

No crear tablas analíticas pesadas al inicio salvo que una métrica lo necesite.
Primero se debe aprovechar la data existente.

### Staff-only

La app debe estar protegida para usuarios internos:

```text
is_staff / staff_required
```

No forma parte de la experiencia normal del usuario.

### No reemplaza Django Admin

Django Admin sigue siendo para inspección técnica de registros.

`admin_analytics` debe ser para inteligencia de producto, negocio y operación.

### No mezclar ejecución con observación

`admin_analytics` no debe ejecutar procesos de negocio como consumir créditos,
crear propuestas, modificar planes o curar alimentos. Debe leer, resumir y
señalar.

## Fuentes de datos

```text
accounts
  AccountPlan
  AccountSubscription
  CreditWallet
  CreditLedger
  entitlements

ai_assistant
  AIUsageEvent
  AICreditLedger / AIUserCreditQuota transicionales
  proposals
  tools
  guardrails
  provider/model/tokens/costos

notas
  Food operativo
  Meal
  DailyPlan
  Program
  Comparisons
  Shares
  Profile/onboarding

food_catalog
  CatalogFood
  fuentes
  estados de curaduría
  calidad/completitud
  importadores

nutrition_solver
  previews/runs cuando existan
  constraints
  calidad de solución
  propuestas solver-ready
```

## Módulos del dashboard

### 1. Overview ejecutivo

Primera pantalla. Debe responder en 30 segundos si el producto está sano.

Indicadores iniciales:

```text
usuarios totales
usuarios nuevos últimos 7/30 días
usuarios activos últimos 7/30 días
usuarios con onboarding completo
Meals creadas
DailyPlans creados
Programs creados
propuestas IA creadas
propuestas IA aprobadas/aplicadas
turnos IA completados
turnos IA bloqueados/error
créditos consumidos
costo IA estimado
```

Señales tipo semáforo:

```text
salud de activación
salud de costo IA
salud de créditos
salud del assistant
salud del food catalog
salud del solver
```

### 2. Funnel de activación

Funnel sugerido:

```text
usuario registrado
→ Profile creado
→ onboarding completo
→ primera Meal
→ primer DailyPlan
→ primer uso de AI Assistant
→ primera propuesta creada
→ primera propuesta aprobada/aplicada
→ primer Program
```

Preguntas que responde:

```text
¿Dónde se pierde el usuario?
¿Cuánto tarda en llegar a valor?
¿Qué acción predice mejor la activación?
¿La IA ayuda a activar o solo genera conversación?
```

### 3. Actividad nutricional

Consume principalmente `notas`.

Indicadores:

```text
Foods operativos creados
Meals creadas/editadas
DailyPlans creados/editados
Programs creados/editados
Meals por DailyPlan
Foods por Meal
Programs con semanas reales
comparaciones guardadas
shares enviados
copias/forks/duplicados
```

### 4. AI Assistant / LLM Operations

Consume `ai_assistant`.

Indicadores:

```text
turnos IA totales
turnos completed/error/blocked
usage por action_type
usage por provider/model
tokens input/output/cached
costo estimado USD
costo promedio por turno
costo por propuesta aplicada
tools llamadas
tools exitosas/fallidas
bloqueos por guardrails
bloqueos por créditos
propuestas creadas/aprobadas/aplicadas
```

Ranking inicial de tools:

```text
list_food_catalog
read_dailyplan
compare_dailyplan_to_targets
create_validated_meal
create_validated_dailyplan
read_proposal
```

### 5. Créditos, planes y economía

Consume `accounts`.

Indicadores:

```text
usuarios por plan: free/basic/pro
suscripciones activas
wallets activos
créditos otorgados
créditos reservados
créditos consumidos
créditos liberados
créditos expirados
usuarios sin créditos
usuarios cerca del límite
consumo promedio por plan
costo IA estimado por plan
margen estimado por plan cuando exista revenue
```

### 6. Food Catalog Quality

Consume `food_catalog`.

Indicadores:

```text
foods catalogados
foods naturales
foods de marca
foods con datos completos
foods incompletos
foods con fuente
foods sin fuente
foods pendientes de revisión
foods aprobados/rechazados
duplicados posibles
cobertura por categoría
foods usados en Meals reales
```

### 7. Nutrition Solver Quality

Consume `nutrition_solver` y propuestas generadas.

Indicadores:

```text
solver runs/previews
solver success/fail
constraints más comunes
targets cumplidos/incumplidos
desviación promedio kcal
desviación promedio proteína/carbs/grasas
tiempo promedio/p95 cuando exista
propuestas solver-ready aceptadas/descartadas
```

### 8. Alertas internas

El dashboard debe evolucionar hacia señales accionables:

```text
costo IA diario sobre umbral
aumento de errores del assistant
reservas de créditos colgadas
ledger inconsistente
usuarios pro con consumo anómalo
solver con alta tasa de fallos
food catalog con muchos alimentos incompletos
caída de activación semanal
```

En primera versión pueden ser alertas visuales. Más adelante pueden activar email,
Slack u otro canal interno.

## Estructura técnica sugerida

```text
admin_analytics/
  __init__.py
  apps.py
  urls.py
  views.py
  selectors/
    accounts.py
    ai_assistant.py
    product_activity.py
    food_catalog.py
    nutrition_solver.py
  services/
    overview.py
    health.py
    filters.py
  viewmodels.py
  templates/admin_analytics/
    base.html
    overview.html
    accounts.html
    ai_assistant.html
    product_activity.html
    food_catalog.html
    nutrition_solver.html
  tests/
```

URLs sugeridas:

```text
/staff/analytics/
/staff/analytics/accounts/
/staff/analytics/ai-assistant/
/staff/analytics/product-activity/
/staff/analytics/food-catalog/
/staff/analytics/nutrition-solver/
/staff/analytics/health/
```

## Métrica norte inicial

```text
Weekly Active Nutrition Builders
```

Usuario contado si en los últimos 7 días realizó al menos una acción nutricional
significativa:

```text
crear/editar Meal
crear/editar DailyPlan
crear/editar Program
aplicar una propuesta IA
guardar una comparación
enviar un share nutricional
```

Esta métrica es mejor que solo usuarios activos, porque intenta medir usuarios
que realmente están construyendo valor nutricional.

## Roadmap de patches propuesto

### ADM00 — Docs: Strategic Dashboard / Admin Analytics strategy

Registrar la decisión de crear `admin_analytics` como app transversal, definir
fuentes de datos, objetivos, módulos, métricas y límites de responsabilidad.

### ADM01 — App base `admin_analytics`

Status: implemented in `0054-admin-analytics-app-shell.md`.

Crear app Django, rutas staff-only, layout base, navegación interna y overview
vacío con estructura preparada.

### ADM02 — Overview ejecutivo con métricas agregadas

Status: implemented in `0055-admin-analytics-executive-overview.md`.

Primera pantalla útil con KPIs básicos de usuarios, actividad, IA, créditos y
salud operacional.

### ADM03 — Account metrics: planes, créditos, wallets y ledger — implemented

Lectura estratégica de `accounts`: usuarios por plan, consumo de créditos,
reservas, wallets, ledger y usuarios cerca de límite.

### ADM04 — AI Assistant metrics: usage, tools, costos y outcomes — implemented

Status: implemented in `0057-admin-analytics-ai-assistant-metrics.md`.

Lectura estratégica de `AIUsageEvent`, tools, provider/model, tokens, costos,
status, guardrails, créditos estimados vs reales y propuestas IA.

### ADM05 — Product activity metrics: `notas` — implemented

Status: implemented in `0058-admin-analytics-product-activity-metrics.md`.

Métricas de Meals, DailyPlans, Programs, Comparisons, Shares, Proposals y acciones
nutricionales de valor. Agrega `/staff/analytics/product-activity/` como pantalla
staff-only read-first para observar activación nutricional real.

### ADM06 — Food Catalog quality metrics — implemented

Status: implemented in `0059-admin-analytics-food-catalog-quality-metrics.md`.

Calidad/completitud del catálogo, fuentes, estados de curaduría, imports, proveedores externos y cola de candidatos. Agrega `/staff/analytics/food-catalog/` como pantalla staff-only read-first para observar la confiabilidad del catálogo maestro.

### ADM07 — Nutrition Solver quality metrics — implemented

Status: implemented in `0060-admin-analytics-nutrition-solver-quality-metrics.md`.

Métricas de solver/previews, éxito/fallo, desviaciones, constraints y aceptación
de propuestas.

### ADM08 — Filtros temporales y segmentación — implemented

Status: implemented in `0061-admin-analytics-temporal-filters-and-segmentation.md`.

Filtros globales por período y segmento de usuario para todas las pantallas del dashboard.

### ADM09 — Alertas internas / health signals — implemented

Status: implemented in `0062-admin-analytics-internal-alerts-health-signals.md`.

Señales visuales de riesgo: costos altos, errores, reservas colgadas, baja
activación, calidad baja de catálogo o solver fallando.

### ADM10 — UI polish + cierre de ciclo — implemented

Status: implemented in `0063-admin-analytics-cycle-closure.md`.

Pulido de navegación activa, estilos específicos del dashboard, estados vacíos, mapa de módulos en overview y registro formal del cierre del ciclo.

## MVP recomendado

Primera etapa mínima:

```text
ADM00 — Docs
ADM01 — App base
ADM02 — Overview ejecutivo
ADM03 — Account metrics
ADM04 — AI Assistant metrics
```

Esto ya permite operar:

```text
activación
uso real
costos IA
créditos
planes
errores
riesgo económico/operacional
```

Luego extender hacia:

```text
ADM05 — Product activity
ADM06 — Food Catalog Quality
ADM07 — Solver Quality
ADM08-ADM10 — filtros, alertas y cierre
```

## Criterios de éxito

El ciclo se considera útil cuando permite responder sin revisar manualmente la base:

```text
cuántos usuarios se activan semanalmente
qué acciones llevan al usuario al valor real
cuánto cuesta la IA por usuario y por función
qué porcentaje de propuestas IA se aplica
qué usuarios o planes consumen más que su margen esperado
dónde se rompe el funnel de onboarding
qué cohortes vuelven y cuáles abandonan
qué tan confiables son Food Catalog y Nutrition Solver
```

## Riesgos y guardrails

```text
No convertir admin_analytics en app que modifica dominio.
No duplicar lógica de negocio de accounts/ai_assistant/notas.
No crear métricas pesadas antes de validar valor.
No mezclar dashboard staff con experiencia usuario.
No depender de datos inexistentes: cada módulo debe degradar con estados vacíos claros.
```

## Estado esperado al cerrar el ciclo

Al cierre, My Scoope debe tener una consola interna que permita operar el producto
con visión estratégica, sin romper la separación de apps alcanzada por los ciclos
Food Catalog, Nutrition Solver, AI Assistant y Account.


### ADM03 implementation note

ADM03 adds a dedicated staff-only Accounts Analytics page at `/staff/analytics/accounts/`.
It reads `AccountPlan`, `AccountSubscription`, `CreditWallet` and `CreditLedger` through
`admin_analytics` selectors/services, preserving the rule that `accounts` produces
commercial data and `admin_analytics` consumes it for product intelligence.


### ADM04 implementation note

ADM04 adds a dedicated staff-only AI Assistant Analytics page at `/staff/analytics/ai-assistant/`.
It reads `AIUsageEvent`, `AIUserCreditQuota`, `AICreditLedger`, `AiNutritionChat` and
AI-sourced `NutritionProposal` records through `admin_analytics` selectors/services.
No models or migrations are added. Per-tool-name ranking remains a future improvement
until tool names are persisted explicitly in usage observability.


### ADM06 implementation note

ADM06 adds a dedicated staff-only Food Catalog Analytics page at `/staff/analytics/food-catalog/`. It reads master catalog, evidence, import, external provider and curation candidate records through `admin_analytics` selectors/services. No models or migrations are added. Duplicate detection and deeper solver-readiness scoring remain future improvements.


### ADM07 implementation note

ADM07 adds a dedicated staff-only Nutrition Solver Analytics page at `/staff/analytics/nutrition-solver/`. It reads proposal validation summaries, operational `notas.Food` solver readiness, Food Catalog solver readiness and pure solver configuration constants through `admin_analytics` selectors/services. No models or migrations are added. Explicit solver run logs remain a future improvement if JSON-derived observability becomes insufficient.

### ADM08 implementation note

ADM08 adds shared request-driven filters to Admin Analytics: period (`7d`, `30d`, `90d`) and user segment (`all`, `staff`, `members`). The filters are parsed in views, passed through services/selectors and rendered consistently across Admin Analytics pages. No models or migrations are added. Segmentation applies where records expose a direct user relation; otherwise pages keep safe global totals.

## Cierre de ciclo ADM00-ADM10

El ciclo queda cerrado con una primera versión operacional de `admin_analytics`:

```text
/staff/analytics/
/staff/analytics/accounts/
/staff/analytics/ai-assistant/
/staff/analytics/product-activity/
/staff/analytics/food-catalog/
/staff/analytics/nutrition-solver/
/staff/analytics/alerts/
```

El dashboard permanece staff-only, read-first y sin modelos propios. Esto confirma
la decisión original: `admin_analytics` no ejecuta negocio, observa el producto y
cruza señales de apps existentes.

Queda habilitada una base suficiente para operar My Scoope internamente sin abrir
la base de datos manualmente para responder preguntas estratégicas de activación,
costos IA, créditos, calidad de datos y salud del solver.

### Próximas mejoras sugeridas

```text
- Persistencia analítica o snapshots si las queries agregadas se vuelven costosas.
- Filtros adicionales por plan comercial, action_type o provider/model.
- Export CSV para análisis puntual.
- Umbrales configurables de alertas.
- Alertas por email/Slack si una señal crítica se mantiene.
- Gráficos temporales cuando exista suficiente volumen de datos.
```

## ADM10.1 independent shell note

ADM10.1 separates Admin Analytics from the normal My Scoope user shell. The console now
extends `admin_analytics/base.html` instead of `notas/base.html`, with its own sidebar,
topbar and CSS surface. This corrects the product boundary: Admin Analytics is the
strategic internal console, while the previous Django/admin operational surfaces remain
legacy/manual tooling.

No models or migrations are added.

## ADM10.2 compact filter bar note

ADM10.2 moves the shared Admin Analytics filters from repeated content cards into a compact
sub-header below the independent console topbar. The controls remain request-driven and keep
the same query parameters (`period` and `user_segment`), but now behave as global console
chrome instead of occupying primary dashboard space on every page.

No models or migrations are added.


## ADM10.3 admin analytics export scope note

ADM10.3 adds a focused ChatGPT export mode for Admin Analytics:

```bash
./scripts/export_for_chatgpt.sh adminanalytics
```

This generates `../proyecto_django_export_adminanalytics.zip` and is intended for future
visual, shell, CSS, navigation, filter and dashboard-structure iterations without sharing
the broader `full` ZIP. It includes the complete `admin_analytics` app, the console CSS,
relevant Admin Analytics docs and minimal model context for dashboard selectors.

Use `full` instead when a change touches cross-app business behavior, models, migrations
or broader regression needs.

No models or migrations are added.

### ADM10.4 — Page title topbar refinement

Implemented after the main cycle closure as a UX refinement for the independent
Admin Analytics shell.

The repeated first `card-detail-block` title sections were removed from each
Admin Analytics page. Page title, subtitle, period and generated timestamp now
live in the shell topbar, so the content area starts directly with meaningful
analytics cards, health signals or tables.

### ADM10.5 — Neutral dark theme refinement

Implemented after ADM10.4 as the final V1 visual refinement for the independent Admin
Analytics shell.

The console palette now uses dark grays and black surfaces as its base, with neutral gray
accents replacing the previous blue-oriented chrome. Operational status colors remain only
where they communicate health severity.

No models or migrations are added.

### ADM10.6 — Mobile shell and filter drawer

Implemented after ADM10.5 as the final mobile UX refinement for Admin Analytics V1.

The sidebar now collapses into an off-canvas drawer from the left on mobile. The topbar
exposes a menu icon and a filter icon; filters are collapsed by default and expand only
when requested. Mobile hides the page subtitle and topbar metadata to preserve space for
actual dashboard content.

No models or migrations are added.
