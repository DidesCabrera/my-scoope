# Primera versión de curación de los 219 alimentos para el solver

Fecha: 2026-11-11. Estado: lote preparado y probado en una copia local; **sin aplicación al catálogo vivo, sin publicación ni actualización de snapshots**.

## Catálogo y cobertura

El catálogo autoridad de My Scoope en Render tiene 222 alimentos publicados: los 219 originales y tres registros del piloto de completo italiano. De los 219 originales, 30 están habilitados para el solver y 189 no. La base local conserva los mismos 219 alimentos por identidad de fuente y nombre, pero usa otros `catalog_ref`; tres porciones predeterminadas también difieren. Los cuatro valores principales por 100 g (energía, proteínas, carbohidratos y grasas) coinciden en los 219. Por ello el comando de preparación empareja por `source_food_id` y nombre, exige fuente autorizada, URL, estado de preparación y porción esperada, y conserva los valores editoriales vivos de leche entera, leche semidescremada y aceite de oliva.

El lote cubre los 219 originales. Propone roles, afinidades, etiquetas dietarias, porciones y límites explícitos; añade un alérgeno **positivo** cuando la identidad lo permite. Una lista vacía de alérgenos sigue significando *no evaluado*: los consumidores que reciben alergias declaradas excluyen estos perfiles. No modifica macronutrientes, estado de preparación, licencias, identidad ni los tres alimentos piloto.

| Resultado tras aplicar el lote al catálogo autoridad | Alimentos |
|---|---:|
| Candidatos directos que pasan la validación de preparación y porciones | 157 (30 existentes, 127 nuevos) |
| Requieren una preparación comestible con nutrición y rendimiento documentados | 52 |
| Ingredientes de receta; no son porciones independientes | 10 |
| Total curado | 219 |

Los 62 últimos mantienen `solver_enabled=false`. Activarlos como alimentos independientes permitiría proponer carne o legumbres crudas, o un plato de ajo/cebolla; eso falsearía la minuta. Están clasificados y conservados para una futura ruta de preparaciones/recetas, pero **todavía no están disponibles como candidatos directos del solver**.

## Fuentes y verificación

- Los 189 alimentos importados de [USDA FoodData Central SR Legacy](https://fdc.nal.usda.gov/data-documentation/) tienen FDC ID, URL, macros por 100 g y fuente CC0 registrados. SR Legacy es la edición final de abril de 2018; la descarga oficial sigue disponible en [FoodData Central](https://fdc.nal.usda.gov/download-datasets/).
- El 2026-11-11 se descargó el archivo oficial `FoodData_Central_sr_legacy_food_json_2018-04.zip` (SHA-256 `0fe8ae486a2c8eb42cb96413f058deb51863a46c8fb8eeb4b1fb45006dd338ef`). El verificador reproducible `verify_solver_usda_sr_legacy.py` cotejó por FDC ID **189/189 fichas**, **528/528 medidas** y **1299 valores nutricionales presentes** contra la evidencia de la base local: **0 diferencias**. Esto incluye el campo `amount` corregido señalado en el [registro de cambios de USDA](https://fdc.nal.usda.gov/log/).
- Tres alimentos (habas cocidas, palmito crudo y tempeh cocido) sólo tienen 100 g como base nutricional en la evidencia. Se usan como peso flexible, sin inventar una medida doméstica.
- Las medidas de cuarto de taza para higo, ciruela y damasco secos se derivan del peso USDA de una taza dividido por cuatro; esa cantidad equivale a media porción de fruta en la [guía adulta de USDA MyPlate](https://www.myplate.gov/sites/default/files/2023-04/1800-calories-ages-14-plus-years.pdf). La derivación se guarda como fuente de la nueva medida.
- La [guía de alérgenos de FDA](https://www.fda.gov/food/nutrition-food-labeling-and-critical-foods/food-allergies) orienta las etiquetas positivas. No se infiere ausencia de alérgenos, ni contacto cruzado, de una ficha genérica. Los productos de marca requerirán su propia etiqueta.

Los roles culinarios, afinidades y límites de optimización son **política interna candidata**, no afirmaciones de USDA. El archivo `solver_219_first_pass_v1.csv` conserva la fuente, valor anterior, valor propuesto y razón por alimento. `catalog_ref` allí identifica la copia local; para aplicar en otro entorno se usa el FDC/source ID, nombre y las comprobaciones de identidad del comando.

## Comprobaciones realizadas

- En una copia local con los IDs originales, el comando creó un lote de 219 alimentos y 1930 propuestas; 1930 válidas y 0 inválidas.
- En otra copia que reproduce los IDs distintos y las tres porciones editoriales del catálogo vivo, el lote volvió a validar 1930/1930. La aplicación local dejó 157 alimentos habilitados y listos, 62 deshabilitados y una versión nueva para los 219.
- Se comprobó que el cambio de versión permite refrescar un snapshot operacional. La aplicación del lote por sí sola no publica una release ni toca `notas.Food`.
- Pasaron 36 pruebas enfocadas de enriquecimiento, reversión de porciones, readiness, consulta del solver y snapshots. La reversión restaura los valores y la porción anterior y retira las medidas derivadas que el lote creó; si esa medida cambió después de aplicarse, la reversión se bloquea para evitar borrar una edición posterior.

## Para ponerlos a disposición del solver

1. Integrar el código y el dataset en la autoridad de Food Catalog.
2. Ejecutar el comando `prepare_solver_food_v1 --environment staging` contra esa autoridad y revisar el lote exacto, el número de propuestas y sus excepciones. Aplicar sólo el lote validado.
3. Construir y publicar una release nueva; importarla en staging y producción para refrescar explícitamente los snapshots operacionales. Verificar 157 candidatos directos por fuente y los filtros de alergia. Registrar la versión y el lote para reversión.
4. Para los 52 que exigen cocción y los 10 componentes, definir preparaciones o recetas con gramajes, nutrición y rendimiento sustentados; entonces podrán participar en el solver por esa ruta sin presentarse como alimentos listos para comer.

La matriz `solver_219_local_audit_2026-11-11.csv` conserva el diagnóstico inicial por registro. La publicación exige una comprobación de calidad de minutas generadas, además de la validación de campos.
