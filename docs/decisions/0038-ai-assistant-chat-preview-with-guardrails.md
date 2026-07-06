# 0038 · AI Assistant chat preview with guardrails

Status: accepted
Date: 2026-07-02

## Context

Patch 56 agregó observabilidad económica mediante `AIUsageEvent`. Patch 57 agregó guardrails técnicos para limitar input, contexto, historial, output y tools por turno.

Con esas dos capas listas, el siguiente paso es conectar el modo `llm_preview` a la superficie existente de AI Nutrition Intake sin convertirlo todavía en producción amplia ni en sistema de créditos.

## Decision

Patch 58 mantiene la UI existente de My Scoope y consolida el preview LLM como una experiencia opt-in:

```text
AI Nutrition Intake existente
  -> ChatEngine
  -> LLMPreviewNutritionIntakeChatEngine bajo AI_ASSISTANT_CHAT_ENGINE_MODE=llm_preview
  -> ExternalLLMChatEngine
  -> ExternalLLMOrchestrator
  -> observabilidad + guardrails
```

El modo `deterministic` sigue siendo el default seguro.

## Implementación

Patch 58 agrega tres ajustes principales:

1. El preview LLM marca explícitamente sus turnos con:

```text
action_type=assistant.ai_nutrition_intake.preview
```

Esto permite medir costos de la función de preview separadamente de otros usos IA.

2. La view de AI Intake pasa metadata segura al engine:

```text
surface=ai_nutrition_intake
conversation_id
turn_id
action_type
tool_user
```

Esto mejora la trazabilidad de `AIUsageEvent` sin guardar prompts ni payloads crudos.

3. La UI muestra un estado mínimo del motor activo:

```text
Determinístico
LLM preview · medición activa · guardrails activos
```

Esto ayuda a validar manualmente en entorno de preview qué motor está respondiendo.

## Fallback

El preview LLM no debe romper el chat si ocurre un error inesperado en el adapter. En ese caso, el sistema conserva la respuesta determinística basal y marca metadata:

```text
llm_preview_fallback=true
```

Los errores controlados del proveedor siguen pasando por `ExternalLLMOrchestrator`, que devuelve respuesta segura, audit y observabilidad.

## Scope

Patch 58 no implementa créditos IA ni límites por membresía. Tampoco activa aplicación automática de propuestas.

Las proposal tools siguen dependiendo de opt-in explícito:

```text
AI_ASSISTANT_ENABLE_REVIEWABLE_PROPOSAL_TOOLS=true
```

Incluso con esa flag activa, las propuestas generadas siguen siendo revisables y requieren aprobación humana.

## Consequences

- El preview ya puede probarse desde el chat real con `AI_ASSISTANT_CHAT_ENGINE_MODE=llm_preview`.
- Cada turno preview queda preparado para medición por función.
- Los guardrails de Patch 57 protegen el turno antes de llamar al proveedor.
- El siguiente paso lógico es implementar créditos IA por plan/membresía usando los datos observados.
