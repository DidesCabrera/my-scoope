# 0030 · AI Assistant chat engine selector

Status: accepted
Date: 2026-07-01

## Context

Patch 51 continúa el ciclo de activación real del AI Assistant externo definido en `0028-ai-assistant-activation-cycle.md`.

Después de Patch 50, My Scoope puede diagnosticar si el proveedor LLM externo está configurado. El siguiente paso no debe activar tools ni cambiar la experiencia por defecto. Debe permitir elegir el motor del chat por configuración, con rollback inmediato al flujo determinístico.

## Decision

Patch 51 agrega un selector explícito para el motor de `AI Nutrition Intake`:

```text
AI_ASSISTANT_CHAT_ENGINE_MODE=deterministic
AI_ASSISTANT_CHAT_ENGINE_MODE=llm_preview
```

El default productivo sigue siendo:

```text
deterministic
```

Cualquier valor desconocido cae de forma segura a `deterministic`.

La selección queda encapsulada en:

```text
notas.application.ai_intake.chat_engine.get_nutrition_intake_chat_engine_mode
notas.application.ai_intake.chat_engine.get_nutrition_intake_chat_engine
```

## LLM preview policy

`llm_preview` permite que el proveedor externo produzca el texto visible del asistente dentro del chat existente, pero conserva la forma de estado que ya usa My Scoope:

```text
NutritionConversationState
NutritionIntakeResult
NutritionBrief
```

Esto significa que:

- la UI existente no cambia;
- la sesión sigue serializando el mismo payload;
- `AiNutritionChat` sigue persistiendo el mismo contrato;
- la creación de propuestas existente sigue dependiendo del brief interno de My Scoope;
- el LLM no ejecuta tools;
- el LLM no crea propuestas;
- el LLM no escribe entidades.

El motor preview se implementa como un wrapper seguro:

```text
LLMPreviewNutritionIntakeChatEngine
  -> DeterministicNutritionIntakeChatEngine construye el estado interno
  -> ExternalLLMChatEngine produce el assistant_text visible
  -> My Scoope reemplaza solo el último mensaje assistant del estado
```

## Scope

Patch 51 no implementa todavía:

- context builder seguro enriquecido;
- ejecución de tools;
- loop LLM + tools;
- creación de `NutritionProposal` desde tool requests;
- cambios de templates;
- rollout por usuario/staff;
- activación productiva global.

## Consequences

- Staging/local pueden probar conversación externa bajo `llm_preview` sin romper el flujo actual.
- Producción mantiene rollback simple removiendo o cambiando `AI_ASSISTANT_CHAT_ENGINE_MODE`.
- Patch 52 puede concentrarse en construir contexto seguro para el proveedor, sin mezclarlo con selección de engine.
- Patch 53 puede introducir ejecución read-only de tools sobre un modo ya seleccionable.
