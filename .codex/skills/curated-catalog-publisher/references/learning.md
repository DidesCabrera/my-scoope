# Publicador del catálogo curado — memoria de aprendizaje

Revisado: 2026-11-19. Rol definido por Felipe; skill en `pilot`. La operación
previa está documentada, pero la atribución de cada chat a este rol nuevo aún no
se ha auditado.

## Aprendizajes comprobables

- **Cuatro acciones distintas para datos.** Publicar `CatalogFood` revisados,
  construir/aprobar una release inmutable, importar esa versión en un consumidor
  y materializar `notas.Food` son pasos separados. Un candidato o food verificado
  no está disponible para Meals o Solver hasta completar el recorrido. Fuentes:
  `food_catalog/README.md` y
  `docs/40_technical/operations/food_catalog_authority_runbook.md`.
- **Staging precede producción.** El consumidor valida versión, esquema, conteo y
  SHA-256 antes de escribir; la importación es atómica e idempotente. Se promueve
  a producción la misma release aceptada en staging. Una release aprobada no se
  edita: una corrección necesita otra versión. Fuente: runbook de autoridad y
  `docs/10_active_cycles/food_catalog_authority_delivery_cycle.md`.
- **Las imágenes son una vía aparte.** Una asignación visual operacional puede
  prevalecer sobre la imagen central sin modificar nutrientes o snapshots.
  `source_note`, ID de ficha y estado publicado son parte de la trazabilidad.
  El manifiesto solo expone imágenes de fichas globales activas y publicadas con
  materialización pertinente. Fuente:
  `docs/00_current/features/food_visual_assets.md`.
- **Verificación real del cambio remoto.** El hito H9 de `PRJ-PROD-003` demostró
  sustitución del PNG de `Camarón cocido`, cambio de digest y aparición en un
  teléfono compatible sin nueva build. Es evidencia de ese caso, no garantía de
  que un lote posterior esté visible. Fuente: ficha del proyecto en
  `/Users/felipedides/Desktop/MyScoope/OPERACIONES/PORTAFOLIO/proyectos/`.
- **La asignación exacta evita errores.** Los documentos visuales registran
  fichas heredadas, duplicados y alimentos parecidos. Un activo aprobado puede
  quedar sin ficha publicable o requerir asignaciones separadas. Fuente:
  `docs/10_active_cycles/visual_identity_food_icon_corrections_2026-11-15.md`.

## Pendientes de operación

El chat [Creador de Imágenes](codex://threads/01a18dbe-b1dd-7093-ae87-9fa4b1627379)
contiene trabajo vigente de panes; verificar su resultado final y el entorno
antes de reportar publicación. Diseñar y mantener un registro por lote con
aprobación, versión/hash, staging, producción, comprobación en app y reversión.
No reutilizar números o IDs de un informe antiguo como estado vivo.
