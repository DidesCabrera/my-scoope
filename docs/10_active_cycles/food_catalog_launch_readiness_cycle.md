# Food Catalog Launch Readiness Cycle

Status: completed
Date: 2026-07-02
Closed: 2026-07-02


## Cierre del ciclo

El ciclo Food Catalog Launch Readiness queda cerrado después de los patches FC-01, FC-02, FC-03, FC-04, FC-05, FC-06, FC-07, FC-08, FC-09, FC-11 y FC-10.

La numeración no fue ejecutada estrictamente en orden: FC-11 se priorizó antes de FC-10 porque el bridge `solver-ready` era más fundacional para abrir el siguiente ciclo de separación de `nutrition_solver`.

El alcance implementado deja a Food Catalog en un estado suficientemente maduro para operar como fuente maestra curada y para alimentar indirectamente al futuro solver mediante `notas.Food`:

- publicación y curación protegidas por workflow;
- seed natural inicial trazable e idempotente;
- normalización semántica mínima y metadata `solver-ready`;
- proveedores externos lookup-only: FatSecret y Open Food Facts;
- referencias externas temporales y logs de fetch sin persistir payload nutricional completo;
- búsqueda unificada propia + externa;
- cola de candidatos de curación;
- bridge operacional de candidatos para solver desde `notas.Food`;
- intake mínimo de productos de marca mediante CSV autorizado.

FC-12, referido a eventos y métricas para dashboard, se difiere fuera de este ciclo. Esa instrumentación debe diseñarse dentro del proyecto transversal `Product Intelligence / Admin Analytics`, porque debe medir Food Catalog, Nutrition Solver, AI Assistant, costos, propuestas y uso real del producto de forma unificada.

## Decisión de traspaso a Nutrition Solver

Con el cierre de este ciclo, el proyecto queda habilitado para iniciar la separación progresiva de `nutrition_solver` desde `notas/application/nutrition_engine`.

La razón es que ya existe una frontera operacional suficientemente segura para el solver:

```text
Food Catalog cura y publica CatalogFood
  -> snapshot explícito materializa notas.Food
  -> notas.Food expone candidatos solver-ready
  -> nutrition_solver puede optimizar sin depender de CatalogFood ni proveedores externos
```

El siguiente ciclo debe preservar esta regla: `nutrition_solver` consume contratos derivados de `notas.Food` operacional, no `CatalogFood`, `ExternalFoodReference`, FatSecret ni Open Food Facts directamente.

## Contexto

My Scoope ya cuenta con una app Django real para Food Catalog:

```text
food_catalog/
```

El ciclo Patch 32-40 separó Food Catalog como fuente maestra interna sin reemplazar `notas.Food` como verdad nutricional operacional.

El estado actual no debe interpretarse como un catálogo de producto completamente listo para lanzamiento. La app ya tiene una fundación técnica fuerte, pero todavía falta convertirla en una capacidad operacional sólida para construir, curar, publicar y ampliar datos alimentarios confiables.

## Estado real de partida

### Lo que ya existe

Food Catalog ya cuenta con:

- app Django física registrada en `INSTALLED_APPS`;
- modelos maestros iniciales:
  - `CatalogFood`;
  - `CatalogFoodPortion`;
  - `CatalogFoodAlias`;
  - `CatalogFoodSource`;
  - `CatalogImportBatch`;
- contratos internos puros en `food_catalog/application/contracts.py`;
- adaptadores de importación en `food_catalog/application/imports/`;
- lector y mapper USDA Foundation Foods;
- comandos propios:

```text
python manage.py dry_run_catalog_usda_foods_json <path> --source-version <version>
python manage.py import_catalog_usda_foods_json <path> --source-version <version>
```

- admin básico para alimentos, porciones, aliases, fuentes e import batches;
- acciones admin iniciales para pasar registros a revisión, publicación o deprecación;
- protocolo de snapshot desde `CatalogFood` publicado hacia `notas.Food`;
- backfill desde alimentos operacionales confiables hacia candidatos maestros;
- tests de contratos, modelos, importadores, comandos, admin y frontera MCP.

### Lo que todavía no existe o está incompleto

El siguiente ciclo debe asumir explícitamente que todavía faltan capacidades importantes:

- integración FatSecret real;
- integración Open Food Facts real;
- flujo Brand Verified real;
- seed natural curado y revisable para lanzamiento;
- workflow robusto de curación y publicación;
- deduplicación avanzada;
- reglas fuertes de licencia, atribución y persistencia por proveedor;
- cache/referencia externa temporal para proveedores no persistibles;
- validación semántica de alimentos críticos:
  - crudo vs cocido;
  - seco vs hidratado;
  - con sal vs sin sal;
  - genérico vs marca;
  - sólido 100 g vs líquido 100 ml;
- UI o consola interna de curación más rica que Django Admin básico;
- búsqueda productiva sobre `CatalogFood` para curadores;
- criterios `solver-ready` confiables propagados hacia `notas.Food`;
- métricas mínimas de búsquedas, selecciones, candidatos y publicaciones.

## Decisión de planificación

El próximo ciclo no debe crear Food Catalog desde cero.

El ciclo debe llamarse y entenderse como una etapa de maduración:

```text
Food Catalog Launch Readiness
```

Su objetivo es llevar la app existente desde una fundación técnica fuerte hacia una capacidad confiable para lanzamiento.

## Tesis del ciclo

El punto débil antes del lanzamiento no es la separación arquitectónica de Food Catalog. Esa frontera ya existe.

El punto débil es operacional y de datos:

```text
¿Con qué alimentos reales, confiables, buscables, atribuibles y utilizables lanzará My Scoope?
```

Por eso el ciclo debe concentrarse en:

- calidad de datos;
- cobertura mínima útil;
- integración controlada con proveedores externos;
- curación interna;
- publicación segura hacia `notas.Food`;
- preparación indirecta para `nutrition_solver`.

## Regla arquitectónica que no debe romperse

La frontera vigente sigue siendo válida:

```text
food_catalog.CatalogFood
    = fuente maestra, curada, trazable, versionada y publicable

notas.Food
    = snapshot operacional estable usado por el producto

Meals / DailyPlans / Programs / Comparators / Proposals / Solver / MCP
    = consumen notas.Food, no CatalogFood directamente
```

Food Catalog puede importar, normalizar, curar y publicar alimentos. El producto operativo usa snapshots explícitos.

## Relación con `nutrition_solver`

El futuro `nutrition_solver` no debe consumir `CatalogFood` directamente.

La relación correcta es:

```text
Food Catalog cura y publica CatalogFood
  -> protocolo de snapshot materializa notas.Food
  -> nutrition_solver recibe candidatos derivados de notas.Food
```

Esto protege:

- planes históricos;
- consistencia de Meals y DailyPlans;
- frontera MCP;
- auditabilidad de propuestas;
- estabilidad ante cambios futuros del catálogo maestro.

El ciclo Food Catalog debe, sin embargo, preparar alimentos operacionales más útiles para el solver mediante:

- porciones default razonables;
- porciones mínimas/máximas;
- step de porción;
- grupos y subgrupos nutricionales;
- flags de confianza;
- calidad de fuente;
- trazabilidad del snapshot;
- posibilidad de excluir alimentos no aptos para optimización.

## Rol estratégico de FatSecret

FatSecret puede ser un proveedor clave para lanzamiento, pero no debe convertirse automáticamente en la base persistida de My Scoope.

La integración debe respetar la diferencia entre:

```text
referencia externa
caché temporal
candidato de curación
CatalogFood propio publicado
notas.Food operacional
```

Rol recomendado:

```text
FatSecret = proveedor externo operativo y fallback de cobertura
Food Catalog = fuente maestra propia y curada
notas.Food = snapshot operacional usado por el producto
```

El sistema debe guardar solamente aquello que los términos/licencia permitan guardar. Los datos no persistibles deben consultarse nuevamente o manejarse como caché temporal según corresponda.

La integración debe contemplar desde el inicio:

- atribución visible cuando se muestre contenido externo;
- límites de persistencia;
- identificadores externos almacenables;
- logs de fetch;
- fecha de consulta;
- separación entre resultado externo y alimento propio;
- camino para convertir alimentos frecuentemente usados en candidatos de curación interna.

## Rol estratégico de Open Food Facts

Open Food Facts debe evaluarse como fuente abierta complementaria, especialmente para:

- productos con barcode;
- ingredientes;
- información de etiqueta;
- candidatos persistibles con trazabilidad;
- contraste con otras fuentes.

No debe reemplazar la curación interna. Debe entrar como proveedor/candidato dentro del flujo de Food Catalog.

## Rol estratégico de marcas

El flujo Brand Verified no necesita partir como portal completo.

La primera versión puede ser operacional e interna:

```text
CSV / formulario / evidencia de etiqueta / autorización
  -> revisión interna
  -> CatalogFood verified/published
  -> snapshot a notas.Food
```

El valor estratégico es construir una fuente local y diferenciada para LATAM/España sin depender únicamente de proveedores externos.

## Objetivo de lanzamiento

Para un lanzamiento cercano, la meta no debe ser una base gigantesca.

Meta realista:

```text
Catálogo propio pequeño, curado y útil
+ FatSecret como proveedor externo operativo
+ proceso de curación para convertir demanda real en catálogo propio
+ frontera estable hacia notas.Food y futuro nutrition_solver
```

Referencia de cobertura inicial deseada:

- 150-300 alimentos naturales curados y revisables;
- productos de marca relevantes agregados de forma progresiva;
- búsqueda externa para cubrir long-tail;
- candidatos creados desde uso real;
- publicación controlada hacia `notas.Food`.

## Ciclo de patches propuesto

### FC-LR-01 · Auditoría documentada y alcance del ciclo

Registrar el estado real de Food Catalog como app existente y declarar explícitamente que el ciclo no crea la app, sino que madura capacidades operacionales para lanzamiento.

Entregables esperados:

- documento de planificación del ciclo;
- actualización del índice de `docs/10_active_cycles/`;
- vínculo desde documentación vigente de Food Catalog hacia el ciclo planificado.

### FC-LR-02 · Curación y publicación robusta

Status: implemented in this cycle.

Fortalecer el flujo de estados de `CatalogFood`.

Objetivo:

```text
candidate / normalized / pending_review / reviewed / verified / published
```

debe convertirse en workflow protegido, no solo en valores de estado.

Capacidades esperadas:

- reglas para publicar;
- bloqueo de publicación si falta evidencia crítica;
- bloqueo si licencia o atribución no permite uso;
- validadores de macros y fuente;
- historial mínimo de revisión;
- tests de transición de estados.

Resultado FC-02:

- se agrega `food_catalog/application/curation.py` como workflow explícito de transición de estados;
- las acciones admin dejan de usar `queryset.update()` para cambios críticos de curación;
- publicación pasa por transición protegida y por el guard de `publication.py`;
- publicación queda restringida a alimentos `reviewed` o `verified`;
- las decisiones de revisión actualizan `reviewed_at` y `reviewed_by` cuando hay usuario autenticado;
- se agregan tests de workflow, publicación y acciones admin.

### FC-LR-03 · Seed natural curado para lanzamiento

Status: implemented in this cycle.

Construir una base propia pequeña, revisable y útil.

Capacidades esperadas:

- dataset/fixture interno de alimentos naturales prioritarios;
- comandos dry-run y apply;
- trazabilidad de fuente;
- categorías y subcategorías;
- porciones default razonables;
- tests de calidad.

Esta etapa debe evitar importaciones masivas no curadas.

Resultado FC-03:

- se agrega el seed empaquetado `food_catalog/data/core_natural_foods_es_cl_v1.json`;
- se agregan contratos/validadores en `food_catalog/application/core_natural_foods.py`;
- se agrega servicio idempotente de aplicación en `food_catalog/infrastructure/core_natural_foods_seed.py`;
- se agregan comandos propios:

```text
python manage.py dry_run_catalog_core_natural_foods
python manage.py apply_catalog_core_natural_foods
python manage.py apply_catalog_core_natural_foods --publish
```

- los alimentos se crean como `natural_verified`, país `CL`, estado `verified`, fuente trazable y licencia interna permitida;
- `--publish` no salta reglas: usa el workflow protegido y el guard de publicación de FC-01/FC-02;
- el seed inicial no pretende ser la base final de 150-300 alimentos, sino el primer bloque curado/idempotente para expandir sin importaciones masivas ciegas.

### FC-LR-04 · Normalización semántica y deduplicación

Mejorar la capacidad de distinguir alimentos que no deben mezclarse.

Casos obligatorios:

- crudo/cocido;
- seco/hidratado;
- con/sin sal;
- con/sin piel;
- genérico/marca;
- presentación comercial vs alimento base;
- idioma/alias sin perder identidad.

Capacidades esperadas:

- reglas de normalización;
- deduplicación más segura;
- señales de posible duplicado;
- tests de casos críticos.

### FC-LR-05 · Provider interface externo

Crear una frontera común para proveedores externos.

Capacidades esperadas:

- contrato base de búsqueda;
- contrato base de detalle;
- DTOs de resultados externos;
- separación entre resultado externo y `CatalogFood`;
- tests de contrato con providers simulados.

### FC-LR-06 · FatSecret como proveedor externo operativo

Status: implemented in this cycle.

Integrar FatSecret como fallback/cobertura externa sin convertirlo en catálogo propio persistido.

Capacidades implementadas hasta FC-06:

- cliente/provider FatSecret lookup-only;
- configuración por environment variables;
- búsqueda externa;
- detalle por IDs externos;
- contratos puros de resultados externos;
- `ExternalFoodReference` para referencias externas seleccionables/temporales;
- `ExternalProviderFetchLog` para auditoría de búsquedas, detalles y servings;
- hashes de payload para trazabilidad sin guardar respuesta nutricional completa;
- expiración/refresco por defecto a 24 horas;
- atribución almacenada como metadata de presentación;
- admin de referencias externas y fetch logs;
- tests con mocks y tests de referencia externa.

Regla protegida:

```text
ExternalFoodReference no crea CatalogFood.
ExternalFoodReference no crea notas.Food.
ExternalFoodReference no vuelve visible el alimento para MCP ni nutrition_solver.
```

### FC-LR-07 · Búsqueda unificada propia + externa

Status: implemented in this cycle.

Agregar una primera búsqueda unificada que muestre primero resultados propios del catálogo maestro y luego resultados externos lookup-only cuando el flujo lo solicite.

Capacidades implementadas:

- búsqueda de `CatalogFood` publicados por nombre, canonical name, marca y aliases;
- contrato `UnifiedFoodSearchItem` para distinguir resultados `catalog` y `external`;
- búsqueda opcional contra proveedores externos compatibles con el protocolo de FC-05;
- registro opcional de `ExternalFoodReference` para resultados externos vistos;
- logging de búsquedas externas mediante `ExternalProviderFetchLog`;
- captura de errores de proveedor sin romper la búsqueda local;
- comando `dry_run_catalog_unified_food_search` para validación manual;
- tests de orden de resultados, referencias externas y fallback ante errores.

Regla protegida:

```text
Búsqueda unificada muestra candidatos.
No crea notas.Food.
No crea CatalogFood desde externos.
No habilita MCP/Solver sobre ExternalFoodReference.
```

### FC-LR-08 · Cola de candidatos para curación

Status: implemented in this cycle.

Crear una cola explícita que convierta demanda de referencias externas en trabajo revisable por curadores, sin convertir resultados externos en catálogo propio ni alimentos operacionales.

Capacidades implementadas:

- modelo `CatalogCurationCandidate`;
- creación/actualización idempotente desde `ExternalFoodReference`;
- criterios mínimos de demanda por `selected_count` o `seen_count`;
- motivo y prioridad inferidos desde uso real;
- admin de candidatos;
- comando `queue_catalog_external_curation_candidates`;
- tests de cola, idempotencia y comando;
- ausencia deliberada de macros/payload nutricional externo en el candidato.

Regla protegida:

```text
ExternalFoodReference -> CatalogCurationCandidate
CatalogCurationCandidate != CatalogFood
CatalogCurationCandidate != notas.Food
```

### FC-LR-09 · Open Food Facts como fuente abierta complementaria

Status: implemented in this cycle.

Integrar Open Food Facts como proveedor abierto complementario, especialmente por barcode/product code, sin convertir resultados externos en `CatalogFood` ni en `notas.Food`.

Capacidades implementadas:

- `OpenFoodFactsProvider` lookup-only;
- búsqueda básica por texto;
- detalle por barcode/product code;
- servings normalizados `per_100g` y `serving` cuando existe porción declarada;
- settings por environment variables;
- comando `dry_run_catalog_openfoodfacts_search`;
- soporte en búsqueda unificada junto a FatSecret;
- registro opcional como `ExternalFoodReference`;
- trazabilidad mediante atribución y hashes, sin payload nutricional persistido;
- tests con mocks.

### FC-LR-10 · Brand Verified Intake mínimo

Crear flujo interno de carga/revisión de productos de marca.

Capacidades esperadas:

- template CSV o carga interna;
- evidencia de etiqueta;
- autorización/fuente;
- status `brand_submitted` -> `verified` -> `published`;
- trazabilidad;
- tests de importación y publicación.

### FC-LR-11 · Búsqueda y consola interna de curación

Crear una experiencia operativa mínima para curar catálogo maestro más allá de Django Admin básico.

Capacidades esperadas:

- búsqueda en `CatalogFood`;
- filtros por status, fuente, calidad, marca y país;
- vista de detalle con evidencia;
- acciones de revisión/publicación;
- identificación de duplicados/candidatos.

### FC-LR-12 · Snapshot operacional solver-ready

Mejorar la información que llega desde `CatalogFood` a `notas.Food` para uso futuro por `nutrition_solver`.

Capacidades esperadas:

- porciones razonables;
- grupo/subgrupo nutricional;
- calidad/confianza de fuente;
- flags de aptitud para optimización;
- metadata de snapshot;
- tests para asegurar que `nutrition_solver` siga consumiendo `notas.Food` y no `CatalogFood`.

### FC-LR-13 · Métricas mínimas para crecimiento de catálogo

Agregar eventos mínimos para medir operación de Food Catalog.

Eventos sugeridos:

```text
catalog_search_performed
catalog_food_published
catalog_food_snapshot_created
external_food_search_performed
external_food_selected
catalog_candidate_created
catalog_candidate_approved
catalog_candidate_rejected
brand_food_submitted
```

Estas métricas alimentarán más adelante el ciclo de Product Intelligence/Admin Analytics.

## Mínimo viable para lanzamiento

Si el tiempo obliga a recortar alcance, el mínimo recomendable es:

```text
FC-LR-02 Curación/publicación robusta
FC-LR-03 Seed natural curado
FC-LR-05 Provider interface externo
FC-LR-06 FatSecret operativo
FC-LR-07 Búsqueda unificada
FC-LR-12 Snapshot solver-ready básico
```

Esto permitiría lanzar con:

- datos propios confiables para alimentos base;
- cobertura externa para alimentos no presentes;
- separación legal/técnica entre proveedor externo y catálogo propio;
- publicación estable hacia `notas.Food`;
- preparación razonable para `nutrition_solver`.

## Riesgos principales

### Riesgo 1 · Confundir proveedor externo con fuente propia

Mitigación:

- separar `ExternalFoodReference`, `CatalogCurationCandidate`, caché temporal y `CatalogFood` publicado;
- documentar persistencia por proveedor;
- tests para evitar importaciones masivas indebidas.

### Riesgo 2 · Publicar alimentos sin curación suficiente

Mitigación:

- reglas de publicación;
- status claros;
- evidencia obligatoria;
- revisión interna.

### Riesgo 3 · Solver sobre datos pobres

Mitigación:

- seed natural curado;
- porciones razonables;
- flags de aptitud para solver;
- snapshot operacional enriquecido.

### Riesgo 4 · Reabrir frontera CatalogFood -> producto operacional

Mitigación:

- conservar regla `notas.Food` como única verdad operacional;
- tests de frontera;
- no exponer `CatalogFood` a MCP ni solver.

## Criterios de cierre del ciclo

El ciclo puede considerarse cerrado cuando:

- Food Catalog tenga un flujo claro para curar y publicar alimentos;
- exista un seed natural propio, revisable y trazable;
- FatSecret funcione como proveedor externo sin confundirse con catálogo propio;
- Open Food Facts o Brand Verified tengan al menos una primera capacidad operativa o queden explícitamente diferidos;
- los snapshots hacia `notas.Food` transporten suficiente metadata para operación y futuro solver;
- existan tests de frontera que impidan que MCP, Solver o producto operativo dependan de `CatalogFood` directamente;
- la documentación vigente refleje qué capacidades son producto real y cuáles siguen siendo planificación.

## Estado de cierre

Cerrado como ciclo de maduración operacional. Quedan mejoras futuras de Food Catalog, pero ya no bloquean el inicio del ciclo `nutrition_solver`:

- UI/consola interna de curación más rica;
- expansión del seed natural hacia 150-300 alimentos;
- pruebas reales con credenciales FatSecret/Open Food Facts;
- operación real del intake de marcas;
- métricas transversales de uso y calidad dentro de Product Intelligence/Admin Analytics.

## Decisiones que podrían convertirse en ADR

Durante la implementación, probablemente convenga crear ADRs específicos para:

- reglas de persistencia y atribución de proveedores externos;
- workflow de curación/publicación;
- seed natural verificado;
- Brand Verified intake;
- metadata solver-ready en `notas.Food`;
- métricas de crecimiento del catálogo.

## Launch Readiness · FC-04

Food Catalog agrega normalización semántica mínima y criterios `solver-ready` sin romper la frontera vigente con `notas.Food`.

Nuevos criterios maestros en `CatalogFood`:

```text
preparation_state = unknown / raw / cooked / dry / hydrated / ready_to_eat
solver_enabled = true/false
solver_min_portion_g
solver_max_portion_g
solver_portion_step_g
```

La intención es evitar errores críticos para optimización nutricional, especialmente mezclar alimentos crudos/cocidos, secos/hidratados o alimentos sin porciones razonables. Un alimento puede seguir siendo curado y publicado con `solver_enabled=False`; solo los alimentos explícitamente habilitados para solver deben tener preparación, grupo alimentario y porciones inferibles/validadas.

El protocolo de snapshot propaga estos datos hacia `notas.Food`, manteniendo la regla:

```text
Food Catalog cura y publica.
notas.Food opera.
nutrition_solver consumirá notas.Food, no CatalogFood.
```

## Launch Readiness · FC-05

Food Catalog agrega la primera integración real de proveedor externo con FatSecret, manteniendo una regla estricta:

```text
FatSecret = lookup externo operativo
CatalogFood = catálogo maestro propio/curado
notas.Food = alimento operacional
```

FC-05 introduce contratos puros para resultados externos y un `FatSecretProvider` de infraestructura. El provider permite buscar alimentos y leer detalles/porciones desde FatSecret, pero no persiste resultados, no crea `CatalogFood`, no crea `notas.Food` y no transforma respuestas externas en snapshots propios.

La configuración queda controlada por environment variables:

```text
FOOD_CATALOG_FATSECRET_ENABLED
FOOD_CATALOG_FATSECRET_CLIENT_ID
FOOD_CATALOG_FATSECRET_CLIENT_SECRET
FOOD_CATALOG_FATSECRET_TOKEN_URL
FOOD_CATALOG_FATSECRET_API_BASE_URL
FOOD_CATALOG_FATSECRET_TIMEOUT_SECONDS
```

También se agrega el comando de verificación manual:

```text
python manage.py dry_run_catalog_fatsecret_search "avena"
```

Este comando solo consulta y muestra resultados externos. No persiste datos.

La persistencia correcta de referencias externas, caché temporal, atribución visible y selección de usuario queda deliberadamente diferida al siguiente patch del ciclo para no mezclar provider externo con modelo de datos propio.

## Launch Readiness · FC-09

FC-09 agrega Open Food Facts como proveedor externo complementario y abierto. La implementación sigue el mismo principio de FC-05/FC-06: Open Food Facts es una superficie de lookup y evidencia externa, no un catálogo propio automático.

Nuevo provider:

```text
food_catalog/infrastructure/external_providers/open_food_facts.py
```

Capacidades:

```text
- búsqueda por texto;
- detalle por barcode/product code;
- mapeo de datos por 100 g;
- mapeo de serving cuando existe serving_quantity;
- atribución estándar;
- settings por environment variables;
- integración opcional en búsqueda unificada;
- tests con mocks.
```

Regla protegida:

```text
Open Food Facts result
  != CatalogFood
  != notas.Food
  != alimento MCP/Solver
```

Si se registra una referencia externa, solo se guarda `ExternalFoodReference` con identificadores, metadatos, atribución, hashes y expiración. La curación posterior sigue pasando por `CatalogCurationCandidate` y revisión humana.

## Launch Readiness · FC-11

Se prioriza el bridge solver-ready antes de completar Brand Verified Intake porque el siguiente ciclo arquitectónico depende de que `nutrition_solver` tenga una fuente operacional estable y segura.

FC-11 implementa el contrato inicial de candidatos de alimentos para optimización desde `notas.Food`, no desde `CatalogFood` ni desde proveedores externos. Esto mantiene la frontera:

```text
CatalogFood = maestro curado
ExternalFoodReference = referencia externa temporal
CatalogCurationCandidate = trabajo pendiente de curación
notas.Food = alimento operacional
nutrition_solver = consumidor futuro de notas.Food
```

Capacidades implementadas:

- query `list_solver_food_candidates` en `notas.application.queries.solver_food_candidates`;
- validación `check_operational_food_solver_ready` sobre `notas.Food`;
- DTO que expone solo `food_id` operacional;
- filtros por `solver_enabled`, estado activo, calidad mínima, preparación explícita, grupo y porciones completas;
- búsqueda por nombre, canonical name, grupo, subgrupo y aliases operacionales;
- comando `dry_run_solver_food_candidates` para inspección manual;
- tests para asegurar que no se expongan IDs de Food Catalog ni referencias externas.

La planificación queda reordenada: FC-10 Brand Verified Intake sigue pendiente, pero FC-11 se adelanta porque habilita la base técnica para el ciclo posterior de `nutrition_solver`.

## Launch Readiness · FC-10

FC-10 implementa el intake mínimo de productos enviados o autorizados por marcas. No se crea todavía un portal de marcas; se habilita una vía interna y controlada mediante CSV.

Capacidades implementadas:

- template CSV interno para productos de marca;
- validación estricta de columnas requeridas;
- rechazo de filas sin `authorization_confirmed`;
- creación/actualización idempotente de `CatalogFood` con `status=brand_submitted`;
- creación de `CatalogFoodSource` con licencia permitida, atribución y evidencia de etiqueta/autorización;
- creación de porción default y aliases;
- comando `import_catalog_brand_foods_csv` con `--dry-run`;
- tests de validación, idempotencia y comando.

Frontera protegida:

```text
Brand CSV
  -> CatalogFood brand_submitted
  -> revisión/curación humana
  -> verified/published si corresponde
  -> snapshot explícito a notas.Food
```

FC-10 no crea `notas.Food`, no publica automáticamente y no convierte un producto de marca en alimento operacional sin revisión posterior.
