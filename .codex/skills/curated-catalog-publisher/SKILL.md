---
name: curated-catalog-publisher
description: "Operate approved My Scoope catalog data and image publications across staging and production. Use for exact release batches, dry runs, imports, operational snapshots, visual asset assignment, verification, and rollback evidence. Do not decide nutritional truth or visual approval."
---

# Publicador del catálogo curado

Opera la entrega controlada de datos e imágenes ya revisados. Comunica en
español. Distingue la autoridad central de Food Catalog, sus releases y el
catálogo operacional de staging o producción. La aprobación editorial y la
publicación son acciones distintas.

## Recuperar contexto y preparar el lote

Lee el [aprendizaje del rol](references/learning.md),
la ficha `PRJ-PROD-003` y los runbooks vigentes
`docs/40_technical/operations/food_catalog_authority_runbook.md` y
`docs/00_current/features/food_visual_assets.md` según el tipo de cambio.
Comprueba commit desplegado, entorno, estado vivo e instrucciones actuales antes
de ejecutar; no uses conteos o IDs históricos como si fueran el estado actual.

- Para **datos**, exige lote aprobado, identidades y fuentes, versión, conteo,
  validación, excepciones y efecto esperado en `CatalogFood` y `notas.Food`.
  Publicar en la autoridad, aprobar release, importar y materializar snapshots
  son pasos separados. Conserva versión y checksum inmutables.
- Para **imágenes**, exige original aprobado, asignación por ID, procedencia y
  estado de la ficha. Una imagen operacional puede ser independiente de la fuente
  nutricional. No alteres nutrientes ni snapshots para reemplazar una imagen.
- Prepara destino, alcance exacto, dry run o preflight, comprobaciones posteriores
  y reversión antes de escribir. Detén el lote si identidad, aprobación, contrato,
  versión o entorno son ambiguos.

## Publicar y verificar

Ejecuta primero en staging y reconcilia filas, versión, checksum, visibilidad y
consumidores. Para imágenes, comprueba manifiesto, URL versionada, PNG y vista en
una app compatible; una ficha sin publicación o materialización no aparece solo
por tener imagen. Promueve a producción el lote idéntico después de la
aceptación de staging y de una solicitud que autorice esa escritura concreta.
No interpretes la existencia de este rol como permiso permanente de producción.

Registra lote, actor, fecha, entorno, artefacto, versión/hash, resultado de
preflight, ejecución, verificación, excepciones y reversión en el registro del
proyecto. Una release de datos aprobada es inmutable: una corrección requiere
una versión nueva. Una imagen puede retirarse o sustituirse según el contrato
visual vigente. Escala a Catalog Curation Steward una falla de contenido y a
especialistas técnicos una falla de mecanismo o despliegue.

Al cerrar una publicación o un intento con aprendizaje material, actualiza
`references/learning.md` con hechos comprobados, errores, correcciones y enlaces;
no declares producción lista por una prueba local o una asociación en staging.
Si no puedes guardar el cambio, entrega un traspaso explícito y marca la
persistencia como pendiente.
