# My Scoope Remote MCP Deployment

Este documento describe cómo desplegar, configurar y validar el servidor MCP remoto de My Scoope.

El objetivo del MCP remoto es permitir que una IA externa pueda interactuar con My Scoope de forma segura mediante tools controladas.

## Principio de seguridad

La regla central es:

```text
La IA puede leer, validar y crear propuestas.
La IA no puede aplicar cambios directamente.
El humano revisa y aprueba.
```

Por eso el MCP remoto solo expone tools seguras:

```text
read_dailyplan
read_proposal
list_user_proposals
compare_dailyplan_to_targets
list_food_catalog
create_validated_meal_proposal
create_validated_dailyplan_proposal
create_validated_dailyplan_build_proposal
```

Y no debe exponer tools peligrosas como:

```text
apply_proposal
apply_validated_proposal
delete_dailyplan
update_dailyplan
raw_sql
raw_model_mutation
```

---

## Arquitectura

El flujo remoto esperado es:

```text
External AI / MCP Client
        ↓
My Scoope MCP Server
        ↓
Django API Adapter
        ↓
Internal AI Tools Layer
        ↓
NutritionProposal
```

El MCP server no toca la base de datos directamente.

El MCP server solo llama al API Adapter de Django usando un token interno.

## Frontera de alimentos

`list_food_catalog` es un nombre histórico de tool. En el contrato vigente lista alimentos operativos expuestos por Django desde la capa nutricional operacional. No debe leer directamente la app maestra Food Catalog ni exponer trazas internas del catálogo como IDs de alimentos para MCP.


---

## Servicios en Render

La arquitectura recomendada usa dos servicios separados en Render:

```text
Servicio 1: My Scoope Web
- Django
- Base de datos
- UI
- API Adapter interno

Servicio 2: My Scoope MCP
- MCP Streamable HTTP server
- Tools seguras
- Cliente HTTP hacia Django
```

Ambos servicios pueden apuntar al mismo repositorio de GitHub.

---

## Servicio Django

El servicio Django sigue siendo el servicio principal de la aplicación.

### Variables de entorno necesarias

En el servicio Django de Render deben existir:

```text
MYSCOOPE_INTERNAL_API_TOKEN=<token-interno>
MYSCOOPE_INTERNAL_API_USERNAME=<username-real-de-produccion>
```

### Importante

El valor de:

```text
MYSCOOPE_INTERNAL_API_TOKEN
```

debe ser exactamente igual al valor de:

```text
MYSCOOPE_API_AUTH_TOKEN
```

configurado en el servicio MCP.

Ejemplo conceptual:

```text
Servicio MCP:
MYSCOOPE_API_AUTH_TOKEN=abc123

Servicio Django:
MYSCOOPE_INTERNAL_API_TOKEN=abc123
```

El username debe corresponder a un usuario real de producción que tenga acceso a los DailyPlans y Proposals que serán leídos o creados por el MCP.

---

## Servicio MCP

El servicio MCP debe crearse como un Web Service separado en Render.

### Repositorio

Usar el mismo repositorio de My Scoope.

### Root Directory

Dejar vacío.

No usar:

```text
mcp_server
```

como root directory.

El servicio debe correr desde la raíz del proyecto para poder acceder correctamente a:

```text
requirements.txt
mcp_server/requirements.txt
mcp_server/
```

---

## Build command del servicio MCP

```bash
pip install -r requirements.txt && pip install -r mcp_server/requirements.txt
```

---

## Start command del servicio MCP

```bash
PYTHONPATH=mcp_server python -m myscoope_mcp.run_protocol_server --transport streamable-http
```

---

## Variables de entorno del servicio MCP

En el servicio MCP de Render deben existir:

```text
MYSCOOPE_MCP_TRANSPORT=streamable-http
MYSCOOPE_MCP_HOST=0.0.0.0
MYSCOOPE_MCP_PUBLIC_URL=https://myscoope-mcp.onrender.com
MYSCOOPE_MCP_EXTERNAL_AUTH_TOKEN=<token-externo-largo-y-seguro>
MYSCOOPE_API_BASE_URL=https://www.myscoope.com/app
MYSCOOPE_API_AUTH_TOKEN=<token-interno-mcp-a-django>
PYTHON_VERSION=3.13.5
```

No crear manualmente:

```text
PORT
```

Render define `PORT` automáticamente.

---

## Tokens

El sistema usa dos tokens distintos.

### 1. Token externo MCP

Variable:

```text
MYSCOOPE_MCP_EXTERNAL_AUTH_TOKEN
```

Uso:

```text
Cliente externo / IA externa → MCP Server
```

Este token permite que un cliente MCP externo entre al servidor MCP.

Debe mantenerse privado.

Si se comparte accidentalmente, debe rotarse.

---

### 2. Token interno API

Variables:

```text
MYSCOOPE_API_AUTH_TOKEN
MYSCOOPE_INTERNAL_API_TOKEN
```

Uso:

```text
MCP Server → Django API Adapter
```

Estos dos valores deben ser iguales.

El MCP envía:

```text
Authorization: Bearer <MYSCOOPE_API_AUTH_TOKEN>
```

Django valida contra:

```text
MYSCOOPE_INTERNAL_API_TOKEN
```

---

## Generar tokens seguros

Desde la terminal local:

```bash
python - <<'PY'
import secrets

print("MYSCOOPE_MCP_EXTERNAL_AUTH_TOKEN=" + secrets.token_urlsafe(48))
print("MYSCOOPE_API_AUTH_TOKEN=" + secrets.token_urlsafe(48))
PY
```

Luego:

```text
MYSCOOPE_MCP_EXTERNAL_AUTH_TOKEN
```

va solo en el servicio MCP.

```text
MYSCOOPE_API_AUTH_TOKEN
```

va en el servicio MCP.

El mismo valor de `MYSCOOPE_API_AUTH_TOKEN` debe copiarse en el servicio Django como:

```text
MYSCOOPE_INTERNAL_API_TOKEN
```

---

## Rotación de tokens

Rotar un token significa cambiarlo por uno nuevo.

Debe rotarse un token si:

```text
- Fue pegado accidentalmente en un chat.
- Fue subido a GitHub.
- Fue compartido por correo o mensaje.
- Se sospecha que pudo quedar expuesto.
```

Para rotar el token externo:

```text
Render
→ Servicio MCP
→ Environment
→ MYSCOOPE_MCP_EXTERNAL_AUTH_TOKEN
→ reemplazar por nuevo valor
→ Save and deploy
```

Para rotar el token interno:

```text
1. Generar un nuevo token.
2. Cambiar MYSCOOPE_API_AUTH_TOKEN en el servicio MCP.
3. Cambiar MYSCOOPE_INTERNAL_API_TOKEN en el servicio Django.
4. Redeploy de ambos servicios.
5. Ejecutar smoke test remoto.
```

---

## Validación local del MCP HTTP

Con Django local corriendo:

```bash
export MYSCOOPE_INTERNAL_API_TOKEN="dev-mcp-token"
export MYSCOOPE_INTERNAL_API_USERNAME="felipe"

python manage.py runserver
```

Levantar MCP local:

```bash
export MYSCOOPE_API_BASE_URL="http://127.0.0.1:8000/app"
export MYSCOOPE_API_AUTH_TOKEN="dev-mcp-token"

export MYSCOOPE_MCP_EXTERNAL_AUTH_TOKEN="external-dev-mcp-token"
export MYSCOOPE_MCP_PUBLIC_URL="http://127.0.0.1:8001"

PYTHONPATH=mcp_server python -m myscoope_mcp.run_protocol_server \
  --transport streamable-http \
  --host 127.0.0.1 \
  --port 8001
```

Probar cliente local:

```bash
PYTHONPATH=mcp_server python -m myscoope_mcp.http_smoke_client \
  --url http://127.0.0.1:8001/mcp \
  --token "external-dev-mcp-token"
```

---

## Validación remota del MCP

### 1. Probar sin token

Debe fallar.

```bash
PYTHONPATH=mcp_server python -m myscoope_mcp.http_smoke_client \
  --url https://myscoope-mcp.onrender.com/mcp \
  --token ""
```

Si no falla, el MCP remoto está expuesto incorrectamente.

---

### 2. Probar con token externo

Debe listar las tools disponibles.

```bash
PYTHONPATH=mcp_server python -m myscoope_mcp.http_smoke_client \
  --url https://myscoope-mcp.onrender.com/mcp \
  --token "TOKEN_EXTERNO_REAL"
```

Resultado esperado:

```text
Available MCP tools:
- list_user_proposals
- list_food_catalog
- read_dailyplan
- read_proposal
- compare_dailyplan_to_targets
- create_validated_meal_proposal
- create_validated_dailyplan_proposal
- create_validated_dailyplan_build_proposal
```

---

### 3. Ejecutar una tool segura

```bash
PYTHONPATH=mcp_server python -m myscoope_mcp.http_smoke_client \
  --url https://myscoope-mcp.onrender.com/mcp \
  --token "TOKEN_EXTERNO_REAL" \
  --tool list_user_proposals \
  --arguments '{}'
```

Resultado esperado:

```json
{
  "ok": true,
  "data": {
    "proposals": []
  },
  "error": null
}
```

También puede devolver proposals existentes.

---

## Flujo remoto validado

El flujo completo validado para IA externa es:

```text
read_dailyplan
compare_dailyplan_to_targets
create_validated_dailyplan_proposal
list_user_proposals
read_proposal
```

---

## Ejemplo: leer DailyPlan

```bash
PYTHONPATH=mcp_server python -m myscoope_mcp.http_smoke_client \
  --url https://myscoope-mcp.onrender.com/mcp \
  --token "TOKEN_EXTERNO_REAL" \
  --tool read_dailyplan \
  --arguments '{"dailyplan_id": DAILYPLAN_ID_REAL}'
```

---

## Ejemplo: comparar DailyPlan contra targets

```bash
PYTHONPATH=mcp_server python -m myscoope_mcp.http_smoke_client \
  --url https://myscoope-mcp.onrender.com/mcp \
  --token "TOKEN_EXTERNO_REAL" \
  --tool compare_dailyplan_to_targets \
  --arguments '{"dailyplan_id": DAILYPLAN_ID_REAL, "targets": {"protein": 190, "total_kcal": 2800}, "tolerances": {"protein": 10, "total_kcal": 100}}'
```

---

## Ejemplo: crear proposal segura

```bash
PYTHONPATH=mcp_server python -m myscoope_mcp.http_smoke_client \
  --url https://myscoope-mcp.onrender.com/mcp \
  --token "TOKEN_EXTERNO_REAL" \
  --tool create_validated_dailyplan_proposal \
  --arguments '{"dailyplan_id": DAILYPLAN_ID_REAL, "title": "Propuesta IA externa - Ajuste nutricional seguro", "summary": "Propuesta generada mediante MCP remoto simulando una IA externa. El objetivo es acercar el plan diario a los targets definidos sin aplicar cambios automáticamente.", "targets": {"protein": 190, "total_kcal": 2800}, "tolerances": {"protein": 10, "total_kcal": 100}, "proposed_payload": {"intent": "adjust_dailyplan_to_targets", "source": "external_ai_simulation", "analysis": {"goal": "Acercar el plan diario a los objetivos definidos de proteína y calorías.", "safety_boundary": "La IA solo crea una propuesta pendiente de revisión; no aplica cambios directamente.", "strategy": "Priorizar cambios nutricionales revisables, conservadores y compatibles con los targets del usuario."}, "suggested_changes": [{"type": "review_dailyplan_macros", "priority": "medium", "reason": "Revisar la diferencia entre los valores actuales del plan y los objetivos definidos antes de aprobar cambios concretos."}]}}'
```

Resultado esperado:

```json
{
  "ok": true,
  "data": {
    "proposal": {
      "status": "pending_review"
    }
  },
  "error": null
}
```

La estructura exacta puede variar, pero debe cumplir:

```text
ok: true
status: pending_review
```

---

## Ejemplo: listar proposals

```bash
PYTHONPATH=mcp_server python -m myscoope_mcp.http_smoke_client \
  --url https://myscoope-mcp.onrender.com/mcp \
  --token "TOKEN_EXTERNO_REAL" \
  --tool list_user_proposals \
  --arguments '{}'
```

---

## Ejemplo: leer proposal

```bash
PYTHONPATH=mcp_server python -m myscoope_mcp.http_smoke_client \
  --url https://myscoope-mcp.onrender.com/mcp \
  --token "TOKEN_EXTERNO_REAL" \
  --tool read_proposal \
  --arguments '{"proposal_id": PROPOSAL_ID_REAL}'
```

---

## Validación de tools prohibidas

Intentar llamar una tool peligrosa debe fallar.

Ejemplo:

```bash
PYTHONPATH=mcp_server python -m myscoope_mcp.http_smoke_client \
  --url https://myscoope-mcp.onrender.com/mcp \
  --token "TOKEN_EXTERNO_REAL" \
  --tool apply_proposal \
  --arguments '{"proposal_id": 1}'
```

Resultado esperado:

```text
Unknown tool: apply_proposal
```

Esto confirma que aunque un cliente conozca el nombre de una acción peligrosa, el MCP remoto no la expone ni la ejecuta.

---

## Tests mínimos

Para validar la superficie MCP segura:

```bash
PYTHONPATH=mcp_server python -m unittest \
mcp_server.tests.test_mcp_tool_registry
```

Para validar runtime y auth externa MCP:

```bash
PYTHONPATH=mcp_server python -m unittest \
mcp_server.tests.test_mcp_external_auth \
mcp_server.tests.test_mcp_local_runtime \
mcp_server.tests.test_mcp_protocol_server \
mcp_server.tests.test_mcp_tool_registry
```

---

## Checklist antes de conectar una IA externa real

Antes de conectar una IA externa real, confirmar:

```text
[ ] El servicio MCP está arriba en Render.
[ ] El servicio Django está arriba en Render.
[ ] MYSCOOPE_MCP_PUBLIC_URL usa la URL real del servicio MCP.
[ ] MYSCOOPE_MCP_PUBLIC_URL no contiene placeholders como <url-del-servicio-mcp>.
[ ] MYSCOOPE_MCP_HOST está configurado como 0.0.0.0 en Render.
[ ] PORT no está configurado manualmente.
[ ] MYSCOOPE_MCP_EXTERNAL_AUTH_TOKEN existe y es privado.
[ ] MYSCOOPE_API_AUTH_TOKEN existe en el servicio MCP.
[ ] MYSCOOPE_INTERNAL_API_TOKEN existe en el servicio Django.
[ ] MYSCOOPE_API_AUTH_TOKEN y MYSCOOPE_INTERNAL_API_TOKEN tienen el mismo valor.
[ ] MYSCOOPE_INTERNAL_API_USERNAME corresponde a un usuario real de producción.
[ ] El smoke client sin token falla.
[ ] El smoke client con token lista tools.
[ ] list_user_proposals responde ok:true.
[ ] read_dailyplan responde ok:true con un dailyplan real.
[ ] compare_dailyplan_to_targets responde ok:true.
[ ] create_validated_dailyplan_proposal crea una proposal pending_review.
[ ] read_proposal puede leer la proposal creada.
[ ] apply_proposal no aparece en la lista de tools.
[ ] apply_proposal falla con Unknown tool.
[ ] test_mcp_tool_registry pasa.
```

---

## Señales de error comunes

### Error: invalid international domain name

Ejemplo:

```text
Input should be a valid URL, invalid international domain name
input_value='https://<url-del-servicio-mcp>.onrender.com'
```

Causa:

```text
MYSCOOPE_MCP_PUBLIC_URL tiene un placeholder literal.
```

Solución:

```text
Reemplazar por la URL real del servicio MCP.
```

Ejemplo correcto:

```text
MYSCOOPE_MCP_PUBLIC_URL=https://myscoope-mcp.onrender.com
```

---

### Error: 401 Unauthorized desde My Scoope API

Ejemplo:

```json
{
  "ok": false,
  "error": {
    "code": "api_http_error",
    "details": {
      "status": 401,
      "reason": "Unauthorized"
    }
  }
}
```

Causa probable:

```text
MYSCOOPE_API_AUTH_TOKEN del servicio MCP no coincide con MYSCOOPE_INTERNAL_API_TOKEN del servicio Django.
```

Solución:

```text
Copiar exactamente el mismo valor en ambas variables y redeployar ambos servicios.
```

---

### Error: not_found al leer DailyPlan

Ejemplo:

```json
{
  "ok": false,
  "error": {
    "code": "not_found",
    "message": "The requested resource was not found or is not available for this user."
  }
}
```

Causas probables:

```text
- El dailyplan_id no existe en producción.
- El dailyplan_id pertenece a otro usuario.
- MYSCOOPE_INTERNAL_API_USERNAME apunta a un usuario distinto.
```

Solución:

```text
Usar un dailyplan_id real de producción perteneciente al usuario configurado.
```

---

### Error: No open ports detected

Causa probable:

```text
El servicio no está escuchando en 0.0.0.0 o no está usando PORT correctamente.
```

Validar:

```text
MYSCOOPE_MCP_HOST=0.0.0.0
No configurar PORT manualmente
Start command correcto
```

Start command esperado:

```bash
PYTHONPATH=mcp_server python -m myscoope_mcp.run_protocol_server --transport streamable-http
```

---

## Regla operativa final

El MCP remoto puede:

```text
- Leer dailyplans
- Leer proposals
- Listar proposals
- Comparar dailyplans contra targets
- Crear proposals validadas
- Consultar catálogo de foods
```

El MCP remoto no puede:

```text
- Aplicar proposals
- Borrar dailyplans
- Modificar modelos directamente
- Ejecutar SQL crudo
- Saltarse ownership de usuario
- Saltarse revisión humana
```

---

## Estado validado

Este despliegue queda considerado válido cuando:

```text
1. El MCP remoto lista tools con token externo.
2. list_user_proposals responde ok:true.
3. read_dailyplan responde ok:true con un dailyplan real.
4. compare_dailyplan_to_targets responde ok:true.
5. create_validated_dailyplan_proposal crea una proposal pending_review.
6. read_proposal lee la proposal creada.
7. apply_proposal falla con Unknown tool.
8. test_mcp_tool_registry pasa.
```

Cuando todos esos puntos están cumplidos, el sistema está listo para el siguiente paso:

```text
Conectar una IA externa compatible con MCP y probar el mismo flujo desde esa IA.
```