# 0019 · External LLM sobre el chat existente de My Scoope

Status: accepted  
Date: 2026-06-30

## Context

My Scoope ya cuenta con una estructura conversacional para el flujo de AI Nutrition Intake:

```text
AiNutritionChat
notas/application/ai_intake/
notas/interface/views/ai_intake.py
notas/templates/notas/ai_intake.html
notas/templates/notas/_ai_chat_thread.html
notas/templates/notas/ai_chats/list.html
```

Esa estructura ya resuelve una parte importante de la experiencia:

- historial de chats;
- mensajes user/assistant;
- thread renderizable;
- composer;
- cards de propuesta generada;
- vínculo con `NutritionProposal`;
- navegación hacia detalle de propuesta.

El siguiente ciclo busca integrar un LLM externo para aportar naturalidad, comprensión del usuario e interpretación de intención. Sin embargo, el LLM no debe convertirse en dueño de datos, cálculos, validaciones ni persistencia.

También existe una decisión reciente de frontera alimentaria:

```text
food_catalog.CatalogFood = catálogo maestro interno
notas.Food = única verdad nutricional operacional
MCP / AI operational planning = solo notas.Food
```

Por lo tanto, el LLM externo no debe acceder directamente a Food Catalog ni usar IDs maestros de catálogo.

## Decision

La integración de LLM externo debe construirse **sobre la estructura de chat existente de My Scoope**.

No se debe crear una UI de AI Assistant paralela, aislada o duplicada. La experiencia conversacional principal debe evolucionar desde el chat actual.

Arquitectura objetivo:

```text
Chat UI existente de My Scoope
  -> AiNutritionChat / historial conversacional
  -> AI Assistant Orchestrator
  -> LLM externo
  -> Tool registry permitido
  -> notas.Food / Solver / Proposals / validadores
  -> respuesta estructurada
  -> chat thread + cards + NutritionProposal
```

Regla central:

```text
El LLM entiende y conversa.
My Scoope calcula, valida, persiste y decide qué se puede aplicar.
```

## Hard rules

El ciclo debe respetar estas reglas:

```text
1. El LLM no escribe directamente modelos operacionales.
2. El LLM no accede a food_catalog.
3. El LLM no acepta ni devuelve catalog_food_id como food_id operativo.
4. El LLM solo puede usar tools registradas explícitamente.
5. Las tools operativas usan notas.Food.id.
6. Los cálculos nutricionales finales vienen de My Scoope, no del LLM.
7. Toda creación/modificación relevante termina como NutritionProposal revisable.
8. El usuario aprueba antes de aplicar cambios productivos.
9. El contexto enviado al proveedor externo debe ser mínimo y necesario.
10. La UI de chat existente es el contenedor del AI Assistant.
```

## Relationship with current AI Intake

El flujo actual de AI Intake puede seguir funcionando como motor determinístico o semideterminístico.

La integración LLM no debe borrar ese flujo. Debe introducir una abstracción progresiva para que el chat pueda usar distintos motores:

```text
Chat UI
  -> Chat Engine
      -> Deterministic Nutrition Intake Engine
      -> External LLM Chat Engine
```

El primer objetivo no es crear un agente libre. El objetivo es que la conversación existente pueda interpretar mejor al usuario y producir propuestas más útiles sin saltarse las reglas del dominio.

## Relationship with MCP and tools

El LLM externo puede usar tools, pero esas tools deben ser un contrato controlado por My Scoope.

Permitido:

```text
read_dailyplan
read_meal
list_operational_foods
compare_dailyplan_to_targets
create_meal_proposal
create_dailyplan_proposal
```

No permitido:

```text
read_catalog_food
search_food_catalog_master
create_food_snapshot_from_catalog
write_dailyplan_directly
write_meal_directly
apply_proposal_without_review
```

Si el nombre histórico `list_food_catalog` se reutiliza como tool, debe mantener el contrato del Patch 38: listar alimentos operativos desde `notas.Food`, no desde `food_catalog`.

## Patch cycle plan

Este ADR abre el ciclo Patch 41-49.

### Patch 41 — AI Assistant chat cycle decision

Documentar la decisión de usar el chat existente como UI del AI Assistant, las reglas duras y el roadmap del ciclo.

No conecta proveedor externo.

### Patch 42 — AI Assistant app + Chat engine abstraction

Crear la app Django `ai_assistant` e introducir una abstracción para que el chat actual no dependa directamente del motor determinístico vigente.

Objetivo:

```text
UI chat -> ai_assistant.ChatEngine -> motor actual o futuro motor LLM
```

Patch 42 no conecta un proveedor externo ni crea modelos persistentes. El chat sigue usando el motor determinístico actual mediante `notas.application.ai_intake.chat_engine.DeterministicNutritionIntakeChatEngine`.

### Patch 43 — LLM provider gateway

Crear una capa de proveedor externo desacoplada:

```text
ai_assistant/infrastructure/providers/openai_client.py
ai_assistant/infrastructure/providers/fake_client.py
```

Debe usar settings y fallar de forma controlada si falta configuración.

### Patch 44 — Structured message and intent contracts

Definir contratos internos para intención, mensajes, tool requests, tool results y respuestas finales.

El LLM debe producir estructuras, no instrucciones libres para modificar modelos.

### Patch 45 — Controlled tool registry

Definir tools disponibles para el asistente.

Debe bloquear explícitamente:

```text
food_catalog
catalog_food_id
writes directos
aplicación sin aprobación
```

### Patch 46 — External LLM chat orchestrator v1

Implementar el loop básico:

```text
mensaje usuario
  -> contexto mínimo
  -> llamada LLM
  -> tool calls permitidas
  -> resultados tools
  -> respuesta final
  -> persistencia en chat
```

### Patch 47 — Proposal cards inside chat

Asegurar que las propuestas generadas por AI aparezcan como cards dentro del thread existente y enlacen al detalle de `NutritionProposal`.

### Patch 48 — Chat history upgrade

Evolucionar la lista/historial de chats para representar el AI Assistant completo, no solo intake inicial.

Debe evitar una migración invasiva prematura si `AiNutritionChat` todavía sirve como base compatible.

### Patch 49 — AI audit, safety and closure

Agregar trazabilidad del ciclo:

```text
modelo usado
tools solicitadas
tools ejecutadas
errores
proposal creada
latencia/tokens si están disponibles
```

No guardar API keys ni payloads innecesarios. Desde Patch 49 esto queda materializado en `ai_assistant.application.audit`, con snapshots sanitizados adjuntos a `AssistantStructuredResponse.metadata["audit"]`. La traza no guarda prompts, mensajes completos, argumentos de tools, headers ni raw provider responses.

## Consequences

La integración LLM queda alineada con la arquitectura existente:

- se reutiliza el chat actual;
- no se duplica UI;
- se mantiene el patrón proposal-first;
- Food Catalog sigue aislado del MCP/AI operativo;
- `notas.Food` sigue siendo la única fuente nutricional para herramientas;
- el proveedor externo queda encapsulado detrás de una capa propia;
- los futuros cambios pueden probarse con fake clients sin depender de internet ni gastar tokens.

## Non-goals of this cycle

Este ciclo no busca:

- entrenar un modelo propio;
- reemplazar el solver nutricional;
- reemplazar Food Catalog;
- dar acceso libre a la base de datos;
- permitir que el LLM aplique cambios sin aprobación;
- crear una UI paralela de chat;
- construir multiagentes complejos;
- implementar voz, streaming o memoria larga en la primera versión.
