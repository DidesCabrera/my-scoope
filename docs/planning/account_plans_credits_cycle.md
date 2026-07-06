# Account Plans + Credits Cycle

Status: completed
Date: 2026-07-04
Cycle code: ACC

## Context

My Scoope ya cuenta con una app `accounts` que conduce responsabilidades de cuenta y onboarding, pero el dominio comercial todavía está fragmentado.

Actualmente existen tres piezas relevantes:

```text
accounts
  -> login/account/onboarding flow

notas.Plan / notas.Profile.plan
  -> rol, permisos legacy y límites básicos del usuario

ai_assistant
  -> AIUsageEvent, AIUserCreditQuota, AICreditLedger y settings de créditos IA
```

El modelo `notas.Plan` nació dentro del dominio nutricional/productivo, pero el crecimiento del producto cambia su responsabilidad. Los planes comerciales, suscripciones, créditos, límites de uso y entitlements no pertenecen naturalmente a `notas`; pertenecen al dominio de cuenta.

Además, My Scoope necesita mantener una frontera clara entre:

```text
Tokens
  -> métrica técnica interna del proveedor LLM.

Costos USD estimados
  -> métrica operacional interna para control de margen.

Créditos
  -> unidad comercial visible para usuario y planes.
```

## Strategic decision

`accounts` debe evolucionar desde una app de autenticación/onboarding hacia el dominio propietario de:

```text
AccountPlan
AccountSubscription
CreditWallet
CreditLedger
entitlements comerciales
estado de plan actual
créditos disponibles / usados / reservados
relación futura con billing
```

`notas` debe conservar el dominio nutricional/productivo:

```text
Food
Meal
DailyPlan
Program
NutritionProposal
snapshots operativos
experiencia de creación y edición nutricional
```

`ai_assistant` debe conservar la ejecución, observabilidad y auditoría de IA, pero no debe ser el dueño final del modelo comercial de planes. Su capa actual de créditos IA se considera una implementación útil y transicional que debe integrarse gradualmente con `accounts`.

## Product rule

El usuario final no debe comprar, ver ni administrar tokens como unidad principal.

Permitido internamente:

```text
input_tokens
cached_input_tokens
output_tokens
total_tokens
estimated_cost_usd
provider/model
action_type
latency/status/error
```

Permitido externamente:

```text
plan actual
créditos incluidos
créditos disponibles
créditos usados
límite diario/mensual de asistencia IA
upgrade por más capacidad
```

No permitido como UX comercial primaria:

```text
comprar tokens
mostrar tokens como unidad de plan
hacer depender la experiencia de pricing técnico del proveedor
```

## Migration principle

La migración debe ser gradual y compatible.

No se debe eliminar `notas.Plan` en la primera etapa. El objetivo es crear el nuevo dominio en paralelo, adaptar consumidores de forma progresiva y solo luego deprecatar el modelo legacy o acotarlo a compatibilidad histórica.

Regla de transición:

```text
notas.Plan
  -> legacy/current compatibility para permisos existentes.

accounts.AccountPlan
  -> plan comercial real.

accounts.AccountSubscription
  -> suscripción/estado del usuario.

accounts CreditWallet/CreditLedger
  -> saldo comercial auditable.

ai_assistant AIUsageEvent
  -> evento operacional que informa consumo real.
```

## Patch cycle

| Patch | Objetivo | Resultado esperado |
|---:|---|---|
| ACC00 | Docs: Account Plans + Credits strategy | Registrar estrategia, fronteras de dominio, relación con `notas.Plan` y migración gradual. |
| ACC01 | AccountPlan / AccountSubscription base | Crear modelos base de plan comercial y suscripción sin reemplazar todavía `notas.Plan`. |
| ACC02 | CreditWallet / CreditLedger | Crear wallet y ledger comercial append-only para créditos de cuenta. |
| ACC03 | Seed de planes comerciales | Agregar seed idempotente de planes iniciales y entitlements base. |
| ACC04 | Integración con AI Assistant: estimar/reservar créditos | Conectar preflight/reserva de créditos desde `accounts` antes de ejecutar acciones IA costosas. |
| ACC05 | Registro real de AIUsageEvent | Alinear eventos reales de IA con ledger comercial: tokens/costo siguen internos, créditos se cargan a cuenta. |
| ACC06 | Profile/Admin UI: mostrar plan y créditos | Mostrar plan y créditos al usuario/perfil y crear superficies admin para inspección operacional. |
| ACC07 | Migración gradual desde notas.Plan hacia account entitlements | Adaptar permisos/límites para leer desde `accounts`, dejando `notas.Plan` como legacy o compatibilidad. |

## ACC00 scope

ACC00 solo registra documentación. No debe cambiar modelos, migraciones ni comportamiento de producción.

Debe dejar claro:

```text
- Por qué `accounts` es el dueño correcto de planes y créditos.
- Por qué tokens no son una unidad comercial de usuario.
- Qué piezas actuales son transicionales.
- Qué ciclo de patches implementará el cambio.
- Qué riesgos deben evitarse durante la migración.
```

## ACC01 expected model direction

Modelo tentativo:

```text
AccountPlan
  slug
  name
  description
  status/is_active
  included_monthly_credits
  daily_credit_limit
  monthly_credit_limit
  entitlements JSON
  metadata JSON
  created_at / updated_at

AccountSubscription
  user
  plan
  status
  current_period_start
  current_period_end
  source
  metadata JSON
  created_at / updated_at
```

Notas:

```text
- `AccountPlan.slug` debe ser estable y no depender del nombre visible.
- `entitlements` puede partir como JSON para evitar sobrediseño prematuro.
- La relación inicial puede ser con `User`; si luego aparece un modelo Account/Organization, se migra.
- La suscripción debe poder existir aunque `notas.Profile.plan` siga activo.
```

## ACC02 expected credit direction

Modelo tentativo:

```text
CreditWallet
  user
  balance
  reserved_balance
  period
  plan_snapshot_code
  created_at / updated_at

CreditLedger
  wallet
  user
  kind: grant / reserve / consume / release / refund / adjustment / expire
  credits_delta
  balance_after
  reference_type
  reference_id
  reason
  metadata JSON
  created_at
```

Reglas iniciales:

```text
- Ledger append-only.
- No modificar movimientos históricos.
- Toda corrección debe ser un nuevo movimiento de ajuste.
- El saldo visible debe poder reconstruirse desde ledger o auditarse contra él.
- Reservas y consumos de IA deben soportar fallbacks: si una acción falla, se libera o reembolsa.
```

## ACC03 expected seed direction

Los planes iniciales deben crearse de forma idempotente mediante management command.

```bash
python manage.py seed_account_plans
python manage.py seed_account_plans --dry-run
```

El comando debe poder ejecutarse varias veces sin duplicar planes.

Los nombres comerciales finales pueden cambiar. Los slugs deben permanecer estables.

Planes semilla actuales:

```text
free
basic
pro
```

`basic` y `pro` son los códigos comerciales visibles del ciclo ACC. Los códigos legacy `member`, `nutritionist` y `default` quedan como aliases de compatibilidad hacia `basic`, `pro` y `free`, respectivamente, mientras `notas.Profile.plan` siga existiendo como fallback transicional.

Los entitlements quedan como JSON para evitar sobrediseño prematuro; ACC07 podrá mapearlos gradualmente contra permisos legacy de `notas.Plan`.

## ACC04 / ACC05 relationship with AI Assistant

La integración correcta no es reemplazar `AIUsageEvent`; es conectarlo con el nuevo ledger comercial.

Flujo deseado:

```text
1. Usuario solicita acción IA.
2. AI Assistant construye request y estima costo/créditos.
3. accounts valida plan, wallet y límites.
4. accounts reserva créditos si corresponde.
5. AI Assistant ejecuta provider/tool.
6. AIUsageEvent registra tokens/costo/status.
7. accounts consume, libera o ajusta créditos según resultado real.
```

Tokens y USD quedan como observabilidad interna de `ai_assistant`. Créditos y saldos quedan como responsabilidad comercial de `accounts`.

## ACC06 UI/Admin direction

Superficie usuario/perfil:

```text
Plan actual
Créditos disponibles
Créditos usados del periodo
Límite diario/mensual cuando aplique
Estado de renovación o periodo actual
```

Superficie admin:

```text
AccountPlan
AccountSubscription
CreditWallet
CreditLedger
relación con AIUsageEvent
usuarios con alto consumo
bloqueos por límite
ajustes manuales auditables
```

## ACC07 migration direction

La lectura de permisos y límites debe migrar por adaptadores, no por reemplazo abrupto.

Orden recomendado:

```text
1. Crear modelos nuevos en `accounts`.
2. Seedear planes comerciales.
3. Crear suscripción por defecto para usuarios existentes.
4. Crear servicio de resolución de entitlements.
5. Cambiar nuevos consumidores para leer desde `accounts`.
6. Mantener fallback a `notas.Profile.plan` durante transición.
7. Registrar decisión de deprecación cuando el fallback ya no sea necesario.
```

## Risks

| Riesgo | Mitigación |
|---|---|
| Duplicar reglas entre `notas.Plan` y `AccountPlan` | Resolver entitlements mediante un servicio único con fallback legacy explícito. |
| Mezclar tokens con créditos visibles | Mantener tokens solo en observabilidad interna y créditos como unidad comercial. |
| Romper usuarios existentes | Crear modelos paralelos y migraciones de backfill idempotentes. |
| Cobrar créditos por acciones fallidas | Separar reserva, consumo, liberación y refund en ledger. |
| Sobrediseñar billing antes de validar pricing | Partir con planes/ledger internos; billing externo queda fuera del ciclo ACC inicial. |

## Non-goals for this cycle

Este ciclo no busca implementar todavía:

```text
pagos reales
integración Stripe/MercadoPago
facturación/impuestos
multi-tenant organizations
paquetes comprables de créditos extra
pricing final público
```

Esos temas pueden apoyarse en esta base, pero pertenecen a ciclos posteriores.

## Completion criteria

El ciclo ACC se puede considerar cerrado cuando:

```text
- `accounts` tiene modelos comerciales base.
- Existen planes seed idempotentes.
- Cada usuario puede resolver su plan comercial actual.
- Existe wallet/ledger auditable.
- AI Assistant puede reservar/consumir créditos desde `accounts`.
- `AIUsageEvent` queda vinculado o correlacionable con movimientos comerciales.
- Profile/Admin muestran plan y créditos.
- `notas.Plan` queda marcado como legacy/transicional o con responsabilidad acotada.
```


## ACC04 applied note

ACC04 corrige los planes comerciales a `free`, `basic` y `pro`, mantiene aliases legacy (`member -> basic`, `nutritionist -> pro`, `default -> free`) e integra el preflight de AI Assistant con `accounts.CreditWallet`/`accounts.CreditLedger` para reservar, consumir o liberar créditos comerciales.

## ACC05 implemented direction

ACC05 cierra el ciclo real del turno IA contra el wallet comercial sin mover la
observabilidad operacional fuera de `ai_assistant`.

Regla implementada:

```text
AIUsageEvent
  -> conserva provider/model, tokens, costo estimado, status, error y action_type.

accounts.CreditWallet / CreditLedger
  -> conserva el saldo, reservas, consumos y liberaciones comerciales.

AIUsageEvent.metadata.account_credit_outcome
  -> correlaciona el evento operacional con el resultado comercial real.
```

Comportamiento esperado:

```text
completed
  -> calcula créditos reales, carga AIUserCreditQuota/AICreditLedger transicional,
     consume la reserva de accounts y registra outcome en AIUsageEvent.metadata.

error / blocked
  -> no cobra créditos reales, libera la reserva de accounts si existe y registra
     outcome en AIUsageEvent.metadata.
```

Esta etapa mantiene `AIUsageEvent` como fuente operacional de uso real y evita
que el usuario vea tokens o costos USD como unidad comercial. Los créditos
visibles siguen perteneciendo a `accounts`.


## ACC06 implemented direction

ACC06 expone la información comercial mínima en Profile y mejora la inspección
operacional desde Django Admin.

Reglas implementadas:

```text
Profile
  -> muestra plan comercial efectivo, créditos disponibles, créditos reservados,
     límites diario/mensual, estado de suscripción y periodo.

accounts.services.profile
  -> construye un resumen read-only para UI sin crear wallets solo por abrir el
     perfil. Si no existe wallet, muestra los créditos incluidos del plan como
     referencia mensual.

Django Admin
  -> AccountPlan, AccountSubscription y CreditWallet muestran campos derivados
     útiles para operar planes, suscripciones, créditos disponibles y movimientos.

CreditLedger
  -> continúa append-only y no se habilitan cambios manuales directos desde admin.
```

Esta etapa vuelve visible el nuevo dominio comercial sin eliminar todavía
`notas.Plan`. La UI distingue explícitamente `Plan legacy` de `Plan comercial`
para preparar ACC07.

## ACC07 implemented direction

ACC07 inicia la migración real de permisos desde `notas.Plan` hacia
`accounts` sin eliminar todavía el modelo legacy.

Reglas implementadas:

```text
accounts.services.entitlements
  -> resuelve permisos de producto desde AccountPlan.entitlements["nutrition_workspace"].

notas.application.services.access.capabilities
  -> mantiene la API actual (`can_publish`, `can_copy`, etc.), pero ahora prefiere
     entitlements de accounts y usa `notas.Profile.plan` solo como fallback.

accounts.services.subscriptions
  -> permite crear suscripciones account idempotentes para usuarios nuevos o
     existentes usando los aliases legacy (`member -> basic`, `nutritionist -> pro`).

sync_account_subscriptions
  -> management command para backfill gradual de usuarios existentes.
```

Comandos operativos:

```bash
python manage.py sync_account_subscriptions --dry-run
python manage.py sync_account_subscriptions
python manage.py sync_account_subscriptions --update-existing
```

`notas.Plan` queda explícitamente como compatibilidad transicional. Los
consumidores nuevos deben leer capacidades mediante el servicio de capabilities,
que ya delega en `accounts`.

## Cycle closure

Status after ACC07: completed.

El ciclo ACC deja `accounts` como fuente preferente de planes comerciales,
suscripciones, créditos, ledger y entitlements. `notas.Plan` permanece como
compatibilidad transicional y fallback explícito, pero los consumidores nuevos no
deben leerlo directamente para decisiones comerciales.

Resultado arquitectónico:

```text
accounts
  -> AccountPlan / AccountSubscription
  -> CreditWallet / CreditLedger
  -> entitlements comerciales
  -> profile/admin commercial display

ai_assistant
  -> AIUsageEvent / tokens / costos / auditoría operacional
  -> correlación con outcome comercial en accounts

notas
  -> experiencia nutricional y modelos operativos
  -> notas.Plan solo como legacy fallback
```

El dashboard estratégico futuro no debe implementarse dentro de `accounts`. Debe
vivir como app transversal (`admin_analytics` o `product_intelligence`) que lea
señales de `accounts`, `ai_assistant`, `notas`, `food_catalog` y
`nutrition_solver` sin convertir a `accounts` en coordinador global del producto.

Ver también:

- `docs/decisions/0052-account-app-enrichment-cycle-closure.md`
- `docs/planning/product_intelligence_admin_analytics_cycle.md`
