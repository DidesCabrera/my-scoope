# 0027 · AI Assistant audit, safety and cycle closure

Status: accepted  
Date: 2026-07-01

## Context

El ciclo Patch 41-49 introdujo una integración progresiva de LLM externo sobre el chat existente de My Scoope:

```text
Chat UI existente
  -> ChatEngine
  -> ai_assistant
  -> provider gateway
  -> contratos estructurados
  -> tool registry
  -> orquestador LLM v1
  -> proposal cards e historial
```

Antes de avanzar hacia ejecución real de tools o activación productiva del motor externo, faltaba una frontera de auditabilidad y seguridad que permitiera observar cada turno sin guardar información innecesaria del proveedor.

## Decision

Patch 49 agrega una capa de audit/safety en `ai_assistant.application.audit`.

La traza por turno queda representada por:

```text
AssistantTurnAuditSnapshot
AssistantToolAuditItem
AUDIT_SCHEMA_VERSION = ai_assistant_turn_audit.v1
```

El orquestador LLM v1 adjunta una versión sanitizada en:

```text
AssistantStructuredResponse.metadata["audit"]
AssistantStructuredResponse.metadata["audit_version"]
```

La traza incluye:

```text
- engine
- provider
- provider_model
- provider_response_id
- provider_usage si existe
- latency_ms
- tools solicitadas
- estado de tools pending/blocked/error/ok
- tools_executed
- proposal_ids reales adjuntadas por My Scoope
- requires_human_review
- safety_flags
- errores de proveedor o parsing
- conteo de proposal_ids ignorados del proveedor externo
```

La traza no incluye:

```text
- API keys
- headers
- prompts
- mensajes completos
- payloads crudos
- argumentos de tools
- raw provider response
- cookies o tokens de autorización
```

## Provider error policy

Si el proveedor externo falla antes de entregar una respuesta usable, el orquestador devuelve una respuesta segura:

```text
No pude completar este turno con el proveedor externo.
Mantendré la conversación segura y sin aplicar cambios.
```

Ese fallo se audita con código y tipo de error, pero sin persistir el mensaje crudo del proveedor. Esto evita guardar accidentalmente secretos, payloads o detalles de infraestructura.

## Safety policy

Patch 49 mantiene las reglas vigentes:

- no activa `ExternalLLMChatEngine` en la view productiva;
- no ejecuta tools;
- no crea ni aplica propuestas;
- no consulta `food_catalog`;
- no guarda prompts ni payloads crudos;
- no confía en `proposal_ids` enviados por el proveedor;
- mantiene `tools_executed=False` hasta que un dispatcher interno explícito exista.

## Consequences

- El ciclo Patch 41-49 queda cerrado con una base segura para observabilidad.
- Los futuros patches pueden activar ejecución controlada de tools con una traza común.
- La UI de `notas` puede recibir metadata de audit sin conocer detalles del proveedor.
- Los tests protegen que la traza no contenga argumentos de tools ni secretos.
