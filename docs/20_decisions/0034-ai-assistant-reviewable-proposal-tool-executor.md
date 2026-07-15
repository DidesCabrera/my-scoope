# 0034 · AI Assistant reviewable proposal tool executor

## Status

Accepted · Patch 55

## Context

Patch 54 dejó operativo el loop `LLM -> read-only tools -> LLM final answer`. El siguiente paso del ciclo de activación productiva es permitir que el LLM externo solicite la creación de propuestas nutricionales reales, pero sin permitir writes directos ni aplicación automática de cambios.

My Scoope ya tiene servicios internos para crear `NutritionProposal` revisables. La integración segura debe reutilizar esos servicios y mantener la misma frontera de revisión humana que el resto del sistema.

## Decision

Se agrega `ReviewableProposalToolExecutor` en:

```text
ai_assistant/application/tools/proposal_executor.py
```

El executor acepta únicamente tools de categoría `proposal` declaradas en el registry controlado:

```text
create_validated_meal_proposal
create_validated_dailyplan_build_proposal
create_nutrition_engine_dailyplan_proposal
iterate_nutrition_engine_dailyplan_proposal
```

Estas tools pueden crear registros `NutritionProposal` revisables mediante servicios internos de My Scoope, pero no pueden aplicar propuestas, crear entidades finales directamente ni modificar modelos fuera del flujo de propuestas.

## Orchestrator opt-in

`ExternalLLMOrchestrator` recibe una nueva configuración:

```python
AssistantOrchestratorConfig(enable_reviewable_proposal_tools=False)
```

El default es `False`.

Con el default, si el proveedor solicita una tool de propuesta, el resultado queda bloqueado con:

```text
reviewable_proposal_tools_disabled
```

Con opt-in explícito, el orquestador puede ejecutar la tool mediante `ReviewableProposalToolExecutor`, adjuntar los `proposal_ids` creados y enviar un segundo turno al proveedor con `tool_results` sanitizados.

## Safety boundaries

Patch 55 mantiene estas garantías:

- El proveedor externo no recibe API keys, headers, sesión cruda ni payloads privados.
- El proveedor no puede inventar `proposal_ids`; los IDs del provider siguen siendo ignorados.
- Solo los `proposal_ids` retornados por tools internas de My Scoope se adjuntan al response.
- Toda propuesta creada exige revisión humana.
- Ninguna tool aplica cambios al DailyPlan, Meal, Food o Program.
- `food_catalog` y `catalog_food_id` siguen prohibidos en argumentos.
- La UI existente todavía no queda activada para producción; esa integración corresponde al Patch 56.

## Consequences

- Patch 55 crea la primera frontera controlada para propuestas reales desde LLM.
- El modo productivo sigue protegido porque el opt-in no está conectado automáticamente al chat actual.
- Patch 56 podrá habilitar el flujo en modo preview/staff/dev usando esta capacidad sin rediseñar el executor.
