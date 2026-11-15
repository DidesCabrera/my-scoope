# Descripciones editoriales de alimentos

Status: active
Estado de ejecución: primer lote editorial versionado. Responsable: Catálogos. Alcance: alimentos globales activos con visibilidad `core` o `extended` disponibles para usuarios en producción. El estado de despliegue se confirma con GitHub Actions y Render.

## Resultado buscado

Cada ficha de alimento muestra un texto breve en español que explica su identidad, su estado de preparación y el aporte que puede hacer dentro de una alimentación variada. El texto no modifica valores nutricionales, elegibilidad del solver ni registros personales.

## Método

1. Reconciliar el inventario operacional visible con el catálogo maestro y registrar identidades, fuentes y excepciones.
2. Redactar un texto individual por identidad alimentaria. Sustentar composición en la fuente del registro y beneficios generales en guías alimentarias institucionales. Evitar promesas terapéuticas y atribuir propiedades solo cuando la evidencia del alimento las respalda.
3. Revisar cobertura, duplicados, variantes crudas/cocidas, ingredientes secos, marcas y seguridad de la formulación. Conservar la fuente y el estado de revisión de cada texto.
4. Exponer solo textos aprobados en el detalle del alimento. Mantener el contenido editorial separado del snapshot nutricional para poder corregirlo sin recalcular comidas o planes.
5. Validar en staging, revisar el lote exacto y su reversión, promover a producción y comprobar la pantalla con el catálogo real.

## Criterios de aceptación

- Un texto aprobado para cada alimento global activo del inventario objetivo, o una excepción documentada.
- Coincidencia por identidad estable y nombre exacto; ningún texto en alimentos personales ni resultados externos temporales.
- Referencias consultables por registro y lenguaje sin afirmaciones clínicas infundadas.
- El cliente móvil ya distribuido puede mostrar el texto mediante el contrato de detalle vigente.
- Conteos de cobertura y comprobación de producción registrados antes de cerrar la iniciativa.

## Inventario y lote preparado

Consulta de solo lectura en Render, 15 de noviembre de 2026:

| Tipo | Alimentos visibles | Evidencia de identidad | Tratamiento editorial |
| --- | ---: | --- | --- |
| Vinculados a `CatalogFood` publicado | 222 | `catalog_ref`, nombre y fuente maestra | Descripción de identidad, preparación y aporte general respaldada por la ficha de composición y guías alimentarias. |
| Heredados sin vínculo al catálogo | 49 | ID operacional y nombre, sin fuente de composición registrada | Texto limitado a la identidad; se explicita cuando faltan presentación, preparación o evidencia. |
| Total | 271 | 271 identidades cotejadas, 0 discrepancias | 271 textos en `food_catalog/data/food_descriptions_v1.json`. |

Los 49 heredados están activos, visibles como `extended` y marcados `is_verified=false`. Entre ellos hay nombres ambiguos (`Alimento`, `Fajita`, `pan`) y suplementos (`Creatina`, `Whey Protein`, `Colageno Hidrolizado`). La iniciativa no convierte esos registros en alimentos verificados ni valida sus valores nutricionales. La ficha `Alimento` indica expresamente que no hay base para atribuirle características o beneficios. Su saneamiento requiere una tarea separada de identidad, fuente y posible reclasificación.

El lote se vincula por `catalog_ref` y nombre exacto para los 222 registros maestros. Los 49 heredados se vinculan por ID operacional y nombre exacto; esta combinación evita que el texto se aplique por accidente a otro alimento tras una reasignación. No se muestran textos en alimentos personales ni en registros inactivos. Los textos se entregan mediante el `subtitle` del detalle móvil vigente, por lo que no se necesita una versión nueva de la app para que la pantalla actual los muestre.

## Segunda fase: sección dedicada en staging

El contrato nuevo conserva `description` en `CatalogFood` y en `notas.Food`, con copia solo en la creación o actualización explícita del snapshot. La migración inicial carga el lote revisado en las identidades exactas de ambos modelos y en los alimentos globales heredados elegibles. La API añade `description` al detalle y mantiene `subtitle` para versiones anteriores de la app. La app nueva presenta **Descripción** al final de la ficha de alimento y usa el subtítulo como respaldo si consulta un servidor anterior. Esta fase se integra únicamente en `origin/staging`; la producción conserva la experiencia anterior hasta una promoción y una publicación móvil posteriores.

La reversión de esta fase consiste en revertir el código de API y app y, si fuera necesario, la migración de esquema. La operación inversa de carga de datos no borra correcciones editoriales realizadas después de la migración. Ningún valor nutricional ni dato personal se modifica.

La reversión es retirar el lote y la consulta editorial del servidor mediante un despliegue del commit anterior; no hay migración ni escritura de datos nutricionales. Antes de cerrar se debe comprobar el despliegue de producción y una muestra de fichas reales de ambos grupos.

## Fuentes marco

- [Guías Alimentarias para Chile](https://inta.uchile.cl/dam/jcr%3A35b9d7e6-32e0-44c9-b77c-409604b35e37/Gu%C3%ADas%20Alimentarias%20para%20Chile_c.pdf)
- [OMS, alimentación saludable](https://www.who.int/news-room/fact-sheets/detail/healthy-diet)
- [USDA FoodData Central, documentación de datos](https://fdc.nal.usda.gov/data-documentation/)

Estas guías respaldan mensajes de alimentación general; la ficha de composición o etiqueta del producto respalda hechos específicos del alimento.
