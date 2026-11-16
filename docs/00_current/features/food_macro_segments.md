# Segmentos internos de composición calórica de alimentos

## Estado y finalidad

La regla `macro_kcal_7centers_2026_11_v1` clasifica cada alimento en A–G según
el reparto de calorías calculadas de proteínas (P), carbohidratos (C) y grasas
(F). Es una etiqueta interna para describir el perfil del alimento y preparar
futuras decisiones del solver. No cambia por sí sola elegibilidad, porciones,
objetivos ni recomendaciones nutricionales.

La regla fue ajustada sobre los 157 alimentos del snapshot de staging
`evaluation/foods_staging_2026-11-solver-v1.json`, capturado el 2026-11-11.
Cada alimento tuvo el mismo peso. Se probaron entre 2 y 13 centros; siete
separan patrones interpretables sin los grupos de uno o dos alimentos que
aparecen al forzar trece. Estos centros describen esa muestra, no representan
necesariamente todos los alimentos futuros ni la distribución de producción.

| Segmento | Centro P | Centro C | Centro F | Alimentos en muestra |
| --- | ---: | ---: | ---: | ---: |
| A | 8,1 % | 87,8 % | 4,1 % | 67 |
| B | 23,6 % | 68,7 % | 7,6 % | 36 |
| C | 37,4 % | 48,2 % | 14,3 % | 15 |
| D | 82,4 % | 7,7 % | 9,9 % | 12 |
| E | 43,8 % | 6,5 % | 49,7 % | 9 |
| F | 21,1 % | 11,7 % | 67,2 % | 12 |
| G | 2,9 % | 3,4 % | 93,7 % | 6 |

Los valores exactos e inmutables de v1 viven en
`shared_kernel/food_macro_segments.py`; los porcentajes de la tabla están
redondeados solo para lectura.

## Cálculo y límites

Con los gramos de macronutrientes en una misma base de cantidad, se calculan
`(4P, 4C, 9F)` kcal y se divide cada componente por su suma. Se asigna el
centro A–G con menor distancia euclidiana cuadrada entre los tres porcentajes.
Las fronteras están a igual distancia de dos centros; un empate exacto se
resuelve por orden alfabético. La regla cubre toda composición válida con
aporte positivo de al menos un macronutriente.

La base puede ser 100 g, 100 ml o una porción: una escala uniforme no cambia
las proporciones. Las calorías declaradas en la etiqueta no sustituyen la suma
4/4/9 porque pueden incluir fibra u otros aportes. Si falta un valor, es
negativo, no finito o los tres aportes son cero, el segmento queda vacío;
vacío no significa A ni una composición equilibrada.

## Persistencia y actualización

`CatalogFood` y `notas.Food` guardan `macro_segment` y
`macro_segment_version` de forma independiente. Las migraciones 0025 del
catálogo y 0105 de `notas` calculan la etiqueta para todos los registros
existentes, incluidos candidatos y alimentos de usuario. Nuevos registros y
ediciones normales de macronutrientes la recalculan. Los cambios de otros
campos no alteran la etiqueta. Las escrituras masivas directas que omitan
`save()` requieren recalcularla explícitamente.

Un cambio en `CatalogFood` no reescribe automáticamente el alimento operativo:
la nutrición y la clasificación llegan a `notas.Food` mediante el protocolo de
snapshot explícito. El solver puede leer la etiqueta del alimento operativo,
pero v1 no introduce todavía una decisión de optimización basada en ella.

El segmento es distinto de `myscoope_group` y de `food_group`: aquellos
identifican el tipo de alimento; este describe exclusivamente la composición
calórica relativa. Una clasificación A–G no prueba que el alimento aporte una
cantidad absoluta alta de algún macronutriente por porción.

## Limitaciones y evolución

La asignación por centro más cercano siempre produce una letra para una
composición válida, incluso lejos de los alimentos observados. Antes de usar
la etiqueta como restricción o objetivo del solver hay que evaluar cobertura
fuera de la muestra, distancia al límite, variabilidad de la fuente nutricional
y efectos en los escenarios de optimización. Una recalibración crea una nueva
versión de la regla y una migración o recálculo explícito; no se alteran los
centros de v1 en silencio.
