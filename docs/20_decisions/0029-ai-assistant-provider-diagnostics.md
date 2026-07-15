# 0029 · AI Assistant provider operational diagnostics

Status: accepted
Date: 2026-07-01

## Context

Patch 50 inicia el ciclo de activación real del AI Assistant externo definido en `0028-ai-assistant-activation-cycle.md`.

Antes de seleccionar un motor LLM en la experiencia productiva o permitir ejecución real de tools, My Scoope necesita una forma segura de responder esta pregunta operacional:

```text
¿El proveedor LLM externo está configurado y puede responder?
```

Esa respuesta debe poder obtenerse sin cambiar el motor activo del chat, sin ejecutar tools, sin crear propuestas y sin exponer secretos.

## Decision

Patch 50 agrega diagnósticos operacionales en:

```text
ai_assistant.application.provider_diagnostics
ai_assistant.management.commands.diagnose_ai_assistant_llm
```

La capa expone:

```text
diagnose_llm_provider(...)
LLMProviderDiagnosticResult
python manage.py diagnose_ai_assistant_llm
python manage.py diagnose_ai_assistant_llm --live
```

Por defecto, el diagnóstico es local y no hace red:

```text
python manage.py diagnose_ai_assistant_llm
```

El chequeo live requiere opt-in explícito:

```text
python manage.py diagnose_ai_assistant_llm --live
```

El resultado informa solo metadata segura:

```text
provider
configured
client_buildable
model
base_url_configured
live_check
missing settings por nombre
status
```

No informa:

```text
API keys
headers
payloads
prompts
mensajes de usuario
raw responses
URLs completas sensibles
argumentos de tools
```

## Scope

Patch 50 no cambia la experiencia de producto:

- no conecta `ExternalLLMChatEngine` a la view productiva;
- no agrega selector de engine;
- no ejecuta tools;
- no crea `NutritionProposal`;
- no toca `food_catalog`;
- no modifica templates;
- no cambia el default determinístico.

## Live check policy

El live check usa un mensaje mínimo, genérico y sin datos del usuario:

```text
AI Assistant provider diagnostic ping. Reply with OK only.
```

El request limita tokens y marca metadata interna de diagnóstico. La metadata no se envía al proveedor según el contrato vigente del gateway.

Si el proveedor falla, el resultado queda como `provider_error` o `configuration_error`, pero no se propaga información cruda del proveedor.

## Consequences

- Render/staging/local pueden validar configuración antes de activar el LLM en UI.
- Patch 51 puede introducir selector de engine sobre una base operacional verificable.
- Los tests siguen usando `FakeLLMClient` sin red ni API keys.
- El ciclo mantiene rollback simple al motor determinístico.
