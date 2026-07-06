# 0021 · LLM provider gateway

Status: accepted  
Date: 2026-06-30

## Context

El Patch 41 definió que el LLM externo debe vivir sobre el chat existente de My Scoope y operar solo mediante contratos controlados.

El Patch 42 creó la app Django `ai_assistant` y el contrato `ChatEngine`, manteniendo como motor activo el flujo determinístico actual de AI Intake.

El siguiente paso del ciclo es preparar la conexión con un proveedor externo sin conectar todavía ese proveedor al chat productivo.

## Decision

Se crea una capa de proveedor LLM desacoplada dentro de `ai_assistant`:

```text
ai_assistant/infrastructure/providers/contracts.py
ai_assistant/infrastructure/providers/fake_client.py
ai_assistant/infrastructure/providers/openai_client.py
ai_assistant/infrastructure/providers/factory.py
```

La capa expone contratos mínimos de transporte:

```text
LLMMessage
LLMProviderRequest
LLMProviderResponse
LLMClient
```

Estos contratos no representan todavía intención, tools ni respuestas estructuradas del asistente. Esa definición queda para Patch 44.

## Provider policy

El gateway soporta dos proveedores iniciales:

```text
fake  = proveedor determinístico local para tests y desarrollo sin red
openai = gateway HTTP hacia OpenAI Responses API
```

El proveedor activo se resuelve mediante:

```text
AI_ASSISTANT_LLM_PROVIDER=fake|openai
```

La configuración de OpenAI queda detrás de settings/env vars:

```text
AI_ASSISTANT_OPENAI_API_KEY
AI_ASSISTANT_OPENAI_MODEL
AI_ASSISTANT_OPENAI_BASE_URL
AI_ASSISTANT_OPENAI_TIMEOUT_SECONDS
```

Si falta configuración obligatoria, el gateway falla con `LLMProviderConfigurationError` y no intenta llamar al proveedor.

## Hard rules preserved

El gateway de Patch 43:

- no se conecta todavía al chat productivo;
- no crea modelos persistentes;
- no importa ni accede a `food_catalog`;
- no escribe `Food`, `Meal`, `DailyPlan`, `Program` ni `NutritionProposal`;
- no aplica propuestas;
- no reenvía metadata interna de My Scoope al proveedor externo;
- no guarda API keys ni payloads en base de datos.

## OpenAI gateway behavior

El adapter `OpenAIResponsesClient` usa una llamada HTTP explícita para mantener bajo control el payload enviado al proveedor.

Payload mínimo esperado:

```text
model
input
store=false
max_output_tokens opcional
```

La metadata interna de `LLMProviderRequest` permanece local y no se incluye en el payload enviado al proveedor.

## Fake client behavior

`FakeLLMClient` permite:

- respuestas scriptadas;
- respuesta determinística por defecto;
- registro de requests normalizados;
- tests sin API key, internet ni costo de tokens.

Esto permite construir Patch 44-46 con pruebas confiables antes de activar cualquier proveedor real.

## Consequences

- La integración externa queda encapsulada detrás de una frontera reemplazable.
- El chat actual sigue usando `DeterministicNutritionIntakeChatEngine`.
- El orquestador futuro podrá depender de `LLMClient` sin conocer detalles de OpenAI.
- La configuración productiva puede mantenerse desactivada usando `AI_ASSISTANT_LLM_PROVIDER=fake`.
- La conexión real queda preparada pero no se ejecuta salvo que un futuro patch la consuma explícitamente.

## Next step

Patch 44 debe definir contratos estructurados de intención, mensajes, tool requests, tool results y respuesta final del asistente.
