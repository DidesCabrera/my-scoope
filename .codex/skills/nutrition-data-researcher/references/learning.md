# Investigador de datos nutricionales — memoria de aprendizaje

Revisado: 2026-11-19. Rol definido por Felipe; skill en `pilot`. Estas son
conclusiones documentadas de investigaciones previas, no una afirmación de que
el rol ya haya sido medido como tal en chats anteriores.

## Aprendizajes comprobables

- **Cobertura chilena.** Felipe priorizó alimentos distinguibles y usados en
  Chile, como marraqueta, hallulla y reineta. No se ha establecido una única
  base nacional suficientemente completa, confiable y reutilizable. La dirección
  aceptada es construir candidatos con método de varias fuentes y procedencia
  por campo, sin alterar retrospectivamente fichas históricas. Fuente:
  `.codex/team/memory/areas/catalog-operations.md`, decisión 2026-10-30.
- **USDA tiene alcance preciso.** En el lote original de 219 alimentos, 189
  identificadores de USDA SR Legacy 2018-04, 528 medidas y 1299 valores presentes
  se cotejaron contra la descarga oficial con cero diferencias reportadas. Eso
  verifica la correspondencia de esa evidencia, no representatividad chilena ni
  validez de todos los candidatos para el solver. Fuente:
  `food_catalog/data/curation/solver_219_source_assessment_2026-11-11.md`.
- **Estado de preparación importa.** El lote propuso 157 candidatos directos,
  mientras 52 requieren preparación comestible documentada y 10 son componentes
  de receta. Era un lote preparado en copia local, sin publicación de datos vivos
  en ese informe. Fuente: mismo informe, sección de resultados y estado.
- **Vacío no equivale a negación.** Una lista de alérgenos vacía allí significa
  no evaluada, no ausencia confirmada. Un alimento de marca requiere su etiqueta
  específica; la fuente USDA genérica no prueba su formulación. Fuente: informe
  de los 219 y `.codex/team/areas/catalog-operations/source-registry.yaml`.
- **Separar fuente y decisión editorial.** La planilla de porciones de 219 Foods
  fue una superficie de trabajo y aprobación; el JSON versionado registra el
  lote incorporado. Hay que reconciliarla con el `CatalogFood` y `notas.Food`
  actuales antes de llamarla estado vivo. Fuente: `PRJ-PROD-003` y registro de
  fuentes de Catalog Operations.

## Próxima investigación

Construir una matriz de cobertura chilena con identidad, fuente, licencia,
nutrientes, porciones, estado de preparación y conflicto por campo. Los datos de
otro país pueden ser evidencia complementaria con límite geográfico explícito.
El resultado es un dossier para curación; no cambia el catálogo ni la política
del solver por sí solo.
