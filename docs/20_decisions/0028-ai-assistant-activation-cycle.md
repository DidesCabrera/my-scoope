# 0028 · AI Assistant activation cycle 50-58

Status: accepted, amended by 0035
Date: 2026-07-01

## Context

El ciclo Patch 41-49 dejó una base segura para integrar un LLM externo sobre el chat existente de My Scoope:

```text
Chat UI existente
  -> ChatEngine
  -> ai_assistant
  -> provider gateway
  -> contratos estructurados
  -> tool registry
  -> orquestador LLM v1
  -> proposal cards e historial
  -> audit/safety sanitizado
```

Sin embargo, después de Patch 49 el LLM externo todavía no está funcionando como experiencia real de producto. Existen dos pasos pendientes que deben mantenerse separados:

```text
1. Activación productiva/controlada del motor externo.
2. Ejecución real de tools internas.
```

Activar el motor externo solo permite conversación e interpretación con contexto acotado. Ejecutar tools permite que el asistente lea datos reales, compare targets y cree `NutritionProposal` revisables. Ambas capacidades son necesarias para que el AI Assistant se sienta realmente integrado, pero no deben habilitarse de golpe.

## Decision

Se define un nuevo ciclo de implementación:

```text
Ciclo Patch 50-58 · Activación real del AI Assistant externo
```

El ciclo debe avanzar por etapas, manteniendo rollback simple al motor determinístico y usando el audit sanitizado de Patch 49 como frontera obligatoria.

Amendment posterior a Patch 55: la decisión `0035-ai-assistant-usage-observability-and-credits.md` reevalúa el tramo restante. Patch 50-55 queda como base técnica ya implementada; Patch 56 en adelante incorpora observabilidad de costos, límites técnicos, créditos IA y activación productiva extendida hasta Patch 62.

## Patch sequence

| Patch | Objetivo | Resultado esperado |
|---:|---|---|
| 50 | Configuración operacional del proveedor externo. | My Scoope puede diagnosticar si el proveedor externo está correctamente configurado sin cambiar la experiencia del usuario. |
| 51 | Feature flag / selector de engine. | El chat puede elegir motor determinístico o LLM preview por configuración, manteniendo deterministic como default seguro. |
| 52 | Context builder seguro para LLM. | El proveedor recibe contexto mínimo, estructurado y suficiente, sin objetos Django crudos ni datos innecesarios. |
| 53 | Tool executor read-only. | El LLM puede solicitar consultas seguras sobre datos reales, sin crear ni modificar entidades. |
| 54 | Loop LLM + tools. | My Scoope puede ejecutar tools permitidas, devolver resultados al LLM y recibir una respuesta final estructurada. |
| 55 | Executor de propuestas nutricionales. | El LLM puede solicitar creación de `NutritionProposal` revisables mediante servicios internos, no writes directos. |
| 56 | Observabilidad de uso IA y costos por función. | Se registran `action_type`, provider/model, usage, tokens, costo estimado, status y errores seguros. |
| 57 | Límites técnicos de protección. | Se limitan contexto, output, historial, tool calls y requests para evitar consumo accidental excesivo. |
| 58 | Integración en chat modo preview con medición. | El flujo real puede probarse dentro de la UI existente bajo modo controlado, staff/dev/staging o feature flag. |
| 59 | Créditos IA por plan/membresía. | Tokens/costos internos se traducen a créditos comerciales, cuotas y bloqueos por plan. |
| 60 | Dashboard/admin de consumo IA. | Se monitorea costo por usuario, función, modelo, periodo, créditos, presión de cuota, errores y uso alto. |
| 61 | Optimización de costos. | Se ajusta modelo/contexto/payload por `action_type` para mejorar rentabilidad. |
| 62 | Activación productiva gradual. | El LLM externo puede habilitarse por fases con límites, créditos, observabilidad y rollback inmediato. |

## Activation levels

El estado del asistente debe entenderse como niveles progresivos:

| Nivel | Qué permite | Significado de producto |
|---|---|---|
| `deterministic` | Motor actual sin proveedor externo. | Base estable y fallback. |
| `llm_preview` | LLM conversa y estructura, sin tools reales. | Demo conversacional controlada. |
| `llm_readonly_tools` | LLM usa tools de lectura. | Asistente contextual con datos reales. |
| `llm_tool_loop` | LLM usa resultados de tools en un segundo paso. | Agente básico controlado. |
| `llm_proposals` | LLM solicita `NutritionProposal` reales. | Asistente útil para generación nutricional. |
| `llm_usage_observed` | Uso, tokens y costos por función quedan registrados. | Producto medible y evaluable económicamente. |
| `llm_credit_limited` | Uso IA se controla por créditos y membresía. | Producto con frontera comercial y operacional. |
| `llm_production` | Flujo habilitado gradualmente en producción. | Producto real con observabilidad, créditos y rollback. |

Los nombres exactos de settings pueden ajustarse durante la implementación, pero la progresión de riesgo debe mantenerse.

## Non-goals for the next cycle

El ciclo 50-58 no debe abrir estas capacidades:

```text
- UI paralela provista por el proveedor externo.
- Aplicación automática de propuestas.
- Writes directos sobre Food, Meal, DailyPlan, Program o Profile.
- Acceso directo a food_catalog.
- Uso de catalog_food_id como identificador operacional.
- Ejecución de SQL, comandos shell o mutaciones dinámicas.
- Guardado de prompts, payloads crudos, headers, API keys o argumentos completos de tools.
```

## Required safety gates

Cada etapa del ciclo debe cumplir estas puertas:

1. **Default seguro:** producción debe poder seguir en `deterministic`.
2. **Opt-in explícito:** cualquier motor LLM real debe activarse por setting/flag.
3. **Fake first:** los tests deben poder correr con `FakeLLMClient` sin red ni API keys.
4. **Registry first:** toda tool debe pasar por `ai_assistant.application.tools.registry`.
5. **Ownership:** toda tool que lea o cree datos debe validar usuario/alcance antes de responder.
6. **Proposal-first:** cualquier creación útil debe terminar como `NutritionProposal`, no como entidad aplicada.
7. **Human review:** ninguna propuesta debe aplicarse sin revisión/aprobación humana.
8. **Audit:** cada turno LLM debe producir metadata sanitizada compatible con Patch 49.
9. **Fallback:** errores del proveedor deben degradar de forma segura sin aplicar cambios.
10. **Food Catalog boundary:** el asistente operativo solo usa `notas.Food`; `food_catalog` queda fuera.

## Tool execution order

La ejecución real de tools debe habilitarse en este orden:

```text
1. Solo lectura.
2. Loop LLM + resultados de lectura.
3. Creación de NutritionProposal mediante servicios internos.
4. Observabilidad de uso/costo por función.
5. Límites técnicos de protección.
6. Preview controlado en UI con medición por action_type.
7. Créditos IA por membresía.
8. Dashboard/admin de consumo.
9. Optimización de costos.
10. Producción gradual.
```

No se deben implementar primero tools de escritura o aplicación. La primera experiencia útil de escritura debe ser creación de propuestas revisables.

## Definition of “LLM funcionando”

Para My Scoope, el LLM no se considera realmente integrado solo por responder texto.

Se distinguen estos hitos:

| Hito | Descripción |
|---|---|
| Conversacional | El proveedor externo responde dentro del chat, sin tools. |
| Contextual | El proveedor puede leer datos reales mediante tools read-only. |
| Agente controlado | El proveedor solicita tools, recibe resultados y genera respuesta final. |
| Producto útil | El proveedor puede solicitar propuestas reales revisables. |
| Observabilidad económica | Cada turno registra usage/costo por función. |
| Créditos | El uso IA se limita por plan/membresía con créditos. |
| Producción | El flujo está habilitado gradualmente con audit, límites, créditos y rollback. |

El primer punto donde el usuario percibe valor nutricional real es cuando el asistente puede generar `NutritionProposal` visibles como cards en el chat.

## Patch 50 execution note

Patch 50 implementa el primer punto del ciclo mediante diagnóstico operacional seguro del proveedor externo. El diagnóstico permite validar configuración local o live bajo opt-in explícito, sin cambiar el chat productivo y sin ejecutar tools.

Ver `docs/20_decisions/0029-ai-assistant-provider-diagnostics.md`.

## Patch 51 execution note

Patch 51 implementa el selector explícito de engine para la superficie existente de AI Nutrition Intake. El default sigue siendo `deterministic`; el modo `llm_preview` requiere opt-in por `AI_ASSISTANT_CHAT_ENGINE_MODE` y no ejecuta tools ni crea propuestas.

Ver `docs/20_decisions/0030-ai-assistant-chat-engine-selector.md`.

## Patch 52 execution note

Patch 52 implementa el context builder seguro para el LLM externo. El proveedor recibe un payload mínimo y estructurado, derivado de `ChatEngineRequest` y, en `llm_preview`, del `NutritionConversationState` calculado por My Scoope. No se envían objetos Django, payloads crudos de sesión, user_id real, headers, API keys, tokens, emails ni datos innecesarios. Tools y creación de propuestas siguen deshabilitadas.

Ver `docs/20_decisions/0031-ai-assistant-safe-llm-context-builder.md`.

## Patch 54 execution note

Patch 54 implementa el loop `LLM -> read-only tools -> LLM final answer`. `ExternalLLMOrchestrator` puede ejecutar tools read-only mediante `ReadOnlyToolExecutor`, enviar resultados sanitizados al proveedor en una segunda llamada y bloquear nuevas tool requests si el proveedor intenta continuar el loop. No crea propuestas ni realiza writes.

Ver `docs/20_decisions/0033-ai-assistant-llm-read-only-tool-loop.md`.


## Patch 55 execution note

Patch 55 implementa `ReviewableProposalToolExecutor` y agrega opt-in explícito en `ExternalLLMOrchestrator` para ejecutar tools de categoría `proposal`. Estas tools pueden crear `NutritionProposal` revisables mediante servicios internos, adjuntar `proposal_ids` reales retornados por My Scoope y enviar resultados sanitizados al proveedor. El default sigue bloqueado (`enable_reviewable_proposal_tools=False`) y no se aplican cambios automáticamente.

Ver `docs/20_decisions/0034-ai-assistant-reviewable-proposal-tool-executor.md`.


## Patch 56 execution note

Patch 56 implementa observabilidad de uso IA mediante `AIUsageEvent` y `DjangoAIUsageRecorder`. `ExternalLLMOrchestrator` intenta registrar por turno `action_type`, provider/model, usage agregado, tokens, costo estimado configurable, status, error seguro, latencia y cantidad de tool results. El registro es best-effort y no guarda prompts, argumentos completos de tools, headers, API keys ni payloads raw del proveedor.

Ver `docs/20_decisions/0036-ai-assistant-usage-observability-implementation.md`.

## Consequences

- Patch 50 debe enfocarse en configuración operacional y diagnóstico del proveedor, no en ejecución de tools.
- Patch 51 debe introducir selección segura de engine sin cambiar el default productivo.
- Patch 52 debe resolver el contexto antes de exponer datos reales al proveedor.
- Patch 53 debe iniciar tool execution solo con herramientas read-only.
- Patch 55 será el punto de integración con propuestas reales y reutilizará el render seguro de Patch 47.
- Patch 56 debe priorizar medición de uso y costos antes de expandir el preview en UI.
- Patch 59 debe convertir los costos observados en créditos IA por plan/membresía, no exponer tokens al usuario final.
- Patch 62 debe incluir una estrategia de rollout gradual, no una activación global inmediata.

Ver también `docs/20_decisions/0035-ai-assistant-usage-observability-and-credits.md`.


## Patch 57 implementation note

Patch 57 agrega guardrails técnicos configurables para input estimado, contexto, historial, output, tool loop y cantidad de tool requests. Ver `0037-ai-assistant-technical-guardrails.md`.


## Patch 58 implementation note

Patch 58 conecta `llm_preview` al chat existente de AI Nutrition Intake con metadata de observabilidad, badge de motor activo y fallback determinístico. Ver `0038-ai-assistant-chat-preview-with-guardrails.md`.


## Patch 59 implementation note

Patch 59 materializa los créditos IA como unidad comercial configurable. Agrega `AIUserCreditQuota`, `AICreditLedger`, campos de créditos en `AIUsageEvent` y preflight opcional de cuota antes de llamar al proveedor. El enforcement queda desactivado por defecto mediante `AI_ASSISTANT_CREDITS_ENABLED=False`.

Ver `docs/20_decisions/0039-ai-assistant-ai-credits-by-membership.md`.


## Patch 61 implementation note

Patch 61 agrega routing configurable de proveedor/modelo por `action_type` mediante `AI_ASSISTANT_LLM_MODEL_ROUTES`. Esto permite optimizar costos por función sin cambiar la UI, sin exponer tokens al usuario y sin asumir precios hardcodeados. Ver `docs/20_decisions/0041-ai-assistant-model-routing-by-action-type.md`.


## Patch 62 execution note

Patch 62 implementa activación productiva gradual mediante `AI_ASSISTANT_CHAT_ENGINE_MODE=llm_production` y un gate adicional de rollout (`AI_ASSISTANT_LLM_ROLLOUT_*`). Si el usuario no pasa el gate, el flujo vuelve al motor determinístico con metadata de fallback. Ver `docs/20_decisions/0042-ai-assistant-gradual-production-rollout.md`.
