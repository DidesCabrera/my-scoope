# Launch Readiness & Operational Safety Cycle

Status: planned
Date: 2026-07-07
Cycle code: LR

## Context

My Scoope ya cerro ciclos relevantes de arquitectura y operacion interna:

```text
accounts
  -> AccountPlan, AccountSubscription, CreditWallet, CreditLedger

ai_assistant
  -> AIUsageEvent, costo estimado por tokens, guardrails tecnicos,
     router de modelo, rollout gate y consumo de creditos

admin_analytics
  -> observabilidad estrategica transversal

admin_operations
  -> workflows staff-only para Food Catalog, Accounts & Credits,
     AI Assistant y audit log
```

El estado actual permite realizar pruebas reales de planes, limites, costos y cobros
por creditos. El objetivo del siguiente ciclo ya no es crear el dominio comercial,
sino preparar el producto para operar en staging/produccion sin defaults peligrosos.

La revision inicial del export `proyecto_django_export_ai(240).zip` mostraba estos
riesgos de lanzamiento, que este ciclo LR va cerrando por patch:

```text
miapp/settings/base.py
  ALLOWED_HOSTS = ["*"]
  AUTH_PASSWORD_VALIDATORS = []
  ACCOUNT_EMAIL_VERIFICATION = "none"

miapp/settings/prod.py
  no declara todavia cookies secure, SSL redirect, HSTS,
  SECURE_PROXY_SSL_HEADER ni CSRF_TRUSTED_ORIGINS

requirements.txt
  no incluia django-ratelimit ni sentry-sdk

.github/workflows/
  no existe CI basico en el export
```

Tambien existe una regla importante para no duplicar trabajo: el ciclo ACC ya resolvio
la base comercial de planes y creditos. LR debe endurecer configuracion, limites,
operacion y verificacion, apoyandose en esas piezas existentes.

## Strategic decision

Crear un ciclo corto de Launch Readiness antes de continuar expandiendo features.

El foco es:

```text
seguridad de cuenta
seguridad tecnica de produccion
control de abuso
control de costo AI
observabilidad de errores
confianza de deploy
checklist de staging/produccion
```

No es foco de este ciclo:

```text
crear nuevos planes comerciales
integrar billing real
reestructurar apps ya cerradas
migrar a Celery/RQ
crear nuevas features de usuario final
```

## Product rule

My Scoope puede seguir probando IA real con creditos activos y pricing configurable,
pero no debe abrir produccion comercial en una combinacion peligrosa:

```text
LLM productivo activo
  + creditos desactivados
  + sin rate limiting
  + sin observabilidad de errores
```

El sistema debe poder fallar de forma controlada cuando una variable critica falte,
y debe dejar claro en docs/checks que entorno esta listo para pruebas, beta o produccion.

## Current strengths to preserve

- `accounts` ya es el propietario de planes comerciales, suscripciones, wallets y ledger.
- Los creditos son la unidad comercial; tokens y costos USD siguen siendo internos.
- `ai_assistant` ya estima costos por `input`, `cached_input` y `output`.
- El flujo AI ya puede reservar, consumir o liberar creditos contra `CreditWallet`.
- `admin_operations` ya permite revisar cuentas, creditos, reservas, eventos IA y auditoria.
- El LLM ya tiene guardrails tecnicos y rollout gate.
- Google OAuth ya recupero una experiencia fluida que no debe romperse al endurecer allauth.

## Risks to close

| Riesgo | Severidad | Cierre esperado |
|---|---:|---|
| Passwords debiles | Alta | Activar validadores de Django. |
| Email falso o no verificable | Alta | Verificacion obligatoria en prod, con SMTP real y OAuth fluido. |
| Defaults inseguros de host | Alta | Quitar `ALLOWED_HOSTS = ["*"]` de base. |
| Cookies/HTTPS/HSTS incompletos | Alta | Settings productivos seguros para Render. |
| Abuso de login/signup/AI | Alta | Rate limiting por IP/usuario en endpoints criticos. |
| Gasto AI descontrolado por config | Alta | Guard de produccion que exija creditos activos cuando LLM productivo este activo. |
| Errores invisibles en produccion | Media/Alta | Sentry o equivalente. |
| Deploy sin red de seguridad | Media/Alta | CI basico y checklist operacional. |

## Patch cycle

| Patch | Objetivo | Resultado esperado |
|---:|---|---|
| LR00 | Docs: Launch Readiness plan | Registrar ciclo, alcance, riesgos, dependencias con ACC/Admin Operations y criterios de lanzamiento. |
| LR01 | Production security settings baseline | Implementado: password validators, `ALLOWED_HOSTS` cerrado, cookies secure, SSL redirect, HSTS inicial, proxy SSL y CSRF trusted origins configurables por env. |
| LR02 | Email verification without breaking Google OAuth | Implementado: verificacion obligatoria en prod/staging cuando SMTP este configurado, preservando auto-signup/autoconnect de Google y evitando la pantalla intermedia de allauth. |
| LR03 | Rate limiting baseline | Agregar `django-ratelimit` y proteger login, signup y endpoint del AI Assistant con limites conservadores. |
| LR04 | AI credits production guard | Implementado: system check fail-closed si `llm_production` o rollout productivo esta activo sin creditos, pricing o limites tecnicos configurados. |
| LR05 | Error observability | Implementado: Sentry por env vars, con sanitizacion de prompts, secrets, headers y payloads sensibles antes de enviar eventos. |
| LR06 | CI baseline | Implementado: workflow de GitHub Actions para `python manage.py check` y `python manage.py test`, con frontera e2e/Playwright documentada. |
| LR07 | Staging/production readiness checklist | Documentar variables requeridas, smoke tests, comandos de seed/sync, rollback y criterios de beta. |

## Recommended implementation order

Aunque la tabla define el ciclo completo, el orden operativo recomendado es:

```text
LR00 -> LR01 -> LR04 -> LR03 -> LR02 -> LR05 -> LR06 -> LR07
```

Razon:

1. Primero se registra el plan y se cierra el piso de settings.
2. Luego se bloquea la combinacion mas peligrosa: LLM productivo sin creditos.
3. Despues se limita abuso directo de login/signup/AI.
4. Email verification se implementa con mas cuidado porque toca UX de allauth/Google.
5. Observabilidad y CI reducen riesgo del tramo final.
6. El checklist convierte la configuracion en una operacion repetible.

## LR00 scope

LR00 solo registra documentacion y no modifica comportamiento productivo.

Debe dejar claro:

```text
- que ACC ya cubrio planes, wallets, ledger y creditos comerciales;
- que LR no reemplaza ni duplica ACC;
- que Admin Operations es la superficie staff para operar cuentas/creditos/AI;
- que el nuevo foco es seguridad, abuso, costo global, observabilidad y deploy;
- que billing real queda fuera del alcance inmediato salvo decision comercial posterior.
```

## LR01 expected direction

Cambios esperados:

```python
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
```

Y en settings productivos:

```python
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = int(os.environ.get("SECURE_HSTS_SECONDS", "3600"))
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
CSRF_TRUSTED_ORIGINS = [...]
```

`base.py` no debe tener `ALLOWED_HOSTS = ["*"]`. Los hosts deben venir de `prod.py`,
`dev.py` o una variable de entorno explicita.

### LR01 implementation notes

El patch LR01 deja el baseline productivo sin cambiar todavia la experiencia de
login/signup:

```text
base.py
  -> elimina ALLOWED_HOSTS = ["*"]
  -> agrega helper de listas por env
  -> activa validadores estandar de password de Django

prod.py
  -> exige SECRET_KEY en produccion
  -> define ALLOWED_HOSTS desde env con defaults productivos
  -> define CSRF_TRUSTED_ORIGINS desde env o desde hosts HTTPS
  -> activa cookies secure, SSL redirect, proxy SSL header y HSTS inicial
```

`ACCOUNT_EMAIL_VERIFICATION` queda fuera de LR01 de forma intencional. Se abordara
en LR02 para preservar el flujo fluido de Google OAuth y evitar reintroducir la
pantalla intermedia de `/accounts/3rdparty/signup/`.

## LR02 expected direction

La meta no es solo activar email verification; es hacerlo sin degradar el flujo social.

Reglas:

```text
Google OAuth:
  - debe seguir usando email verificado de Google;
  - debe seguir evitando /accounts/3rdparty/signup/ cuando allauth puede resolver
    auto-signup/autoconnect de forma segura.

Signup por email/password:
  - debe requerir verificacion en staging/prod cuando SMTP real exista;
  - debe conservar una configuracion tolerante para desarrollo local.
```

### LR02 implementation notes

El patch LR02 deja la politica de verificacion de email como configuracion
operacional, no como bloqueo global:

```text
dev/base
  -> ACCOUNT_EMAIL_VERIFICATION default "none"
  -> puede sobreescribirse por ACCOUNT_EMAIL_VERIFICATION

prod/staging
  -> ACCOUNT_EMAIL_VERIFICATION default "mandatory" si EMAIL_BACKEND es SMTP
     y EMAIL_HOST esta configurado
  -> conserva default "none" si aun no existe SMTP real
  -> puede sobreescribirse por env para rollback controlado
```

Google OAuth conserva el flujo fluido porque `MyScoopeSocialAccountAdapter`
mantiene a Google como proveedor de email verificado y permite autenticacion por
email/autoconnect cuando corresponde. La intencion es endurecer signup por
email/password sin reintroducir `/accounts/3rdparty/signup/` en el login social.

## LR03 expected direction

Puntos iniciales:

```text
login
  -> limite por IP

signup
  -> limite por IP

ai assistant turn endpoint
  -> limite por usuario autenticado y fallback por IP
```

Los limites deben ser configurables por env para ajustar staging/produccion sin patch.

### LR03 implementation notes

El patch LR03 agrega `django-ratelimit` como dependencia y centraliza los limites
en `core.rate_limits`:

```text
RATE_LIMIT_LOGIN=10/m
RATE_LIMIT_SIGNUP=5/m
RATE_LIMIT_AI_ASSISTANT_TURN_USER=20/h
RATE_LIMIT_AI_ASSISTANT_TURN_IP=5/h
```

Superficies protegidas:

```text
accounts/login/
  -> limite por IP solo en POST

accounts/signup/
  -> limite por IP solo en POST

app/ai-nutrition/intake/
  -> limite solo en POST
  -> usuario autenticado por user id
  -> fallback anonimo por IP
```

Las rutas explicitas de login/signup se declaran antes de `allauth.urls` para
conservar las vistas y nombres de allauth, agregando solo el wrapper de rate limit.
GET sigue disponible para cargar formularios y pantallas.

## LR04 expected direction

Agregar una verificacion explicita que detecte configuraciones inseguras:

```text
AI_ASSISTANT_CHAT_ENGINE_MODE=llm_production
  o AI_ASSISTANT_LLM_ROLLOUT_ENABLED=true

requiere:
  AI_ASSISTANT_CREDITS_ENABLED=true
  AI_ASSISTANT_USD_PER_AI_CREDIT > 0
  planes comerciales seeded/resolubles
  limites tecnicos vigentes
```

Puede implementarse como system check de Django para que `python manage.py check`
avise o falle segun severidad.

### LR04 implementation notes

El patch LR04 agrega un system check registrado por `AiAssistantConfig.ready()`:

```text
ai_assistant.E001
  -> LLM productivo/rollout activo sin AI_ASSISTANT_CREDITS_ENABLED=true

ai_assistant.E002
  -> LLM productivo/rollout activo sin AI_ASSISTANT_USD_PER_AI_CREDIT > 0

ai_assistant.E003
  -> LLM productivo/rollout activo sin limites tecnicos positivos

ai_assistant.W001
  -> no existe al menos un plan de creditos claramente limitado
```

El check se activa cuando:

```text
AI_ASSISTANT_CHAT_ENGINE_MODE=llm_production
```

o cuando existe rollout activo:

```text
AI_ASSISTANT_LLM_ROLLOUT_ENABLED=true
AI_ASSISTANT_LLM_ROLLOUT_MODE=staff|allowlist|percentage|all
```

La intencion operacional es que `python manage.py check` y
`python manage.py check --deploy` fallen antes de abrir IA productiva si el costo
no esta cubierto por creditos, pricing y limites. El modo deterministico y el
rollout `off` siguen sin exigir esta configuracion.

## LR05 expected direction

Sentry debe capturar errores de servidor, pero no debe guardar datos sensibles de IA.

Reglas:

```text
- no prompts crudos;
- no tool payloads completos;
- no API keys;
- no headers de Authorization;
- environment separado para staging/prod;
- DSN por env var.
```

### LR05 implementation notes

El patch LR05 agrega `sentry-sdk` y una capa `core.observability` para inicializar
Sentry solo cuando `SENTRY_DSN` esta configurado:

```text
SENTRY_DSN
SENTRY_ENVIRONMENT
SENTRY_RELEASE
SENTRY_TRACES_SAMPLE_RATE
SENTRY_PROFILES_SAMPLE_RATE
```

Por defecto, `SENTRY_TRACES_SAMPLE_RATE=0.0` y
`SENTRY_PROFILES_SAMPLE_RATE=0.0`, por lo que el primer alcance es captura de
errores de servidor. Performance/profiling queda disponible por env, no activado
por accidente.

Antes de enviar eventos, `sanitize_sentry_event` filtra:

```text
Authorization / Cookie / CSRF
tokens, secrets, passwords, api keys
prompts, messages, inputs, outputs
request body/data/json/env/cookies
tool payloads y tool results
```

Se conserva metadata operacional no sensible, como URL, status y provider/modelo
cuando viajan bajo claves no secretas.

## LR06 expected direction

Crear CI minimo:

```text
python manage.py check
python manage.py test
```

El e2e puede quedar preparado como job posterior o manual si requiere servidor activo,
pero el workflow debe dejar documentada esa frontera.

### LR06 implementation notes

El patch LR06 agrega:

```text
.github/workflows/django-ci.yml
scripts/ci_django_checks.sh
```

El job principal corre en `ubuntu-latest` con Python 3.13:

```text
python -m pip install -r requirements.txt
python manage.py check
python manage.py test
```

El workflow fija:

```text
DJANGO_SETTINGS_MODULE=miapp.settings.dev
SENTRY_DSN=""
```

Esto evita que CI dependa de variables productivas o envie errores a Sentry. El
tramo e2e/Playwright queda documentado como frontera pendiente porque requiere
definir servidor activo, navegador y estado de autenticacion estable.

## LR07 expected direction

Checklist esperado:

```text
Variables:
  SECRET_KEY
  DATABASE_URL
  ALLOWED_HOSTS
  CSRF_TRUSTED_ORIGINS
  EMAIL_*
  AI_ASSISTANT_*
  SENTRY_DSN

Comandos:
  python manage.py migrate
  python manage.py seed_account_plans
  python manage.py sync_account_subscriptions
  python manage.py check --deploy

Smoke tests:
  login email/password
  login Google
  onboarding
  chat AI con consumo de creditos
  bloqueo por limite de creditos
  Admin Analytics
  Admin Operations
```

## Definition of done

El ciclo LR se considera completo cuando:

```text
- `python manage.py check --deploy` no reporta issues criticos evitables;
- staging opera con creditos AI activos y consumo visible en profile/admin;
- el endpoint AI no queda expuesto sin rate limit;
- Google OAuth sigue fluido;
- signup por email tiene verificacion real en staging/prod;
- errores de servidor llegan a observabilidad;
- existe CI basico antes de deploy;
- existe checklist de variables y smoke tests para staging/produccion.
```

## Deferred scope

Queda fuera de LR salvo decision explicita:

```text
Stripe / Mercado Pago
Celery / RQ
Redis obligatorio para cache general
autoscaling
app nativa
nuevas features de usuario final
refactors estructurales de `notas`
```

Estos temas pueden planificarse despues de una beta controlada o cuando las metricas
reales de uso indiquen el cuello de botella.
