# Export para ChatGPT / IA

Este proyecto usa un sistema de exportación optimizado para compartir el código con ChatGPT u otras herramientas de IA durante revisiones, refactors y debugging.

El objetivo de estos ZIP no es contener absolutamente todos los archivos del proyecto, sino entregar una versión suficientemente completa para comprender la arquitectura, la lógica de negocio, la interfaz y los flujos principales, evitando archivos pesados o generados que consumen contexto sin aportar valor en la mayoría de los análisis.

## Modos de exportación

El script principal está ubicado en:

```bash
scripts/export_for_chatgpt.sh
```

Soporta cuatro modos:

```bash
./scripts/export_for_chatgpt.sh ai
./scripts/export_for_chatgpt.sh full
./scripts/export_for_chatgpt.sh usda
./scripts/export_for_chatgpt.sh foodcatalog
```

Importante: el script debe ejecutarse desde la raíz real del proyecto, es decir, desde la carpeta donde existe `manage.py`. El ZIP se genera en la carpeta padre del proyecto, no dentro de la raíz del repo. Por ejemplo, al ejecutar `./scripts/export_for_chatgpt.sh usda`, el resultado esperado es `../proyecto_django_export_usda.zip`.

## Modo `ai`

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
* cambios en MCP, proposals o lógica interna cuando no se requiere ejecutar tests.

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
* contrato entre Food Catalog y Meals/DailyPlans/Programs.

Si el problema depende de un registro real del dataset USDA o de una fuente externa completa, se debe adjuntar ese archivo puntual o usar el modo `usda`.

## Archivos excluidos en ambos modos

Ambos modos excluyen archivos que normalmente no son necesarios para entender el proyecto:

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

Para trabajo focalizado en Food Catalog App:

```bash
./scripts/export_for_chatgpt.sh foodcatalog
```

Si el problema está relacionado específicamente con USDA, imágenes o archivos excluidos, se debe compartir ese archivo puntual además del ZIP.

## Nota sobre PWA startup images

Las imágenes de arranque de la PWA para iOS/iPadOS no deben guardarse como bloques base64 dentro de archivos Python. Ese patrón aumenta artificialmente el tamaño de los ZIP y dificulta las revisiones de IA.

La app conserva las mismas rutas y dimensiones declaradas en `apple-touch-startup-image`, pero genera los PNG de startup de forma dinámica desde `notas/interface/views/pwa_startup_images.py` usando solo la librería estándar de Python. Así se mantiene la compatibilidad de la PWA sin incluir binarios pesados ni texto base64 extenso en los exports.

Si más adelante se necesita revisar un problema visual específico del splash, conviene compartir una captura de pantalla del dispositivo y no incluir todos los PNG generados en el ZIP.

## `manual_docs/`

La carpeta `manual_docs/` es de uso personal del desarrollador humano y no forma parte de la documentación oficial del proyecto.

Por esta razón, el script de exportación la excluye. Una IA debe basarse en `docs/`, especialmente `docs/current/` y `docs/decisions/`.
