# 0031 · AI Assistant safe LLM context builder

Status: accepted
Date: 2026-07-01

## Context

Patch 52 continúa el ciclo de activación real del AI Assistant externo definido en `0028-ai-assistant-activation-cycle.md`.

Después de Patch 51, el chat de AI Nutrition Intake puede seleccionar `llm_preview` por configuración, pero el proveedor externo todavía no debe recibir objetos Django crudos, payloads de sesión completos ni datos innecesarios. Antes de habilitar tools reales, My Scoope necesita una frontera explícita para decidir qué contexto puede salir hacia el proveedor.

## Decision

Patch 52 agrega un context builder seguro en:

```text
ai_assistant.application.context_builder
```

La salida provider-facing es `SafeLLMContext`, un payload pequeño, estructurado y serializable:

```text
surface
user
conversation
nutrition_brief
runtime
metadata
```

El builder expone solo señales mínimas:

```text
- si hay usuario autenticado, sin enviar user_id real;
- si existe payload previo, sin enviar el payload crudo;
- conteos de mensajes y preguntas pendientes;
- campos útiles del NutritionBrief ya interpretado por My Scoope;
- runtime flags que declaran que tools y creación de propuestas siguen deshabilitadas.
```

## Provider integration

`ExternalLLMChatEngine` ahora construye o consume `safe_llm_context` y lo pasa al `ExternalLLMOrchestrator`.

`ExternalLLMOrchestrator` envía el contexto como mensaje `developer` separado, junto con una policy explícita:

```text
context_is_bounded=true
context_is_read_only=true
do_not_request_missing_private_data=true
tools_remain_disabled_until_later_patch=true
```

El modo `llm_preview` de AI Nutrition Intake usa primero el motor determinístico para construir `NutritionConversationState`; luego deriva desde ese estado un `SafeLLMContext`. Por lo tanto, el LLM puede ver un resumen nutricional útil sin recibir sesión cruda ni modelos Django.

## Non-goals

Patch 52 no implementa:

```text
- ejecución real de tools;
- lectura de DailyPlan, Meal, Food o Proposal desde base de datos;
- creación de NutritionProposal;
- writes directos;
- cambios de UI;
- rollout por usuario o staff;
- acceso a food_catalog.
```

## Safety guarantees

El builder y el orquestador deben mantener estas reglas:

```text
- no enviar API keys, tokens, cookies, headers, passwords, emails o secrets;
- no enviar `user_id` real al proveedor, solo `id_present`;
- no enviar `existing_payload` crudo;
- no enviar objetos Django ni clases internas como datos de negocio;
- truncar textos largos;
- limitar listas;
- mantener `tools_enabled=false` y `proposal_creation_enabled=false`.
```

## Consequences

- `llm_preview` puede responder con más contexto nutricional sin ejecutar tools.
- Patch 53 puede construir el tool executor read-only sobre una frontera de contexto ya explícita.
- La frontera con Food Catalog sigue cerrada.
- El rollback sigue siendo simple: volver a `AI_ASSISTANT_CHAT_ENGINE_MODE=deterministic`.
