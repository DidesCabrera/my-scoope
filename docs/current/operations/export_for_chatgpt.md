# Export para ChatGPT / IA

Este proyecto usa un sistema de exportación optimizado para compartir el código con ChatGPT u otras herramientas de IA durante revisiones, refactors y debugging.

El objetivo de estos ZIP no es contener absolutamente todos los archivos del proyecto, sino entregar una versión suficientemente completa para comprender la arquitectura, la lógica de negocio, la interfaz y los flujos principales, evitando archivos pesados o generados que consumen contexto sin aportar valor en la mayoría de los análisis.

## Modos de exportación

El script principal está ubicado en:

```bash
scripts/export_for_chatgpt.sh
```

Soporta siete modos:

```bash
./scripts/export_for_chatgpt.sh ai
./scripts/export_for_chatgpt.sh full
./scripts/export_for_chatgpt.sh usda
./scripts/export_for_chatgpt.sh foodcatalog
./scripts/export_for_chatgpt.sh planning
./scripts/export_for_chatgpt.sh adminanalytics
./scripts/export_for_chatgpt.sh adminoperations
```

Importante: el script debe ejecutarse desde la raíz real del proyecto, es decir, desde la carpeta donde existe `manage.py`. El ZIP se genera en la carpeta padre del proyecto, no dentro de la raíz del repo. Por ejemplo, al ejecutar `./scripts/export_for_chatgpt.sh usda`, el resultado esperado es `../proyecto_django_export_usda.zip`.

## Modo `ai`

Desde Patch 42, el modo `ai` debe incluir la app `ai_assistant/` porque contiene la frontera del AI Assistant y los contratos `ChatEngine` sobre el chat existente.

El modo `ai` es el modo recomendado para compartir el proyecto en la mayoría de las conversaciones de desarrollo.

Genera:

```text
../proyecto_django_export_ai.zip
```

Este modo excluye:

* archivos de entorno virtual;
* archivos generados por Python;
* cachés;
* base de datos local;
* archivos de configuración privada;
* ZIPs previos;
* patches temporales;
* imágenes;
* fuentes de datos USDA;
* tests.

Uso recomendado:

* revisión de templates;
* revisión de CSS;
* revisión de JavaScript;
* revisión de views;
* revisión de services;
* revisión de forms;
* revisión de urls;
* refactors generales;
* debugging de interfaz;
* análisis de estructura del proyecto;
* cambios en MCP, proposals, `ai_assistant` o lógica interna cuando no se requiere ejecutar tests.

## Modo `full`

El modo `full` conserva más contexto técnico que el modo `ai`.

Genera:

```text
../proyecto_django_export_full.zip
```

Este modo excluye imágenes y fuentes de datos USDA, pero mantiene los tests.

Uso recomendado:

* cambios delicados en lógica de negocio;
* validaciones;
* services críticos;
* proposals;
* tools MCP;
* importadores;
* actions;
* resolvers;
* refactors donde los tests ayudan a entender el comportamiento esperado.


## Modo `foodcatalog`

El modo `foodcatalog` es el modo recomendado para trabajar en **Food Catalog App** como sistema separado del entorno de gestión nutricional.

Genera:

```text
../proyecto_django_export_foodcatalog.zip
```

Este modo usa una allowlist: en vez de exportar todo el proyecto y excluir algunas carpetas, incluye solo las rutas necesarias para comprender y modificar el subsistema de catálogo alimentario.

Incluye principalmente:

* la app Django `food_catalog/` creada como frontera física del catálogo maestro;
* documentación vigente de Food Catalog;
* decisiones arquitectónicas relacionadas;
* historial archivado específico de food catalog;
* modelos necesarios para entender `Food`, importaciones, aliases y estados;
* servicios de importación, normalización, calidad y curaduría;
* commands de importación/exportación/promoción de alimentos;
* queries y DTOs relacionados con Food;
* interfaz actual de Foods como contrato de consumo desde Nutrition Management;
* templates, JS y viewmodels de Foods cuando ayudan a entender el contrato;
* tests y fixtures relacionados con alimentos, USDA e importadores.

Desde Patch 32, este modo debe incluir también `miapp/settings/***` para verificar el registro de la app `food_catalog` en `INSTALLED_APPS`.

Desde Patch 33, este modo debe incluir `food_catalog/application/***` y sus tests para revisar los contratos internos de candidatos, evidencia, publicación y snapshot operacional.

Desde Patch 34, este modo debe incluir `food_catalog/models.py`, `food_catalog/admin.py`, `food_catalog/migrations/***` y tests de modelos para revisar la persistencia del catálogo maestro sin abrir acceso MCP ni reemplazar `notas.Food`.

Desde Patch 35, este modo debe incluir `notas/application/services/food_catalog_snapshots.py` y la migración de trazabilidad de `notas.Food`, porque ese es el único puente interno permitido para materializar `CatalogFood` publicado como snapshot operacional.

Desde Patch 36, este modo debe incluir `food_catalog/application/imports/***` porque los adaptadores puros de fuentes, normalización, calidad y USDA pertenecen a Food Catalog. Las rutas históricas de `notas/application/services/food_imports/***` se mantienen como wrappers temporales para revisar compatibilidad.

Desde Patch 37, este modo debe incluir `food_catalog/infrastructure/imports/***` y `food_catalog/management/commands/***` para revisar los comandos catalog-first de dry-run/importación de candidatos maestros.

Desde Patch 39, este modo debe incluir `notas/application/services/commands/food_catalog_backfill.py` y `notas/management/commands/backfill_catalog_from_operational_foods.py`, porque el backfill desde `notas.Food` hacia candidatos maestros vive en `notas` por frontera arquitectónica.

Desde Patch 40, este modo debe incluir tests de frontera (`notas.tests.test_architecture_boundaries`, `notas.tests.test_domain_model_boundaries`, `notas.tests.test_food_catalog_cycle_completion`, `food_catalog.tests.test_boundary_contracts` y tests MCP relevantes) para que futuras iteraciones de Food Catalog puedan validarse sin exportar todo el proyecto.

Excluye por defecto:

* el resto de entidades no alimentarias cuando no son necesarias;
* imágenes/assets pesados;
* datasets externos completos en `data/food_sources/`;
* patches temporales, bases locales, cachés y archivos generados.

La intención es que una IA pueda leer el estado de Food Catalog App con menos ruido, sin mezclar innecesariamente Programas, Proposals, Comparators, Inbox u otros flujos del producto.

Uso recomendado:

* rediseño de Food Catalog App;
* separación entre catálogo alimentario y gestión nutricional;
* importadores de alimentos;
* normalización de fuentes;
* Food candidates;
* marcas verificadas;
* alimentos naturales verificados;
* aliases/nombres regionales;
* estados de revisión y curaduría;
* protocolo interno entre Food Catalog y `notas.Food`;
* decisión híbrida: Food Catalog como fuente maestra y `notas.Food` como snapshot operativo;
* frontera MCP: MCP solo consume alimentos operativos desde `notas.Food`, sin consultar `food_catalog`.

Si el problema depende de un registro real del dataset USDA o de una fuente externa completa, se debe adjuntar ese archivo puntual o usar el modo `usda`.


## Modo `planning`

El modo `planning` es el modo recomendado cuando el objetivo de la conversación es ordenar próximos proyectos, ciclos de patches, métricas o decisiones estratégicas antes de tocar código productivo.

Genera:

```text
../proyecto_django_export_planning.zip
```

Este modo usa una allowlist y prioriza:

* `docs/README.md`;
* `docs/current/***`;
* `docs/decisions/***`;
* `docs/planning/***`;
* `scripts/export_for_chatgpt.sh`;
* contexto mínimo del proyecto (`manage.py`, `requirements.txt`, settings/urls de `miapp`).

Excluye por diseño:

* tests;
* datasets externos;
* imágenes/assets pesados;
* base local;
* código productivo amplio no necesario para planificación.

Uso recomendado:

* planificar próximos ciclos antes de implementarlos;
* revisar prioridades entre Food Catalog, IA interna, dashboards y producto;
* preparar documentación estratégica para futuras conversaciones con IA;
* mantener una memoria oficial de planificación sin usar `manual_docs/`.

Si durante una conversación de planificación se decide implementar código, se debe cambiar a `ai`, `full` o un modo focalizado como `foodcatalog` según corresponda.


## Modo `adminanalytics`

El modo `adminanalytics` es el modo recomendado para iterar sobre **Admin Analytics / Strategic Console** sin compartir un ZIP `full`.

Genera:

```text
../proyecto_django_export_adminanalytics.zip
```

Este modo usa una allowlist y prioriza:

* la app completa `admin_analytics/`;
* el CSS propio de la consola estratégica: `notas/static/notas/css/components/admin_analytics.css`;
* documentación vigente del ciclo Admin Analytics;
* decisiones arquitectónicas relacionadas con `admin_analytics`;
* contexto mínimo de Django (`manage.py`, `requirements.txt`, settings/urls de `miapp`);
* modelos y migraciones mínimas de apps fuente que alimentan los selectors del dashboard: `accounts`, `ai_assistant`, `food_catalog`, `notas` y `nutrition_solver`;
* `scripts/export_for_chatgpt.sh` para mantener visible la regla de exportación.

Excluye por diseño:

* templates y views amplios de la experiencia nutricional de usuario;
* datasets externos;
* imágenes/assets pesados;
* base local;
* patches temporales;
* código no relacionado con la consola estratégica.

Uso recomendado:

* cambios estéticos del dashboard interno;
* ajustes del shell independiente;
* navegación interna de la consola;
* filtros compactos;
* tarjetas KPI, tablas, empty states y health signals;
* pequeños ajustes de selectors/services de `admin_analytics` cuando basta revisar modelos fuente.

Si el cambio toca lógica de negocio fuera del dashboard, modelos nuevos, settings transversales o tests integrales de varias apps, se debe usar `full`.


## Modo `adminoperations`

El modo `adminoperations` es el modo recomendado para iterar sobre **Admin Operations / Operational Console** sin compartir un ZIP `full`.

Genera:

```text
../proyecto_django_export_adminoperations.zip
```

Este modo usa una allowlist y prioriza:

* la app completa `admin_operations/`;
* sus templates, urls, views, selectors, services, viewmodels, tests y migraciones;
* la auditoría operacional `AdminOperationAuditEvent`;
* el CSS compartido de consolas staff;
* el bridge mínimo desde `admin_analytics` hacia Operations;
* la app `accounts` como dependencia principal para planes comerciales, suscripciones, wallets, reservas, ledger y entitlements;
* los servicios y tests de créditos/cuentas más relevantes;
* el contexto mínimo de `ai_assistant` para límites de uso, costos, créditos y señales operativas;
* el contexto mínimo de `food_catalog`, `notas`, `core` y `nutrition_solver` necesario para que los workflows actuales de Admin Operations sigan siendo comprensibles.

Excluye por diseño:

* templates y views amplios de edición nutricional;
* gestión editorial completa de Plans, Meals, Foods y Programs;
* datasets externos;
* imágenes/assets pesados;
* base local;
* patches temporales;
* código no relacionado con la consola operacional.

Uso recomendado:

* corregir UI o navegación de `admin_operations`;
* ajustar flujos de Food Catalog, Accounts & Credits, AI Assistant y Audit Log;
* trabajar planes comerciales, límites de créditos/costos, wallets, reservas y suscripciones;
* revisar gestión operacional de usuarios sin abrir todo el producto nutricional;
* reducir dependencia de Django Admin para operaciones comerciales y soporte.

Si el cambio requiere edición profunda de entidades nutricionales como Plan, DailyPlan, Meal, Food o Program, se debe usar `full` o crear un nuevo modo focalizado para ese dominio.

## Archivos excluidos en los modos principales

Los modos de exportación excluyen archivos que normalmente no son necesarios para entender el proyecto:

```text
.git/
.github/
.idea/
.vscode/
venv/
.venv/
env/
__pycache__/
*.pyc
*.pyo
.pytest_cache/
.mypy_cache/
.ruff_cache/
.coverage
htmlcov/
.DS_Store
__MACOSX/
.env
.env.*
db.sqlite3
*.sqlite3
*.db
staticfiles/
media/
node_modules/
dist/
build/
*.zip
*.tar
*.tar.gz
*.log
*.patch
*.bak
*.tmp
*.orig
*.rej
*.swp
*.swo
tmp/
temp/
```

## Exclusión de USDA

La fuente USDA local se excluye de los ZIP normales:

```text
data/food_sources/
```

La razón es que los archivos USDA son fuentes de datos externas, no código fuente propio de MyScoope.

Para comprender cómo funciona el proyecto normalmente basta con revisar:

* modelos;
* services;
* commands;
* mappers;
* normalizadores;
* tests;
* documentación;
* templates;
* views;
* forms;
* urls.

Es decir, para entender MyScoope es más importante ver cómo el sistema importa, limpia, transforma, guarda, busca y presenta los alimentos que revisar todos los registros completos del dataset USDA.

USDA debe compartirse solo cuando el problema esté directamente relacionado con:

* alimentos específicos del dataset;
* nombres crudos de USDA;
* nutrientes específicos;
* errores de mapping;
* depuración de importación;
* comparación de fuentes alimentarias;
* duplicados provenientes de datos externos.

## Exclusión de imágenes

Las imágenes también se excluyen de los ZIP normales:

```text
static/img/
notas/static/notas/img/
*.jpg
*.jpeg
*.png
*.webp
*.gif
*.ico
*.svg
```

Esto permite reducir significativamente el tamaño del ZIP sin afectar la comprensión del código.

Para revisar HTML, CSS o templates normalmente basta con conservar las rutas a los assets. No es necesario incluir cada imagen real dentro del ZIP.

Si el problema es visual, se recomienda compartir:

* el ZIP `ai`;
* una captura de pantalla;
* o la imagen puntual involucrada.

## Tests

El modo `ai` excluye tests para reducir tamaño y ruido cuando el análisis es principalmente de código, UI o estructura.

El modo `full` mantiene tests para casos donde el comportamiento esperado del sistema es importante.

El modo `usda` mantiene tests e incluye `data/food_sources/`. Debe usarse solo cuando el problema dependa directamente de datos USDA.

El modo `foodcatalog` mantiene solo el contexto necesario para Food Catalog App y excluye datasets externos completos para evitar ruido, salvo fixtures pequeñas de tests.

Regla práctica:

```text
ai         → uso normal
full       → cuando los tests importan
usda       → cuando el dataset USDA completo es parte directa del problema
foodcatalog→ cuando el trabajo se concentra en Food Catalog App
planning  → cuando el trabajo se concentra en planificación/documentación estratégica
adminanalytics → cuando el trabajo se concentra en consola estratégica
adminoperations → cuando el trabajo se concentra en consola operacional, cuentas, créditos y planes comerciales
```

## Recomendación de uso

Para trabajo cotidiano con ChatGPT:

```bash
./scripts/export_for_chatgpt.sh ai
```

Para revisiones delicadas o cambios que deberían validarse con tests:

```bash
./scripts/export_for_chatgpt.sh full
```

Para trabajo focalizado en Food Catalog App, planificación o consolas internas:

```bash
./scripts/export_for_chatgpt.sh foodcatalog
./scripts/export_for_chatgpt.sh planning
./scripts/export_for_chatgpt.sh adminanalytics
./scripts/export_for_chatgpt.sh adminoperations
```

Si el problema está relacionado específicamente con USDA, imágenes o archivos excluidos, se debe compartir ese archivo puntual además del ZIP.

## Nota sobre PWA startup images

Las imágenes de arranque de la PWA para iOS/iPadOS no deben guardarse como bloques base64 dentro de archivos Python. Ese patrón aumenta artificialmente el tamaño de los ZIP y dificulta las revisiones de IA.

La app conserva las mismas rutas y dimensiones declaradas en `apple-touch-startup-image`, pero genera los PNG de startup de forma dinámica desde `notas/interface/views/pwa_startup_images.py` usando solo la librería estándar de Python. Así se mantiene la compatibilidad de la PWA sin incluir binarios pesados ni texto base64 extenso en los exports.

Si más adelante se necesita revisar un problema visual específico del splash, conviene compartir una captura de pantalla del dispositivo y no incluir todos los PNG generados en el ZIP.

## `manual_docs/`

La carpeta `manual_docs/` es de uso personal del desarrollador humano y no forma parte de la documentación oficial del proyecto.

Por esta razón, el script de exportación la excluye. Una IA debe basarse en `docs/`, especialmente `docs/current/` y `docs/decisions/`.

## Food Catalog / MCP boundary note

Desde Patch 38, el modo `foodcatalog` debe seguir incluyendo `mcp_server/***` cuando se revisen fronteras de IA/MCP, porque la regla ejecutable es que MCP no importe ni exponga Food Catalog maestro. El nombre histórico `list_food_catalog` debe interpretarse como lectura operacional de `notas.Food`.


## Patch 41 · Ciclo AI Assistant / External LLM

Para el ciclo de integración LLM sobre el chat existente, el modo `ai` sigue siendo el export recomendado porque incluye la estructura de chat, views, templates, aplicación y documentación vigente sin tests pesados ni datasets externos.

Antes de generar patches de este ciclo, revisar especialmente:

```text
docs/decisions/0019-external-llm-over-existing-chat.md
docs/current/features/ai_assistant/README.md
docs/current/features/ai_nutrition_onboarding/ai_nutrition_onboarding.md
notas/application/ai_intake/
notas/interface/views/ai_intake.py
notas/templates/notas/ai_intake.html
notas/templates/notas/_ai_chat_thread.html
notas/templates/notas/ai_chats/list.html
```

Si un patch toca contratos de tools, fronteras con Food Catalog o MCP, usar `full` o adjuntar tests relevantes para validar las guardas.

## Planning Docs

Desde Patch 63, `docs/planning/` es parte de la documentación oficial para ciclos futuros. El modo `planning` debe incluir esta carpeta completa para conservar planes como Product Intelligence & Admin Analytics, futuros ciclos de Food Catalog y mejoras de integración IA interna.
