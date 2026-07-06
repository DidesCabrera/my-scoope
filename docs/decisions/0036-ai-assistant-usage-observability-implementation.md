# 0036 · AI Assistant usage observability implementation

Status: accepted
Date: 2026-07-02

## Context

La decisión `0035-ai-assistant-usage-observability-and-credits.md` redefinió el tramo posterior a Patch 55: antes de ampliar el preview real del LLM externo, My Scoope debe medir el costo operacional de cada turno.

Patch 55 ya permite que el orquestador solicite propuestas revisables bajo opt-in. Ese flujo puede consumir tokens de forma variable, especialmente cuando existe tool loop o creación de propuestas. Por eso Patch 56 implementa observabilidad antes de avanzar a límites técnicos, créditos o producción.

## Decision

Se implementa una primera capa persistente de observabilidad de uso IA mediante `AIUsageEvent`.

La regla queda:

```text
Cada turno del ExternalLLMOrchestrator debe intentar registrar un evento sanitizado de uso IA.
```

El registro es best-effort: si la persistencia falla, el turno del usuario no se bloquea ni aplica cambios. La falla queda acotada como metadata de observabilidad.

## Implementación

Se agregan:

```text
ai_assistant.models.AIUsageEvent
ai_assistant.application.usage
ai_assistant.migrations.0001_initial
AIUsageEventAdmin
```

`ExternalLLMOrchestrator` ahora acepta un `usage_recorder` inyectable. Por defecto usa `DjangoAIUsageRecorder`.

El recorder persiste solo datos económicos/operacionales:

```text
user
period
conversation_id
turn_id
action_type
provider
model_name
input_tokens
cached_input_tokens
output_tokens
total_tokens
estimated_cost_usd
status
error_type
latency_ms
tool_calls_count
usage_payload sanitizado
metadata sanitizada
```

No se guardan prompts, mensajes completos, argumentos completos de tools, headers, API keys ni payloads raw del proveedor.

## Pricing

Patch 56 no hardcodea precios de proveedor ni define créditos comerciales.

La estimación de costo usa una configuración opcional:

```python
AI_ASSISTANT_LLM_PRICING_USD_PER_1M_TOKENS = {
    "openai": {
        "model-name": {
            "input": "0.00",
            "cached_input": "0.00",
            "output": "0.00",
        }
    }
}
```

Si no existe pricing configurado para el proveedor/modelo, `estimated_cost_usd` queda nulo. Esto evita inventar precisión antes de fijar una política comercial.

## Action types

Patch 56 permite declarar `action_type` desde `AssistantTurnRequest.metadata`:

```text
action_type
ai_action_type
```

Si no viene explícito, se infiere desde intent, tool results o proposals.

Acciones iniciales:

```text
assistant.chat
assistant.tool_call
assistant.create_meal_proposal
assistant.create_dailyplan_proposal
assistant.modify_program
```

La lista puede crecer en patches posteriores, especialmente cuando se conecte el preview real a UI y se diferencien funciones como explicar Food, Meal, DailyPlan o comparar planes.

## Settings

Se agrega:

```text
AI_ASSISTANT_USAGE_OBSERVABILITY_ENABLED=true
AI_ASSISTANT_LLM_PRICING_USD_PER_1M_TOKENS={}
```

El primer setting permite apagar temporalmente la persistencia de uso si hay incidentes operacionales. El segundo deja preparada la tabla de precios por proveedor/modelo sin acoplarla a un proveedor concreto.

## Consequences

- Patch 56 cumple la primera condición de `0035`: medir uso antes de ampliar el preview.
- Los tokens siguen siendo una métrica interna, no una unidad comercial visible.
- Los créditos IA siguen pendientes para Patch 59.
- Patch 57 debe enfocarse en límites técnicos de protección: contexto, output, historial, tool loop y requests.
- Patch 58 podrá conectar preview real en UI solo después de que Patch 57 agregue guardrails de consumo.
