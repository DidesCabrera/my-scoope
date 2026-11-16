# Densidad calórica y segmentos internos D1–D6

## Estado y finalidad

La regla `caloric_density_log6_2026_11_v1` guarda una densidad calórica continua y asigna un segmento D1–D6 a cada alimento con datos suficientes. Sirve para ordenar y comparar alimentos por energía por unidad de cantidad. Es independiente de los [segmentos A–G de distribución calórica](food_macro_segments.md) y de los grupos alimentarios `myscoope_group` y `food_group`. No cambia por sí sola la elegibilidad, las porciones ni el objetivo del optimizador, y no es una calificación de calidad nutricional.

## Origen de los seis tramos

El análisis exploratorio utilizó **222 alimentos publicados** del catálogo de noviembre de 2026, con el mismo peso por alimento. Se calculó su densidad con las calorías registradas y se aplicó **k-means unidimensional con seis centros sobre el logaritmo de la densidad positiva**. Esta escala permite distinguir alimentos de densidad baja y alta sin que los valores altos dominen las distancias. La asignación al centro más cercano en la escala logarítmica sitúa cada frontera aproximadamente en el punto medio entre dos centros consecutivos; en la escala original equivale a una media geométrica. Se fijaron después los límites a cuatro decimales para que la regla sea estable y auditable.

| Segmento | Centro aproximado (kcal/unidad) | Alimentos de la muestra | Intervalo exacto de v1 (kcal/unidad) |
| --- | ---: | ---: | --- |
| D1 | 0,1833 | 30 | 0 ≤ d < 0,2558 |
| D2 | 0,3569 | 51 | 0,2558 ≤ d < 0,4865 |
| D3 | 0,6631 | 45 | 0,4865 ≤ d < 0,9477 |
| D4 | 1,3544 | 51 | 0,9477 ≤ d < 2,0540 |
| D5 | 3,1152 | 37 | 2,0540 ≤ d < 4,5314 |
| D6 | 6,5917 | 8 | d ≥ 4,5314 |

Los centros son descriptivos y están redondeados; **los cinco límites exactos de la última columna son los que clasifican**. Un alimento situado exactamente en un límite entra al tramo superior: 0,2558 corresponde a D2 y 4,5314 a D6. La regla cubre cualquier densidad válida no negativa, aunque quede fuera del rango observado en la muestra.

Los centros y conteos registran el resultado del análisis original. No se conserva aquí un snapshot versionado de las 222 filas que permita repetir exactamente el ajuste; por eso la ejecución usa los límites congelados y cualquier reestimación debe tratarse como una nueva versión.

## Cálculo aplicado a cada alimento

La densidad `d` es `kcal por 100 unidades ÷ 100`. Primero se toma la energía declarada o registrada si es finita y no negativa, incluido cero. Si falta o es inválida, se calcula `4 × proteínas + 4 × carbohidratos + 9 × grasas`, con los tres macronutrientes expresados por 100 unidades. El respaldo 4/4/9 exige tres valores finitos y no negativos y un aporte total positivo. Si ninguna fuente sirve, la densidad es nula y el segmento queda vacío; vacío no significa D1.

El valor se guarda con **cuatro decimales** y ese valor guardado se compara con los límites. Por ejemplo, 1,6500 kcal/unidad corresponde a D4. `caloric_density_source` distingue `declared` de `macro_4_4_9`; `caloric_density_version` conserva la versión de la regla.

La unidad configurada es g o ml. Para g, el resultado se expresa en kcal/g. Para ml, se usa la aproximación **1 ml ≈ 1 g** y el resultado es una estimación de kcal/ml, marcada con `caloric_density_estimated = true`. La equivalencia es menos precisa para líquidos como el aceite. No se debe presentar una densidad por ml como medida física exacta mientras la fuente original no confirme su base volumétrica.

## Persistencia, límites y evolución

`CatalogFood` y `notas.Food` conservan la densidad, el segmento, la fuente, la marca de estimación y la versión. Las migraciones 0026 del catálogo y 0106 de `notas` calculan esos campos para los registros existentes. Las altas y ediciones normales recalculan la clasificación. Una escritura masiva que evite `save()` debe recalcularla explícitamente.

Las nuevas fichas operativas copiadas del catálogo conservan también la energía declarada. En una ficha histórica, la migración solo recupera ese dato del catálogo actual si coinciden la identidad, versión, unidad y macronutrientes de su snapshot; en otro caso usa 4/4/9, porque no se conservó la energía declarada original. Los cambios del catálogo llegan a una ficha operativa mediante el refresco explícito del snapshot.

La clasificación es una síntesis: para ordenar alimentos se usa el valor continuo. Los alimentos próximos a un límite pueden cambiar de tramo si cambia la fuente nutricional o la aproximación de volumen. Una recalibración debe crear una versión nueva de la regla y un recálculo explícito; los límites de v1 no se modifican en silencio. Los valores inmutables que ejecuta la aplicación están en `shared_kernel/food_caloric_density.py`.
