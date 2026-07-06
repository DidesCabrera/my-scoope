# 0022 · AI Assistant structured contracts

Status: accepted  
Date: 2026-06-30

## Context

El Patch 43 creó el gateway de proveedor LLM externo con contratos de transporte:

```text
LLMMessage
LLMProviderRequest
LLMProviderResponse
LLMClient
```

Esos contratos sirven para hablar con proveedores externos, pero no describen todavía la semántica interna que My Scoope necesita para orquestar una conversación segura.

El siguiente paso del ciclo es definir una capa estructurada para:

```text
mensajes internos
intención detectada
tool requests futuros
tool results futuros
respuesta estructurada del asistente
```

## Decision

Se crea un contrato semántico provider-agnostic en:

```text
ai_assistant/domain/contracts.py
```

La capa define:

```text
AssistantMessage
AssistantIntent
AssistantTurnRequest
AssistantToolRequest
AssistantToolResult
AssistantStructuredResponse
```

También define enumeraciones normalizadas para:

```text
AssistantMessageRole
AssistantIntentName
AssistantToolStatus
```

Estos contratos pertenecen al dominio de `ai_assistant` porque describen la forma conceptual de una conversación y no dependen de HTTP, Django views, templates, OpenAI, MCP, `notas` ni `food_catalog`.

## Intent policy

`AssistantIntent` expresa una interpretación de alto nivel, por ejemplo:

```text
answer_question
ask_clarification
capture_nutrition_brief
create_meal_proposal
create_dailyplan_proposal
create_program_proposal
iterate_proposal
read_context
unknown
```

La intención no autoriza writes por sí misma.

Una intención de escritura solo puede transformarse en cambios reales mediante futuros tools controlados, servicios de aplicación y propuestas revisables.

## Tool policy

`AssistantToolRequest` y `AssistantToolResult` definen la forma del intercambio con tools, pero Patch 44 no registra ni ejecuta tools.

La lista permitida de tools queda para Patch 45.

Esto preserva la frontera:

```text
LLM interpreta -> orquestador decide -> tool registry valida -> My Scoope ejecuta -> propuesta revisable
```

## Human review boundary

`AssistantStructuredResponse` usa `requires_human_review=True` por defecto.

Esto mantiene la regla vigente:

```text
La IA conversa y estructura.
My Scoope calcula, valida y persiste.
El usuario revisa y aprueba.
```

Los turnos puramente informativos podrán optar explícitamente por no requerir revisión humana en un futuro orquestador, pero las intenciones de escritura deben mantenerse proposal-first.

## Hard rules preserved

Patch 44:

- no conecta el LLM externo al chat productivo;
- no ejecuta tools;
- no crea modelos persistentes;
- no importa ni accede a `food_catalog`;
- no importa `notas` desde los contratos semánticos;
- no escribe `Food`, `Meal`, `DailyPlan`, `Program` ni `NutritionProposal`;
- no aplica propuestas;
- no cambia templates ni UI.

## Consequences

- Patch 45 puede construir un tool registry sobre contratos explícitos.
- Patch 46 puede implementar el orquestador LLM v1 usando `AssistantTurnRequest` y `AssistantStructuredResponse`.
- El provider gateway de Patch 43 sigue siendo una capa de transporte, no una capa semántica.
- El chat actual continúa usando `DeterministicNutritionIntakeChatEngine`.

## Next step

Patch 45 debe definir el tool registry controlado y sus políticas de allowlist, sin permitir acceso directo a `food_catalog` ni writes fuera de propuestas revisables.
