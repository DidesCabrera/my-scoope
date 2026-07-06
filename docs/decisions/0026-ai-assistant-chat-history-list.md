# 0026 · AI Assistant chat history list

Status: accepted  
Date: 2026-07-01

## Context

Desde Patch 42 el AI Assistant reutiliza el chat persistido `AiNutritionChat`. Desde Patch 47 el hilo puede mostrar proposal cards generadas por My Scoope, pero la lista histórica seguía siendo una superficie mínima: título, fecha, último mensaje y estado.

Para continuar la integración externa sin activar todavía el proveedor productivo, la siguiente mejora debe fortalecer la experiencia de historial sobre la UI existente de `notas`.

## Decision

El Patch 48 mejora la lista de chats sin crear una UI paralela ni mover la propiedad visual hacia el proveedor externo.

La lista ahora muestra metadatos derivados del estado persistido existente:

```text
- chat activo en la sesión actual
- objetivo detectado en el brief
- comidas por día detectadas
- cantidad de mensajes guardados
- cantidad de proposal cards históricas
- estado de readiness del brief
- propuesta asociada, si existe
```

También se agrega una acción explícita para iniciar un nuevo chat:

```text
ai_nutrition_chat_new
```

Esa acción solo limpia la sesión activa:

```text
AI_NUTRITION_CHAT_SESSION_KEY
AI_NUTRITION_CONVERSATION_SESSION_KEY
AI_NUTRITION_BRIEF_SESSION_KEY
```

No borra chats históricos, no borra propuestas y no cambia entidades nutricionales.

## Safety policy

Patch 48:

- no activa `ExternalLLMChatEngine`;
- no llama al proveedor LLM;
- no ejecuta tools;
- no crea ni aplica propuestas;
- no agrega modelos ni migraciones;
- solo renderiza información derivada de `AiNutritionChat` y su `NutritionProposal` asociada.

## Consequences

- El usuario puede distinguir el chat activo de los históricos.
- La lista deja de ser un registro plano y pasa a ser una superficie de navegación útil para AI Assistant.
- El botón `Nuevo chat` permite iniciar otra conversación sin perder el historial anterior.
- La UI sigue viviendo en `notas`, mientras `ai_assistant` conserva el rol de orquestación futura.
