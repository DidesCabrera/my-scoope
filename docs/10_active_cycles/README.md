# 10 Active Cycles

Esta carpeta contiene planes de ciclos futuros, activos, pausados, completados o superados que no deben confundirse con contratos vigentes de implementación.

Su objetivo es permitir que My Scoope conserve una **memoria estratégica accionable** sin mezclarla con los contratos actuales de arquitectura, features o decisiones ya aceptadas.

## Cuándo usar esta carpeta

Usar `docs/10_active_cycles/` para:

- planificar ciclos de patches próximos;
- ordenar prioridades entre proyectos grandes;
- definir métricas, objetivos y alcance antes de escribir código;
- preparar decisiones que más adelante pasarán a `docs/20_decisions/`;
- conservar contexto estratégico para futuras conversaciones con IA.

## Qué no debe vivir aquí

No usar esta carpeta como reemplazo de:

- `docs/00_current/`, que sigue siendo la fuente de verdad vigente para implementar;
- `docs/20_decisions/`, que registra decisiones aceptadas o historia técnica;
- `docs/90_archive/`, que conserva documentos superados o bitácoras históricas;
- `manual_docs/`, que contiene notas personales fuera de la documentación oficial.

## Estado de los documentos

Cada plan debe declarar un estado explícito:

```text
Status: planned / active / paused / completed / superseded
```

Cuando un ciclo planificado empiece a implementarse, el documento puede permanecer aquí como plan operacional, pero las decisiones estables que surjan deben registrarse también en `docs/20_decisions/`.

## Planes actuales

- `food_catalog_growth_cycle.md`: ciclo activo FCG00-FCG10 con implementación completa y
  validación de datos reales en staging pendiente, para poblar efectivamente
  `CatalogFood` desde fuentes persistibles trazables, aprender su operación desde Admin
  Operations y validar muestras pequeñas antes de escalar, manteniendo `notas.Food` como
  snapshot operacional y dejando FatSecret fuera del alcance.
- `nutrition_solver_optimization_v2_cycle.md`: ciclo activo NSO00-NSO10 para evolucionar el
  solver de porciones v2 hacia optimización conjunta, explicable y contractualmente integrada
  con capacidades curadas de Food Catalog mediante snapshots operacionales.
- `ai_assistant_post_tool_followup_transport_cycle.md`: ciclo completado PT00-PT06 para diagnosticar y corregir la correlación post-tool de Responses API, hacer visibles las degradaciones, alinear el provider fake con producción y revalidar la conducta antes oculta por acknowledgements locales.
- `ai_assistant_behavioral_alignment_cycle.md`: ciclo completado BA00-BA07. El contrato conductual y post-tool fue promovido a `docs/00_current/` y la frontera global pasó `check`, 2 regresiones núcleo y 1.446 tests mediante `scripts/ci_django_checks.sh`.
- `ai_assistant_client_memory_profile_objects_cycle.md`: ciclo completado CM00-CM24. La ejecución live final y el rerun dirigido de `cambio_de_direccion` aprobaron invariantes automáticas y revisión humana, consolidando function calling nativo, estado/tool grounding, cards explícitas y fallbacks state-only.
- `launch_readiness_operational_safety_cycle.md`: ciclo planificado LR00-LR07 para preparar My Scoope para staging/produccion con seguridad de cuenta, settings productivos, rate limiting, guardas de creditos AI, observabilidad, CI y checklist operacional, apoyandose en el dominio comercial ya cerrado por ACC.
- `account_plans_credits_cycle.md`: ciclo completado ACC00-ACC07 para mover planes comerciales, suscripciones, créditos y entitlements hacia `accounts`, manteniendo tokens/costos como observabilidad interna y migrando gradualmente desde `notas.Plan` y créditos IA transicionales.
- `onboarding_nutrition_profile_cycle.md`: ciclo completado ONB00-ONB09 para onboarding nutricional mínimo: `accounts` conduce el flujo, `notas` persiste ficha personal y Body Metrics, `ai_assistant` decide sujeto nutricional y `nutrition_solver` calcula sobre `NutritionSubjectContext`, incluyendo warning cuando una propuesta externa se guarda en librería personal.
- `nutrition_solver_app_cycle.md`: ciclo completado para separar progresivamente el motor de optimización nutricional hacia una app Django `nutrition_solver`, con contratos puros, solver/validators extraídos, adapter operacional desde `notas.Food`, integración con AI Assistant y propuestas revisables. La UI directa se canceló/difirió por decisión estratégica.
- `food_catalog_launch_readiness_cycle.md`: ciclo completado para madurar la app existente `food_catalog` desde fundación técnica hacia capacidad operacional de lanzamiento: curación, seed natural, FatSecret, Open Food Facts, marcas y bridge solver-ready. FC-12 de métricas se difiere al ciclo transversal de Product Intelligence/Admin Analytics.
- `product_intelligence_admin_analytics_cycle.md`: ciclo completado ADM00-ADM10.6 para crear `admin_analytics` como dashboard estratégico staff-only, transversal y read-first, con overview ejecutivo, métricas de cuentas/créditos, AI Assistant, actividad nutricional, Food Catalog, Nutrition Solver, filtros, alertas internas, shell independiente y refinamientos mobile.
- `admin_operations_console_cycle.md`: ciclo completado OPS00-OPS08 para crear `admin_operations` como consola operacional staff-only, action-oriented y auditable, separada de `admin_analytics` y del Django Admin legacy/raw.

## Relación con CI y test hygiene

El ciclo CI00-CI05 ya está cerrado y documentado como QA/operación vigente en:

```text
docs/40_technical/qa/ci_stabilization_qa.md
docs/40_technical/operations/testing_and_ci_policy.md
docs/20_decisions/0080-ci-stabilization-and-test-hygiene.md
```

Los ciclos futuros deben considerar esta política antes de cambiar contratos, workflows, tests o settings de CI.

## Relación con arquitectura documental

La evolución de `docs/` queda regulada por:

```text
docs/00_current/AI_README.md
docs/00_current/PROJECT_STATE.md
docs/40_technical/operations/docs_information_architecture.md
docs/20_decisions/0082-docs-information-architecture-baseline.md
```

Un plan completado no debe quedar como fuente ambigua. Sus decisiones durables deben promoverse a `docs/00_current/` o registrarse en `docs/20_decisions/`.
