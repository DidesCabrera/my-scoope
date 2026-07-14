# 0032 · AI Assistant read-only tool executor

Status: accepted  
Date: 2026-07-01

## Context

Patch 52 dejó al `llm_preview` enviando contexto seguro al proveedor externo, pero el LLM todavía no podía usar datos reales mediante tools ejecutadas por My Scoope.

El ciclo de activación definido en `0028-ai-assistant-activation-cycle.md` indica que el siguiente paso debe ser un executor read-only antes de cualquier loop LLM+tools o creación de propuestas.

## Decision

Se agrega un executor local y explícitamente limitado a lectura:

```text
ai_assistant/application/tools/executor.py
```

El executor:

- recibe `AssistantToolRequest`;
- normaliza el nombre y argumentos;
- valida la request contra el registry controlado;
- bloquea tools desconocidas, prohibidas o con argumentos inválidos;
- bloquea cualquier tool que no sea categoría `read`;
- despacha solo tools read-only reales de `notas.application.ai_tools`;
- devuelve `AssistantToolResult` provider-agnostic;
- conserva `writes_allowed = false` en metadata.

Tools read-only conectadas inicialmente:

```text
read_dailyplan
read_proposal
list_user_proposals
search_operational_foods
list_operational_foods
```

`search_operational_foods` y `list_operational_foods` operan sobre alimentos operativos de `notas.Food`; no exponen `food_catalog` ni `catalog_food_id`.

## Consequences

Patch 53 no activa todavía el loop LLM+tools. El orquestador puede seguir validando tool requests como `pending` sin ejecutarlas automáticamente.

El nuevo executor queda listo para que Patch 54 lo componga dentro de un ciclo controlado:

```text
LLM -> tool_requests -> read-only executor -> tool_results -> LLM final answer
```

Quedan fuera de Patch 53:

- ejecución de tools de validación;
- ejecución de tools de propuesta;
- creación de `NutritionProposal`;
- writes sobre entidades productivas;
- activación productiva del LLM.

## Safety rules

- Solo se ejecutan tools de categoría `read`.
- Las tools de categoría `validation` y `proposal` se bloquean con `non_read_only_tool_blocked`.
- El executor no importa ni consulta `food_catalog`.
- El registry sigue siendo provider-agnostic; la dependencia con `notas` vive solo en el executor.
- Los resultados se normalizan como `AssistantToolResult`.
- Los límites de listados se normalizan y se acotan para evitar respuestas excesivas.
