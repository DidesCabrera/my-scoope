# FCG00-FCG10 · Food Catalog Growth

Status: planned
Date: 2026-07-17
Target branch: `staging`
Baseline inspected: `88f3006` (`Merge pull request #9 from DidesCabrera/feature/food-catalog-observatory`)

## Propósito

Poblar efectivamente el catálogo maestro con alimentos reales, atribuibles y revisables; aprender su operación desde Admin Operations; y validar cada fuente con una muestra pequeña antes de aumentar volumen.

Este ciclo no vuelve a crear Food Catalog ni reemplaza los importadores existentes. Consolida las capacidades ya construidas y cierra sus brechas de operación, trazabilidad y convergencia.

## Estado de partida verificado

La observación desplegada en staging después del PR #9 reportó:

- `CatalogFood`: 0;
- `notas.Food`: 1;
- alimentos operacionales elegibles para backfill: 0.

La inspección de `staging` confirma que ya existen:

- modelos `CatalogFood`, `CatalogFoodSource`, `CatalogImportBatch`, porciones y aliases;
- workflow protegido de curación/publicación y validaciones de publicación;
- protocolo explícito de snapshot `CatalogFood` publicado -> `notas.Food`;
- seed interno idempotente de exactamente 30 alimentos naturales, con dry-run;
- lector, mapper, dry-run e importador persistente de USDA Foundation Foods;
- intake CSV autorizado de marcas, con modo `--dry-run` y batch;
- backfill `notas.Food` -> Food Catalog, con dry-run, límite, muestras y batch;
- lookup, referencias temporales y candidatos de curación para Open Food Facts;
- lookup equivalente de FatSecret, fuera del alcance de este ciclo;
- Admin Operations con cola de curación, transiciones con razón obligatoria, auditoría append-only e inventario completo con métricas de calidad.

Brechas confirmadas:

- el seed crea `CatalogFood` y `CatalogFoodSource`, pero no `CatalogImportBatch`;
- la UI operacional no ejecuta ni registra planes de dry-run/import batches;
- USDA entra con el tipo genérico `external_temporary`, porque el modelo no posee un tipo USDA explícito;
- el flujo manual con evidencia no tiene un intake persistente uniforme;
- Open Food Facts no tiene todavía un camino aprobado de persistencia en `CatalogFood` condicionado por licencia/atribución;
- el backfill puede estar correctamente vacío y necesita distinguir ese resultado de un fallo;
- no existe una prueba de frontera dedicada que demuestre que alimentos privados de usuarios quedan excluidos de promoción automática;
- la observabilidad muestra batches indirectamente por evidencia, pero no constituye todavía un cockpit operacional completo de dry-run, importación y reconciliación.

## Contratos no negociables

1. Ninguna fuente de este ciclo escribe directamente en `notas.Food`.
2. Toda mutación persistible converge en `CatalogFood` + `CatalogFoodSource` + `CatalogImportBatch`.
3. Importar crea o actualiza trabajo de curación; no publica.
4. Publicar cambia el estado maestro; no crea ni refresca automáticamente el snapshot operacional.
5. Picker, Meals, Solver y MCP continúan consumiendo `notas.Food`.
6. Toda mutación de datos exige un dry-run previo sobre los mismos parámetros y artefacto de entrada.
7. Datos sintéticos sólo pueden vivir en tests; nunca se cargan como catálogo real de staging.
8. Cada dry-run, importación, decisión de curación, publicación y snapshot debe registrar actor, razón, fuente, versión, conteos y resultado.
9. Un patch equivale a un commit; no se agrupan patches del ciclo en un mismo commit.
10. No se fusiona un patch con CI fallando ni con una regresión dura de fronteras, permisos, licencias, publicación o snapshots.
11. FatSecret queda explícitamente fuera de FCG00-FCG10: no se modifica, prueba en vivo, importa ni usa como fuente de volumen.

## Definición cuantitativa de éxito del ciclo

Al cierre:

- 100% de los `CatalogFood` creados o actualizados por FCG tienen al menos un `CatalogFoodSource`;
- 100% de esas fuentes persistidas por FCG apuntan a un `CatalogImportBatch` no nulo;
- 100% de los batches mutantes tienen un dry-run correlacionable, actor, razón, versión de fuente, parámetros, conteos y timestamps;
- 0 imports publican automáticamente;
- 0 publicaciones crean snapshots automáticamente;
- 0 alimentos privados de usuario se promueven automáticamente;
- 0 escrituras directas en `notas.Food` desde seed, USDA, marcas, curación manual, backfill u Open Food Facts;
- exactamente 30 filas válidas en el seed interno y exactamente 30 procesadas en su primera aplicación limpia;
- cada fuente nueva supera primero una muestra de staging: USDA 5-10, marcas 3-5, manual 3-5, backfill hasta 10 elegibles y Open Food Facts 3-5 sólo si pasa el gate legal;
- cada muestra logra 0 errores no explicados, 0 fuentes huérfanas, 0 batches huérfanos y 100% de atribución/licencia requerida;
- duplicados de una repetición idempotente: 0 nuevos `CatalogFood`; el batch o resultado debe explicar todos los skips/updates;
- 100% de acciones mutantes desde Admin Operations quedan en auditoría append-only;
- suite dirigida Food Catalog/Admin Operations/fronteras verde y CI completa verde antes de mergear cada patch.

Los conteos de muestra son límites de validación, no metas de volumen. El escalamiento se autoriza por fuente sólo después de dos ejecuciones pequeñas consecutivas sin regresión dura: primera carga y repetición idempotente.

## Patches

### FCG00 · Baseline, contratos y runbook

Objetivo: fijar el estado real, las fronteras y la secuencia operacional antes de cambiar código o datos.

Entregables:

- este documento y su entrada en el índice;
- matriz de capacidades existentes/reutilizables y brechas;
- contrato formal dry-run -> aprobación -> import -> reconciliación;
- queries/checks read-only para baseline y criterios de go/no-go.

Aceptación:

- baseline identifica commit, entorno y conteos;
- ninguna operación de base de datos mutante;
- FatSecret señalado como fuera de alcance;
- revisión explícita de los siete caminos incluidos y de las cinco fronteras de consumo/publicación.

### FCG01 · Trazabilidad convergente de imports

Objetivo: hacer que toda fuente persistible use el mismo sobre operacional sin reemplazar sus adaptadores de dominio.

Entregables:

- identidad/correlación de dry-run y batch;
- metadata común: actor, razón, parámetros normalizados, hash del artefacto, fuente, dataset, versión y resumen;
- `CatalogFoodSource.import_batch` obligatorio por servicio para toda escritura FCG;
- estados terminales confiables, incluyendo fallo y completado con errores;
- migraciones compatibles con filas históricas.

Aceptación:

- tests contractuales para seed, USDA, marcas, manual, backfill y eventual OFF;
- rollback atómico ante error no recuperable;
- ninguna escritura a `notas.Food`;
- repetición explica create/update/skip/fail sin duplicar alimentos.

### FCG02 · Control plane en Admin Operations

Objetivo: aprender y operar el catálogo desde una interfaz staff-only, usando los servicios existentes.

Entregables:

- vista de fuentes, dry-runs y batches;
- formularios guiados por fuente con razón obligatoria y confirmación;
- dry-run separado de apply; apply bloqueado sin dry-run vigente y equivalente;
- detalle de resultados, muestras de errores, reconciliación e historial auditable;
- no exponer secretos ni payloads crudos sensibles.

Aceptación:

- usuario no staff recibe denegación;
- apply sin dry-run, con dry-run vencido o parámetros distintos es rechazado;
- toda acción mutante genera un evento append-only;
- importar desde Admin Operations no publica ni crea snapshot.

### FCG03 · Seed interno de 30 alimentos

Objetivo: poblar la primera base real reutilizando `core_natural_foods_es_cl_v1.json` y su servicio idempotente.

Trabajo requerido:

- envolver el seed existente en `CatalogImportBatch` y correlación de dry-run;
- preservar evidencia, porciones, aliases y estado no publicado;
- remover o bloquear cualquier opción que combine importación y publicación en una misma acción operacional.

Aceptación de staging:

- dry-run: total 30, válidos 30, inválidos 0;
- apply: 30 `CatalogFood`, 30 o más fuentes, un batch terminal, 0 publicados;
- segundo dry-run/apply: 0 alimentos nuevos y resultado idempotente explicable;
- inventario muestra 30 filas y 0 fuentes/batches faltantes.

### FCG04 · USDA, muestra antes de volumen

Objetivo: reutilizar reader, mapper, normalización, calidad e importador USDA de Food Catalog.

Trabajo requerido:

- introducir representación USDA inequívoca en source type/dataset sin romper datos existentes;
- exigir versión, atribución y hash del artefacto;
- seleccionar una muestra real de 5-10 Foundation Foods que cubra crudo/cocido o seco/hidratado;
- revisar deduplicación contra el seed antes de escalar.

Aceptación de staging:

- dry-run y apply con idéntico hash/parámetros;
- 5-10 filas procesadas; 0 errores no explicados; 0 publicados;
- 100% con source, batch, USDA FoodData Central, dataset y versión;
- repetición crea 0 alimentos nuevos;
- revisión humana del 100% de la muestra antes de autorizar un lote mayor.

### FCG05 · Marcas autorizadas

Objetivo: reutilizar el intake CSV existente y endurecer la evidencia de autorización.

Trabajo requerido:

- muestra real de 3-5 productos de una fuente autorizada;
- autorización identificable, evidencia de etiqueta, país, marca y versión de fuente;
- bloqueo si autorización, licencia/uso o evidencia requerida está ausente;
- operación y reconciliación desde Admin Operations.

Aceptación de staging:

- 3-5 productos reales, 100% con autorización y evidencia verificable;
- 0 publicación automática y 0 snapshots;
- 0 filas sin batch/source;
- repetición idempotente: 0 duplicados nuevos;
- revisión humana del 100% de la muestra.

### FCG06 · Curación manual con evidencia

Objetivo: crear un camino explícito para conocimiento curado, sin convertir texto libre o datos ficticios en catálogo.

Entregables:

- intake manual staff-only que requiere razón, referencia de evidencia, licencia/permiso, atribución, versión/fecha y macros;
- dry-run de validación y duplicados;
- batch de tipo manual/admin claramente identificable;
- estado inicial de candidato o pendiente de revisión, nunca publicado.

Aceptación de staging:

- 3-5 alimentos reales con evidencia independiente revisable;
- dos personas o dos pasos diferenciados para crear y revisar/publicar;
- 100% con source y batch, 0 campos críticos de evidencia ausentes;
- 0 publicación o snapshot implícito.

### FCG07 · Backfill operacional y prueba negativa de privacidad

Objetivo: reutilizar el backfill existente para alimentos globales/verificados/activos y demostrar la exclusión de privados.

Entregables:

- criterio de elegibilidad único y documentado;
- reporte separado de global/verificado/activo, duplicado, privado, inactivo y sin evidencia suficiente;
- test de integración con fixtures sintéticas que prueba que un alimento privado jamás se promueve automáticamente;
- batch y auditoría para toda aplicación real.

Aceptación de staging:

- el baseline actual de 0 elegibles es un resultado válido, no un error;
- dry-run inspecciona todos los candidatos y reporta por razón el 100%;
- si aparecen elegibles, primer apply limitado a máximo 10 y revisión humana total;
- 0 privados creados como `CatalogFood` tanto en test como en reconciliación de staging;
- no se altera el `notas.Food` origen.

### FCG08 · Open Food Facts condicionado a licencia y atribución

Objetivo: decidir y, sólo si corresponde, habilitar persistencia reutilizando provider, referencias y cola existentes.

Gate obligatorio antes de código mutante:

- decisión documental de licencia, atribución, share-alike, alcance de campos, retención y exposición;
- aprobación explícita del responsable del producto/datos;
- si el gate no pasa, OFF permanece lookup/reference-only y el patch cierra sin persistir alimentos.

Aceptación si el gate pasa:

- muestra real de 3-5 productos con barcode;
- 100% con licencia, atribución, URL/source id, hashes y batch;
- 0 publicación automática y 0 snapshots;
- repetición crea 0 duplicados;
- inventario identifica inequívocamente el origen OFF.

Aceptación si el gate no pasa:

- 0 `CatalogFood` OFF;
- guard automatizado impide persistencia accidental;
- decisión y razón visibles operacionalmente.

### FCG09 · Escalamiento controlado y aprendizaje operacional

Objetivo: aumentar volumen fuente por fuente sólo con evidencia de muestras sanas.

Entregables:

- checklist go/no-go por fuente;
- límites por batch, rate/timeout cuando aplique y kill switch;
- métricas de create/update/skip/fail, duplicados, calidad, licencia, revisión y publicación;
- cola de remediación en Admin Operations.

Aceptación:

- ninguna fuente escala sin dos ejecuciones pequeñas consecutivas aprobadas;
- error no explicado <= 1% y siempre 0 para violaciones de licencia, privacidad o frontera;
- fuentes huérfanas = 0; batches huérfanos = 0;
- duplicados no resueltos < 1% del lote y bloquean publicación, no necesariamente importación;
- reconciliación post-batch explica el 100% de las filas.

### FCG10 · Publicación, snapshots explícitos y cierre

Objetivo: validar el handoff maestro-operacional sin acoplarlo a importación ni publicación.

Entregables:

- selección manual de una muestra ya revisada para publicar;
- acción de snapshot separada, confirmada y auditable;
- prueba de que consumidores siguen usando `notas.Food`;
- reporte final por fuente, runbook estable y promoción de decisiones durables a `docs/00_current`/`docs/20_decisions`.

Aceptación de staging:

- publicar N alimentos cambia `CatalogFood` publicado en N y `notas.Food` en 0 durante esa acción;
- crear snapshots explícitos para una submuestra M <= N aumenta/actualiza sólo los snapshots esperados;
- Picker, Meals, Solver y MCP resuelven IDs operacionales, no `CatalogFood.id`;
- trazabilidad bidireccional de la submuestra M = 100%;
- prueba negativa: import sin publicación, publicación sin snapshot y privado sin promoción;
- CI completa verde y sin regresión dura antes de cerrar.

## Runbook operacional de staging

Cada fuente debe seguir exactamente esta secuencia:

1. Confirmar commit desplegado, migraciones aplicadas, identidad del operador y ventana de trabajo.
2. Capturar baseline read-only: conteos de catálogo, estados, fuentes, batches, huérfanos, `notas.Food` y elegibles de backfill.
3. Registrar artefacto real, fuente, versión, licencia/permiso, atribución, hash, tamaño de muestra y razón.
4. Ejecutar dry-run sin mutación y guardar el resultado correlacionable.
5. Revisar el 100% de la muestra y resolver todo error no explicado.
6. Obtener aprobación go/no-go; cualquier cambio de archivo, hash, parámetros o versión invalida el dry-run.
7. Ejecutar apply con el mismo alcance y un límite explícito.
8. Reconciliar: `total = created + updated + skipped + failed`, fuentes y batches no huérfanos, estados no publicados y `notas.Food` sin cambios.
9. Repetir dry-run/apply para probar idempotencia antes de escalar.
10. Curar/revisar desde Admin Operations con razón obligatoria.
11. Publicar sólo mediante acción separada; volver a comprobar que `notas.Food` no cambió.
12. Si se requiere disponibilidad operacional, ejecutar un snapshot separado sobre IDs explícitos y reconciliar consumidores.

## Stop conditions

Detener el batch y no escalar si ocurre cualquiera de estos eventos:

- escritura inesperada en `notas.Food`;
- publicación o snapshot implícito;
- alimento privado incluido;
- licencia, atribución, autorización o evidencia ausente/restringida;
- dry-run inexistente, vencido o no equivalente al apply;
- fuente o batch huérfano;
- conteos no reconciliables;
- duplicación no explicada;
- secreto o payload restringido expuesto;
- CI fallando o regresión dura.

La recuperación debe preservar el audit trail. No se corrige una carga borrando evidencia operacional sin una decisión explícita y documentada.

## Orden de ejecución y commits

El orden normal es FCG00 -> FCG10. Cada patch se implementa en un commit independiente con tests y documentación del alcance. Un patch puede cerrar como decisión sin mutación (por ejemplo, OFF bloqueado por licencia), pero no se salta silenciosamente.

FCG00 es únicamente planificación y baseline. Este documento no autoriza ejecutar imports, publicaciones, snapshots ni otros comandos que escriban en base de datos.
