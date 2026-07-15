# 0023 · AI Assistant tool registry controlado

Status: accepted  
Date: 2026-06-30

## Context

El Patch 43 creó el gateway de proveedor LLM externo, pero sin conectarlo al chat productivo.

El Patch 44 definió contratos semánticos provider-agnostic para mensajes, intenciones, tool requests, tool results y respuestas estructuradas.

El siguiente paso del ciclo es definir qué tools podrá solicitar un futuro orquestador LLM y cuáles deben quedar explícitamente bloqueadas antes de ejecutar cualquier acción interna.

## Decision

Se crea un registry controlado en:

```text
ai_assistant/application/tools/
  contracts.py
  registry.py
```

La capa define:

```text
AssistantToolSpec
AssistantToolCategory
AssistantToolRiskLevel
AssistantToolRegistryError
```

Y una allowlist inicial de tools:

```text
read_dailyplan
read_proposal
list_user_proposals
search_operational_foods
list_operational_foods
compare_dailyplan_to_targets
create_validated_meal_proposal
create_validated_dailyplan_build_proposal
create_nutrition_engine_dailyplan_proposal
iterate_nutrition_engine_dailyplan_proposal
```

El registry es metadata y validación. No ejecuta tools todavía, no llama al proveedor externo y no cambia la UI.

## Tool policy

Cada tool queda clasificada como:

```text
read
validation
proposal
```

Y con nivel de riesgo:

```text
low
medium
review_required
```

Las tools de propuesta siempre deben requerir revisión humana.

Esto preserva la regla vigente:

```text
LLM interpreta -> registry valida -> My Scoope ejecuta servicios internos -> NutritionProposal revisable -> usuario aprueba
```

## Forbidden tools

El registry bloquea nombres de tools que implican writes directos, ejecución cruda o saltarse el flujo proposal-first, por ejemplo:

```text
apply_proposal
create_food
create_meal
create_dailyplan
update_food
update_meal
update_dailyplan
delete_food
delete_meal
delete_dailyplan
raw_sql
raw_command_execution
raw_model_mutation
```

También bloquea cualquier tool orientada a Food Catalog maestro, por ejemplo:

```text
list_food_catalog
search_food_catalog
read_catalog_food
```

## Food boundary

Para AI Assistant, las tools alimentarias permitidas se nombran explícitamente como operacionales:

```text
search_operational_foods
list_operational_foods
```

Estas tools representan el universo seguro de `notas.Food`, no `food_catalog.CatalogFood`.

El registry además bloquea requests que incluyan claves como:

```text
catalog_food_id
```

Esto evita que el LLM confunda IDs maestros con IDs operacionales.

## Consequences

- Patch 46 podrá construir el orquestador LLM v1 usando una allowlist explícita.
- El provider externo podrá recibir declaraciones mínimas de tools sin recibir flags internos de política.
- El chat actual sigue usando `DeterministicNutritionIntakeChatEngine`.
- No hay modelos nuevos ni migraciones.
- No se ejecutan tools desde la view.
- No se otorga acceso directo a `food_catalog`.
- No se habilitan writes directos sobre entidades operacionales.

## Next step

Patch 46 debe implementar el orquestador LLM v1 usando:

```text
AssistantTurnRequest
LLMClient
AssistantToolRegistry
AssistantStructuredResponse
```

El orquestador debe seguir sin aplicar cambios productivos directamente y debe mantener las operaciones relevantes como propuestas revisables.
