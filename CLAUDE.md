# My Scoope

Django 6.0 monolito modular (nutrición/planes de comida). Apps: `notas` (núcleo,
grande), `food_catalog`, `ai_assistant`, `nutrition_solver`, `billing`, `admin_analytics`,
`admin_operations`, `accounts`, `core`. Settings en `miapp/settings/{base,dev,prod}.py`.

Además, `mcp_server/` (paquete `myscoope_mcp`) es un **subsistema separado e
importante**, no una app Django más: expone My Scoope a clientes MCP/IA externos
(stdio local + deployment remoto). Corre como proceso propio y habla con Django solo
por HTTP vía `MyscoopeAPIClient` — no comparte proceso, `INSTALLED_APPS` ni test
runner con el resto. Tiene su propio `requirements.txt`, `README.md`,
`REMOTE_MCP_DEPLOYMENT.md` y suite de tests en `mcp_server/tests/` que **no** corre
con `python manage.py test`. Antes de tocar algo ahí, leer `mcp_server/README.md`.

## Antes de escribir código

Leer primero, en este orden:

1. `docs/current/architecture/layers.md` — capas: domain → application → presentation → interface.
2. `docs/current/architecture/rules.md` — dirección de dependencias permitida/prohibida,
   incluye qué apps requieren el split completo y cuáles no (ver sección "Reglas de
   arquitectura" abajo).
3. `docs/current/architecture/section_creation_guide.md` y `ui_patterns.md` si se agrega una sección UI nueva.
4. `docs/current/features/<feature>/` si existe una doc de feature similar.
5. `docs/current/operations/` si el cambio toca `admin_operations` o flujos operativos/auditoría.
6. `docs/current/qa/` si el cambio toca testing, QA o criterios de aceptación.
7. `docs/decisions/` — buscar si ya existe un ADR relacionado antes de asumir algo.

`docs/archive/` es histórico: nunca usar como patrón para código nuevo.
`manual_docs/` es del desarrollador humano: nunca leer ni usar como fuente.

## Reglas de arquitectura

La separación completa en 4 capas **no es uniforme para todo el proyecto** — es por
tier de app. Ver ADR [0079](docs/decisions/0079-layer-strictness-by-app-tier.md).

**Tier 1 — split completo obligatorio (no negociable):** `notas`, `ai_assistant`,
`nutrition_solver`, `billing`. Ahí:

- `domain` no importa `application`, `presentation` ni `interface`.
- `application` no importa `presentation` ni `interface` (nada de `request`,
  `messages`, `redirect`, templates).
- `presentation` no ejecuta escrituras a la base de datos; solo arma viewmodels/contratos.
- Los comandos de escritura (crear, actualizar, borrar, aplicar propuestas) viven en
  `application/services/commands/`.
- Hay un test de arquitectura (`notas/tests/test_bounded_contexts.py`) que hace cumplir
  estas reglas automáticamente para `notas` (bounded contexts, matrices de
  dependencia). Si un cambio lo rompe, el fix es mover el código a la capa correcta,
  no debilitar el test. Este test **no cubre** `ai_assistant` ni `nutrition_solver` hoy.

**Tier 2 — patrón liviano permitido, sin split de 4 capas:** `food_catalog`,
`admin_analytics`, `admin_operations`, `accounts`, `core`. No hace falta crear
`domain`/`presentation`/`interface` ahí. Igual aplica siempre, sin excepción:

- los writes viven en un módulo de services/commands identificable, nunca inline en
  una view o en un selector de cara a template;
- el código que arma datos de lectura (selectors/viewmodels/page builders) nunca
  escribe a la base de datos;
- el código tipo "application" no depende de `request`, `messages`, `redirect` ni
  templates.

Si una app Tier 2 necesita que su lógica de escritura se reutilice desde otro entry
point (API, MCP, mobile), promoverla a Tier 1 como decisión explícita (nuevo ADR), no
agregar el split calladamente.

**Regla aparte, para el subsistema `mcp_server`:** `mcp_server/myscoope_mcp` no
importa Django ni internals de `notas` directamente.

## Comandos

```bash
python manage.py check
python manage.py test                 # suite Django (unit/integration)
pytest e2e/                           # suite e2e con Playwright (requiere server corriendo)
python manage.py makemigrations --dry-run --check   # validar antes de mover modelos
```

No hay CI configurado todavía: correr `check` + `test` localmente antes de dar por
cerrado cualquier patch.

## Flujo de trabajo por ciclos (así se hacen los cambios acá)

1. Los ciclos grandes se planifican en `docs/planning/<nombre>_cycle.md` con un
   `Status:` explícito (planned/active/paused/completed).
2. Cada decisión estable que surge del ciclo se registra como ADR nuevo en
   `docs/decisions/000N-<slug>.md`, siguiendo el estilo de los ADRs existentes
   (Context → Decision → detalles).
3. `docs/current/` se actualiza solo cuando la decisión ya es vigente, no mientras
   se está planificando.
4. Si el cambio agrega lógica reusable, agregar/actualizar tests en el mismo patch.

## IA / seguridad de dominio

`ai_assistant` no escribe directo sobre `Food`, `Meal`, `DailyPlan`, `Program` ni
`NutritionProposal`: genera propuestas revisables que se aprueban explícitamente antes
de aplicarse. No saltarse este flujo aunque parezca más directo escribir el modelo a mano.

## Gotchas

- `SECRET_KEY` sale de variable de entorno en `prod`/`dev`; nunca hardcodear ni commitear `.env`.
- `notas` es la app más grande (~79k líneas): cambios ahí requieren más cuidado y
  más probabilidad de tocar varias capas.
- El script `scripts/export_for_chatgpt.sh` genera ZIPs acotados para otras IAs sin
  acceso directo al repo — no es necesario para trabajar en esta sesión, que ya tiene
  acceso directo a los archivos.
