# MCP00-MCP04 · Validación del MVP MCP con Codex

Status: active
Date: 2026-10-22

## Objetivo y corte

Comprobar que una AI externa puede autenticarse como un usuario PRO, descubrir un
catálogo pequeño, leer únicamente datos autorizados y crear una propuesta
nutricional revisable mediante el MCP de My Scoope. El cliente externo aporta el
modelo; My Scoope ejecuta tools y servicios de producto.

El MVP usa staging y publica estas capacidades existentes:

- `list_food_catalog` (alimentos operacionales `notas.Food`);
- `list_user_proposals`;
- `read_proposal`;
- `create_nutrition_engine_dailyplan_proposal` (creación revisable, sin aplicar).

No se presenta a revisión pública del directorio de OpenAI durante este ciclo.
La validación privada se hace primero con una conexión MCP de Codex y un token
de usuario de corta duración. La revisión pública exige una URL estable,
credenciales de demostración y el proceso externo de OpenAI.

## Etapas y evidencia de cierre

| Etapa | Trabajo | Evidencia exigida |
| --- | --- | --- |
| MCP00 | Baseline y contrato | Servidor existente, catálogo, auth y datos staging identificados. |
| MCP01 | Acceso PRO | Entitlement en `accounts`; emisión y llamadas rechazan Free/Basic, caducidad y downgrade. |
| MCP02 | Superficie MVP | Staging descubre solo cuatro tools; no expone aplicación directa ni token técnico. |
| MCP03 | Servicio staging | URL HTTPS `/mcp`, metadata OAuth y endpoint Django conectados; deploy live y smoke. |
| MCP04 | Cliente OpenAI | Codex descubre las cuatro tools y completa lectura + propuesta revisable con usuario PRO; negativos de token/ownership. |

## Límites y validación

- `accounts.AccountSubscription` y `AccountPlan.entitlements` deciden acceso
  comercial; `billing.ProviderSubscription` es evidencia, no autoridad.
- El token identifica al usuario y limita scopes; Django reevalúa PRO en cada
  llamada. El MCP standalone no consulta ni escribe modelos Django.
- Un downgrade invalida uso posterior del token sin borrar propuestas existentes.
- Ninguna tool aplica propuestas ni llama al proveedor LLM de My Scoope.
- MCP01 toca autenticación y migración: tests enfocados durante desarrollo y gate
  Django completo una vez antes de integrar. MCP02 ejecuta además la suite MCP.
- El smoke real distingue transporte, auth, ownership y creación revisable;
  una suite local verde no prueba conectividad ni configuración de staging.

## Condición de cierre

Cerrar el ciclo solo con la llamada MCP observada desde Codex y la propuesta
visible para la cuenta de prueba en staging. Registrar por separado cualquier
gobierno externo de OpenAI que quede pendiente.
