# 20 Decisions

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

- `0080-ci-stabilization-and-test-hygiene.md`: estabilización de CI y política de higiene de tests.
- `0081-testing-hygiene-baseline.md`: baseline de estructura y reglas para que los tests ayuden sin entorpecer.
- `0082-docs-information-architecture-baseline.md`: baseline de arquitectura documental para que `docs/` guíe a humanos e IA sin convertirse en ruido plano.

- `0083-numbered-docs-information-architecture.md`: refactor numerado de `docs/` para reducir ambigüedad y mejorar lectura asistida por IA.

- `0084-export-modes-alignment.md`: alineación de modos de exportación con la nueva arquitectura documental y ayuda operativa del script.
- `0085-ai-assistant-client-memory-profile-objects.md`: decisión de evolucionar el AI Assistant hacia memoria de cliente basada en objetos visibles, drafts y aprobación explícita para ficha/preferencias.
- `0086-ai-assistant-tool-oriented-operator.md`: decisión que enmienda el ciclo de memoria para tratar al AI Assistant como operador asistido por tools del producto, no como simple redactor ni como controlador determinístico paralelo.
- `0087-ai-assistant-validation-tool-executor.md`: decisión que conecta la categoría `validation` a un executor propio para que el AI Assistant pueda operar comparaciones reales sin writes.
- `0088-ai-assistant-profile-draft-tools.md`: decisión que agrega tools de lectura de ficha y draft de perfil para que el LLM complete objetos estructurados sin persistir cambios hasta aprobación explícita.
- `0089-ai-assistant-profile-card-tool-results.md`: decisión que permite renderizar cards de ficha desde tool results controlados como objetos scrolleables dentro del chat.
- `0090-ai-assistant-profile-commit-approval-tool.md`: decisión que agrega una tool interna de aprobación para persistir campos de ficha después de una acción explícita del usuario, sin exponer esa write tool al proveedor LLM.
- `0091-ai-assistant-preference-draft-tools.md`: decisión que agrega tools de draft para preferencias alimentarias y organización de comidas, separadas de la ficha personal y sin persistencia automática.
- `0092-ai-assistant-proposal-preference-tools.md` — Proposal-scoped preference tools and card boundary.

- `0093-ai-assistant-saved-comparison-read-tools.md`: tools read-only para listar y leer comparaciones guardadas como objetos reales del Assistant.
- `0094-ai-assistant-tool-result-state-sync.md`: sincronización de resultados de tools draft con el estado temporal del chat para evitar que cards y brief conversacional diverjan.
- `0095-ai-assistant-proposal-from-drafts-tool.md`: tool reviewable para crear propuestas DailyPlan desde `profile_draft`, `preference_draft` y `proposal_preferences`, componiendo un `NutritionBrief` interno sin persistir memoria.
- `0096-ai-assistant-tool-oriented-intake-context.md`: contexto provider-facing para que el LLM opere drafts y tools como asistente, en vez de depender de hints legacy o claims de texto.
- `0097-ai-assistant-tool-led-regression-tests.md`: regresiones CM12 para memoria vía tools, no repetición visible y límites de aprobación.
- `0098-ai-assistant-client-memory-cycle-closure.md`: cierre del ciclo CM00-CM13 y promoción del contrato actual de memoria/tool-oriented a `docs/00_current/features/ai_assistant/tool_oriented_client_memory.md`.
- `0099-ai-assistant-llm-native-tool-intake-runtime.md`: elimina preguntas determinísticas del contexto provider-facing en modo LLM y hace que `read_user_profile_context` produzca draft/card/patch de ficha para el runtime tool-oriented.

- `0100-ai-assistant-chat-object-context.md`: expone cards recientes del chat como contexto provider-facing para que el LLM resuelva referencias como “completemoslos” sin reabrir campos ya conocidos.
- `0101-ai-assistant-conversation-debug-harness.md`: comando de replay/debug y frontera final anti-JSON visible para iterar el comportamiento del Assistant sin depender solo de la UI.
- `0102-ai-assistant-scripted-replay-scenarios.md`: escenarios scriptados con provider fake para validar parser, tools, estado, cards y texto visible antes de pruebas manuales con proveedor real.
- `0103-ai-assistant-tool-contracts-over-prompt-overstructuring.md`: decisión de preferir libertad del LLM guiada por tools tipadas sobre prompts sobre-estructurados, guardias conversacionales rígidas o parsers semánticos paralelos.
- `0104-ai-assistant-draft-update-card-sharing-boundary.md`: separa actualización silenciosa de drafts y presentación explícita de cards, y amplía la procedencia canónica de `NutritionBrief` a campos de perfil, propuesta y preferencias.
- `0105-ai-assistant-provider-context-simplification.md`: simplifica el contexto provider-facing para exponer objetos actuales y capacidades sin reconstruir un entrevistador determinístico; además preserva drafts/cards anidados bajo el sanitizador seguro.
- `0106-ai-assistant-adaptive-prompt-response-policy.md`: elimina el orden fijo de intake y el límite universal de una pregunta desde prompts provider-facing; adopta ritmo adaptativo y deja la semántica de campos en tools tipadas.
- `0107-ai-assistant-invariant-based-conversation-replays.md`: reemplaza coreografías exactas por invariantes de estado, tools, cards, texto visible y persistencia; agrega variantes conversacionales y una propuesta real pendiente de revisión.
- `0108-ai-assistant-legacy-deterministic-boundary-isolation.md`: separa físicamente el runtime determinístico, crea un resultado state-only para turnos LLM, desacopla readiness de copy conversacional y hace observable cuándo el fallback determinístico fue realmente invocado.
- `0109-ai-assistant-real-provider-ux-validation-gate.md`: implementa el gate CM24 con escenarios sintéticos contra proveedor real, invariantes automáticos, metadata semántica acotada, observabilidad de uso/créditos y revisión UX humana obligatoria antes del cierre.
- `0110-ai-assistant-tool-grounded-state-claims.md`: exige que afirmaciones de lectura/cambio/uso de estado estén respaldadas por tools tipadas y calibra CM24 para usar `AIUsageEvent` como evidencia dura del proveedor.
- `0111-ai-assistant-strict-structured-provider-transport.md`: decisión intermedia, hoy superada por 0112, que probó Structured Outputs estrictos con tool plan anidado y un retry acotado.
- `0112-ai-assistant-native-provider-function-call-transport.md`: reemplaza tool requests anidados en JSON textual por function calling nativo de Responses API, devuelve resultados como `function_call_output` y mantiene validación, permisos y límites en My Scoope.
- `0113-ai-assistant-proposal-complexity-and-post-tool-resilience.md`: incorpora `complexity_level` al draft de propuesta y preserva resultados tipados de tools cuando falla únicamente la redacción posterior del proveedor, sin activar intake determinístico.
- `0114-ai-assistant-explicit-proposal-preference-function-schema.md`: convierte los campos de `update_proposal_preferences.updates` en propiedades provider-facing explícitas y compactas, para que “algo simple” viaje como `complexity_level=low` sin parsers locales ni aumento de límites.
- `0115-ai-assistant-capability-scoped-tools-and-strict-nullable-proposal-arguments.md`: alinea el catálogo provider-facing con las capacidades realmente habilitadas y convierte `update_proposal_preferences` en una función estricta con campos anulables, evitando omisiones silenciosas sin parsers locales ni aumento de límites.
- `0116-ai-assistant-proposal-complexity-state-sync-completeness.md`: corrige la proyección local de `proposal_preferences.complexity_level` hacia `NutritionBrief` y preserva su procedencia, sin cambiar prompts, schemas ni límites.
- `0117-ai-assistant-post-tool-local-ack-state-only.md`: limita el fallback local posterior a tools a confirmar estado validado, sin elegir la siguiente pregunta ni reconstruir un entrevistador determinístico.
- `0118-ai-assistant-behavioral-alignment-cycle.md`: inicia BA00-BA07 para alinear identidad, dominio, iniciativa, tool governance y calidad conversacional sin restaurar un guion determinístico.
- `0119-ai-behavior-export-mode.md`: agrega el modo focalizado `ai_behavior` y consolida una única definición canónica por modo en el script de exportación.
- `0125-contract-faithful-post-tool-test-double.md`: hace que el provider fake valide correlación nativa y continuidad de razonamiento con el mismo contrato del transporte real, y bloquea acknowledgements locales camuflados como turnos saludables.
- `0126-post-tool-behavioral-revalidation.md`: vuelve a validar repreguntas sobre datos ya conocidos y cautela ante mensajes ambiguos una vez restauradas las respuestas post-tool del proveedor.
- `0127-profile-aware-real-provider-validation-fixtures.md`: hace que el escenario PT06 adapte sus expectativas a los datos realmente persistidos en la ficha, sin ocultar pérdidas de sincronización cuando esos datos sí existen.
- `0128-ai-assistant-behavioral-alignment-current-contract.md`: promueve BA/PT al contrato vigente, fija la semántica de tool restraint, progreso, correlación post-tool y fallback degradado, y reserva el cierre formal para la regresión global del ZIP `full`.
- `0129-ai-assistant-behavioral-alignment-cycle-closure.md`: cierra BA00-BA07 tras aprobar el gate live aceptado, alinear tests documentales con la arquitectura numerada y pasar `check`, 2 regresiones núcleo y 1.446 tests mediante el script oficial de CI.
- `0130-behavioral-replays-real-provider-ux-gate.md`: combina replays determinísticos por invariantes con revisión UX humana explícita para validaciones contra proveedor real.
- `0139-nutrition-solver-optimization-v2-baseline.md`: congela el baseline previo a NSO.
- `0140-food-catalog-solver-capability-requirements.md`: requisitos explícitos de capacidades.
- `0141-versioned-solver-food-profiles.md`: perfiles versionados con confianza y procedencia.
- `0142-food-catalog-curated-solver-capabilities.md`: capacidades curadas en Food Catalog.
- `0143-operational-solver-capability-snapshot.md`: snapshot operativo para el solver.
- `0144-optimization-problem-v2-meal-grammar.md`: contrato V2 y gramática de comidas.
- `0145-candidate-portfolio-combination-planning.md`: portfolios acotados de combinaciones.
- `0146-cp-sat-optimization-backend.md`: backend CP-SAT seleccionable.
- `0147-whole-day-optimization-and-alternatives.md`: optimización diaria y alternativas.
- `0148-shadow-quality-and-regression-gates.md`: shadow, calidad y regresiones duras.
- `0149-nutrition-solver-optimization-v2-closure.md`: activación controlada y cierre NSO.
- `0150-open-food-facts-remains-reference-only.md`: mantiene Open Food Facts como lookup/referencia hasta aprobar explícitamente las obligaciones ODbL del catálogo combinado.
- `0151-governed-food-catalog-growth-boundary.md`: hace obligatorios dry-run/batch/source, escala controlada y separación importación/publicación/snapshot.
- `0152-executable-project-control-and-ai-context.md`: adopta un estado ejecutable y sanitizado compartido por CLI, Admin Operations y clientes AI, junto con registros de documentos, transiciones y apuestas basadas en evidencia.
- `0153-calendarization-snapshots-and-idempotent-web-push.md`: separa la ejecución fechada del programa editable y el evento lógico de cada delivery Web Push por dispositivo.
