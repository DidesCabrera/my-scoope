# 0024 · AI Assistant LLM orchestrator v1

Status: accepted  
Date: 2026-06-30

## Context

El Patch 43 creó el gateway de proveedor LLM externo.

El Patch 44 definió contratos semánticos internos para mensajes, intención, tool requests/results y respuestas estructuradas.

El Patch 45 definió un registry controlado de tools allowlist y bloqueos explícitos para writes directos, Food Catalog y referencias `catalog_food_id`.

El siguiente paso del ciclo es crear un orquestador LLM v1 que conecte esas piezas sin saltarse la frontera de seguridad.

## Decision

Se crea el orquestador en:

```text
ai_assistant/application/orchestrator.py
```

La capa expone:

```text
ExternalLLMOrchestrator
AssistantOrchestratorConfig
AssistantProviderParseResult
AssistantOrchestratorError
```

Y un adapter no productivo al contrato de chat:

```text
ai_assistant/application/llm_chat_engine.py
ExternalLLMChatEngine
```

El orquestador hace cuatro cosas:

```text
AssistantTurnRequest
  -> LLMProviderRequest
  -> provider response JSON
  -> AssistantStructuredResponse
  -> validación local de tool requests
```

## JSON contract

El proveedor debe responder como JSON válido sin markdown.

Formato esperado:

```json
{
  "format": "ai_assistant_structured_response.v1",
  "assistant_message": {"content": "texto para mostrar al usuario"},
  "intent": {
    "name": "answer_question",
    "confidence": 0.8,
    "summary": "resumen breve",
    "slots": {},
    "missing_slots": [],
    "safety_flags": []
  },
  "tool_requests": [],
  "requires_human_review": true
}
```

Si el proveedor devuelve texto plano o JSON inválido, el orquestador cae a una respuesta segura con intención `unknown` y `requires_human_review=True`.

## Tool policy

El orquestador solo valida tool requests mediante:

```text
ai_assistant.application.tools.validate_tool_request
```

Patch 46 no ejecuta tools.

Un tool request permitido queda como `pending`. Un tool request desconocido, prohibido, incompleto o con referencias de Food Catalog queda como `blocked`.

Esto conserva la frontera:

```text
LLM interpreta
  -> My Scoope valida el tool request
  -> futuro dispatcher ejecuta servicios internos
  -> NutritionProposal revisable
  -> usuario aprueba
```

## Proposal policy

El orquestador no confía en `proposal_ids` devueltos por el proveedor externo.

Si el proveedor incluye `proposal_ids`, se ignoran y se registran en metadata como `ignored_provider_proposal_ids`.

Solo My Scoope podrá adjuntar propuestas reales después de ejecutar servicios internos controlados en un patch posterior.

## Chat policy

Patch 46 no reemplaza todavía el motor productivo del chat de AI Intake.

El flujo existente continúa usando:

```text
DeterministicNutritionIntakeChatEngine
```

`ExternalLLMChatEngine` queda disponible como adapter de aplicación para pruebas y para el siguiente ciclo, pero no se conecta por defecto a `notas/interface/views/ai_intake.py`.

## Hard rules preserved

Patch 46:

- no toca templates;
- no crea modelos ni migraciones;
- no importa ni accede a `food_catalog`;
- no escribe `Food`, `Meal`, `DailyPlan`, `Program` ni `NutritionProposal`;
- no aplica propuestas;
- no ejecuta tools;
- no confía en IDs de propuesta generados por el proveedor;
- mantiene revisión humana por defecto.

## Consequences

- El proyecto ya tiene una ruta real de orquestación LLM testeable.
- El provider externo puede interpretar intención y solicitar tools en un contrato controlado.
- La ejecución real de tools queda separada para un patch posterior.
- Patch 47 puede decidir cómo mostrar respuestas/proposal cards generadas desde resultados de tools dentro del chat existente.

## Next step

Patch 47 debe conectar resultados revisables al chat existente, probablemente mediante un dispatcher controlado de tools de propuesta y render de proposal cards, sin aplicar cambios productivos automáticamente.
