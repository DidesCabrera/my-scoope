# AI Assistant

## Estado

Ciclo arquitectónico abierto desde Patch 41.

Desde Patch 42 existe la app Django física `ai_assistant` y el chat actual pasa por una abstracción `ChatEngine`. Desde Patch 43 existe un gateway de proveedor LLM externo desacoplado, todavía no conectado al chat productivo. Desde Patch 44 existen contratos semánticos provider-agnostic para mensajes, intención, tool requests/results y respuesta estructurada. Desde Patch 45 existe un registry controlado de tools allowlist. Desde Patch 46 existe un orquestador LLM v1 testeable que valida tool requests, sin ejecutar tools ni reemplazar todavía el motor activo del chat. Desde Patch 47 existe un puente de render para mostrar proposal cards del AI Assistant dentro del hilo actual, solo cuando My Scoope entregue propuestas reales ya visibles para el usuario. Desde Patch 48, la lista histórica de chats muestra metadata útil del AI Assistant y permite iniciar un nuevo chat limpiando solo la sesión activa. Desde Patch 49 existe una capa de audit/safety sanitizada para cada turno LLM, con latencia, proveedor/modelo, uso/tokens, tools solicitadas/bloqueadas y errores seguros, sin guardar prompts, payloads crudos ni secretos. Desde Patch 50 existe diagnóstico operacional seguro del proveedor externo. Desde Patch 51 existe selector explícito de engine para `deterministic` o `llm_preview`, manteniendo determinístico como default y fallback. Desde Patch 52 existe `SafeLLMContext` para enviar contexto mínimo y sanitizado al proveedor externo. Desde Patch 53 existe un executor read-only que puede ejecutar tools reales de lectura contra servicios internos de My Scoope, sin writes ni propuestas. Desde Patch 54, el orquestador compone el loop `LLM -> read-only tools -> LLM final answer` con una segunda llamada al proveedor usando `tool_results` sanitizados. Desde Patch 55 existe `ReviewableProposalToolExecutor` para crear `NutritionProposal` revisables bajo opt-in explícito, sin aplicación automática. Desde Patch 56 existe `AIUsageEvent` y `DjangoAIUsageRecorder` para registrar uso IA, tokens, costo estimado configurable, status y errores seguros por turno. Desde Patch 57 existen guardrails técnicos por turno para input estimado, contexto, historial, output, tool loop y cantidad de tool requests. Desde Patch 58 el modo `llm_preview` queda conectado como preview operativo sobre el chat existente, con `action_type` propio, metadata segura de conversación/turno y badge de motor activo. Tras CM23, un fallo del proveedor devuelve un fallback técnico y no ejecuta el entrevistador determinístico para el mismo turno. Desde Patch 59 existe una primera capa de créditos IA por membresía: `AIUserCreditQuota`, `AICreditLedger`, campos de créditos en `AIUsageEvent` y bloqueo opcional por cuota, detrás de `AI_ASSISTANT_CREDITS_ENABLED`. Desde Patch 60 existe un dashboard interno en Django Admin para revisar consumo IA por periodo, función, modelo, usuario, créditos, costos estimados y presión de cuota. Desde Patch 61 existe un router configurable de proveedor/modelo por `action_type`, para optimizar costos por función sin exponer tokens ni modelos al usuario final.

Desde la decisión 0028 quedó definido el ciclo Patch 50-58 para activar el LLM externo de forma gradual hasta propuestas revisables. Con Patch 55 ya implementado, la decisión 0035 reevalúa el tramo posterior: antes de preview productivo amplio se debe incorporar observabilidad de uso IA, límites técnicos, créditos IA por membresía y activación gradual con control de costos.

El AI Assistant debe evolucionar sobre la estructura de chat existente de My Scoope, no como una UI paralela.


## Current client-memory/tool-oriented baseline

The CM00-CM13 Client Memory & Profile Objects cycle is closed. The current implementation contract for this area lives in:

```text
docs/00_current/features/ai_assistant/tool_oriented_client_memory.md
```

The durable posture is:

```text
The LLM acts as an assistant/operator over My Scoope capabilities.
My Scoope exposes capabilities as allowlisted tools.
Profile, preference and proposal facts are represented as visible draft objects/cards.
Persistent writes require explicit user approval.
Tool results must synchronize with temporary chat state before follow-up questions.
```

Future work should improve tools and object contracts before adding prompt-only fixes.

## Decisión central

```text
El LLM entiende y conversa.
My Scoope calcula, valida, persiste y controla qué puede aplicarse.
```

La experiencia conversacional debe reutilizar:

```text
AiNutritionChat
notas/templates/notas/ai_intake.html
notas/templates/notas/_ai_chat_thread.html
notas/templates/notas/ai_chats/list.html
```

El LLM externo aporta comprensión natural, interpretación de intención y generación de respuestas. No es fuente de verdad nutricional ni escritor directo de entidades.

## Arquitectura objetivo

```text
Chat UI existente
  -> AiNutritionChat / historial
  -> AI Assistant Orchestrator
  -> LLM externo
  -> Tool registry permitido
  -> servicios internos de My Scoope
  -> NutritionProposal
  -> aprobación humana
```

## Reglas duras

- No crear una UI nueva aislada para AI Assistant.
- No permitir que el LLM escriba directamente `Food`, `Meal`, `DailyPlan`, `Program` ni `NutritionProposal` sin servicios de aplicación.
- No permitir que el LLM acceda a `food_catalog`.
- No permitir `catalog_food_id` como `food_id` operacional.
- No permitir que el LLM calcule macros finales como fuente de verdad.
- No aplicar cambios productivos sin aprobación humana.
- Enviar al proveedor externo solo contexto mínimo y necesario.

## Relación con Food Catalog

El AI Assistant no consume `food_catalog.CatalogFood`.

El universo alimentario disponible para tools del AI Assistant es el mismo universo operacional definido para MCP:

```text
notas.Food
```

Si un alimento maestro todavía no fue materializado como `notas.Food`, entonces no existe para el AI Assistant operativo.

## Relación con Proposals

Toda creación o modificación relevante debe terminar como `NutritionProposal` revisable.

Flujo esperado:

```text
usuario pide algo en lenguaje natural
  -> LLM interpreta
  -> tools consultan/validan
  -> My Scoope crea propuesta
  -> chat muestra card de propuesta
  -> usuario revisa/aprueba
  -> aplicación segura
```

## Relación con el chat actual

El flujo actual de AI Intake debe verse como la primera versión de conversación nutricional.

La integración LLM debe introducir una abstracción de motor, no reemplazar directamente templates ni views por lógica de proveedor externo.

Desde Patch 42 la frontera queda materializada así:

```text
ai_assistant/
  application/
    chat_engines.py      # contratos puros de engine
  infrastructure/
    providers/           # gateway LLM externo desde Patch 43
  domain/                # futuros contratos de intención/mensajes

notas/application/ai_intake/deterministic_chat_engine.py
  # runtime determinístico explícito

notas/application/ai_intake/chat_engine.py
  # runtime LLM, selección de engine y sincronización de tools/cards
```

Desde Patch 43 existen estos contratos de proveedor:

```text
LLMMessage
LLMProviderRequest
LLMProviderResponse
LLMClient
```

Y estos adapters iniciales:

```text
FakeLLMClient
OpenAIResponsesClient
get_llm_client
```



Desde Patch 44 existen estos contratos semánticos internos:

```text
AssistantMessage
AssistantIntent
AssistantTurnRequest
AssistantToolRequest
AssistantToolResult
AssistantStructuredResponse
```

Estos contratos no llaman al proveedor externo, no ejecutan tools y no escriben propuestas por sí mismos. Solo definen la forma que deberá conectar el futuro orquestador.

Desde Patch 45 existe este registry controlado:

```text
ai_assistant/application/tools/
  contracts.py      # ToolSpec, categorías y niveles de riesgo
  registry.py       # allowlist, forbidden tools y validación de requests
```

El registry solo define y valida tools. No ejecuta tools, no conecta el proveedor externo y no cambia la view del chat.

Desde Patch 46 existe un orquestador LLM v1:

```text
ai_assistant/application/orchestrator.py      # ExternalLLMOrchestrator
ai_assistant/application/llm_chat_engine.py   # adapter ChatEngine no productivo
```

El orquestador transforma `AssistantTurnRequest` en una llamada al proveedor, exige JSON estructurado, parsea `AssistantStructuredResponse` y valida cada `AssistantToolRequest` contra el registry. En Patch 46 las tools quedan solo como `pending` o `blocked`; no se ejecutan todavía.

Tools permitidas inicialmente:

```text
read_dailyplan
read_proposal
list_user_proposals
search_operational_foods
list_operational_foods
compare_dailyplan_to_targets
create_validated_meal_proposal
create_validated_dailyplan_build_proposal
create_nutrition_engine_dailyplan_proposal
iterate_nutrition_engine_dailyplan_proposal
```

Las tools de propuesta requieren revisión humana. El registry bloquea nombres de tools directas como `apply_proposal`, `create_dailyplan`, `raw_sql` y cualquier intento de usar referencias `catalog_food_id`.

El gateway ya puede ser consumido por `ExternalLLMOrchestrator`, pero la view productiva del chat aún no cambia de motor.

```text
Chat UI
  -> ChatEngine
      -> DeterministicNutritionIntakeChatEngine   # activo en Patch 46
      -> ExternalLLMChatEngine                    # disponible, no conectado por defecto
```


Desde Patch 53 existe el executor read-only:

```text
ai_assistant/application/tools/executor.py   # ReadOnlyToolExecutor
```

El executor conecta solo estas tools reales de lectura:

```text
read_dailyplan
read_proposal
list_user_proposals
search_operational_foods
list_operational_foods
```

Quedan bloqueadas en Patch 53 las tools de validación y propuesta, aunque estén declaradas en el registry para etapas posteriores. Desde Patch 54, el orquestador puede ejecutar esas tools dentro de un único loop read-only y devolver sus resultados sanitizados al proveedor para obtener una respuesta final. Si el proveedor solicita nuevas tools en la segunda llamada, se bloquean por límite de iteraciones.

El orquestador de Patch 46 no confía en `proposal_ids` enviados por el proveedor externo. Solo My Scoope podrá adjuntar propuestas reales después de ejecutar servicios internos controlados. Desde Patch 47, el chat puede renderizar esas propuestas como cards si el caller entrega objetos `NutritionProposal` ya scopeados al usuario; el renderer no consulta por ids del proveedor. Desde Patch 48, la lista de chats reutiliza `AiNutritionChat` y deriva metadata del brief persistido sin consultar al proveedor externo. Desde Patch 49, `ExternalLLMOrchestrator` adjunta `metadata["audit"]` y `metadata["audit_version"]` a sus respuestas estructuradas; esa traza es sanitizada y no contiene prompts, argumentos de tools, payloads crudos, headers ni API keys.

Desde Patch 60, los datos de observabilidad y créditos se pueden revisar internamente desde el Django Admin de `AIUsageEvent` mediante el enlace `Usage dashboard`. Desde Patch 61, `AI_ASSISTANT_LLM_MODEL_ROUTES` permite enrutar funciones simples a modelos más baratos y reservar modelos más capaces para acciones complejas. Esa vista resume KPIs por periodo, desglose por `action_type`, provider/model, usuarios de alto uso, cuotas con mayor presión y eventos recientes.

Desde Patch 56, el mismo orquestador intenta registrar observabilidad económica mediante:

```text
ai_assistant.models.AIUsageEvent
ai_assistant.application.usage.DjangoAIUsageRecorder
```

El registro agrega usage de una o más llamadas al provider en el turno, infiere o respeta `action_type`, estima costo con pricing por modelo y guarda metadata segura. Los tokens quedan como métrica interna; créditos IA quedan materializados desde Patch 59 como capa comercial configurable y desactivada por defecto hasta rollout.

Desde el patch de pricing operacional, `settings` incluye precios default por 1M tokens para modelos OpenAI usados por My Scoope y permite override por variable de entorno:

```text
AI_ASSISTANT_LLM_PRICING_USD_PER_1M_TOKENS_JSON
```

Ejemplo para Render:

```json
{"openai":{"gpt-5.4-mini":{"input":"0.75","cached_input":"0.075","output":"4.50"},"default":{"input":"0.75","cached_input":"0.075","output":"4.50"}}}
```

El costo estimado se guarda en `AIUsageEvent.estimated_cost_usd`; los créditos se calculan desde ese costo cuando existe pricing, usando `AI_ASSISTANT_USD_PER_AI_CREDIT`.

Desde Patch 57, antes de llamar al proveedor, el orquestador valida límites técnicos configurables:

```text
AI_ASSISTANT_MAX_INPUT_TOKENS
AI_ASSISTANT_MAX_CONTEXT_CHARS
AI_ASSISTANT_MAX_MESSAGE_CHARS
AI_ASSISTANT_MAX_HISTORY_MESSAGES
AI_ASSISTANT_MAX_OUTPUT_TOKENS
AI_ASSISTANT_OPENAI_REASONING_EFFORT
AI_ASSISTANT_MAX_TOOL_LOOP_ITERATIONS
AI_ASSISTANT_MAX_TOOL_REQUESTS_PER_TURN
```

Estos límites no son créditos comerciales ni membresías. Son protección operacional para evitar contexto accidentalmente excesivo, tool loops grandes o requests sobredimensionados mientras se recopilan costos reales.

## Ciclos de patches

### Ciclo Patch 41-49 · Base segura

| Patch | Objetivo |
|---:|---|
| 41 | Documentar decisión, reglas y ciclo sobre chat existente. |
| 42 | Crear app Django `ai_assistant` e introducir abstracción `ChatEngine`. |
| 43 | Crear gateway de proveedor LLM y fake client. |
| 44 | Definir contratos estructurados de mensajes/intenciones. |
| 45 | Definir tool registry controlado. |
| 46 | Implementar orquestador LLM v1 sin ejecutar tools ni reemplazar el motor activo. |
| 47 | Renderizar proposal cards generadas por AI dentro del chat existente, usando solo propuestas reales visibles para el usuario. |
| 48 | Mejorar historial/lista de chats para AI Assistant. |
| 49 | Agregar audit/safety sanitizado y cerrar ciclo Patch 41-49. |

### Ciclo Patch 50-55 · Base de activación real del LLM externo

| Patch | Objetivo | Resultado esperado |
|---:|---|---|
| 50 | Configuración operacional del proveedor externo. | Diagnóstico claro sin cambiar la experiencia del usuario. |
| 51 | Feature flag / selector de engine. | Motor determinístico por defecto y LLM preview activable por configuración. Implementado con `AI_ASSISTANT_CHAT_ENGINE_MODE`. |
| 52 | Context builder seguro. | Implementado con `SafeLLMContext`: contexto mínimo, estructurado, sanitizado y sin payloads crudos. |
| 53 | Tool executor read-only. | Implementado con `ReadOnlyToolExecutor`: lectura segura de datos reales sin writes. |
| 54 | Loop LLM + tools. | Implementado con un único loop read-only: tools ejecutadas por My Scoope, resultados sanitizados y respuesta final estructurada. |
| 55 | Executor de propuestas nutricionales. | Implementado con `ReviewableProposalToolExecutor`: creación de `NutritionProposal` revisables mediante servicios internos, detrás de opt-in explícito. |

### Ciclo Patch 56-62 · Observabilidad, créditos y activación controlada

| Patch | Objetivo | Resultado esperado |
|---:|---|---|
| 56 | Observabilidad de uso IA y costos por función. | Registrar por turno `action_type`, proveedor/modelo, usage del provider, tokens, costo estimado, status y errores seguros. |
| 57 | Límites técnicos de protección. | Limitar contexto, output, historial, tool calls y requests para evitar consumo accidental excesivo. |
| 58 | Integración en chat modo preview con medición. | Prueba real en UI existente bajo staff/dev/staging o feature flag, ya con medición activa. |
| 59 | Créditos IA por plan/membresía. | Traducir costos reales a créditos comerciales, cuota mensual/diaria y bloqueo por plan. |
| 60 | Dashboard/admin de consumo IA. | Ver costo por usuario, función, modelo, periodo, errores y uso alto. |
| 61 | Optimización de costos por modelo y `action_type`. | Selección de modelos por función, compactación de contexto y reducción de payloads. |
| 62 | Activación productiva gradual. | Rollout por fases con límites, créditos, observabilidad y rollback inmediato al motor determinístico. |

La progresión de riesgo queda ajustada así:

```text
deterministic
  -> llm_preview
  -> llm_readonly_tools
  -> llm_tool_loop
  -> llm_proposals
  -> llm_usage_observed
  -> llm_guarded_preview
  -> llm_credit_limited
  -> llm_production
```

El LLM ya alcanza valor de producto cuando puede solicitar propuestas revisables, pero no debe escalarse a producción amplia sin observabilidad de costos, límites técnicos y una futura capa de créditos IA.

## Activación real del LLM externo

La activación del LLM externo y la ejecución real de tools son capacidades distintas. Deben implementarse en etapas:

```text
1. Proveedor configurado y diagnosticable.
2. Engine seleccionable con fallback determinístico.
3. Contexto seguro para el proveedor.
4. Tools read-only.
5. Loop LLM + tools.
6. Creación de NutritionProposal revisables.
7. Observabilidad de tokens/costos por función.
8. Límites técnicos de consumo y contexto.
9. Preview controlado en UI con medición.
10. Créditos IA por membresía.
11. Dashboard/admin de consumo.
12. Optimización de costos.
13. Producción gradual.
```

Reglas para el ciclo Patch 50-62:

- producción debe conservar `deterministic` como default hasta una activación explícita;
- toda prueba automatizada debe poder correr con `FakeLLMClient`;
- toda tool debe pasar por el registry y validar ownership;
- las primeras tools ejecutables deben ser solo lectura;
- las primeras tools de escritura útil deben crear `NutritionProposal`, no entidades aplicadas;
- el audit sanitizado de Patch 49 debe acompañar cada turno LLM;
- cada turno LLM debe registrar uso/costo por `action_type` antes de preview amplio;
- cualquier error del proveedor debe degradar sin aplicar cambios.

Ver `docs/20_decisions/0028-ai-assistant-activation-cycle.md` y `docs/20_decisions/0035-ai-assistant-usage-observability-and-credits.md`.

## Configuración LLM externa

Patch 43 agrega settings/env vars para preparar proveedores externos sin activar todavía un motor LLM productivo:

```text
AI_ASSISTANT_LLM_PROVIDER=fake
AI_ASSISTANT_OPENAI_API_KEY=
AI_ASSISTANT_OPENAI_MODEL=gpt-5.4-mini
AI_ASSISTANT_OPENAI_BASE_URL=https://api.openai.com/v1
AI_ASSISTANT_OPENAI_TIMEOUT_SECONDS=30
```

Regla vigente: aunque `AI_ASSISTANT_LLM_PROVIDER=openai` esté configurado, el chat existente sigue usando el motor determinístico. En Patch 46 el proveedor puede ser consumido por `ExternalLLMOrchestrator`, pero no queda conectado por defecto a la view productiva.

## Diagnóstico operacional del proveedor

Patch 50 agrega un diagnóstico seguro para validar configuración antes de activar el LLM externo en producto:

```bash
python manage.py diagnose_ai_assistant_llm
```

Este comando no hace llamadas de red por defecto. Revisa proveedor, settings requeridos y construcción segura del cliente.

Para una prueba mínima real del proveedor se debe pedir explícitamente:

```bash
python manage.py diagnose_ai_assistant_llm --live
```

El live check usa un mensaje genérico, sin datos de usuario y sin tools. El resultado no imprime API keys, headers, payloads, prompts, raw responses ni argumentos de tools.

Ejemplo esperado en local con provider fake:

```text
AI Assistant LLM diagnostics

provider: fake
configured: true
client_buildable: true
model: fake-llm
live_check: skipped
status: ok
```

Ejemplo esperado si OpenAI está incompleto:

```text
provider: openai
configured: false
client_buildable: false
missing:
  - AI_ASSISTANT_OPENAI_API_KEY
status: configuration_error
```


## Costos, tokens y créditos IA

La integración del LLM externo debe distinguir entre métrica interna y unidad comercial:

```text
tokens = métrica interna de costo del proveedor
créditos IA = unidad comercial visible para usuarios y membresías
```

Reglas vigentes desde la reevaluación posterior a Patch 55:

- My Scoope no debe vender ni mostrar tokens como unidad principal al usuario final.
- Cada turno LLM debe poder asociarse a un `action_type` estable.
- El sistema debe registrar usage del proveedor, tokens y costo estimado cuando estén disponibles.
- Los créditos IA por plan/membresía se implementarán después de observar costos reales por función.
- El preview en UI no debe escalarse sin medición y límites técnicos.

Campos mínimos esperados para observabilidad de uso IA:

```text
user
conversation_id
message_id / turn_id
action_type
provider
model
input_tokens
output_tokens
total_tokens
estimated_cost_usd
status
error_type
created_at
```

Action types iniciales recomendados:

```text
assistant.chat
assistant.tool_selection
assistant.tool_call
assistant.tool_result_summary
assistant.explain_food
assistant.explain_meal
assistant.explain_dailyplan
assistant.compare_dailyplans
assistant.create_meal_proposal
assistant.create_dailyplan_proposal
assistant.modify_program
```

Ver `docs/20_decisions/0035-ai-assistant-usage-observability-and-credits.md`.

## Frontera de app

`ai_assistant` es una app de orquestación. No es dueña del chat persistido actual ni de las entidades nutricionales. Desde Patch 56 sí tiene un modelo propio acotado (`AIUsageEvent`) para observabilidad económica/operacional del LLM externo.

Permitido para `ai_assistant` en ciclos posteriores:

```text
contratos conversacionales
provider gateway
prompts versionados
tool registry controlado
safety / audit
observabilidad de uso IA
orquestación sobre servicios permitidos
```

No permitido:

```text
modelos Food/Meal/DailyPlan/Program
acceso directo a food_catalog
creación directa de entidades operacionales sin proposal
aplicación sin aprobación humana
```

## Documentación relacionada

- `docs/20_decisions/0019-external-llm-over-existing-chat.md`
- `docs/20_decisions/0020-ai-assistant-django-app-and-chat-engine.md`
- `docs/20_decisions/0021-llm-provider-gateway.md`
- `docs/20_decisions/0022-ai-assistant-structured-contracts.md`
- `docs/20_decisions/0023-ai-assistant-tool-registry.md`
- `docs/20_decisions/0024-ai-assistant-llm-orchestrator-v1.md`
- `docs/20_decisions/0025-ai-assistant-proposal-cards-in-chat.md`
- `docs/20_decisions/0026-ai-assistant-chat-history-list.md`
- `docs/20_decisions/0027-ai-assistant-audit-safety-closure.md`
- `docs/20_decisions/0028-ai-assistant-activation-cycle.md`
- `docs/20_decisions/0035-ai-assistant-usage-observability-and-credits.md`
- `docs/20_decisions/0036-ai-assistant-usage-observability-implementation.md`
- `docs/20_decisions/0008-ai-assisted-onboarding-to-first-plan.md`
- `docs/20_decisions/0010-mcp-operational-food-boundary.md`
- `docs/20_decisions/0016-mcp-food-boundary-hardening.md`
- `docs/00_current/features/ai_nutrition_onboarding/ai_nutrition_onboarding.md`
- `docs/00_current/features/proposals.md`


### Patch 55 · Reviewable proposal tools

Patch 55 agrega `ReviewableProposalToolExecutor` para ejecutar únicamente tools de categoría `proposal` desde el registry controlado. El orquestador puede usarlo solo con `AssistantOrchestratorConfig(enable_reviewable_proposal_tools=True)`.

Con el default seguro, las propuestas siguen bloqueadas con `reviewable_proposal_tools_disabled`. Con opt-in, las tools internas pueden crear `NutritionProposal` revisables y devolver `proposal_ids` reales, pero nunca aplicar cambios automáticamente.

### Patch 56 · Usage observability

Patch 56 agrega `AIUsageEvent` y `DjangoAIUsageRecorder` para medir cada turno del `ExternalLLMOrchestrator` antes de avanzar a preview amplio o créditos comerciales.

El registro es best-effort y guarda solo datos sanitizados:

```text
action_type
provider / model
input_tokens / cached_input_tokens / output_tokens / total_tokens
estimated_cost_usd
status / error_type
latency_ms
tool_calls_count
metadata segura
```

No guarda prompts, mensajes completos, argumentos completos de tools, headers, API keys ni payloads raw del proveedor.

Patch 56 no vende tokens ni implementa cuotas. Los tokens quedan como métrica interna; los créditos IA quedan pendientes para el ciclo posterior definido en Patch 59.


## Patch 58 execution note

Patch 58 consolida el modo `llm_preview` sobre la UI existente de AI Nutrition Intake. El preview usa `assistant.ai_nutrition_intake.preview` como `action_type`, pasa metadata segura de conversación/turno al recorder, muestra estado del motor activo en el chat y conserva fallback determinístico. Ver `docs/20_decisions/0038-ai-assistant-chat-preview-with-guardrails.md`.


## Patch 59 note

Patch 59 introduce créditos IA por membresía detrás de `AI_ASSISTANT_CREDITS_ENABLED`. Los tokens siguen siendo métrica interna; el usuario final debe ver créditos, cuotas mensuales/diarias y mensajes de upgrade en ciclos posteriores.


Desde Patch 62 existe activación productiva gradual:

```text
AI_ASSISTANT_CHAT_ENGINE_MODE=llm_production
AI_ASSISTANT_LLM_ROLLOUT_ENABLED=true
AI_ASSISTANT_LLM_ROLLOUT_MODE=staff|allowlist|percentage|all
```

El modo productivo no reemplaza la UI del chat. Usa la superficie existente de AI Nutrition Intake, mantiene observabilidad, guardrails, créditos y routing por `action_type`, y vuelve a `deterministic` si el usuario no pasa el gate de rollout.

- [0042 · AI Assistant gradual production rollout](../../../20_decisions/0042-ai-assistant-gradual-production-rollout.md)
