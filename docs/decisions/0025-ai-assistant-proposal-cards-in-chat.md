# 0025 · AI Assistant proposal cards in existing chat

Status: accepted  
Date: 2026-07-01

## Context

El Patch 46 dejó un orquestador LLM v1 capaz de interpretar un turno, validar tool requests y devolver una `AssistantStructuredResponse` sin ejecutar tools ni adjuntar propuestas reales.

El siguiente paso del ciclo es preparar el render seguro de propuestas generadas por My Scoope dentro del chat existente. Este paso no debe activar el motor externo por defecto ni confiar en IDs generados por el proveedor.

## Decision

Se reutiliza el hilo actual de AI Intake y su patrón de card de propuesta:

```text
notas/templates/notas/_ai_chat_thread.html
notas/templates/notas/_ai_generated_plan_card.html
notas/presentation/pages/ai_intake_page.py
```

Se agrega una función de puente en presentación:

```text
append_ai_assistant_structured_response
build_generated_plan_cards_for_ai_response
```

La función recibe:

```text
AssistantStructuredResponse
visible_proposals
```

Y solo renderiza cards para propuestas que cumplan ambas condiciones:

```text
1. El id aparece en structured_response.proposal_ids.
2. El caller entrega un objeto NutritionProposal ya visible/autorizado para el usuario.
```

El renderer no consulta la base de datos por ids y no confía en `proposal_ids` del proveedor externo. Los ids solo se vuelven renderizables cuando una capa futura de dispatch de tools haya creado propuestas reales mediante servicios internos y haya pasado objetos ya scopeados al usuario.

## Template policy

Se extrae la card repetida a:

```text
notas/templates/notas/_ai_generated_plan_card.html
```

Esto permite que el chat renderice igual:

```text
- cards históricas dentro de conversation.messages
- card actual asociada al chat activo
- futuras cards generadas desde AI Assistant
```

## Safety policy

Patch 47:

- no activa `ExternalLLMChatEngine` como motor productivo;
- no ejecuta tools;
- no crea propuestas;
- no aplica propuestas;
- no consulta propuestas usando ids entregados por proveedor;
- no importa `food_catalog`;
- mantiene el flujo proposal-first y revisión humana.

## Consequences

- El chat existente ya puede mostrar cards provenientes de una `AssistantStructuredResponse` cuando My Scoope adjunte propuestas reales.
- El orquestador LLM sigue aislado de la UI productiva.
- El siguiente paso puede enfocarse en historial/lista de chats o en un dispatcher controlado de tools, sin reescribir templates.
