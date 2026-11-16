# Forma de porcionar alimentos

## Clasificación interna

La versión `portioning_review_2026_11_v1` registra cómo se sirve razonablemente cada alimento, de manera independiente de su grupo alimentario, composición de macronutrientes y densidad calórica.

| Valor persistido | Etiqueta | Criterio |
| --- | --- | --- |
| `by_weight` | Porcionable por peso | La cantidad puede ajustarse por gramos o mililitros medidos. |
| `by_unit` | Escalonado por unidades | La cantidad se expresa mejor en piezas o fracciones de pieza. |
| `fixed_pack` | Envase fijo | La cantidad práctica depende de un envase de tamaño definido. |

La propuesta revisada del 16 de noviembre de 2026 asigna las 329 fichas operativas observadas: 264 por peso, 54 por unidades y 11 por envase. Incluye fichas activas, inactivas, globales y personales. Las 222 fichas vinculadas al catálogo también reciben la etiqueta en `CatalogFood`. El conjunto aprobado queda congelado en `shared_kernel/food_portioning.py`; sus identidades usan ID operativo, resumen SHA-256 del nombre exacto, marca global y UUID de catálogo cuando existe. Se omiten nombres personales del código fuente.

Las migraciones solo aplican una asignación cuando la identidad coincide. Para fichas vinculadas se usa el UUID estable del catálogo más el resumen del nombre y la marca global; para fichas sin vínculo, ID operativo más el resumen del nombre y la marca global. Esto permite etiquetar fichas con distintos IDs entre ambientes sin confundir alimentos. Un registro nuevo o no coincidente queda con valor vacío hasta revisión. Las altas y cambios posteriores pueden asignar el modo explícitamente; `portioning_mode_version` registra la versión de la taxonomía. Los snapshots nuevos y sus refrescos copian la etiqueta del catálogo a la ficha operativa. La administración permite ver y filtrar por ella.

La etiqueta se expone como metadato en el perfil del candidato del optimizador. **No modifica por sí sola el tamaño mínimo, máximo o incremento de la porción**: esas restricciones siguen en los campos de porción ya existentes. Para convertir `by_unit` o `fixed_pack` en una restricción numérica se necesitan, por alimento, el peso de la unidad comestible, las fracciones admisibles o el contenido del envase. La propuesta aprobó el tipo, pero no proporciona esos valores para todos los registros; inferirlos produciría porciones incorrectas. Hasta su curación, la clasificación es utilizable para consulta, análisis y futuras reglas del optimizador, sin alterar silenciosamente las cantidades que este ofrece.
