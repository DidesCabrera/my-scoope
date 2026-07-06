# AI Implementation Guide

Guía para que una IA implemente cambios en My Scoope sin romper patrones del sistema.

## Antes de modificar código

1. Leer `docs/README.md`.
2. Leer `docs/current/architecture/layers.md`.
3. Leer `docs/current/architecture/rules.md`.
4. Leer `docs/current/architecture/section_creation_guide.md`.
5. Revisar docs de feature si existen.

## Documentos de autoridad

Alta autoridad:

```text
docs/current/
docs/decisions/
```

Baja autoridad:

```text
docs/archive/
manual_docs/
```

`manual_docs/` no debe usarse para implementar.

## Reglas de código

- Mantener views delgadas.
- No poner lógica de negocio reusable en templates.
- No poner writes en presentation.
- No importar presentation/interface desde application.
- No crear CSS nuevo si existe patrón reutilizable.
- No dividir `domain/models.py` sin una tarea dedicada.
- Agregar tests cuando se toque parsing, payloads, commands o rutas críticas.

## AI nutricional y generación asistida

Para flujos de onboarding nutricional, generación de planes o asistentes internos, leer además:

```text
docs/current/features/ai_assistant/README.md
docs/current/features/ai_nutrition_onboarding/ai_nutrition_onboarding.md
docs/current/features/proposals.md
docs/current/features/food_catalog/food_catalog_app.md
```

Regla principal:

```text
La IA conversa. MyScoope calcula, valida y optimiza. El usuario revisa y aprueba.
```

La IA no debe crear entidades productivas directamente. Debe producir briefs, preguntas, explicaciones o propuestas revisables que pasen por validación de aplicación.

## External LLM / AI Assistant

Desde Patch 41, cualquier integración con un LLM externo debe construirse sobre la estructura de chat existente de My Scoope. Desde Patch 42, esa integración tiene una app Django propia: `ai_assistant`.

Reglas obligatorias:

```text
Chat existente -> AI Assistant Orchestrator -> LLM externo -> tools permitidas -> NutritionProposal
```

No crear una UI paralela de AI Assistant si el flujo puede vivir en `AiNutritionChat`, `ai_intake.html`, `_ai_chat_thread.html` y la lista de chats actual. La UI puede seguir en `notas`; el motor conversacional debe pasar por la abstracción `ChatEngine`.

El LLM externo no debe escribir modelos operacionales directamente, no debe acceder a `food_catalog`, no debe usar `catalog_food_id` como `food_id`, no debe calcular macros finales como fuente de verdad y no debe aplicar cambios sin revisión humana. Desde Patch 45, cualquier tool futura debe pasar primero por `ai_assistant.application.tools.registry`. Desde Patch 46, el orquestador LLM v1 solo valida tool requests; no ejecuta tools ni confía en `proposal_ids` entregados por el proveedor. Desde Patch 47, proposal cards del AI Assistant solo pueden renderizarse cuando el caller entrega objetos `NutritionProposal` reales y visibles para el usuario. Desde Patch 48, las mejoras de historial/lista deben seguir usando `AiNutritionChat` y no deben pedir metadata visual al proveedor externo. Desde Patch 49, los turnos LLM deben producir audit sanitizado mediante `ai_assistant.application.audit`; no se deben guardar prompts, payloads crudos, headers, API keys ni argumentos completos de tools.

Desde la decisión 0028, la activación real del LLM externo debe avanzar por el ciclo Patch 50-58: configuración operacional, selector de engine, context builder seguro, tools read-only, loop LLM+tools, creación de propuestas revisables, preview controlado, hardening y producción gradual. No saltar directo a tools de escritura ni activar el proveedor externo para todos los usuarios sin fallback a `deterministic`.

Antes de implementar un patch de este ciclo, ubicar su nivel de riesgo:

```text
deterministic
  -> llm_preview
  -> llm_readonly_tools
  -> llm_tool_loop
  -> llm_proposals
  -> llm_production
```

Reglas específicas del ciclo 50-58:

- `deterministic` debe seguir siendo default hasta activación explícita.
- Los tests deben poder usar `FakeLLMClient` sin red ni API keys.
- Toda tool ejecutada debe pasar por el registry y validar ownership.
- La primera ejecución real de tools debe ser read-only.
- La primera escritura útil debe crear `NutritionProposal` revisable.
- Ningún patch debe aplicar propuestas automáticamente.
- Todo turno LLM debe mantener audit sanitizado compatible con Patch 49.

Ver:

```text
docs/decisions/0019-external-llm-over-existing-chat.md
docs/decisions/0020-ai-assistant-django-app-and-chat-engine.md
docs/decisions/0021-llm-provider-gateway.md
docs/decisions/0022-ai-assistant-structured-contracts.md
docs/decisions/0023-ai-assistant-tool-registry.md
docs/decisions/0024-ai-assistant-llm-orchestrator-v1.md
docs/decisions/0025-ai-assistant-proposal-cards-in-chat.md
docs/decisions/0026-ai-assistant-chat-history-list.md
docs/decisions/0027-ai-assistant-audit-safety-closure.md
docs/decisions/0028-ai-assistant-activation-cycle.md
docs/current/features/ai_assistant/README.md
```

## Cuando haya duda

Buscar una sección similar vigente y seguir su estructura actual, no documentos archivados.
