# 0042 · AI Assistant gradual production rollout

Status: accepted
Date: 2026-07-02

## Context

Patch 56-61 dejaron al AI Assistant externo con observabilidad de uso, límites técnicos, preview medible, créditos IA, dashboard/admin y routing de modelo por `action_type`.

El siguiente riesgo ya no es solo técnico. El riesgo es operacional:

```text
habilitar el LLM externo para demasiados usuarios, demasiado rápido,
sin una forma simple de controlar alcance y volver al motor determinístico.
```

My Scoope necesita una activación productiva gradual que mantenga la UI existente, use los guardrails ya creados y permita rollback inmediato.

## Decision

Patch 62 introduce un gate de rollout productivo separado del selector de engine.

Para que el modo productivo use LLM deben cumplirse dos condiciones:

```text
AI_ASSISTANT_CHAT_ENGINE_MODE=llm_production
AI_ASSISTANT_LLM_ROLLOUT_ENABLED=true
```

Además, el usuario debe pasar la política configurada en:

```text
AI_ASSISTANT_LLM_ROLLOUT_MODE
```

Modos soportados:

| Mode | Comportamiento |
|---|---|
| `off` | Nadie usa LLM productivo. |
| `staff` | Solo usuarios staff. |
| `allowlist` | Solo `user_id` explícitamente permitidos. |
| `percentage` | Rollout sticky por bucket de usuario. |
| `all` | Todos los usuarios pasan el gate. |

Si el gate no permite el turno, el chat vuelve al motor determinístico y deja metadata de fallback/rollout.

## Implementation

Se agrega:

```text
ai_assistant/application/rollout.py
```

Con:

```text
AIRolloutDecision
resolve_ai_llm_rollout
stable_user_bucket
```

Se agrega el engine:

```text
LLMProductionNutritionIntakeChatEngine
```

El modo productivo usa el mismo chat de AI Nutrition Intake. No introduce una UI paralela.

## Settings

```python
AI_ASSISTANT_LLM_ROLLOUT_ENABLED = False
AI_ASSISTANT_LLM_ROLLOUT_MODE = "off"
AI_ASSISTANT_LLM_ROLLOUT_USER_IDS = ""
AI_ASSISTANT_LLM_ROLLOUT_PERCENT = 0
AI_ASSISTANT_LLM_ROLLOUT_STICKY_SALT = "ai-assistant-rollout-v1"
```

El default sigue siendo seguro: `deterministic`.

## Operational rollout recommendation

Orden recomendado:

```text
1. deterministic
2. llm_preview en staging/staff
3. llm_production + rollout staff
4. llm_production + allowlist de usuarios internos
5. llm_production + percentage bajo
6. llm_production + all solo cuando métricas y costos sean aceptables
```

## Consequences

- El modo productivo se puede activar sin cambiar templates.
- El rollback inmediato es volver a `AI_ASSISTANT_CHAT_ENGINE_MODE=deterministic` o `AI_ASSISTANT_LLM_ROLLOUT_ENABLED=false`.
- El rollout es independiente de créditos: créditos controlan consumo comercial; rollout controla alcance productivo.
- La observabilidad sigue usando `action_type`, ahora con `assistant.ai_nutrition_intake.production`.
- El gateway LLM recibe metadata segura de `action_type`, conversación y turno para que routing, usage y dashboard sean coherentes.

## Non-goals

Patch 62 no define precios finales, no cambia planes comerciales visibles y no aplica automáticamente propuestas. La aprobación humana sigue siendo obligatoria.
