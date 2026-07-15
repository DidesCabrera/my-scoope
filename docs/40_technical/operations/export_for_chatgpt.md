# Export para ChatGPT / IA

Status: current
Last updated: 2026-07-14
Audience: developers and AI assistants working with exported My Scoope context

## Purpose

My Scoope usa `scripts/export_for_chatgpt.sh` para generar ZIPs optimizados para conversaciones con IA.

El objetivo del export **no** es copiar todo el repositorio cada vez. Su objetivo es entregar el contexto correcto para la tarea correcta, reduciendo ruido, archivos pesados y documentos históricos que puedan competir por atención.

La regla general es:

> Un ZIP debe ser lo suficientemente completo para entender el problema, pero lo suficientemente pequeño para que la IA priorice lo vigente.

## Ejecutar el script

El script debe ejecutarse desde la raíz real del proyecto, es decir, desde la carpeta que contiene `manage.py`.

```bash
./scripts/export_for_chatgpt.sh ai
```

Los ZIP se generan en la carpeta padre del proyecto:

```text
../proyecto_django_export_ai.zip
../proyecto_django_export_full.zip
../proyecto_django_export_planning.zip
```

Para ver los modos disponibles:

```bash
./scripts/export_for_chatgpt.sh --help
```

No ejecutar el script desde una carpeta exportada, por ejemplo `proyecto_django_export_ai/`, porque eso produciría exports recursivos o incompletos.

## Selección rápida de modo

| Modo | Usar cuando | Evitar cuando |
| --- | --- | --- |
| `planning` | La conversación es sobre estrategia, próximos ciclos, documentación o decisiones | Se necesita cambiar código productivo |
| `ai` | Desarrollo general con IA, UI, views, templates, services o refactors medianos | Se necesitan tests o datasets completos |
| `full` | El cambio toca lógica delicada, regresiones, CI o comportamiento protegido por tests | El problema es solo documental o visual menor |
| `foodcatalog` | El foco es Food Catalog, importadores, curaduría, fuentes o frontera con `notas.Food` | El cambio toca flujos no alimentarios amplios |
| `adminanalytics` | El foco es la consola estratégica interna | El cambio toca operaciones comerciales o soporte |
| `adminoperations` | El foco es backoffice operacional, usuarios, créditos, límites IA o auditoría | El cambio toca edición nutricional profunda |
| `accounts` | El foco es Account, planes, suscripciones, créditos, entitlements u onboarding | El cambio es auth puro, AI Assistant profundo o UI nutricional amplia |
| `aiassistant` | El foco es chat, tools, propuestas, usage, provider gateway, créditos IA o MCP | El cambio requiere todo el repo o solo documentación |
| `ai_behavior` | El foco es identidad, anclaje de dominio, tool governance, iniciativa, respuestas, cards, replays o UX conversacional | El cambio es infraestructura IA amplia, billing o regresión transversal |
| `auth` | El foco es login/signup, Google OAuth, allauth, rate limits, redirects o seguridad de acceso | El cambio toca reglas comerciales de Account sin auth |
| `solver` | El foco es Nutrition Solver, contratos puros, validadores o frontera nutricional | El cambio es Food Catalog profundo o UI de usuario amplia |
| `testing` | El foco es CI, regresiones, workflows, estructura de tests o salud de checks | El cambio es producto/UI sin impacto en tests |
| `usda` | El bug depende de registros reales del dataset USDA o fuentes externas | El análisis no requiere datos externos pesados |

## Relación con `docs/`

La arquitectura documental vigente usa carpetas numeradas:

```text
docs/
  00_current/
  10_active_cycles/
  20_decisions/
  30_manuals/
  40_technical/
  90_archive/
```

Los modos de export deben respetar esa jerarquía.

- `docs/00_current/` contiene la fuente vigente de producto, arquitectura, features y diseño.
- `docs/10_active_cycles/` contiene planificación oficial.
- `docs/20_decisions/` contiene decisiones aceptadas.
- `docs/40_technical/` contiene políticas de operación técnica, QA, CI, testing y export.
- `docs/90_archive/` es histórico y no debe exportarse por defecto salvo que el modo lo justifique.

El modo `planning` debe priorizar:

```text
docs/README.md
docs/00_current/
docs/10_active_cycles/
docs/20_decisions/
docs/40_technical/operations/docs_information_architecture.md
docs/40_technical/operations/export_for_chatgpt.md
```

No debe incluir `docs/90_archive/` por defecto, porque puede inducir a una IA a usar contexto superado como si fuera vigente.

## Modos actuales

### `planning`

Genera:

```text
../proyecto_django_export_planning.zip
```

Usar cuando el objetivo sea:

- ordenar próximos proyectos;
- discutir ciclos de patches;
- revisar prioridades;
- registrar decisiones;
- mejorar documentación;
- preparar trabajo antes de tocar código.

Incluye documentación oficial vigente, ciclos activos/planificados, decisiones aceptadas y contexto mínimo de Django.

No es el modo adecuado para implementar cambios de código productivo.

### `ai`

Genera:

```text
../proyecto_django_export_ai.zip
```

Es el modo general para desarrollo asistido por IA.

Excluye:

- tests;
- datasets USDA;
- imágenes/assets pesados;
- bases locales;
- ZIPs, patches y archivos temporales.

Usar para:

- templates;
- CSS;
- JavaScript;
- views;
- forms;
- urls;
- services;
- refactors generales;
- análisis de estructura;
- cambios donde no se requiere ejecutar ni leer tests.

Si un patch toca lógica crítica, límites, créditos, seguridad, propuestas, tools, CI o regresiones, preferir `full`.

### `full`

Genera:

```text
../proyecto_django_export_full.zip
```

Incluye tests y más contexto técnico.

Usar para:

- debugging complejo;
- regresiones;
- cambios en lógica de negocio;
- cambios de seguridad;
- CI;
- workflows;
- auth;
- créditos/límites/costos;
- proposals;
- tools MCP;
- refactors donde los tests expresan comportamiento esperado.

Sigue excluyendo datasets USDA e imágenes pesadas.

### `foodcatalog`

Genera:

```text
../proyecto_django_export_foodcatalog.zip
```

Es un modo focalizado para Food Catalog App.

Usar para:

- catálogo alimentario;
- importadores;
- fuentes externas;
- normalización;
- curaduría;
- aliases;
- candidatos;
- `CatalogFood`;
- snapshot operativo hacia `notas.Food`;
- frontera entre Food Catalog y Nutrition Management.

Este modo no debe arrastrar Programas, Proposals, Comparators, Inbox u otros flujos salvo que sean necesarios para proteger la frontera alimentaria.

### `adminanalytics`

Genera:

```text
../proyecto_django_export_adminanalytics.zip
```

Es un modo focalizado para la consola estratégica.

Usar para:

- dashboard estratégico;
- filtros;
- KPI cards;
- health signals;
- selectors;
- navegación interna;
- UI staff de análisis.

Si el cambio se mueve desde observación estratégica hacia acciones operacionales, usar `adminoperations`.

### `adminoperations`

Genera:

```text
../proyecto_django_export_adminoperations.zip
```

Es un modo focalizado para backoffice operacional.

Usar para:

- planes comerciales;
- suscripciones;
- créditos;
- wallets;
- reservas;
- límites IA;
- usuarios;
- auditoría;
- flujos de soporte;
- acciones operacionales sobre Food Catalog o AI Assistant.

No debe transformarse en un export de edición completa de entidades nutricionales. Para cambios profundos en Plan, DailyPlan, Meal, Food o Program, usar `full` o crear un modo focalizado nuevo.


### `accounts`

Genera:

```text
../proyecto_django_export_accounts.zip
```

Es un modo focalizado para Account como dominio comercial y de usuario.

Usar para:

- planes comerciales;
- suscripciones;
- créditos y wallets;
- reservas de créditos;
- entitlements;
- onboarding;
- perfil de cuenta;
- límites derivados de membresía;
- integración mínima con Admin Operations y AI Assistant.

Preferir `auth` cuando el problema sea estrictamente login/signup/OAuth/rate limits. Preferir `adminoperations` cuando el foco sea operar usuarios o planes desde backoffice.

### `aiassistant`

Genera:

```text
../proyecto_django_export_aiassistant.zip
```

Es un modo focalizado para AI Assistant como dominio de conversación, tools y propuestas.

Usar para:

- chat interno;
- provider gateway;
- model routing;
- prompts/context builder;
- tools read-only o reviewable;
- propuestas generadas por IA;
- usage observability;
- costos/créditos IA;
- frontera con MCP Server;
- integración mínima con Nutrition Solver.

Preferir `full` si el cambio combina AI Assistant con muchas apps de producto o si se necesita una revisión amplia de regresiones.

### `ai_behavior`

Genera:

```text
../proyecto_django_export_ai_behavior.zip
```

Es el modo focalizado para **AI Assistant Behavioral Alignment & Tool Governance**.

Usar para:

- identidad y anclaje de dominio de My Scoope;
- respuestas breves ante temas externos y retorno natural al producto;
- abstracción de capacidades sin revelar nombres internos de tools;
- cautela ante mensajes ambiguos;
- iniciativa orientada a resultados;
- calidad de respuestas posteriores a tools;
- cards, replays y validación UX con proveedor real.

Incluye el núcleo completo de `ai_assistant`, runtime `ai_intake`, AI tools, UI focalizada del chat, comandos de replay/live validation, tests conductuales y contratos mínimos con Account, Solver, Food Catalog y MCP. También incorpora dependencias directas pequeñas requeridas por esos tests, como `accounts/seed_plans.py`.

El workspace elimina intencionalmente `django.contrib.admin` y usa un URLConf mínimo. Por esa razón, los tests HTTP exclusivos del dashboard administrativo deben vivir en módulos separados y quedan fuera de `ai_behavior`; continúan cubiertos por `full`, `testing` y los modos administrativos correspondientes.

Preferir `aiassistant` cuando el foco sea infraestructura amplia del provider, créditos, ejecución de propuestas o integración MCP. Preferir `full` cuando el cambio cruce muchas apps, settings, migraciones o imports no cubiertos por la allowlist.

### `auth`

Genera:

```text
../proyecto_django_export_auth.zip
```

Es un modo focalizado para autenticación y seguridad de acceso.

Usar para:

- login;
- signup;
- Google OAuth;
- allauth/socialaccount;
- rate limits;
- redirects post-login;
- templates de autenticación;
- errores de URLConf asociados a auth;
- smoke tests de boot/auth.

Este modo existe para evitar usar `full` ante cada bug de acceso. Si el problema incluye reglas comerciales de planes/créditos, usar `accounts` o `adminoperations`.

### `solver`

Genera:

```text
../proyecto_django_export_solver.zip
```

Es un modo focalizado para Nutrition Solver.

Usar para:

- contratos nutricionales puros;
- validadores;
- portion solver;
- adapters hacia alimentos operacionales;
- cálculo de macros;
- preview tools consumidas por AI Assistant;
- frontera con Food Catalog y `notas`.

Preferir `foodcatalog` cuando el problema nazca en importadores, fuentes externas o curaduría alimentaria. Preferir `aiassistant` cuando el problema sea orquestación conversacional o tools.

### `testing`

Genera:

```text
../proyecto_django_export_testing.zip
```

Es un modo focalizado para CI, regresiones y salud de tests.

Usar para:

- workflows de GitHub Actions;
- scripts de validación;
- tests de regresión;
- estructura de tests;
- `manage.py check`;
- fallos de staging/CI;
- higiene de tests;
- cambios en documentación QA.

A diferencia de otros modos focalizados, `testing` usa una allowlist propia para poder incluir `.github/workflows`, porque los modos normales excluyen `.github/` por defecto.

### `usda`

Genera:

```text
../proyecto_django_export_usda.zip
```

Incluye `data/food_sources/`.

Usar solo cuando el problema dependa directamente de datos externos completos, por ejemplo:

- mapping de nutrientes;
- nombres crudos USDA;
- duplicados de fuente;
- errores de importación dependientes de registros reales;
- comparación de fuentes externas.

## Archivos excluidos normalmente

Los modos excluyen por defecto archivos que consumen espacio o tokens sin aportar comprensión:

```text
.git/
.github/
venv/
.venv/
env/
__pycache__/
.pytest_cache/
.mypy_cache/
.ruff_cache/
.env
.env.*
db.sqlite3
staticfiles/
media/
node_modules/
dist/
build/
*.zip
*.patch
*.orig
*.rej
*.log
tmp/
temp/
manual_docs/
```

`manual_docs/` se excluye porque contiene notas personales y no forma parte de la documentación oficial del proyecto.

## Regla para elegir entre `ai` y `full`

Usar `ai` cuando la pregunta es principalmente de lectura, diseño, UI, templates o refactor no crítico.

Usar `full` cuando la pregunta necesita confianza operacional:

- hay error de CI;
- hay traceback;
- hay bug que ya llegó a staging;
- se cambian tests;
- se cambian settings;
- se toca auth;
- se toca seguridad;
- se toca billing/créditos/límites;
- se toca AI Assistant productivo;
- se toca aplicación de propuestas;
- se toca lógica de negocio.

## Agregar un nuevo modo

Crear un modo nuevo solo cuando exista un dominio suficientemente estable y repetido.

Antes de agregarlo, responder:

1. ¿Reduce ruido frente a `ai` o `full`?
2. ¿Tiene frontera arquitectónica clara?
3. ¿Se usará más de una vez?
4. ¿Puede mantenerse sin duplicar demasiadas reglas?
5. ¿Tiene documentación vigente o ciclo activo que justifique su existencia?

Pasos mínimos:

1. Agregar el modo a `VALID_MODES` en `scripts/export_for_chatgpt.sh`.
2. Agregar el bloque `*_INCLUDES` si será allowlist.
3. Agregar el caso en `case "$MODE"`.
4. Agregar el resumen final del modo.
5. Actualizar este documento.
6. Actualizar una decisión en `docs/20_decisions/` si el modo representa una frontera estable.

## Antipatrones

Evitar:

- usar `full` por costumbre cuando basta `planning` o `ai`;
- usar `planning` para pedir implementación de código;
- incluir `90_archive/` por defecto;
- incluir `manual_docs/`;
- agregar modos nuevos para tareas de una sola vez;
- mezclar datasets externos pesados en exports normales;
- crear exports tan grandes que la IA pierda la jerarquía documental;
- ocultar tests cuando el cambio depende de comportamiento crítico.

## Regla final

El export debe ser parte de la arquitectura de colaboración con IA.

No es solo una herramienta de compresión. Es una forma de decidir qué contexto merece atención para que My Scoope pueda evolucionar con más velocidad, menos ruido y menor riesgo.

## Cycle-aware executable workspaces (EXP02)

A focused export may now declare an executable validation contract.

Use strict validation when a failed gate must prevent artifact creation:

```bash
./scripts/export_for_chatgpt.sh ai_behavior --validate
```

Use diagnostic validation when the workspace must still be shared to correct a
failure:

```bash
./scripts/export_for_chatgpt.sh ai_behavior --validate-warn
```

`--validate-warn` creates the ZIP even when tests fail, marks the result in
`EXPORT_MANIFEST.md` and includes `EXPORT_VALIDATION.log`. The default `auto`
policy behaves the same way for executable workspaces, so a broken focused
export remains inspectable. CI or release gates should keep using the explicit
strict `--validate` option.

Use `--no-validate` only when dependencies are unavailable and no executable
evidence can be collected. `EXPORT_VALIDATE=always|warn|never|auto` provides the
equivalent environment-level control.

Every generated ZIP contains `EXPORT_MANIFEST.md` with its workspace type,
purpose, fallback and validation commands. `ai_behavior` is the first fully
migrated cycle workspace; other modes keep their previous behavior until their
next architecture or cycle update.

A new development cycle should document its primary export, fallback and test
boundary before implementation patches begin.
