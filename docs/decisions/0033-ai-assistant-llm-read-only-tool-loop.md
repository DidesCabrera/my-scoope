# 0033 · AI Assistant LLM read-only tool loop

Status: accepted  
Date: 2026-07-01

## Context

Patch 53 conectó un `ReadOnlyToolExecutor` capaz de ejecutar tools reales de lectura de My Scoope bajo allowlist y ownership de usuario. Sin embargo, el orquestador LLM todavía necesitaba componer el ciclo completo:

```text
LLM
  -> tool_requests
  -> ReadOnlyToolExecutor
  -> tool_results
  -> LLM final answer
```

Sin ese loop, el proveedor podía pedir tools, pero no podía usar sus resultados para responder con datos reales.

## Decision

Patch 54 habilita un único loop read-only dentro de `ExternalLLMOrchestrator`.

El flujo queda así:

```text
AssistantTurnRequest
  -> provider call #1
  -> parse AssistantStructuredResponse
  -> validate tool_requests contra registry
  -> ejecutar solo tools read-only con ReadOnlyToolExecutor
  -> provider call #2 con tool_results sanitizados
  -> respuesta final estructurada
```

El loop queda limitado a:

```text
max_tool_loop_iterations = 1
```

Si el proveedor solicita nuevas tools en la segunda llamada, My Scoope las bloquea con:

```text
tool_loop_max_iterations_reached
```

## Safety rules

Patch 54 mantiene estas fronteras:

```text
- no writes
- no creación de NutritionProposal
- no aplicación de propuestas
- no acceso a food_catalog
- no catalog_food_id
- no ejecución de tools no read-only
- no ejecución sin usuario autenticado disponible para ownership
- no más de un loop de tools por turno
```

El proveedor nunca ejecuta tools directamente. Solo solicita tools mediante JSON estructurado; My Scoope valida, ejecuta y devuelve resultados controlados.

## Tool user boundary

Para ejecutar tools reales, el orquestador requiere un usuario interno en `AssistantTurnRequest.metadata`:

```text
tool_user
user
current_user
```

Si no existe usuario interno, la tool queda bloqueada con:

```text
tool_user_required
```

La view de AI Intake puede transportar `request.user` internamente en metadata. Ese objeto no se incluye en `SafeLLMContext` ni se envía al proveedor externo.

## Provider-facing tool results

Los `tool_results` enviados al segundo llamado del proveedor pasan por sanitización provider-safe. El objetivo es permitir respuesta contextual con datos reales, sin exponer prompts, headers, secretos ni payloads crudos.

## Consequences

- El AI Assistant alcanza el hito de agente básico controlado read-only.
- El LLM puede usar resultados reales de lectura para formular la respuesta final.
- Las tools de validación y propuesta siguen bloqueadas hasta patches posteriores.
- `NutritionProposal` sigue fuera de alcance hasta Patch 55.
- La activación productiva sigue dependiendo del selector/flags y rollout posterior.

## Next step

Patch 55 debe implementar el executor de propuestas nutricionales revisables, reutilizando servicios internos y manteniendo aprobación humana.
