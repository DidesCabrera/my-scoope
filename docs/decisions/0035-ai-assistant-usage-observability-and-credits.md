# 0035 · AI Assistant usage observability and AI credits cycle

Status: accepted
Date: 2026-07-02

## Context

Patch 55 dejó implementado `ReviewableProposalToolExecutor`, permitiendo que el orquestador ejecute tools de categoría `proposal` bajo opt-in explícito y cree `NutritionProposal` revisables mediante servicios internos.

Con esa frontera ya disponible, el siguiente riesgo relevante deja de ser solo técnico y pasa a ser operacional/comercial:

```text
El LLM externo tiene costo variable por tokens.
My Scoope necesita conocer y controlar ese costo por usuario, plan y función.
```

La unidad de costo del proveedor puede ser tokens, pero la unidad comercial visible para el usuario no debe ser tokens. My Scoope debe vender y limitar una unidad propia más comprensible:

```text
créditos IA
```

## Decision

Se reevalúa el ciclo posterior a Patch 55. La activación en UI y producción no debe avanzar sin una etapa explícita de observabilidad de uso IA.

La nueva regla de arquitectura es:

```text
Antes de convertir el LLM externo en experiencia productiva amplia,
My Scoope debe registrar uso, tokens, costo estimado y action_type por turno.
```

Los tokens quedan como métrica interna. Los créditos IA quedan como futura unidad comercial.

## Commercial boundary

My Scoope no debe mostrar ni vender tokens directamente al usuario final.

Permitido internamente:

```text
tokens de input
tokens de output
tokens totales
costo estimado en USD
modelo/proveedor
action_type
```

Permitido externamente/futuro producto:

```text
créditos IA incluidos
créditos IA usados
límite mensual de asistencia IA
límite diario de asistencia IA
upgrade por mayor asistencia IA
```

No permitido como UX comercial primaria:

```text
comprar tokens
mostrar tokens como unidad de plan
hacer que el usuario entienda pricing técnico del proveedor
```

## Revised patch cycle after Patch 55

El ciclo se ajusta así:

| Patch | Objetivo | Resultado esperado |
|---:|---|---|
| 56 | Observabilidad de uso IA y costos por función. | Registrar por turno `action_type`, proveedor/modelo, usage del provider, tokens, costo estimado, status y errores seguros. Sin bloqueo comercial todavía. |
| 57 | Límites técnicos de protección. | Limitar contexto, output, historial, tool calls y requests para evitar consumo accidental excesivo. |
| 58 | Integración en chat modo preview con medición. | Probar el flujo real en la UI existente bajo staff/dev/staging o feature flag, ya midiendo uso por función. |
| 59 | Créditos IA por plan/membresía. | Materializar cuotas mensuales/diarias, ledger, cargo por turno completado y bloqueo opcional antes del provider. |
| 60 | Dashboard/admin de consumo IA. | Ver costo por usuario, función, modelo, periodo, errores y uso alto. |
| 61 | Optimización de costos por modelo y action_type. | Seleccionar modelos por función, compactar contexto, reducir tool result payloads y mejorar fallback. |
| 62 | Activación productiva gradual. | Rollout por fases con límites, créditos, observabilidad y rollback inmediato al motor determinístico. |

## Required usage fields

La implementación de observabilidad debe capturar, como mínimo:

```text
user
conversation_id
message_id / turn_id
action_type
provider
model
input_tokens
output_tokens
total_tokens
estimated_cost_usd
status
error_type
created_at
```

Si el provider no entrega usage confiable, My Scoope debe guardar valores nulos o estimados de forma explícita, sin inventar precisión.

## action_type contract

El costo debe poder analizarse por función, no solo como “chat”.

Action types iniciales recomendados:

```text
assistant.chat
assistant.tool_selection
assistant.tool_call
assistant.tool_result_summary
assistant.explain_food
assistant.explain_meal
assistant.explain_dailyplan
assistant.compare_dailyplans
assistant.create_meal_proposal
assistant.create_dailyplan_proposal
assistant.modify_program
```

La lista puede crecer, pero cada nueva función IA relevante debe declarar su `action_type` para poder medir costo y rentabilidad.

## Staging rule

Patch 58 puede activar preview real en UI solo si Patch 56 y Patch 57 ya dejaron al sistema con:

```text
registro de usage por turno
status/error seguro
límite de output
límite de contexto
límite de tool loop
fallback determinístico
```

Esto evita probar el flujo real sin trazabilidad de costos.

## Credit implementation rule

El sistema de créditos no debe implementarse antes de tener datos reales o semi-reales de consumo.

Orden correcto:

```text
1. Medir tokens/costos/action_type.
2. Proteger límites técnicos.
3. Probar preview controlado.
4. Definir conversión costo -> créditos IA.
5. Restringir por plan/membresía.
```

## Consequences

- Patch 56 ya no debe ser integración directa en UI; debe ser observabilidad de uso IA.
- La integración en UI pasa a Patch 58, después de medir y limitar.
- La activación productiva gradual se mueve a Patch 62.
- El ciclo de AI Assistant deja explícito que rentabilidad y seguridad operacional son parte de la activación del LLM externo.
- El pricing comercial se podrá decidir con datos reales de uso por función.


## Patch 56 implementation note

Patch 56 materializa esta decisión con `AIUsageEvent`, `DjangoAIUsageRecorder` y helpers de uso/costo en `ai_assistant.application.usage`. La estimación monetaria depende de pricing explícito en settings; si no hay precio configurado, el costo queda nulo.

Ver `docs/decisions/0036-ai-assistant-usage-observability-implementation.md`.


## Patch 57 implementation note

Patch 57 materializa la segunda condición de esta decisión: límites técnicos antes de preview amplio. Agrega `ai_assistant.application.limits`, settings configurables y bloqueo seguro de turnos que exceden el input estimado permitido. También limita tool requests por turno.

Ver `docs/decisions/0037-ai-assistant-technical-guardrails.md`.


## Patch 58 note

El preview operativo del chat usa `assistant.ai_nutrition_intake.preview` como función medible. Los créditos por membresía siguen pendientes para el siguiente ciclo.


## Patch 59 note

Patch 59 implementa la base de créditos IA por membresía sin exponer tokens al usuario final. La activación comercial queda detrás de settings para permitir rollout gradual.

Ver `docs/decisions/0039-ai-assistant-ai-credits-by-membership.md`.


## Patch 61 update

Después de medir uso, créditos y dashboard, el ciclo incorpora routing de modelos por `action_type`. La selección de proveedor/modelo queda en configuración y se valida por tests, mientras `AIUsageEvent` sigue registrando el provider/model efectivo de cada turno. Esta capa prepara optimización de costos sin convertir tokens en una unidad visible para usuarios.


## Patch 62 update

Patch 62 agrega rollout productivo gradual separado de créditos y separado del selector de engine. `llm_production` solo se usa si el gate `AI_ASSISTANT_LLM_ROLLOUT_*` permite el turno; en caso contrario, la experiencia vuelve al motor determinístico con metadata de fallback.

Ver `docs/decisions/0042-ai-assistant-gradual-production-rollout.md`.
