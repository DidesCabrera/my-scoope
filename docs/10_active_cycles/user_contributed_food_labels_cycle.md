# Aportes voluntarios de etiquetas para Food Catalog

Status: planned · propuesto para `catalog-curation-steward` · 2026-11-15
Patrocinador: Felipe Dides
Proyecto relacionado: `PRJ-PROD-003 — Curación de Catálogos`

## Resultado buscado

Convertir fotografías de etiquetas y valores confirmados que los usuarios deciden compartir en **candidatos de curación** trazables. El especialista podrá revisar la evidencia, corregir o descartar candidatos y preparar lotes para Food Catalog. Ningún aporte modifica por sí solo el catálogo global ni se publica automáticamente.

## Punto de partida y frontera

La captura guarda un alimento privado `notas.Food`. La opción de compartir, apagada por defecto, añade al `FoodLabelCaptureReceipt` un `curation_payload` de valores confirmados, una copia JPEG recodificada sin metadatos, un hash y la fecha del aporte. La foto personal que el usuario decide guardar es independiente. Desactivar la opción detiene solo aportes futuros. No se ha verificado que haya contribuciones reales en staging o producción.

La autoridad de Food Catalog vive en otra base de datos. Hoy no hay extracción ni cola que lleve estos recibos a esa autoridad. `CatalogCurationCandidate` atiende referencias de búsqueda externa y no debe recibir estos aportes por una adaptación implícita. El tipo `user_created` existente tampoco convierte un alimento privado en fuente aprobada.

```text
foto + valores confirmados + opt-in
  -> FoodLabelCaptureReceipt privado en la aplicación de consumo
  -> [puente gobernado pendiente]
  -> candidato con evidencia en la autoridad central de Food Catalog
  -> revisión humana, deduplicación y decisión registrada
  -> CatalogFood y CatalogFoodSource, solo si se aprueba
  -> publicación, release y snapshot operacional explícitos
```

El último tramo conserva el contrato vigente: `CatalogFood -> release aprobado -> notas.Food -> Meals / Daily Plans / Solver`. El aporte del usuario no salta ninguna de esas fronteras.

## Trabajo del especialista

1. **Establecer el inventario.** Confirmar despliegue, migración y conteos reales por entorno antes de hablar de volumen disponible. Registrar total opt-in, fotos válidas, duplicados aparentes, campos incompletos y antigüedad, sin exponer datos privados en reportes.
2. **Definir criterios de admisión.** Separar producto de marca, alimento genérico y preparación; exigir nombre e identidad suficientes, base por 100 g/ml, porción, nutrientes verificables en foto, fecha/contexto de etiqueta si existen y estado de derechos/uso. Los valores corregidos por el usuario son una transcripción propuesta, no evidencia independiente.
3. **Diseñar el puente.** Proponer una transferencia autorizada desde la base operacional a la autoridad central, con un identificador opaco de recibo, deduplicación, hash de imagen/payload, acceso restringido, registro de lote, reintentos idempotentes y reconciliación. Minimizar datos: no transportar identidad del usuario, alimento privado completo ni información corporal.
4. **Crear una cola de revisión.** Mostrar foto y transcripción lado a lado; permitir cotejo, corrección, rechazo, solicitud de evidencia adicional y detección de coincidencias con `CatalogFood` existentes. Registrar responsable, razón, fuente, versión y decisión. La foto no debe quedar visible en superficies públicas.
5. **Preparar un piloto pequeño.** Seleccionar un lote real y diverso, aplicar la rúbrica, medir utilidad y errores, revisar duplicados y decidir si el intake merece escalar. Un candidato aprobado entra al proceso normal de Food Catalog; publicación y snapshot siguen siendo operaciones separadas.

## Condiciones de cierre del diseño

- La fuente aparece en los registros del área con estado y uso permitido precisos.
- El contrato de transferencia, la retención de imagen y el acceso de curadores están documentados y revisados antes de mover datos entre bases.
- Cada candidato puede rastrearse hasta un recibo opt-in sin revelar al curador datos personales innecesarios.
- La repetición del mismo lote no duplica candidatos; los rechazos y excepciones quedan trazados.
- Una prueba demuestra que aportar datos no crea ni publica `CatalogFood`, no cambia la visibilidad del `notas.Food` privado y no altera los snapshots operacionales.
- El piloto informa conteos de aceptados, rechazados, duplicados y pendientes; todavía no se fija una meta de volumen sin conocer los datos reales.

## Primer siguiente paso

Después de integrar y desplegar la captura, hacer un inventario de solo lectura en staging. Con esa evidencia, el `catalog-curation-steward` preparará la rúbrica y un diseño de intake acotado para revisión antes de implementar transferencias o publicaciones.

Fuentes: `docs/00_current/features/nutrition_label_capture.md`, `docs/20_decisions/0182-on-device-nutrition-label-capture-and-confirmed-private-foods.md`, `docs/20_decisions/0199-central-food-catalog-authority-and-versioned-delivery.md`, `food_catalog/models.py`, `notas/domain/model_modules/food.py`.
