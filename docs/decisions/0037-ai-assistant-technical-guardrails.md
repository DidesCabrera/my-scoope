# 0037 · AI Assistant technical guardrails

Status: accepted
Date: 2026-07-02

## Context

Patch 56 agregó observabilidad de uso IA, tokens y costos estimados por turno. Antes de conectar el preview real del LLM externo a una superficie más amplia, My Scoope necesita límites técnicos que eviten consumo accidental excesivo.

Estos límites no son créditos comerciales ni restricciones por membresía. Son una barrera operacional temprana para proteger costo, latencia y seguridad de contexto mientras se recopilan datos reales de uso.

## Decision

Patch 57 agrega guardrails técnicos por turno para el `ExternalLLMOrchestrator`.

La regla queda:

```text
El orquestador debe validar tamaño de input, contexto, historial y cantidad de tool requests antes de ampliar el uso del proveedor externo.
```

## Implementación

Se agrega:

```text
ai_assistant.application.limits
```

Con helpers para:

```text
AITurnLimitConfig
AILimitViolation
estimate_text_tokens
estimate_provider_request_tokens
validate_provider_request_limits
bounded_text
```

`AssistantOrchestratorConfig` ahora puede cargar defaults desde settings y expone `turn_limits` normalizados.

## Límites iniciales

Settings nuevos:

```text
AI_ASSISTANT_MAX_HISTORY_MESSAGES=8
AI_ASSISTANT_MAX_OUTPUT_TOKENS=900
AI_ASSISTANT_MAX_TOOL_LOOP_ITERATIONS=1
AI_ASSISTANT_MAX_INPUT_TOKENS=6000
AI_ASSISTANT_MAX_CONTEXT_CHARS=8000
AI_ASSISTANT_MAX_MESSAGE_CHARS=2000
AI_ASSISTANT_MAX_TOOL_REQUESTS_PER_TURN=3
AI_ASSISTANT_ENABLE_REVIEWABLE_PROPOSAL_TOOLS=false
```

`AI_ASSISTANT_MAX_INPUT_TOKENS` usa una estimación local estable antes de llamar al proveedor. El uso real del proveedor sigue registrándose en `AIUsageEvent` cuando existe respuesta.

## Comportamiento

Si el input estimado supera el límite, el orquestador no llama al proveedor y devuelve una respuesta segura con metadata:

```text
technical_limit_blocked=true
technical_limit_error_code=ai_input_token_limit_exceeded
```

Ese turno se registra en observabilidad con `status=blocked`.

El historial enviado al proveedor se limita por cantidad de mensajes y por largo máximo de cada mensaje histórico.

Si el proveedor solicita más tools que el máximo por turno, las solicitudes excedentes se bloquean con:

```text
tool_requests_per_turn_limit_exceeded
```

El segundo provider call del tool loop también pasa por validación de límites antes de enviarse.

## MCP docs archive consistency

Durante la validación de Patch 57 se actualizan los tests documentales de MCP para apuntar a la ubicación real de esos documentos:

```text
docs/archive/mcp_stage_logs/
```

Esto preserva la decisión de archivar esos stage logs sin romper la suite MCP.

## Consequences

- Patch 57 cumple la segunda condición de la decisión 0035: proteger límites técnicos antes de ampliar preview.
- Los límites son configurables por entorno y no dependen de membresías.
- Los créditos IA siguen pendientes para Patch 59.
- Patch 58 puede conectar el preview real en UI con medición y guardrails ya activos.
