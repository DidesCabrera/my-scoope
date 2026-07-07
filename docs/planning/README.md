# Planning Docs

Esta carpeta contiene planes de ciclos futuros que todavía no son documentación vigente de implementación.

Su objetivo es permitir que My Scoope conserve una **memoria estratégica accionable** sin mezclarla con los contratos actuales de arquitectura, features o decisiones ya aceptadas.

## Cuándo usar esta carpeta

Usar `docs/planning/` para:

- planificar ciclos de patches próximos;
- ordenar prioridades entre proyectos grandes;
- definir métricas, objetivos y alcance antes de escribir código;
- preparar decisiones que más adelante pasarán a `docs/decisions/`;
- conservar contexto estratégico para futuras conversaciones con IA.

## Qué no debe vivir aquí

No usar esta carpeta como reemplazo de:

- `docs/current/`, que sigue siendo la fuente de verdad vigente para implementar;
- `docs/decisions/`, que registra decisiones aceptadas o historia técnica;
- `docs/archive/`, que conserva documentos superados o bitácoras históricas;
- `manual_docs/`, que contiene notas personales fuera de la documentación oficial.

## Estado de los documentos

Cada plan debe declarar un estado explícito:

```text
Status: planned / active / paused / completed / superseded
```

Cuando un ciclo planificado empiece a implementarse, el documento puede permanecer aquí como plan operacional, pero las decisiones estables que surjan deben registrarse también en `docs/decisions/`.

## Planes actuales

- `launch_readiness_operational_safety_cycle.md`: ciclo planificado LR00-LR07 para preparar My Scoope para staging/produccion con seguridad de cuenta, settings productivos, rate limiting, guardas de creditos AI, observabilidad, CI y checklist operacional, apoyandose en el dominio comercial ya cerrado por ACC.
- `account_plans_credits_cycle.md`: ciclo completado ACC00-ACC07 para mover planes comerciales, suscripciones, créditos y entitlements hacia `accounts`, manteniendo tokens/costos como observabilidad interna y migrando gradualmente desde `notas.Plan` y créditos IA transicionales.
- `onboarding_nutrition_profile_cycle.md`: ciclo completado ONB00-ONB09 para onboarding nutricional mínimo: `accounts` conduce el flujo, `notas` persiste ficha personal y Body Metrics, `ai_assistant` decide sujeto nutricional y `nutrition_solver` calcula sobre `NutritionSubjectContext`, incluyendo warning cuando una propuesta externa se guarda en librería personal.
- `nutrition_solver_app_cycle.md`: ciclo completado para separar progresivamente el motor de optimización nutricional hacia una app Django `nutrition_solver`, con contratos puros, solver/validators extraídos, adapter operacional desde `notas.Food`, integración con AI Assistant y propuestas revisables. La UI directa se canceló/difirió por decisión estratégica.
- `food_catalog_launch_readiness_cycle.md`: ciclo completado para madurar la app existente `food_catalog` desde fundación técnica hacia capacidad operacional de lanzamiento: curación, seed natural, FatSecret, Open Food Facts, marcas y bridge solver-ready. FC-12 de métricas se difiere al ciclo transversal de Product Intelligence/Admin Analytics.
- `product_intelligence_admin_analytics_cycle.md`: ciclo completado ADM00-ADM10.6 para crear `admin_analytics` como dashboard estratégico staff-only, transversal y read-first, con overview ejecutivo, métricas de cuentas/créditos, AI Assistant, actividad nutricional, Food Catalog, Nutrition Solver, filtros, alertas internas, shell independiente y refinamientos mobile.
- `admin_operations_console_cycle.md`: ciclo completado OPS00-OPS08 para crear `admin_operations` como consola operacional staff-only, action-oriented y auditable, separada de `admin_analytics` y del Django Admin legacy/raw.
