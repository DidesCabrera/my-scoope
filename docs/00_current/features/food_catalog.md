# Food Catalog

## Estado

Feature vigente con historia extensa archivada.

## Concepto

El catálogo de alimentos combina alimentos de usuario, alimentos globales, aliases, trazabilidad y datos nutricionales normalizados.

## Regla actual

La documentación histórica del catálogo está en:

```text
docs/90_archive/food_catalog_history/
```

Esa carpeta puede usarse para entender contexto, pero cualquier implementación nueva debe revisar primero el código actual y las reglas vigentes en `docs/00_current/`.

## Food Catalog App

Decisión vigente: Food Catalog debe evolucionar como una aplicación/sistema independiente dentro de MyScoope.

Su responsabilidad no es solo guardar registros `Food`, sino adquirir, investigar, normalizar, validar, deduplicar, versionar y publicar alimentos confiables para el resto del producto.

El core de Meals, DailyPlans, Programs, Comparators y Proposals no debe depender directamente de fuentes externas como USDA, FatSecret, Open Food Facts, tablas públicas, agentes de IA o planillas de marcas. Todas las fuentes deben entrar primero como candidatos y adaptarse a un contrato canónico interno antes de crear o actualizar alimentos publicados.

La relación correcta es:

```text
Food Catalog App
    produce alimentos maestros/canónicos, trazables y versionados

Protocolos internos
    publican, crean o refrescan snapshots operativos

Nutrition Management App y MCP
    consumen únicamente notas.Food para construir comidas, planes, programas y propuestas
```

## Decisión híbrida vigente

Food Catalog no reemplaza inicialmente al modelo operativo `notas.Food`.

La decisión vigente es híbrida:

```text
food_catalog.CatalogFood
    fuente maestra, curada, versionada, trazable y publicable

notas.Food
    snapshot operativo estable usado por Meals, DailyPlans, Programs, Comparators y Proposals
```

Regla central:

```text
Food Catalog es fuente maestra interna.
notas.Food es la única verdad nutricional operacional.
Meals, DailyPlans, Programs, Proposals, Comparators, Solver y MCP no dependen directamente del catálogo maestro.
```

Esto permite que Food Catalog evolucione como app/sistema propio sin romper el flujo actual de creación de Meals ni alterar planes históricos cuando cambie el catálogo maestro.

## Integración vigente con Nutrition Solver Optimization V2

Desde NSO03–NSO04, Food Catalog también cura una proyección versionada de capacidades para el
solver: forma, roles funcionales multirol, afinidades, tags dietarios, alérgenos, esfuerzo, costo y
confianza por feature. El protocolo de publicación las copia a `notas.Food.solver_capabilities`;
Nutrition Solver sólo consume ese snapshot operacional.

La ausencia de datos sigue siendo explícita. El adaptador puede derivar roles desde macros con una
fuente y confianza menores, pero no inventa afinidades, alérgenos ni restricciones dietarias.

La guía operativa actual está en:

- [Knowledge Center: Food Catalog para el Solver](admin_knowledge/food_catalog.md)
- [Knowledge Center: Nutrition Solver](admin_knowledge/nutrition_solver.md)

Admin Operations expone además una pestaña staff-only de `Inventario y calidad`. Esta vista lee
todos los `CatalogFood` persistidos, muestra sus campos y relaciones, permite filtrar el inventario y
calcula cobertura por grupo, origen, estado, solver y brechas de completitud. La vista es de sólo
lectura y no altera el protocolo de publicación/snapshot.

El MCP tampoco accede a Food Catalog directamente. Si un alimento maestro todavía no fue materializado como `notas.Food`, entonces no está disponible para herramientas MCP ni para propuestas operativas.

Desde Patch 33, Food Catalog cuenta con contratos internos puros en `food_catalog/application/contracts.py`. Desde Patch 34, también cuenta con modelos maestros iniciales en `food_catalog/models.py`. Estos modelos persisten candidatos, alimentos maestros, porciones, aliases, fuentes/evidencia e import batches.

Desde Patch 35, existe un protocolo interno y acotado para materializar un `CatalogFood` publicado como `notas.Food`:

```text
notas/application/services/food_catalog_snapshots.py
```

Este protocolo copia datos y trazabilidad hacia `notas.Food`. No convierte a `CatalogFood` en fuente operacional directa y no se expone a MCP.

Desde Patch 36, los adaptadores puros de importación pasan a Food Catalog:

```text
food_catalog/application/imports/
```

Esto incluye contratos de importación, normalización, validación de calidad y el lector/mapper USDA. `notas` conserva wrappers temporales para no romper comandos existentes, pero esos wrappers no habilitan acceso MCP ni lectura operacional directa desde `food_catalog`.

Desde Patch 37, Food Catalog cuenta con comandos propios y acciones admin iniciales para importar candidatos maestros sin escribir `notas.Food`:

```text
python manage.py dry_run_catalog_usda_foods_json <path> --source-version <version> --limit 5 --reason "Validar muestra USDA"
python manage.py import_catalog_usda_foods_json <path> --source-version <version> --limit 5 --dry-run-batch-id <id> --reason "Aplicar muestra USDA revisada"
```

Estos comandos escriben `CatalogFood`, `CatalogFoodSource` y `CatalogImportBatch`. No materializan alimentos operacionales ni cambian lo que MCP puede ver.

Desde Patch 38, la frontera MCP queda endurecida por contrato y tests: `list_food_catalog` conserva su nombre histórico, pero solo lista alimentos operativos desde `notas.Food`. No acepta ni devuelve IDs maestros de Food Catalog. Si se recibe un campo de trazabilidad como `catalog_food_id`, no debe transformarse en alimento operativo para MCP.

Desde Patch 39, existe un backfill interno para sembrar Food Catalog desde alimentos operativos confiables:

```text
python manage.py backfill_catalog_from_operational_foods --dry-run --limit 10 --reason "Validar elegibles globales"
python manage.py backfill_catalog_from_operational_foods --limit 10 --dry-run-batch-id <id> --reason "Aplicar backfill revisado"
```

Este comando vive en `notas` porque lee `notas.Food`, pero escribe candidatos maestros en `food_catalog`. Solo considera alimentos globales, verificados y activos. No modifica `notas.Food`, no publica automáticamente `CatalogFood` y no cambia la disponibilidad MCP.


## Ciclo Launch Readiness · FC-01

El primer patch del ciclo Launch Readiness refuerza la frontera actual antes de incorporar nuevas fuentes o flujos de producto. La publicación de `CatalogFood` desde admin deja de ser una actualización masiva sin validación y pasa por un guard de publicación en:

```text
food_catalog/application/publication.py
```

Ese guard mantiene la regla vigente: publicar un alimento maestro solo lo vuelve elegible para snapshot operacional posterior. No materializa `notas.Food`, no expone `CatalogFood` a MCP y no cambia la frontera de consumo de Solver, Meals, DailyPlans, Programs ni Comparators.

Condiciones mínimas para publicar desde admin:

```text
- nombre visible y canonical_name presentes;
- data_quality_score suficiente;
- macros principales por 100 g dentro de rangos sanos;
- al menos una fuente trazable;
- al menos una fuente con licencia allowed o needs_review;
- al menos una porción;
- una porción marcada como default.
```

También se ajusta el modo `foodcatalog` de `scripts/export_for_chatgpt.sh` para incluir `docs/10_active_cycles/***`, de modo que los ZIP focalizados del Food Catalog traigan los ciclos activos de planificación.

## Launch Readiness · FC-03

Food Catalog suma un primer seed natural propio, pequeño, revisable e idempotente para preparar la base de lanzamiento sin depender de importaciones masivas no curadas.

Archivos principales:

```text
food_catalog/data/core_natural_foods_es_cl_v1.json
food_catalog/application/core_natural_foods.py
food_catalog/infrastructure/core_natural_foods_seed.py
```

Comandos:

```text
python manage.py dry_run_catalog_core_natural_foods --reason "Validar seed interno de 30 alimentos"
python manage.py apply_catalog_core_natural_foods --dry-run-batch-id <id> --reason "Aplicar muestra validada"
```

El comando `apply` exige un dry-run persistido equivalente y crea o actualiza alimentos maestros `CatalogFood` como `natural_verified` y `verified`, con batch, fuente trazable, porciones default y aliases. Nunca publica ni crea o actualiza automáticamente `notas.Food`. La publicación y la materialización operacional siguen siendo acciones posteriores y separadas.

El seed FC-03 es una base inicial para iterar hacia la meta de lanzamiento de 150-300 alimentos naturales curados, no una base nutricional definitiva ni una sustitución de fuentes externas como FatSecret u Open Food Facts.

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


## Launch Readiness · FC-06

Food Catalog agrega referencias externas y logs de consulta para proveedores como FatSecret sin convertir resultados externos en alimentos propios ni operacionales.

Nuevos modelos:

```text
ExternalFoodReference
ExternalProviderFetchLog
```

`ExternalFoodReference` guarda identificadores externos, metadatos de presentación, atribución, hashes de payload, conteos de uso y fecha de expiración/refresco. No guarda payload nutricional completo y no equivale a `CatalogFood` ni a `notas.Food`.

`ExternalProviderFetchLog` registra búsquedas/detalles/servings consultados a proveedores externos con estado, query, identificadores y hash de payload. Tampoco persiste el cuerpo de respuesta del proveedor.

Regla reforzada:

```text
Resultado FatSecret consultado
  != CatalogFood curado
  != notas.Food operacional
  != alimento disponible para MCP/Solver
```

Estos modelos preparan el uso temporal y trazable de proveedores externos. La conversión posterior hacia candidato de curación, `CatalogFood` publicado o snapshot `notas.Food` deberá ocurrir en patches posteriores mediante flujos explícitos.



## Documentación vigente

- [Food Catalog App](food_catalog/food_catalog_app.md): decisión principal sobre Food Catalog como sistema propio separado del entorno de gestión nutricional y sobre la integración híbrida con `notas.Food`.
- [ADR 0009](../../20_decisions/0009-food-catalog-hybrid-source-snapshot.md): decisión arquitectónica de Food Catalog como fuente maestra y `notas.Food` como snapshot operativo.
- [ADR 0010](../../20_decisions/0010-mcp-operational-food-boundary.md): decisión de frontera MCP: MCP solo consume `notas.Food` y no accede directamente a `food_catalog`.
- [ADR 0011](../../20_decisions/0011-food-catalog-internal-contracts.md): contratos internos puros de Food Catalog antes de crear modelos maestros.
- [ADR 0012](../../20_decisions/0012-food-catalog-master-models.md): modelos maestros iniciales de Food Catalog sin reemplazar `notas.Food`.
- [ADR 0013](../../20_decisions/0013-operational-food-snapshot-protocol.md): protocolo interno de snapshot operacional desde `CatalogFood` publicado hacia `notas.Food`.
- [ADR 0014](../../20_decisions/0014-food-catalog-import-adapters.md): adaptadores puros de importación pasan a Food Catalog con wrappers temporales en `notas`.
- [ADR 0015](../../20_decisions/0015-food-catalog-admin-and-import-commands.md): comandos y acciones admin iniciales de Food Catalog para importar candidatos maestros sin escribir `notas.Food`.
- [ADR 0016](../../20_decisions/0016-mcp-food-boundary-hardening.md): endurecimiento de frontera MCP para que `list_food_catalog` sea solo lectura de `notas.Food`.
- [ADR 0017](../../20_decisions/0017-operational-foods-to-catalog-backfill.md): backfill interno desde `notas.Food` confiable hacia candidatos maestros de Food Catalog.
- [Research FatSecret API](food_catalog/fatsecret_research.md): evaluación inicial de FatSecret como proveedor externo temporal/no canónico mientras no exista permiso explícito de persistencia y atribución aceptable.


## Estado Patch 40

El ciclo de separación Patch 32-40 queda cerrado. Food Catalog existe como app Django independiente para catálogo maestro, mientras `notas.Food` se mantiene como única verdad operacional. MCP no accede a `food_catalog`; solo trabaja con alimentos operativos expuestos desde `notas.Food`.

El siguiente ciclo debería enfocarse en capacidades de curaduría/publicación y no en reabrir la frontera de consumo operacional.

## Ciclo planificado: Launch Readiness

La app `food_catalog` ya existe, pero no debe asumirse como una capacidad de producto completamente lista para lanzamiento. La siguiente etapa planificada está registrada en:

```text
docs/10_active_cycles/food_catalog_launch_readiness_cycle.md
```

Ese ciclo busca madurar la app existente con foco en datos reales, curación, seed natural, proveedores externos, marcas, publicación segura hacia `notas.Food` y preparación indirecta para `nutrition_solver`.

Regla a preservar durante ese ciclo:

```text
Food Catalog cura y publica.
notas.Food opera.
Solver, MCP y producto consumen notas.Food, no CatalogFood directamente.
```


## Launch Readiness · FC-02

El flujo de curación/publicación deja de depender de cambios masivos directos de estado en Django Admin. Los estados existentes de `CatalogFood` ahora se tratan como un workflow protegido mediante `food_catalog/application/curation.py`.

Estados clave del ciclo de curación:

```text
candidate / normalized / pending_review / reviewed / verified / published
```

Las acciones admin de revisión, verificación, publicación, rechazo, deprecación y archivo pasan por reglas explícitas de transición. Publicar un `CatalogFood` requiere además pasar el guard de publicación definido en `food_catalog/application/publication.py`.

La publicación sigue sin crear ni modificar automáticamente `notas.Food`; solo marca un alimento maestro como elegible para el protocolo explícito de snapshot operacional.


### Launch Readiness · FC-05

Se agrega FatSecret como proveedor externo de lookup, no como fuente propia persistida.

La integración incorpora contratos puros de resultados externos y un provider de infraestructura capaz de buscar alimentos y leer detalles/porciones con OAuth2 client credentials.

Regla vigente:

```text
FatSecret result != CatalogFood
FatSecret result != notas.Food
```

FC-05 no crea alimentos ni snapshots desde FatSecret. La persistencia de referencias externas, caché temporal, atribución visible y selección de usuario queda para el siguiente patch.

## Launch Readiness · FC-07

Food Catalog agrega una primera búsqueda unificada de catálogo propio + proveedor externo, sin mezclar responsabilidades.

La búsqueda propia consulta `CatalogFood` publicados como resultados maestros curados. La búsqueda externa puede consultar proveedores lookup-only como FatSecret y devolver resultados externos separados. Si se habilita el registro de referencias, solo se persiste `ExternalFoodReference` con identificadores, atribución, hashes y expiración; nunca se persiste el payload nutricional completo del proveedor.

Regla vigente:

```text
Unified search result
  -> catalog item: CatalogFood publicado, todavía no operacional
  -> external item: ExternalFoodReference opcional, todavía no CatalogFood/notas.Food
```

La búsqueda unificada no reemplaza el protocolo MCP ni la frontera operacional. `nutrition_solver`, MCP y producto operativo siguen consumiendo `notas.Food`; esta capacidad sirve para curación/producto y para preparar una experiencia de búsqueda más amplia sin convertir datos externos automáticamente en alimentos propios.

Nuevo comando de verificación manual:

```text
python manage.py dry_run_catalog_unified_food_search "avena"
python manage.py dry_run_catalog_unified_food_search "avena" --include-fatsecret
```


## Launch Readiness · FC-08

Food Catalog agrega una cola explícita de candidatos de curación basada en referencias externas. Esta capacidad transforma señales de demanda de `ExternalFoodReference` en trabajo revisable por curadores, sin crear alimentos propios ni operacionales automáticamente.

Regla vigente:

```text
ExternalFoodReference vista/seleccionada
  -> CatalogCurationCandidate
  -> revisión humana/fuente/evidencia
  -> recién después podría derivar en CatalogFood
```

`CatalogCurationCandidate` guarda identificadores externos, nombre mostrado, marca, atribución, motivo, prioridad y conteos de demanda al momento de creación. No guarda macros externas ni payload nutricional completo.

Nuevo comando de operación interna:

```text
python manage.py queue_catalog_external_curation_candidates --dry-run
python manage.py queue_catalog_external_curation_candidates
```

Además, el modo `foodcatalog` del script de exportación incluye `notas/application/services/mcp_user_tokens.py` para que el ZIP focalizado pueda cargar `miapp.urls` en validaciones completas sin necesitar un `ROOT_URLCONF` temporal.


## Launch Readiness · FC-09

Food Catalog suma Open Food Facts como proveedor externo complementario, especialmente útil para búsquedas por producto/barcode y contraste con fuentes de etiqueta.

Nuevo provider lookup-only:

```text
food_catalog/infrastructure/external_providers/open_food_facts.py
```

Nuevo comando de verificación manual:

```text
python manage.py dry_run_catalog_openfoodfacts_search "avena"
python manage.py dry_run_catalog_openfoodfacts_search "7801234567890" --detail
python manage.py dry_run_catalog_unified_food_search "avena" --include-openfoodfacts
```

La integración no crea `CatalogFood`, no crea `notas.Food` y no persiste payload nutricional completo. Si la búsqueda unificada registra referencias, solo se guarda `ExternalFoodReference` con identificadores, atribución, hashes y expiración. La conversión hacia catálogo propio sigue requiriendo cola de curación y revisión explícita.

## Launch Readiness · FC-11

Food Catalog agrega el primer bridge operacional `solver-ready` sin romper la frontera arquitectónica:

```text
Food Catalog cura y publica.
notas.Food opera.
nutrition_solver consumirá notas.Food, no CatalogFood.
```

FC-11 introduce una consulta estable en `notas.application.queries.solver_food_candidates` para listar únicamente alimentos operacionales aptos para optimización futura. El contrato expone `food_id` de `notas.Food`, macros por 100 g, grupo/subgrupo, estado de preparación, porciones razonables, calidad, visibilidad y origen operacional (`catalog_snapshot`, `global` o `user`). Deliberadamente no expone `catalog_food_id`, `catalog_food_ref`, `ExternalFoodReference`, IDs de proveedores externos ni payloads externos.

El query filtra alimentos activos, `solver_enabled=True`, con preparación explícita, porciones completas, grupo alimentario, calidad mínima y acceso mediante las reglas vigentes de lectura de `notas.Food`. También se agrega un comando `dry_run_solver_food_candidates` para inspección manual del contrato.

## Launch Readiness · FC-10

Food Catalog agrega un flujo mínimo interno de Brand Verified Intake. Esta capacidad permite cargar productos enviados por marcas mediante CSV curado, con evidencia de etiqueta y autorización explícita, sin crear alimentos operacionales automáticamente.

Regla vigente:

```text
CSV autorizado por marca
  -> CatalogFood status=brand_submitted
  -> CatalogFoodSource con evidencia/autorización
  -> revisión interna
  -> verified/published mediante workflow protegido
  -> snapshot explícito hacia notas.Food si corresponde
```

La importación no crea `notas.Food`, no publica automáticamente y no salta el workflow de curación. Los productos quedan como `source_type=brand_submitted`, con porción default, aliases, fuente trazable y evidencia en `CatalogFoodSource.evidence_payload`.

Nuevo template interno:

```text
food_catalog/data/brand_verified_intake_template.csv
```

Nuevo comando:

```text
python manage.py import_catalog_brand_foods_csv path/to/brand_foods.csv --dry-run --limit 3 --reason "Validar muestra autorizada"
python manage.py import_catalog_brand_foods_csv path/to/brand_foods.csv --limit 3 --dry-run-batch-id <id> --reason "Aplicar muestra autorizada"
```

La curación manual basada en evidencia usa un CSV distinto y nunca acepta texto libre sin referencia, licencia y atribución:

```text
python manage.py import_catalog_manual_foods_csv path/to/manual_foods.csv --dry-run --limit 3 --reason "Validar evidencia manual"
python manage.py import_catalog_manual_foods_csv path/to/manual_foods.csv --limit 3 --dry-run-batch-id <id> --reason "Aplicar evidencia revisada"
```

El escalamiento sobre los límites de muestra (USDA 10, marcas/manual 5, backfill 10) exige una `CatalogImportSourcePolicy` aprobada, máximo explícito, kill switch inactivo y dos applies pequeños gobernados y exitosos. Admin Operations registra aprobación y kill switch con razón obligatoria. OFF y FatSecret no pueden aprobarse dentro de FCG.

## Launch Readiness · cierre del ciclo

El ciclo Food Catalog Launch Readiness queda cerrado después de implementar curación/publicación protegida, seed natural inicial, normalización `solver-ready`, proveedores externos lookup-only, referencias externas temporales, búsqueda unificada, cola de candidatos, bridge operacional para solver e intake mínimo de marcas.

La frontera vigente queda reafirmada:

```text
food_catalog.CatalogFood = maestro curado y versionado
notas.Food = alimento operacional estable
nutrition_solver / MCP / AI Assistant = consumen notas.Food, no CatalogFood
```

Las métricas/eventos de dashboard no se completan dentro de este ciclo. Se difieren al proyecto transversal `Product Intelligence / Admin Analytics`, donde podrán medir Food Catalog junto con Nutrition Solver, AI Assistant, costos, propuestas y uso real del producto.

Con este cierre, Food Catalog ya no bloquea el inicio de la separación progresiva de `nutrition_solver`; el solver debe iniciar consumiendo candidatos operacionales desde `notas.application.queries.solver_food_candidates`.
