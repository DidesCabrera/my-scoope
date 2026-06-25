# My Scoope MCP User Token Auth

Este documento describe el modo transicional de autenticación por usuario para el MCP remoto de My Scoope.

## Objetivo

Permitir que una request MCP externa opere en nombre de un usuario real de My Scoope, sin depender de un usuario fijo configurado por variable de entorno.

Este modo prepara el camino hacia OAuth real.

---

## Estado anterior

Antes del user token flow, el MCP remoto operaba así:

```text
Cliente externo
→ MCP remoto
→ MYSCOOPE_API_AUTH_TOKEN
→ Django API Adapter
→ MYSCOOPE_INTERNAL_API_USERNAME
→ usuario fijo
```

Esto funcionaba para pruebas, pero no para producto multiusuario.

---

## Estado actual

Ahora existen dos modos compatibles.

### 1. Modo legacy

```text
Cliente externo
→ Authorization: Bearer MYSCOOPE_MCP_EXTERNAL_AUTH_TOKEN
→ MCP remoto
→ Authorization: Bearer MYSCOOPE_API_AUTH_TOKEN
→ Django
→ MYSCOOPE_INTERNAL_API_USERNAME
```

Uso:

```text
- Smoke tests técnicos
- Compatibilidad temporal
- Desarrollo/control interno
```

---

### 2. Modo user token

```text
Cliente externo
→ Authorization: Bearer mcp_user_xxx
→ MCP remoto
→ Authorization: Bearer mcp_user_xxx
→ Django
→ MCPUserToken
→ usuario real
```

Uso:

```text
- Pruebas multiusuario
- Preparación para OAuth
- Flujo futuro ChatGPT/App/Connector
```

---

## Modelo `MCPUserToken`

El modelo guarda tokens por usuario.

Características:

```text
- Pertenece a un usuario real.
- Guarda solo hash del token.
- El raw token solo se muestra una vez al crearlo.
- Tiene scopes.
- Puede revocarse.
- Puede expirar.
- Registra last_used_at.
```

Campos principales:

```text
user
name
token_hash
scopes
is_active
expires_at
revoked_at
last_used_at
created_at
```

---

## Scopes iniciales

Scopes definidos:

```text
myscoope:read
myscoope:proposals:create
```

### `myscoope:read`

Permite:

```text
list_food_catalog
read_dailyplan
read_proposal
list_user_proposals
compare_dailyplan_to_targets
```

### `myscoope:proposals:create`

Permite:

```text
create_validated_meal_proposal
create_validated_dailyplan_proposal
create_validated_dailyplan_build_proposal
```

---

## Tools no permitidas para IA

No se exponen al MCP remoto:

```text
apply_proposal
delete_dailyplan
update_dailyplan
raw_sql
raw_model_mutation
```

La regla de seguridad sigue siendo:

```text
La IA propone.
My Scoope valida.
El usuario revisa.
El usuario aprueba/aplica.
```

---

## Crear un token de usuario

En Django shell:

```bash
python manage.py shell
```

Ejemplo:

```python
from django.contrib.auth.models import User
from notas.application.services.mcp_user_tokens import create_mcp_user_token

user = User.objects.get(username="Felipe")

created = create_mcp_user_token(
    user=user,
    name="Remote MCP user token",
)

print(created.raw_token)
```

El token impreso se debe guardar de forma segura.

No se debe pegar en chats, commits ni logs públicos.

---

## Crear token solo lectura

```python
from django.contrib.auth.models import User
from notas.application.services.mcp_user_tokens import (
    MCP_SCOPE_READ,
    create_mcp_user_token,
)

user = User.objects.get(username="Felipe")

created = create_mcp_user_token(
    user=user,
    name="Read only MCP token",
    scopes=[MCP_SCOPE_READ],
)

print(created.raw_token)
```

---

## Crear token con lectura y creación de proposals

```python
from django.contrib.auth.models import User
from notas.application.services.mcp_user_tokens import (
    MCP_SCOPE_READ,
    MCP_SCOPE_PROPOSALS_CREATE,
    create_mcp_user_token,
)

user = User.objects.get(username="Felipe")

created = create_mcp_user_token(
    user=user,
    name="Read and proposal MCP token",
    scopes=[
        MCP_SCOPE_READ,
        MCP_SCOPE_PROPOSALS_CREATE,
    ],
)

print(created.raw_token)
```

---

## Revocar token

```python
from notas.domain.models import MCPUserToken
from notas.application.services.mcp_user_tokens import revoke_mcp_user_token

token = MCPUserToken.objects.get(id=1)

revoke_mcp_user_token(token)
```

Después de revocado:

```text
validate_mcp_user_token
→ mcp_user_token_revoked
```

---

## Validación remota con user token

Exportar token localmente:

```bash
export MYSCOOPE_REMOTE_MCP_USER_TOKEN="mcp_user_xxx"
```

Probar listado de proposals:

```bash
PYTHONPATH=mcp_server python -m myscoope_mcp.http_smoke_client \
  --url https://myscoope-mcp.onrender.com/mcp \
  --token "$MYSCOOPE_REMOTE_MCP_USER_TOKEN" \
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

## Validar catálogo

```bash
PYTHONPATH=mcp_server python -m myscoope_mcp.http_smoke_client \
  --url https://myscoope-mcp.onrender.com/mcp \
  --token "$MYSCOOPE_REMOTE_MCP_USER_TOKEN" \
  --tool list_food_catalog \
  --arguments '{"search": null, "limit": 10}'
```

Resultado esperado:

```text
ok: true
count > 0
```

El catálogo debe incluir:

```text
- foods globales;
- foods propios del usuario;
- nunca foods privados de otros usuarios.
```

---

## Validar creación de proposal

```bash
PYTHONPATH=mcp_server python -m myscoope_mcp.http_smoke_client \
  --url https://myscoope-mcp.onrender.com/mcp \
  --token "$MYSCOOPE_REMOTE_MCP_USER_TOKEN" \
  --tool create_validated_dailyplan_proposal \
  --arguments '{"dailyplan_id": 31, "title": "User token MCP - Validación remota", "summary": "Proposal creada usando MCP user token remoto para validar autenticación por usuario.", "targets": {"protein": 190, "total_kcal": 2800}, "tolerances": {"protein": 10, "total_kcal": 100}, "proposed_payload": {"intent": "auth_user_token_validation", "source": "remote_mcp_user_token_test"}}'
```

Resultado esperado:

```text
ok: true
status: pending_review
created_by_username: usuario dueño del token
```

---

## Validar legacy

El modo legacy debe seguir funcionando:

```bash
PYTHONPATH=mcp_server python -m myscoope_mcp.http_smoke_client \
  --url https://myscoope-mcp.onrender.com/mcp \
  --token "TOKEN_EXTERNO_MCP_ACTUAL" \
  --tool list_user_proposals \
  --arguments '{}'
```

Resultado esperado:

```text
ok: true
```

---

## Checklist de cierre

La auth por user token se considera válida si:

```text
[ ] Producción tiene migraciones aplicadas.
[ ] Existe MCPUserToken para usuario real.
[ ] Token raw empieza con mcp_user_.
[ ] MCP remoto acepta mcp_user_xxx.
[ ] MCP remoto reenvía mcp_user_xxx a Django.
[ ] Django resuelve usuario real desde MCPUserToken.
[ ] list_user_proposals responde ok:true.
[ ] list_food_catalog responde ok:true.
[ ] create_validated_dailyplan_proposal crea proposal pending_review.
[ ] La proposal queda creada por el usuario dueño del token.
[ ] Token sin scope create devuelve 403.
[ ] Token revocado devuelve error.
[ ] Modo legacy sigue funcionando.
```

---

## Relación con OAuth

Este flujo no reemplaza OAuth.

Es una etapa puente.

OAuth deberá resolver cómo un usuario obtiene un access token mediante:

```text
login
consentimiento
authorization code
PKCE
token endpoint
revocación
```

Pero gracias a `MCPUserToken`, My Scoope ya tiene resuelto:

```text
bearer token
→ usuario real
→ scopes
→ ownership
→ tools seguras
```

Por eso el siguiente paso natural es implementar OAuth real sobre esta base.