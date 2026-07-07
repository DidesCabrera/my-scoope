# Decisions

Esta carpeta registra decisiones arquitectónicas e históricas relevantes.

Estos documentos son la memoria de migraciones del proyecto: explican qué se decidió, por qué se decidió y qué consecuencias tiene para futuras implementaciones.

Formato recomendado:

```text
Status: accepted / superseded / draft
Date: YYYY-MM-DD
Context
Decision
Consequences
```


## Índice vigente

- `0001-layer-boundaries.md`: límites entre capas de arquitectura.
- `0002-priority3-safe-refactor.md`: refactor seguro de URLs y Program views.
- `0003-saved-comparisons-use-snapshots.md`: snapshots para comparaciones guardadas.
- `0004-ai-export-modes.md`: modos de exportación para IA.
- `0005-ui-system-stage-1.md`: contrato inicial de UI System, tokens y CSS.
- `0006-ui-system-stage-2-component-consolidation.md`: consolidación inicial de componentes repetidos en templates.
- `0007-food-catalog-app-boundary.md`: Food Catalog App como sistema separado.
- `0008-ai-assisted-onboarding-to-first-plan.md`: onboarding nutricional asistido por IA hacia el primer plan útil.
- `0009-food-catalog-hybrid-source-snapshot.md`: Food Catalog como fuente maestra y `notas.Food` como snapshot operativo.
- `0010-mcp-operational-food-boundary.md`: MCP solo consume alimentos operativos de `notas.Food`, sin acceso directo a `food_catalog`.
- `0011-food-catalog-internal-contracts.md`: contratos internos puros de Food Catalog antes de crear modelos maestros.
- `0012-food-catalog-master-models.md`: modelos maestros iniciales de Food Catalog sin reemplazar `notas.Food`.
- `0013-operational-food-snapshot-protocol.md`: protocolo interno para materializar `CatalogFood` publicado como snapshot en `notas.Food`.
- `0014-food-catalog-import-adapters.md`: adaptadores puros de importación pasan a Food Catalog con wrappers temporales en `notas`.
- `0015-food-catalog-admin-and-import-commands.md`: comandos y acciones admin iniciales de Food Catalog para importar candidatos maestros sin escribir `notas.Food`.
- `0016-mcp-food-boundary-hardening.md`: endurecimiento de la frontera MCP para que `list_food_catalog` siga siendo solo lectura de `notas.Food`.
- `0017-operational-foods-to-catalog-backfill.md`: backfill interno desde alimentos operativos confiables de `notas.Food` hacia candidatos maestros de Food Catalog.
- `0018-food-catalog-cycle-closure.md`: cierre del ciclo Patch 32-40 con guardas ejecutables para proteger Food Catalog, `notas.Food` y MCP.
- `0019-external-llm-over-existing-chat.md`: integración de LLM externo sobre la estructura de chat existente de My Scoope, con tools controladas y proposal-first.
- `0020-ai-assistant-django-app-and-chat-engine.md`: creación de la app Django `ai_assistant` y abstracción `ChatEngine` sobre el chat existente.
- `0021-llm-provider-gateway.md`: gateway desacoplado para proveedores LLM externos con cliente fake testeable y adapter OpenAI sin conexión productiva al chat.
- `0022-ai-assistant-structured-contracts.md`: contratos semánticos provider-agnostic para mensajes, intenciones, tool requests/results y respuesta estructurada del AI Assistant.
- `0023-ai-assistant-tool-registry.md`: registry controlado de tools allowlist para el futuro orquestador LLM, con bloqueo de writes directos y referencias a Food Catalog.
- `0024-ai-assistant-llm-orchestrator-v1.md`: orquestador LLM v1 que llama al proveedor, parsea JSON estructurado y valida tool requests sin ejecutarlas.
- `0025-ai-assistant-proposal-cards-in-chat.md`: render seguro de proposal cards del AI Assistant dentro del chat existente, usando solo propuestas reales visibles para el usuario.
- `0026-ai-assistant-chat-history-list.md`: mejora de la lista histórica del AI Assistant con metadata derivada de `AiNutritionChat`, chat activo y acción segura de nuevo chat.
- `0027-ai-assistant-audit-safety-closure.md`: cierre del ciclo Patch 41-49 con audit sanitizado, manejo seguro de errores de proveedor y trazabilidad sin prompts ni secretos.
- `0028-ai-assistant-activation-cycle.md`: ciclo base Patch 50-58 para activar el LLM externo por etapas; amendado por 0035 para extender el tramo posterior a Patch 55 con observabilidad, créditos y activación gradual hasta Patch 62.
- `0029-ai-assistant-provider-diagnostics.md`: Patch 50 agrega diagnóstico operacional seguro del proveedor LLM externo sin activar el chat productivo ni ejecutar tools.
- `0030-ai-assistant-chat-engine-selector.md`: Patch 51 agrega selector explícito entre motor determinístico y `llm_preview`, manteniendo rollback seguro al default determinístico.
- `0031-ai-assistant-safe-llm-context-builder.md`: Patch 52 agrega context builder seguro para enviar contexto mínimo, estructurado y sanitizado al proveedor externo.
- `0032-ai-assistant-read-only-tool-executor.md`: Patch 53 agrega executor local read-only para ejecutar solo tools de lectura allowlist, sin writes ni propuestas.
- [0033 · AI Assistant LLM read-only tool loop](0033-ai-assistant-llm-read-only-tool-loop.md)
- [0034 · AI Assistant reviewable proposal tool executor](0034-ai-assistant-reviewable-proposal-tool-executor.md)
- [0035 · AI Assistant usage observability and AI credits cycle](0035-ai-assistant-usage-observability-and-credits.md)

- `0036-ai-assistant-usage-observability-implementation.md`: implementación de `AIUsageEvent`, recorder best-effort y estimación configurable de costos para Patch 56.

- `0037-ai-assistant-technical-guardrails.md`: límites técnicos configurables por turno para proteger el ciclo LLM externo antes del preview amplio.
- [0038 · AI Assistant chat preview with guardrails](0038-ai-assistant-chat-preview-with-guardrails.md)
- [0039 · AI Assistant AI credits by membership](0039-ai-assistant-ai-credits-by-membership.md)
- [0040 · AI Assistant usage dashboard/admin](0040-ai-assistant-usage-dashboard-admin.md)

- [0041 · AI Assistant model routing by action_type](0041-ai-assistant-model-routing-by-action-type.md)
- [0042 · AI Assistant gradual production rollout](0042-ai-assistant-gradual-production-rollout.md)

- [0043 · Docs planning area and planning export mode](0043-docs-planning-and-planning-export.md)

- [0044 · Nutrition Solver extraction start](0044-nutrition-solver-extraction-start.md)
- [0045 · Nutrition Solver physical app shell](0045-nutrition-solver-physical-app-shell.md)
- [0046 · Nutrition Solver pure contracts moved](0046-nutrition-solver-pure-contracts-moved.md)
- [0047 · Nutrition Solver portion solver and validators moved](0047-nutrition-solver-portion-solver-validators-moved.md)
- [0048 · Nutrition Solver operational food adapter](0048-nutrition-solver-operational-food-adapter.md)
- [0049 · Nutrition Solver AI Assistant preview tool](0049-nutrition-solver-ai-assistant-preview-tool.md)
- [0050 · Nutrition Solver separation cycle closure](0050-nutrition-solver-cycle-closure.md)
- [0051 · Account plans and credits domain](0051-account-plans-and-credits-domain.md)
- [0052 · Account app enrichment cycle closure](0052-account-app-enrichment-cycle-closure.md)
- [0053 · Admin Analytics strategic dashboard](0053-admin-analytics-strategic-dashboard.md)
- [0054 · Admin Analytics app shell](0054-admin-analytics-app-shell.md)
- [0055 · Admin Analytics executive overview](0055-admin-analytics-executive-overview.md)
- [0056 · Admin Analytics account metrics](0056-admin-analytics-account-metrics.md)
- [0057 · Admin Analytics AI Assistant metrics](0057-admin-analytics-ai-assistant-metrics.md)
- [0058 · Admin Analytics product activity metrics](0058-admin-analytics-product-activity-metrics.md)
- [0059 · Admin Analytics Food Catalog quality metrics](0059-admin-analytics-food-catalog-quality-metrics.md)

- [0060 · Admin Analytics Nutrition Solver quality metrics](0060-admin-analytics-nutrition-solver-quality-metrics.md)
- [0061 · Admin Analytics temporal filters and segmentation](0061-admin-analytics-temporal-filters-and-segmentation.md)
- [0062 · Admin Analytics internal alerts / health signals](0062-admin-analytics-internal-alerts-health-signals.md)
- [0063 · Admin Analytics cycle closure](0063-admin-analytics-cycle-closure.md)
- [0064 · Admin Analytics independent shell](0064-admin-analytics-independent-shell.md)
- [0065 · Admin Analytics compact filter bar](0065-admin-analytics-compact-filterbar.md)
- [0066 · Admin Analytics export scope](0066-admin-analytics-export-scope.md)
- [0067 · Admin Analytics page title topbar](0067-admin-analytics-page-title-topbar.md)
- [0068 · Admin Analytics neutral dark theme](0068-admin-analytics-neutral-dark-theme.md)
- [0069 · Admin Analytics mobile shell and filter drawer](0069-admin-analytics-mobile-shell-and-filter-drawer.md)
- [0070 · Admin Operations Console planning](0070-admin-operations-console-planning.md)
- [0071 · Admin Operations app shell](0071-admin-operations-app-shell.md)
- [0072 · Admin Operations operational overview](0072-admin-operations-operational-overview.md)
- [0073 · Admin Operations Food Catalog workflow](0073-admin-operations-food-catalog-workflow.md)
- [0074 · Admin Operations Accounts & Credits workflow](0074-admin-operations-accounts-credits-workflow.md)
- [0075 · Admin Operations AI Assistant workflow](0075-admin-operations-ai-assistant-workflow.md)
- [0076 · Admin Operations audit log foundation](0076-admin-operations-audit-log-foundation.md)
- [0077 · Admin Analytics to Admin Operations cross-links](0077-admin-analytics-operations-cross-links.md)
- [0078 · Admin Operations V1 closure](0078-admin-operations-v1-closure.md)
- [0079 · Layer strictness by app tier](0079-layer-strictness-by-app-tier.md)
