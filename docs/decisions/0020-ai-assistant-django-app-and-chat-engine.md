# 0020 · AI Assistant app Django y ChatEngine

Status: accepted  
Date: 2026-06-30

## Context

El Patch 41 definió que la integración de un LLM externo debe vivir sobre el chat existente de My Scoope, no como una UI paralela.

La estructura de chat existente vive principalmente en `notas`:

```text
AiNutritionChat
notas/application/ai_intake/
notas/interface/views/ai_intake.py
notas/templates/notas/ai_intake.html
notas/templates/notas/_ai_chat_thread.html
notas/templates/notas/ai_chats/list.html
```

Sin embargo, el ciclo nuevo necesita una frontera propia para contratos de motor conversacional, proveedor LLM, tools, prompts, safety y auditoría. Esa responsabilidad no pertenece a `notas` como dominio operacional nutricional ni a `food_catalog` como dominio maestro alimentario.

## Decision

Se crea una app Django independiente:

```text
ai_assistant
```

Responsabilidad de la app:

```text
ai_assistant = orquestación IA, contratos conversacionales, proveedores LLM, tools permitidas, prompts, safety y auditoría.
```

Responsabilidades que no asume:

```text
notas = datos operacionales, chat persistido actual, solver, proposals, Meals, DailyPlans, Programs.
food_catalog = catálogo maestro alimentario, curaduría, importadores y calidad de data.
mcp_server = interfaz externa de tools MCP.
```

## Patch 42 scope

Patch 42 solo introduce la frontera de app y la abstracción inicial de motor:

```text
Chat UI existente
  -> ChatEngine
      -> DeterministicNutritionIntakeChatEngine
      -> futuro ExternalLLMChatEngine
```

El motor activo sigue siendo el flujo determinístico actual de AI Intake. No se conecta proveedor externo todavía.

## Consequences

- `ai_assistant` queda registrado en `INSTALLED_APPS`.
- `ai_assistant.application.chat_engines` define contratos puros de engine.
- `notas.application.ai_intake.chat_engine` adapta el flujo actual al contrato `ChatEngine`.
- `notas.interface.views.ai_intake` deja de llamar directamente al parser conversacional y pasa por el engine activo.
- El chat visual y el historial siguen siendo los existentes.
- No hay migraciones ni modelos nuevos.
- No se habilita acceso a `food_catalog`.
- No se crea proveedor LLM externo.

## Hard rules preserved

```text
LLM/AI Assistant -X-> food_catalog
LLM/AI Assistant -X-> writes directos a entidades operacionales
LLM/AI Assistant -X-> catalog_food_id como food_id
LLM/AI Assistant -X-> aplicación sin aprobación humana
```

## Next step

Patch 43 debe crear el gateway de proveedor LLM externo y un fake client testeable, sin conectarlo aún como motor productivo del chat.
