# Protocolo de corrección nutricional del catálogo

Status: current
Date: 2026-11-10
Applies to: alimentos globales entregados por Food Catalog; no autoriza editar alimentos privados

## Regla de autoridad

`CatalogFood` en la autoridad central conserva la ficha curada y su evidencia. Un
release aprobado es inmutable. Cada entorno importa el release a su espejo local
y, con `import_food_catalog_release --materialize`, crea o refresca
`notas.Food`. Esta última es la ficha **operativa vigente**, no un registro
histórico inmutable. Una corrección requiere versión nueva de la ficha y release
nuevo; no se modifica un release aprobado ni se edita `notas.Food` a mano.

No confundir «snapshot operativo» con «snapshot histórico». El primero se
refresca explícitamente; el segundo conserva los valores del evento o de la
decisión original, salvo una operación específica y auditable de su propietario.

## Mapa de propagación

| Superficie | Dato guardado / lectura | Al importar una corrección | Política |
| --- | --- | --- | --- |
| Autoridad `CatalogFood` y espejo local | Ficha, versión, fuentes y nutrientes por 100 g | Nueva versión y release; importación local transaccional | Corregir en autoridad, conservar evidencia y checksum del release anterior. |
| `notas.Food` global | Copia operativa y `catalog_snapshot_payload/version` | Se refresca en el mismo registro mediante materialización | Verificar ID estable, nutrientes, porciones, búsqueda y aptitud Solver. |
| `MealFood` de comidas de biblioteca, Explorar o incrustadas en minutas | FK a `notas.Food`, cantidad; cálculo vivo por referencia | La cantidad no cambia; sus nutrientes pasan a leer la ficha nueva | Reconstruir `Meal.*_cached` y `foods_aggregation_cached`. |
| `DailyPlan.summary_cache` y `Program.summary_cache` | Totales y paneles derivados de comidas | Deben reconstruirse para los padres afectados | El importador con `--materialize` recorre la cadena Food → Meal → DailyPlan → Program dentro de la transacción. Una edición privada usa `update_food`. |
| Solver, MCP, API y búsqueda | Leen el `notas.Food` local activo, no la autoridad en vivo | Lecturas nuevas usan la ficha operativa actual | Verificar con el mismo selector/API que usa la app; propuestas ya guardadas no se reescriben. |
| `PreparationVersion` e `ingredients_snapshot` | Versión nutricional e ingredientes congelados; `PreparationIngredient.food` es un enlace navegable | **No** se recalcula al cambiar un ingrediente | Publicar revisión nueva de la Preparación antes del release; el release rechaza una versión desfasada. Materializar la nueva revisión actualiza las comidas vivas que la usan. |
| `CalendarizedDay.plan_snapshot` y `snapshot_hash` | Identidad, cantidad y nutrición fechadas | No se modifica por una corrección del catálogo | El día pasado/presente y la evidencia conservan historia. Un día futuro sólo cambia por los comandos explícitos de calendario/revisión, con reglas de elegibilidad y rastro antes/después; nunca por un barrido global de catálogo. |
| `CalendarCommitment.foods_snapshot`, `CalendarizationReview.summary_snapshot`, revisiones y eventos | Evidencia fechada o lista de compras guardada | No se modifica | Recalcular una lista de compras requiere una acción explícita; no alterar revisiones/eventos históricos. |
| `SavedComparison.snapshot_payload` y `ShareResource.snapshot` | Comparación guardada o contenido ya compartido | No se modifica | Crear/actualizar una comparación o compartir de nuevo mediante sus flujos; no reescribir destinatarios ni comparaciones previas. |
| `MealCatalogEntry`, `DailyPlanCatalogEntry`, `PinnedDailyPlan` | Enlaces a entidades vivas, no nutrición independiente | Heredan el valor vivo y sus cachés reconstruidas | Verificar al menos una ficha en Explorar, biblioteca y plan fijado si hay referencias afectadas. |

Código propietario: `notas/management/commands/import_food_catalog_release.py`,
`notas/application/services/food_catalog_snapshots.py`,
`notas/application/services/commands/food_commands.py`,
`notas/application/services/cache/{dailyplan_summary,program_summary}.py`,
`notas/application/services/calendarization/snapshots.py` y
`notas/application/services/commands/preparation_commands.py`.

## Preflight de cada lote o corrección

1. Congelar un manifiesto de filas con `catalog_ref`, nombre, estado de
   preparación, base nutricional, porción, fuente/licencia, versión anterior y
   propuesta, motivo, revisor y excepciones. Separar altas de correcciones y
   Preparaciones de Alimentos. No inventar valores para completar filas.
2. Para cada `catalog_ref` existente, resolver el `notas.Food.id` de staging y
   producción. Contar `MealFood` y comidas distintas; por `DailyPlanMeal` y
   `ProgramDay`, contar minutas y programas afectados. Contar las
   `PreparationIngredient` vinculadas y revisar si una nueva revisión de
   Preparación es obligatoria. Inspeccionar días calendarizados por
   `plan_snapshot.meals[*].foods[*].source_food_id` y registros de comparación
   o compartidos si se propone modificarlos. Los conteos de entidades vivas y
   de snapshots se informan por separado: estos últimos **no** son cola de
   actualización automática.
3. Capturar versión y checksum del último release importado por entorno, más
   nutrientes/porciones y totales de una muestra de Food, Meal, DailyPlan y
   Program afectados. Si la magnitud de referencias hace inviable reconstruir
   cachés en una importación transaccional, detener y preparar una operación
   acotada; no saltar la reconstrucción.
4. Decidir y registrar explícitamente: `actualizar_futuros = sí` para fichas
   operativas y composiciones vivas; `reescribir_históricos = no` por defecto.
   Toda excepción histórica necesita alcance, permisos, comunicación a usuarios,
   auditoría, prueba y rollback propios. Nunca usar la corrección del catálogo
   como permiso implícito para esa excepción.

## Ejecución controlada

1. Corregir sólo en la autoridad, mantener procedencia, incrementar
   `catalog_version`, publicar/revisar Preparaciones dependientes y construir
   un candidato nuevo. Validar conteo, checksum y excepciones antes de aprobar.
2. Importar el mismo release con `--dry-run` y luego `--materialize` en
   staging. Comprobar que repetirlo es idempotente. Comparar nutrientes, porción
   y búsqueda; comprobar que las cachés de Meal, DailyPlan y Program afectados
   coinciden con cálculo vivo y que un `CalendarizedDay` preexistente conserva
   `plan_snapshot` y `snapshot_hash`.
3. Sólo después de aceptación en staging, importar **esa misma versión y
   checksum** en producción. Repetir las comprobaciones con una muestra
   representativa y registrar conteos de creados/refrescados/desfasados y
   Preparaciones. No basta con que el despliegue de código esté activo.
4. Ante un error de validación o importación, la transacción no debe dejar
   cambios parciales. Si una versión aprobada resulta nutricionalmente errónea,
   no editarla: corregir en autoridad y publicar una versión nueva. Los
   snapshots históricos permanecen como fueron registrados.

Prueba focal de la cadena viva e historia congelada:
`food_catalog.tests.test_catalog_releases.CatalogReleaseTests.test_new_release_refreshes_live_caches_without_rewriting_calendar_snapshot`.
El runbook de autoridad y release sigue en
`docs/40_technical/operations/food_catalog_authority_runbook.md`.
